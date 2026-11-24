from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from clang.cindex import Cursor, CursorKind, Type, TypeKind
from jinja2 import Environment, FileSystemLoader, select_autoescape
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger

from clanguru.cparser import TranslationUnit
from clanguru.mock_generator import FoundFunction, SymbolSelection, parse_sources, select_symbols

SCALAR_CTYPES: dict[TypeKind, str] = {
    TypeKind.BOOL: "ctypes.c_bool",
    TypeKind.CHAR_S: "ctypes.c_char",
    TypeKind.SCHAR: "ctypes.c_byte",
    TypeKind.UCHAR: "ctypes.c_ubyte",
    TypeKind.CHAR_U: "ctypes.c_ubyte",
    TypeKind.SHORT: "ctypes.c_short",
    TypeKind.USHORT: "ctypes.c_ushort",
    TypeKind.INT: "ctypes.c_int",
    TypeKind.UINT: "ctypes.c_uint",
    TypeKind.LONG: "ctypes.c_long",
    TypeKind.ULONG: "ctypes.c_ulong",
    TypeKind.LONGLONG: "ctypes.c_longlong",
    TypeKind.ULONGLONG: "ctypes.c_ulonglong",
    TypeKind.FLOAT: "ctypes.c_float",
    TypeKind.DOUBLE: "ctypes.c_double",
    TypeKind.LONGDOUBLE: "ctypes.c_longdouble",
}


class UnsupportedTypeError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class EnumBinding:
    name: str
    constants: list[tuple[str, int]]


@dataclass
class StructBinding:
    name: str
    fields: list[tuple[str, str]]


ARRAY_KINDS = (TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY)


@dataclass
class FunctionBinding:
    name: str
    restype: str
    argtypes: list[str]
    callback_restype: str
    c_return_type: str
    c_parameters: str
    c_arguments: str


@dataclass
class VariableBinding:
    name: str
    ctype: str
    c_declaration: str


@dataclass
class UnsupportedSymbol:
    kind: str
    name: str
    reason: str


class CTypesMapper:
    """Maps libclang types to ctypes expressions and collects the structs and enums they use."""

    def __init__(self) -> None:
        self.enums: dict[str, EnumBinding] = {}
        self.structs: dict[str, StructBinding] = {}
        self._structs_in_progress: set[str] = set()

    def ctype(self, clang_type: Type) -> str:
        canonical = clang_type.get_canonical()
        kind = canonical.kind
        if kind in SCALAR_CTYPES:
            return SCALAR_CTYPES[kind]
        if kind == TypeKind.ENUM:
            return self._enum(canonical.get_declaration())
        if kind == TypeKind.RECORD:
            return self._struct(canonical.get_declaration())
        if kind == TypeKind.POINTER:
            return self._pointer(canonical.get_pointee().get_canonical())
        if kind == TypeKind.CONSTANTARRAY:
            return f"{self.ctype(canonical.get_array_element_type())} * {canonical.get_array_size()}"
        raise UnsupportedTypeError(f"{kind.name.lower()}_not_supported")

    def _pointer(self, pointee: Type) -> str:
        if pointee.kind in (TypeKind.FUNCTIONPROTO, TypeKind.FUNCTIONNOPROTO):
            raise UnsupportedTypeError("function_pointer_not_supported")
        if pointee.kind in ARRAY_KINDS:
            raise UnsupportedTypeError("pointer_to_array_not_supported")
        if pointee.kind == TypeKind.VOID:
            return "ctypes.c_void_p"
        if pointee.kind == TypeKind.RECORD and pointee.get_declaration().get_definition() is None:
            return "ctypes.c_void_p"
        return f"ctypes.POINTER({self.ctype(pointee)})"

    def _enum(self, declaration: Cursor) -> str:
        name = declaration.spelling
        if not name.isidentifier():
            raise UnsupportedTypeError("anonymous_enum_not_supported")
        constants = [(child.spelling, child.enum_value) for child in declaration.get_children() if child.kind == CursorKind.ENUM_CONSTANT_DECL]
        self.enums[name] = EnumBinding(name, constants)
        return self.ctype(declaration.enum_type)

    def _struct(self, declaration: Cursor) -> str:
        name = declaration.spelling
        if declaration.kind == CursorKind.UNION_DECL:
            raise UnsupportedTypeError("union_not_supported")
        if not name.isidentifier():
            raise UnsupportedTypeError("anonymous_struct_not_supported")
        if name in self.structs or name in self._structs_in_progress:
            return name
        completed_before = len(self.structs)
        self._structs_in_progress.add(name)
        try:
            struct_fields = [self._field(field_cursor) for field_cursor in declaration.type.get_fields()]
        except UnsupportedTypeError:
            # Drop the structs completed meanwhile: they may point to this one.
            for completed in list(self.structs)[completed_before:]:
                del self.structs[completed]
            raise
        finally:
            self._structs_in_progress.discard(name)
        self.structs[name] = StructBinding(name, struct_fields)
        return name

    def _field(self, field_cursor: Cursor) -> tuple[str, str]:
        if field_cursor.is_bitfield():
            raise UnsupportedTypeError("bit_field_not_supported")
        return field_cursor.spelling, self.ctype(field_cursor.type)


