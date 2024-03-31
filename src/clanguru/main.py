import sys
from pathlib import Path

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it

from clanguru import __version__
from clanguru.my_app import MyApp

package_name = "clanguru"

app = typer.Typer(name=package_name, help="C language utils and tools based on the clang module.", no_args_is_help=True)


@app.callback(invoke_without_command=True)
def version(
    version: bool = typer.Option(None, "--version", "-v", is_eager=True, help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"{package_name} {__version__}")
        raise typer.Exit()


@app.command()
@time_it("init")
def init(project_dir: Path = typer.Option(Path.cwd().absolute(), help="The project directory"), enable: bool = False) -> None:  # noqa: B008
    logger.info(f"Initializing project in {project_dir} with enable={enable}")


@app.command()
@time_it("run")
def run(project_dir: Path = typer.Option(Path.cwd().absolute(), help="The project directory")) -> None:  # noqa: B008
    MyApp(project_dir).run()


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
