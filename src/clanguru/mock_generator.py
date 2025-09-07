import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, TypeAlias, runtime_checkable

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from mashumaro import DataClassDictMixin
from py_app_dev.core.exceptions import UserNotificationException
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from clanguru.compilation_options_manager import CompilationOptionsManager
from clanguru.cparser import CLangParser, Function, TranslationUnit, Variable


@dataclass
class FileParseResult:
    """Result of parsing a single source file."""

    path: Path
    error: str | None

    @property
    def is_successful(self) -> bool:
        """True if parsing succeeded without errors."""
        return self.error is None


@dataclass
class MockGenerationIssues:
    """Collection of all issues found during mock generation."""

    parse_errors: list[FileParseResult]
    missing_symbols: list[str]
    unsupported_functions: list[str]  # e.g., variadic functions
    excluded_symbols: list[str]  # symbols excluded by patterns

    @property
    def has_any_issues(self) -> bool:
        """True if any issues were found."""
        return bool(self.parse_errors_with_failures or self.missing_symbols or self.unsupported_functions)

    @property
    def parse_errors_with_failures(self) -> list[FileParseResult]:
        """Only parse results that failed."""
        return [result for result in self.parse_errors if not result.is_successful]


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


class MockGenerationReport:
    """Handles creation of detailed mock generation reports."""

    def __init__(self, filename: str, mock_type: MockType, requested_symbols: set[str]) -> None:
        self.filename = filename
        self.mock_type = mock_type
        self.requested_symbols = requested_symbols

    def generate_report(
        self,
        *,
        issues: MockGenerationIssues,
        rendered_functions: list[FoundFunction],
        rendered_variables: list[FoundVariable],
        status: str,
    ) -> str:
        """Generate a comprehensive mock generation report."""
        lines: list[str] = []

        # Header
        lines.extend([f"mock generation report for: {self.filename}", f"mock type: {self.mock_type.value}", ""])

        # Sources section
        lines.append("sources:")
        if not issues.parse_errors:
            lines.append("  (no sources processed)")
        else:
            for result in issues.parse_errors:
                status_text = "OK" if result.is_successful else f"ERROR - {result.error}"
                lines.append(f"  {result.path} : {status_text}")
        lines.append("")

        # Requested symbols
        requested = sorted(self.requested_symbols)
        lines.extend([f"requested symbols ({len(requested)}):", *[f"  {symbol}" for symbol in requested], ""])

        # Successfully mocked symbols
        lines.append("mocked symbols:")
        if not rendered_functions and not rendered_variables:
            lines.append("  (none)")
        else:
            for func in rendered_functions:
                header_info = func.origin.header_file or "-"
                lines.append(f"  function {func.name} -> header={header_info}")
            for var in rendered_variables:
                header_info = var.origin.header_file or "-"
                lines.append(f"  variable {var.name} -> header={header_info}")
        lines.append("")

        # Skipped symbols
        lines.append("skipped symbols:")
        if not issues.unsupported_functions:
            lines.append("  (none)")
        else:
            for func_name in issues.unsupported_functions:
                lines.append(f"  function {func_name} : reason=variadic_not_supported")
        lines.append("")

        # Excluded symbols
        lines.append("excluded symbols:")
        if not issues.excluded_symbols:
            lines.append("  (none)")
        else:
            for symbol in issues.excluded_symbols:
                lines.append(f"  {symbol} : reason=excluded_by_pattern")
        lines.append("")

        # Missing symbols
        lines.append("missing symbols:")
        if not issues.missing_symbols:
            lines.append("  (none)")
        else:
            for symbol in issues.missing_symbols:
                lines.append(f"  {symbol} : reason=not_found")
        lines.append("")

        # Summary
        lines.extend(
            [
                "summary:",
                f"  functions mocked: {len(rendered_functions)}",
                f"  variables mocked: {len(rendered_variables)}",
                f"  functions skipped (variadic): {len(issues.unsupported_functions)}",
                f"  symbols excluded: {len(issues.excluded_symbols)}",
                f"  symbols missing: {len(issues.missing_symbols)}",
                f"  status: {status}",
            ]
        )

        # Raw issues for debugging
        if issues.has_any_issues:
            lines.extend(["", "issues (raw):"])
            for result in issues.parse_errors_with_failures:
                lines.append(f"  - parse_error:{result.path}:{result.error}")
            for symbol in issues.missing_symbols:
                lines.append(f"  - missing_symbol:{symbol}")
            for func_name in issues.unsupported_functions:
                lines.append(f"  - unsupported_variadic:{func_name}")
            for symbol in issues.excluded_symbols:
                lines.append(f"  - excluded_symbol:{symbol}")

        return "\n".join(lines) + "\n"


