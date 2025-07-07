import sys
from pathlib import Path

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it

from clanguru import __version__
from clanguru.compilation_options_manager import CompilationDatabase, CompilationOptionsManager
from clanguru.cparser import CLangParser
from clanguru.doc_generator import MarkdownFormatter, generate_documentation
from clanguru.object_analyzer import ObjectsDataExcelReportGenerator, ObjectsDependenciesReportGenerator, parse_objects

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
