import sys
from enum import Enum
from pathlib import Path

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it

from clanguru import __version__
from clanguru.compilation_options_manager import CompilationDatabase, CompilationOptionsManager
from clanguru.cparser import CLangParser
from clanguru.doc_generator import MarkdownFlavour, MarkdownFormatter, OutputFormatter, RSTFormatter, generate_documentation
from clanguru.mock_generator import MocksGenerator, MocksGeneratorConfig, MockType
from clanguru.object_analyzer import (
    NmExecutor,
    ObjectData,
    ObjectsDataExcelReportGenerator,
    ObjectsDependenciesReportGenerator,
    SymbolLinkage,
    filter_object_data_symbols,
    parse_objects,
)

package_name = "clanguru"

app = typer.Typer(name=package_name, help="C language utils and tools based on the libclang module.", no_args_is_help=True, add_completion=False)


@app.callback(invoke_without_command=True)
def version(
    version: bool = typer.Option(None, "--version", "-v", is_eager=True, help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"{package_name} {__version__}")
        raise typer.Exit()


class DocsFormat(Enum):
    myst = "myst"
    md = "md"
    rst = "rst"


@app.command(help="Generate documentation for C/C++ source code.")
@time_it("docs")
def docs(
    source_file: Path = typer.Option(help="Input source file"),  # noqa: B008
    output_file: Path = typer.Option(help="Output file"),  # noqa: B008
    compilation_database: Path | None = typer.Option(None, help="Compilation database file required if the source file includes external headers."),  # noqa: B008
    format: DocsFormat = typer.Option(  # noqa: B008
        DocsFormat.myst,
        case_sensitive=False,
        help="Output documentation format. Supported: Myst Markdown flavour (default), Markdown, RestructuredText.",
    ),
) -> None:
    parser = CLangParser()
    translation_unit = parser.load(source_file, CompilationOptionsManager(compilation_database))
    formatter: OutputFormatter
    if format == DocsFormat.rst:
        formatter = RSTFormatter()
    else:
        formatter = MarkdownFormatter(MarkdownFlavour.Myst if format == DocsFormat.myst else MarkdownFlavour.Raw)
    generate_documentation(translation_unit, formatter, output_file)


@app.command(help="Generate mocks for C functions and variables.")
@time_it("mock")
def mock(
    source_file: list[Path] = typer.Option(..., help="Input source file(s). Can be used multiple times."),  # noqa: B008
    symbol: list[str] = typer.Option(None, help="Symbols to mock. Can be used multiple times. Optional if partial_object_file is provided."),  # noqa: B008
    output_dir: Path = typer.Option(..., help="Output directory."),  # noqa: B008
    filename: str = typer.Option(help="Filename for generated mock files."),
    compilation_database: Path | None = typer.Option(None, help="Compilation database file required if the source file includes external headers."),  # noqa: B008
    partial_object_file: Path | None = typer.Option(  # noqa: B008
        None,
        help="Partial link object file to extract symbols from. Symbols will be extracted using nm command and added to the symbol list.",
    ),
    # Mock configuration options
    mock_type: MockType | None = typer.Option(None, case_sensitive=False, help="Type of mocks to generate. Supported: gmock (Google Test), cmock (CMock)."),  # noqa: B008
    exclude_symbol_pattern: list[str] = typer.Option(None, help="Symbol patterns to exclude from mock generation (glob patterns). Can be used multiple times."),  # noqa: B008
    strict: bool | None = typer.Option(None, help="Fail if some symbols are not found or source files have compilation errors. Default is strict."),
    config_file: Path | None = typer.Option(None, help="Configuration file for mock generation settings."),  # noqa: B008
) -> None:
    # Load configuration from file or create from command line arguments
    if config_file:
        config = MocksGeneratorConfig.from_file(config_file)
    else:
        config = MocksGeneratorConfig()

    if strict is not None:
        config.strict = strict
    if exclude_symbol_pattern is not None:
        if config.exclude_symbol_patterns is not None:
            config.exclude_symbol_patterns.extend(exclude_symbol_pattern)
        else:
            config.exclude_symbol_patterns = exclude_symbol_pattern
    if mock_type is not None:
        config.mock_type = mock_type

    # Determine which symbols to use
    if partial_object_file:
        # If partial object file is provided, use symbols from it
        object_data = NmExecutor.run(partial_object_file)
        symbols = list(object_data.required_symbols)
        logger.info(f"Extracted {len(symbols)} symbols from {partial_object_file}: {symbols}")
    elif symbol:
        # Otherwise use manually specified symbols
        symbols = list(symbol)
    else:
        # Ensure we have symbols to mock
        raise UserNotificationException("No symbols provided. Either specify --symbol or provide --partial-object-file.")

    MocksGenerator(source_file, symbols, output_dir, filename, compilation_database, config).generate()


@app.command(help="Parse C source code and print the translation unit.")
@time_it("parse")
def parse(
    source_file: Path = typer.Option(help="Input source file"),  # noqa: B008
    output_file: Path | None = typer.Option(None, help="Output file"),  # noqa: B008
    compilation_database: Path | None = typer.Option(None, help="Compilation database file required if the source file includes external headers."),  # noqa: B008
) -> None:
    parser = CLangParser()
    translation_unit = parser.load(source_file, CompilationOptionsManager(compilation_database))
    if output_file:
        with open(output_file, "w") as f:
            f.write(str(translation_unit))
    else:
        logger.info(translation_unit)


def print_objects_data_statistics(object_data: list[ObjectData]) -> None:
    number_of_objects = len(object_data)
    number_of_local_symbols = 0
    number_of_external_symbols = 0

    for obj in object_data:
        for symbol in obj.symbols:
            if symbol.linkage == SymbolLinkage.LOCAL:
                number_of_local_symbols += 1
            elif symbol.linkage == SymbolLinkage.EXTERN:
                number_of_external_symbols += 1

    logger.info(f"Number of objects: {number_of_objects}")
    logger.info(f"Number of local symbols: {number_of_local_symbols}")
    logger.info(f"Number of external symbols: {number_of_external_symbols}")


@app.command(help="Analyze object files dependencies.")
@time_it("analyze")
def analyze(
    compilation_database: Path = typer.Option(help="Compilation database file"),  # noqa: B008
    output_file: Path = typer.Option(help="Output file"),  # noqa: B008
    use_parent_deps: bool = typer.Option(False, help="Use parent dependencies."),
    create_traceability_matrix: bool = typer.Option(False, help="Create object dependencies traceability matrix."),
    exclude_symbol_pattern: list[str] = typer.Option(None, help="Symbol patterns to exclude from analysis (glob). Can be used multiple times."),  # noqa: B008
) -> None:
    object_files = CompilationDatabase.from_json_file(compilation_database).get_output_files()
    if not object_files:
        raise UserNotificationException("No object files found in the compilation database.")
    logger.info("Parse objects files")
    object_data = parse_objects(object_files)
    print_objects_data_statistics(object_data)

    # Apply additional user-specified exclude patterns if provided
    if exclude_symbol_pattern:
        logger.info("Exclude symbols matching patterns")
        object_data = filter_object_data_symbols(object_data, exclude_symbol_pattern)
        print_objects_data_statistics(object_data)

    # If the file extension is .xls or .xlsx use the ObjectsDataExcelReportGenerator generator.
    if output_file.suffix == ".xlsx":
        ObjectsDataExcelReportGenerator(object_data, use_parent_deps=use_parent_deps, create_traceability_matrix=create_traceability_matrix).generate_report(output_file)
        logger.info("Dependencies report generated in Excel format.")
    else:
        ObjectsDependenciesReportGenerator(object_data, use_parent_deps=use_parent_deps).generate_report(output_file)
        logger.info("Dependencies report generated.")


def main() -> int:
    try:
        setup_logger()
        app()
        return 0
    except UserNotificationException as e:
        logger.error(f"{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