def c_declaration(clang_type: Type, declarator: str) -> str:
    """Spell a C declaration; an array's size goes after the name."""
    if clang_type.kind == TypeKind.CONSTANTARRAY:
        return c_declaration(clang_type.get_array_element_type(), f"{declarator}[{clang_type.get_array_size()}]")
    return f"{clang_type.spelling} {declarator}"


def array_element(clang_type: Type) -> Type | None:
    """The element type of an array parameter, which C passes as a pointer; None for other parameters."""
    if clang_type.kind not in ARRAY_KINDS and clang_type.get_canonical().kind not in ARRAY_KINDS:
        return None
    element = clang_type.get_canonical().get_array_element_type()
    if element.get_canonical().kind in ARRAY_KINDS:
        raise UnsupportedTypeError("multidimensional_array_parameter_not_supported")
    return element


def parameter_binding(mapper: CTypesMapper, clang_type: Type, name: str) -> tuple[str, str]:
    """The ctypes argtype and the C parameter declaration of one parameter."""
    element = array_element(clang_type)
    if element is None:
        return mapper.ctype(clang_type), c_declaration(clang_type, name)
    return f"ctypes.POINTER({mapper.ctype(element)})", c_declaration(element, f"*{name}")


def function_binding(mapper: CTypesMapper, cursor: Cursor) -> FunctionBinding:
    function_type = cursor.type
    if function_type.kind == TypeKind.FUNCTIONPROTO and function_type.is_function_variadic():
        raise UnsupportedTypeError("variadic_not_supported")
    result = cursor.result_type.get_canonical()
    if result.kind == TypeKind.RECORD:
        raise UnsupportedTypeError("struct_return_not_supported")
    names = [argument.spelling or f"unnamed{index}" for index, argument in enumerate(cursor.get_arguments(), start=1)]
    parameters = [parameter_binding(mapper, argument.type, name) for argument, name in zip(cursor.get_arguments(), names)]
    restype = "None" if result.kind == TypeKind.VOID else mapper.ctype(result)
    callback_restype = "ctypes.c_void_p" if result.kind == TypeKind.POINTER else restype
    return FunctionBinding(
        name=cursor.spelling,
        restype=restype,
        argtypes=[argtype for argtype, _ in parameters],
        callback_restype=callback_restype,
        c_return_type=cursor.result_type.spelling,
        c_parameters=", ".join(declaration for _, declaration in parameters) or "void",
        c_arguments=", ".join(names),
    )


@dataclass
class BindingContent:
    functions: list[FunctionBinding] = field(default_factory=list)
    variables: list[VariableBinding] = field(default_factory=list)
    mocks: list[FunctionBinding] = field(default_factory=list)
    undefined_variables: list[VariableBinding] = field(default_factory=list)
    unsupported: list[UnsupportedSymbol] = field(default_factory=list)


