from dataclasses import dataclass
from typing import TypeAlias

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
