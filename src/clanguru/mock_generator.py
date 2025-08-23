from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, TypeAlias, runtime_checkable

from jinja2 import Environment, FileSystemLoader, select_autoescape
from py_app_dev.core.exceptions import UserNotificationException

from clanguru.compilation_options_manager import CompilationOptionsManager
from clanguru.cparser import CLangParser, Function, TranslationUnit, Variable


@dataclass
class FoundSymbol:
    translation_unit: TranslationUnit
    symbol: "Decl"
    header_file: str | None


@dataclass
class FoundVariable:
    name: str
    type: str
    origin: FoundSymbol

    def is_constant(self) -> bool:
        t = self.type.strip()
        return t.startswith("const ") or t.endswith(" const")

    def get_definition(self) -> str:
        return f"{self.type} {self.name}".strip()

    def initializer(self) -> str:
        t = self.type.strip()
        if self.is_constant() and (t.startswith("struct ") or t.endswith("_t")):
            return f"({t}){{0}}"
        if "[" in t and "]" in t:
            return "{0}"
        if t.endswith("*"):
            return f"({t})0"
        if t.startswith("struct "):
            return f"({t}){{0}}"
        if t == "void":
            return "void"
        return f"({t})0"


@dataclass
class FunctionArgument:
    name: str
    type: str
    is_const: bool = False
    is_pointer: bool = False
    is_reference: bool = False
    is_variadic: bool = False


@dataclass
class FoundFunction:
    name: str
    return_type: str
    parameters: list[FunctionArgument]
    origin: FoundSymbol

    def get_param_types(self) -> str:
        parts: list[str] = []
        unnamed_index = 1
        for p in self.parameters:
            ptype = " ".join(p.type.split())
            pname = p.name or f"unnamed{unnamed_index}"
            if not p.name:
                unnamed_index += 1
            if ptype.endswith("[]"):
                parts.append(f"{ptype[:-2]} {pname}[]")
            else:
                parts.append(f"{ptype} {pname}".strip())
        return ", ".join(parts)

    def has_return_value(self) -> bool:
        return (self.return_type or "void") != "void"

    def default_return(self) -> str:
        rt = self.return_type or "void"
        if rt == "void":
            return "void"
        if rt.endswith("*"):
            return f"({rt})0"
        if rt.startswith("struct "):
            return f"({rt}){{0}}"
        return f"({rt})0"

    def get_call(self) -> str:
        args = []
        unnamed_index = 1
        for p in self.parameters:
            name = p.name or f"unnamed{unnamed_index}"
            if not p.name:
                unnamed_index += 1
            args.append(name)
        return f"{self.name}({', '.join(args)})"

    def get_signature(self) -> str:
        param_types = self.get_param_types()
        return f"{self.return_type or 'void'} {self.name}({param_types})" if param_types else f"{self.return_type or 'void'} {self.name}()"


Decl: TypeAlias = Function | Variable


def find_symbols(translation_units: list[TranslationUnit], symbols: set[str]) -> list[FoundSymbol]:
    """Find given symbols inside translation units and detect their external declarations in included headers."""
    if not translation_units or not symbols:
        return []

    results: list[FoundSymbol] = []
    for tu in translation_units:
        file_path = str(tu.source_file)
        # Collect all declarations (functions + variables) for requested symbols
        declarations: list[Decl] = [
            *[f for f in CLangParser.get_functions(tu) if f.name in symbols],
            *[v for v in CLangParser.get_variables(tu) if v.name in symbols],
        ]

        # Group by name
        grouped: dict[str, list[Decl]] = {}
        for decl in declarations:
            grouped.setdefault(decl.name, []).append(decl)

        for name in sorted(grouped):  # deterministic within TU
            decls = grouped[name]
            definition: Decl | None = None
            header_file: str | None = None
            for decl in decls:
                loc_file = getattr(decl.origin.raw_node.location.file, "name", None)
                if isinstance(decl, Function):
                    if decl.is_definition and loc_file == file_path:
                        definition = decl
                else:  # Variable
                    is_def = getattr(decl.origin.raw_node, "is_definition", lambda: True)()
                    if is_def and loc_file == file_path:
                        definition = decl
            # Find external declaration in header (different file than TU source)
            for decl in decls:
                loc_file = getattr(decl.origin.raw_node.location.file, "name", None)
                if loc_file and loc_file != file_path:
                    # For functions ensure it's not the definition.
                    if isinstance(decl, Function) and decl.is_definition:
                        continue
                    header_file = loc_file
                    break
            symbol = definition or decls[0]
            results.append(FoundSymbol(translation_unit=tu, symbol=symbol, header_file=header_file))
    # Ensure global deterministic ordering by symbol name then TU path
    results.sort(key=lambda r: (r.symbol.name, str(r.translation_unit.source_file)))
    return results