class BindingGenerator:
    def __init__(
        self,
        source_files: Iterable[Path],
        required_symbols: set[str],
        provided_symbols: set[str],
        output_dir: Path,
        filename: str,
        library_name: str,
        compilation_database: Path | None,
        exclude_symbol_patterns: list[str],
        strict: bool,
    ) -> None:
        self.source_files = list(source_files)
        self.required_symbols = required_symbols
        self.provided_symbols = provided_symbols
        self.output_dir = output_dir
        self.filename = filename
        self.library_name = library_name
        self.compilation_database = compilation_database
        self.exclude_symbol_patterns = exclude_symbol_patterns
        self.strict = strict
        self.env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self) -> None:
        translation_units = parse_sources(self.source_files, self.compilation_database)
        selection = select_symbols(translation_units, self.required_symbols, self.exclude_symbol_patterns, frozenset(self.provided_symbols))
        mapper = CTypesMapper()
        content = self._bind(mapper, selection)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.output_dir / f"{self.filename}.log"
        failed = self.strict and bool(selection.missing)
        log_file.write_text(self._report(translation_units, selection, content, "failed" if failed else "success"))
        if failed:
            raise UserNotificationException(f"Binding generation for '{self.filename}' failed. See '{log_file}' for details.")

        headers = sorted({symbol.origin.header_file for symbol in selection.found if symbol.origin.header_file})
        mocks_source = self.env.get_template("bind/mocks.c.j2").render(headers=headers, variables=content.undefined_variables, functions=content.mocks)
        (self.output_dir / f"{self.filename}_mocks.c").write_text(mocks_source)
        binding = self.env.get_template("bind/binding.py.j2").render(
            library_name=self.library_name,
            enums=list(mapper.enums.values()),
            structs=list(mapper.structs.values()),
            functions=content.functions,
            variables=content.variables,
            mocks=content.mocks,
        )
        (self.output_dir / f"{self.filename}.py").write_text(binding)
        logger.info(f"Binding written to {self.output_dir / f'{self.filename}.py'}")

    def _bind(self, mapper: CTypesMapper, selection: SymbolSelection) -> BindingContent:
        content = BindingContent()
        defined_names = {symbol.name for symbol in selection.defined}
        for symbol in selection.defined + selection.found:
            cursor = symbol.origin.symbol.origin.raw_node
            is_function = isinstance(symbol, FoundFunction)
            is_defined = symbol.name in defined_names
            try:
                binding = function_binding(mapper, cursor) if is_function else VariableBinding(symbol.name, mapper.ctype(cursor.type), c_declaration(cursor.type, symbol.name))
            except UnsupportedTypeError as error:
                content.unsupported.append(UnsupportedSymbol("function" if is_function else "variable", symbol.name, error.reason))
                continue
            if isinstance(binding, FunctionBinding):
                (content.functions if is_defined else content.mocks).append(binding)
                continue
            content.variables.append(binding)
            if not is_defined:
                content.undefined_variables.append(binding)
        return content

    def _report(
        self,
        translation_units: list[TranslationUnit],
        selection: SymbolSelection,
        content: BindingContent,
        status: str,
    ) -> str:
        def section(title: str, entries: list[str]) -> list[str]:
            return [f"{title}:", *[f"  {entry}" for entry in entries or ["(none)"]], ""]

        lines = [
            f"binding generation report for: {self.filename}",
            "",
            *section("sources", [f"{tu.source_file} : {tu.parsing_error() or 'OK'}" for tu in translation_units]),
            *section("bound functions", [function.name for function in content.functions]),
            *section("bound variables", [variable.name for variable in content.variables]),
            *section("python mocks", [mock.name for mock in content.mocks]),
            *section("undefined variables", [variable.name for variable in content.undefined_variables]),
            *section("unsupported symbols", [f"{symbol.kind} {symbol.name} : reason={symbol.reason}" for symbol in content.unsupported]),
            *section("excluded symbols", [f"{name} : reason=excluded_by_pattern" for name in selection.excluded]),
            *section("missing symbols", [f"{name} : reason=undefined_without_declaration" for name in selection.missing]),
            *section("defined symbols without declaration", selection.defined_missing),
            f"status: {status}",
        ]
        return "\n".join(lines) + "\n"