@runtime_checkable
class TemplateRenderer(Protocol):
    def render_all(self, *, data: list[FoundVariable | FoundFunction], missing: list[str]) -> dict[str, str]: ...


class GMockTemplateRenderer:
    def __init__(self, filename: str, output_dir: Path, env: Environment) -> None:
        self.filename = filename
        self.output_dir = output_dir
        self.env = env

    def render_all(self, *, data: list[FoundVariable | FoundFunction], missing: list[str]) -> dict[str, str]:
        # NOTE: filtering of unsupported (e.g. variadic) functions is expected to
        # be handled by the caller (MocksGenerator). We keep an extra guard here
        # to avoid generating invalid mocks if used directly somewhere else.
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
        }


@dataclass
class MocksGeneratorConfig(DataClassDictMixin):
    strict: bool = True
    exclude_symbol_patterns: list[str] | None = None
    mock_type: MockType = MockType.GMOCK

    @classmethod
    def from_file(cls, config_file: Path) -> "MocksGeneratorConfig":
        config_dict = cls.parse_to_dict(config_file)
        return cls.from_dict(config_dict)

    @staticmethod
    def parse_to_dict(config_file: Path) -> dict[str, Any]:
        try:
            with open(config_file) as fs:
                config_dict = yaml.safe_load(fs)
                # Add file name to config to keep track of where configuration was loaded from
                config_dict["file"] = config_file
            return config_dict
        except ScannerError as e:
            raise UserNotificationException(f"Failed scanning configuration file '{config_file}'. \nError: {e}") from e
        except ParserError as e:
            raise UserNotificationException(f"Failed parsing configuration file '{config_file}'. \nError: {e}") from e