def extract_symbols_data(symbols: list[FoundSymbol]) -> list[FoundVariable | FoundFunction]:
    data: list[FoundVariable | FoundFunction] = []
    for fs in symbols:
        sym = fs.symbol
        cursor = sym.origin.raw_node
        if isinstance(sym, Variable):
            vtype = cursor.type.spelling.strip() if hasattr(cursor, "type") else ""
            data.append(FoundVariable(name=sym.name, type=vtype, origin=fs))
        elif isinstance(sym, Function):
            f_cursor = cursor
            rtype = getattr(f_cursor, "result_type", None)
            return_type = (rtype.spelling if rtype else "").strip()
            params: list[FunctionArgument] = []
            for arg in getattr(f_cursor, "get_arguments", lambda: [])():
                t = arg.type.spelling.strip() if hasattr(arg, "type") else ""
                params.append(
                    FunctionArgument(
                        name=arg.spelling or "",
                        type=t,
                        is_const=t.startswith("const "),
                        is_pointer="*" in t,
                        is_reference="&" in t,
                        is_variadic=False,
                    )
                )
            is_variadic = False
            try:
                ftype = f_cursor.type
                is_variadic = bool(getattr(ftype, "is_function_variadic", lambda: False)())
            except Exception as exc:  # pragma: no cover
                import logging

                logging.exception("Failed to determine variadic status: %s", exc)
            if is_variadic and params:
                params[-1].is_variadic = True
            data.append(FoundFunction(name=sym.name, return_type=return_type, parameters=params, origin=fs))
    data.sort(key=lambda s: s.name)
    return data


class MockType(Enum):
    GMOCK = "gmock"
    CMOCK = "cmock"


@runtime_checkable
class TemplateRenderer(Protocol):
    def render_all(self, *, data: list[FoundVariable | FoundFunction], missing: list[str]) -> dict[str, str]: ...


class GMockTemplateRenderer:
    def __init__(self, filename: str, output_dir: Path, env: Environment) -> None:
        self.filename = filename
        self.output_dir = output_dir
        self.env = env

    def render_all(self, *, data: list[FoundVariable | FoundFunction], missing: list[str]) -> dict[str, str]:
        variables = [v for v in data if isinstance(v, FoundVariable)]
        functions = [f for f in data if isinstance(f, FoundFunction) and not any(p.is_variadic for p in f.parameters)]
        headers = sorted({f.origin.header_file for f in functions if f.origin.header_file} | {v.origin.header_file for v in variables if v.origin.header_file})
        ctx = {
            "filename": self.filename,
            "variables": variables,
            "functions": functions,
            "headers": headers,
            "missing": missing,
        }
        return {
            f"{self.filename}.h": self.env.get_template("mock/gmock/header.h.j2").render(**ctx),
            f"{self.filename}.cc": self.env.get_template("mock/gmock/source.cc.j2").render(**ctx),
            f"{self.filename}.log": self._render_log(functions, variables, missing),
        }

    def _render_log(self, functions: list[FoundFunction], variables: list[FoundVariable], missing: list[str]) -> str:
        lines = [f"functions: {len(functions)}", f"variables: {len(variables)}"]
        if missing:
            lines.append("missing: " + ",".join(missing))
        return "\n".join(lines) + "\n"


class MocksGenerator:
    def __init__(
        self,
        source_files: Iterable[Path],
        symbols: Iterable[str],
        output_dir: Path,
        filename: str,
        mock_type: MockType,
        compilation_database: Path | None,
        strict: bool = True,
    ) -> None:
        self.source_files = list(source_files)
        self.symbols = set(symbols)
        self.output_dir = output_dir
        self.filename = filename
        self.mock_type = mock_type
        self.compilation_database = compilation_database
        self.strict = strict
        self.env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
            autoescape=select_autoescape(enabled_extensions=("j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self) -> None:
        tus = self._parse_sources()
        symbols_data = extract_symbols_data(find_symbols(tus, self.symbols))
        missing = sorted(self.symbols - {d.name for d in symbols_data})
        renderer = self._select_renderer()
        rendered = renderer.render_all(data=symbols_data, missing=missing)
        self._write_outputs(rendered)

    def _parse_sources(self) -> list[TranslationUnit]:
        parser = CLangParser()
        compile_commands = CompilationOptionsManager(self.compilation_database) if self.compilation_database else None
        tus: list[TranslationUnit] = []
        for path in self.source_files:
            tu = parser.load(path, compile_commands)
            if (err := tu.parsing_error()) and self.strict:
                raise UserNotificationException(f"Parsing error in {path}: {err}")
            tus.append(tu)
        return tus

    def _select_renderer(self) -> TemplateRenderer:
        if self.mock_type == MockType.GMOCK:
            return GMockTemplateRenderer(self.filename, self.output_dir, self.env)
        raise NotImplementedError("Mock type not implemented")  # pragma: no cover

    def _write_outputs(self, rendered: dict[str, str]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in rendered.items():
            (self.output_dir / name).write_text(content if content.endswith("\n") else content + "\n")
