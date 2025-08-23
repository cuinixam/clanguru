import sys
from pathlib import Path

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it

from clanguru import __version__
from clanguru.compilation_options_manager import CompilationDatabase, CompilationOptionsManager
from clanguru.cparser import CLangParser
from clanguru.doc_generator import MarkdownFormatter, generate_documentation
from clanguru.mock_generator import MocksGenerator, MockType
from clanguru.object_analyzer import NmExecutor, ObjectsDataExcelReportGenerator, ObjectsDependenciesReportGenerator, parse_objects

package_name = "clanguru"

app = typer.Typer(name=package_name, help="C language utils and tools based on the libclang module.", no_args_is_help=True, add_completion=False)


@app.callback(invoke_without_command=True)
def version(
    version: bool = typer.Option(None, "--version", "-v", is_eager=True, help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"{package_name} {__version__}")
        raise typer.Exit()


@app.command(help="Generate documentation from C source code.")
@time_it("generate")
def generate(
    source_file: Path = typer.Option(help="Input source file"),  # noqa: B008
    output_file: Path = typer.Option(help="Output file"),  # noqa: B008
    compilation_database: Path | None = typer.Option(None, help="Compilation database file required if the source file includes external headers."),  # noqa: B008
) -> None:
    parser = CLangParser()
    translation_unit = parser.load(source_file, CompilationOptionsManager(compilation_database))
    generate_documentation(translation_unit, MarkdownFormatter(), output_file)


@app.command(help="Generate mocks for C functions and variables.")
@time_it("mock")
def mock(
    source_file: list[Path] = typer.Option(..., help="Input source file(s). Can be used multiple times."),  # noqa: B008
    symbol: list[str] = typer.Option(None, help="Symbols to mock. Can be used multiple times. Optional if partial_object_file is provided."),  # noqa: B008
    output_dir: Path = typer.Option(..., help="Output directory."),  # noqa: B008
    filename: str = typer.Option(help="Filename for generated mock files."),
    mock_type: MockType = typer.Option(MockType.GMOCK, case_sensitive=False, help="Type of mocks to generate. Supported: gmock (Google Test), cmock (CMock)."),  # noqa: B008
    compilation_database: Path | None = typer.Option(None, help="Compilation database file required if the source file includes external headers."),  # noqa: B008
    partial_object_file: Path | None = typer.Option(  # noqa: B008
        None,
        help="Partial link object file to extract symbols from. Symbols will be extracted using nm command and added to the symbol list.",
    ),
    strict: bool = typer.Option(True, help="Fail if some symbols are not found or source files have compilation errors."),
) -> None:
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

    MocksGenerator(source_file, symbols, output_dir, filename, mock_type, compilation_database, strict).generate()


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


@app.command(help="Analyze object files dependencies.")
@time_it("analyze")
def analyze(
    compilation_database: Path = typer.Option(help="Compilation database file"),  # noqa: B008
    output_file: Path = typer.Option(help="Output file"),  # noqa: B008
    use_parent_deps: bool = typer.Option(False, help="Use parent dependencies."),
) -> None:
    object_files = CompilationDatabase.from_json_file(compilation_database).get_output_files()
    if not object_files:
        raise UserNotificationException("No object files found in the compilation database.")
    object_data = parse_objects(object_files)
    # If the file extension is .xls or .xlsx use the ObjectsDataExcelReportGenerator generator.
    if output_file.suffix == ".xlsx":
        ObjectsDataExcelReportGenerator(object_data, use_parent_deps=use_parent_deps).generate_report(output_file)
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