class MocksGenerator:
    def __init__(
        self,
        source_files: Iterable[Path],
        symbols: Iterable[str],
        output_dir: Path,
        filename: str,
        compilation_database: Path | None,
        config: MocksGeneratorConfig,
    ) -> None:
        self.source_files = list(source_files)
        self.symbols = set(symbols)
        self.output_dir = output_dir
        self.filename = filename
        self.compilation_database = compilation_database
        self.mock_type = config.mock_type
        self.exclude_symbol_patterns = list(config.exclude_symbol_patterns) if config.exclude_symbol_patterns else []
        self.strict = config.strict
        self.env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
            autoescape=select_autoescape(enabled_extensions=("j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self) -> None:
        """Generate mock files with comprehensive error reporting."""
        tus = self._parse_sources()

        # Apply symbol exclusion patterns before finding symbols
        filtered_symbols = self._filter_excluded_symbols(self.symbols)
        excluded_symbols = list(self.symbols - filtered_symbols)

        # Log excluded symbols
        if excluded_symbols:
            from py_app_dev.core.logging import logger

            logger.info(f"Excluded {len(excluded_symbols)} symbols matching exclude patterns: {sorted(excluded_symbols)}")

        symbols_data = extract_symbols_data(find_symbols(tus, filtered_symbols))

        # Collect all issues in structured format
        issues = self._analyze_generation_results(tus, symbols_data, excluded_symbols, filtered_symbols)

        # Determine what can actually be rendered
        filtered_data = self._filter_renderable_symbols(symbols_data)
        rendered_functions = [f for f in filtered_data if isinstance(f, FoundFunction)]
        rendered_variables = [v for v in filtered_data if isinstance(v, FoundVariable)]

        # If strict mode and issues found, write failure log and raise
        if self.strict and issues.has_any_issues:
            report_content = self._create_report(issues=issues, rendered_functions=rendered_functions, rendered_variables=rendered_variables, status="failed")
            self._write_log(report_content)
            raise UserNotificationException(f"Mock generation for '{self.filename}' failed. See '{self.output_dir / f'{self.filename}.log'}' for details.")

        # Success path: generate files then write success log
        renderer = self._select_renderer()
        rendered = renderer.render_all(data=filtered_data, missing=issues.missing_symbols)
        self._write_outputs(rendered)

        report_content = self._create_report(issues=issues, rendered_functions=rendered_functions, rendered_variables=rendered_variables, status="success")
        self._write_log(report_content)

    def _parse_sources(self) -> list[TranslationUnit]:
        """
        Parse all source files into translation units (no error collection).

        If multiple sources are provided they are parsed in parallel to speed
        up processing. Errors are inspected later in generate().
        """
        compile_commands = CompilationOptionsManager(self.compilation_database) if self.compilation_database else None
        if len(self.source_files) <= 1:
            parser = CLangParser()
            return [parser.load(self.source_files[0], compile_commands)] if self.source_files else []

        from concurrent.futures import ThreadPoolExecutor

        def worker(path: Path) -> TranslationUnit:
            p = CLangParser()
            return p.load(path, compile_commands)

        with ThreadPoolExecutor(max_workers=min(8, len(self.source_files))) as ex:
            return list(ex.map(worker, self.source_files))

    def _select_renderer(self) -> TemplateRenderer:
        if self.mock_type == MockType.GMOCK:
            return GMockTemplateRenderer(self.filename, self.output_dir, self.env)
        raise NotImplementedError("Mock type not implemented")  # pragma: no cover

    def _write_outputs(self, rendered: dict[str, str]) -> None:
        """Write all rendered mock files to the output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in rendered.items():
            (self.output_dir / name).write_text(content if content.endswith("\n") else content + "\n")

    def _filter_excluded_symbols(self, symbols: set[str]) -> set[str]:
        """Filter out symbols that match any exclude pattern."""
        if not self.exclude_symbol_patterns:
            return symbols

        filtered_symbols = set()
        for symbol in symbols:
            excluded = False
            for pattern in self.exclude_symbol_patterns:
                if fnmatch.fnmatch(symbol, pattern):
                    excluded = True
                    break
            if not excluded:
                filtered_symbols.add(symbol)

        return filtered_symbols

    def _analyze_generation_results(
        self, translation_units: list[TranslationUnit], symbols_data: list[FoundVariable | FoundFunction], excluded_symbols: list[str], filtered_symbols: set[str]
    ) -> MockGenerationIssues:
        """Analyze parsing and symbol extraction results to identify issues."""
        # Parse results
        parse_errors = []
        for path, tu in zip(self.source_files, translation_units):
            error = tu.parsing_error()
            parse_errors.append(FileParseResult(path=path, error=error))

        # Missing symbols (only from symbols that were not excluded)
        found_symbol_names = {symbol.name for symbol in symbols_data}
        missing_symbols = sorted(filtered_symbols - found_symbol_names)

        # Unsupported functions (e.g., variadic)
        unsupported_functions = []
        for symbol in symbols_data:
            if isinstance(symbol, FoundFunction) and any(p.is_variadic for p in symbol.parameters):
                unsupported_functions.append(symbol.name)

        return MockGenerationIssues(
            parse_errors=parse_errors,
            missing_symbols=missing_symbols,
            unsupported_functions=unsupported_functions,
            excluded_symbols=excluded_symbols,
        )

    def _filter_renderable_symbols(self, symbols_data: list[FoundVariable | FoundFunction]) -> list[FoundVariable | FoundFunction]:
        """Filter out symbols that cannot be rendered (e.g., variadic functions)."""
        return [symbol for symbol in symbols_data if not (isinstance(symbol, FoundFunction) and any(p.is_variadic for p in symbol.parameters))]

    def _create_report(
        self,
        *,
        issues: MockGenerationIssues,
        rendered_functions: list[FoundFunction],
        rendered_variables: list[FoundVariable],
        status: str,
    ) -> str:
        """Create a detailed generation report using the report generator."""
        report_generator = MockGenerationReport(
            filename=self.filename,
            mock_type=self.mock_type,
            requested_symbols=self.symbols,
        )
        return report_generator.generate_report(
            issues=issues,
            rendered_functions=rendered_functions,
            rendered_variables=rendered_variables,
            status=status,
        )

    def _write_log(self, content: str) -> None:
        """Write log content to the log file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.output_dir / f"{self.filename}.log"
        log_file.write_text(content if content.endswith("\n") else content + "\n")
