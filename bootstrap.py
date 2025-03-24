#!/usr/bin/python3
# Source: https://github.com/avengineers/bootstrap
# Tag: v1.15.1
import configparser
import ensurepip
import hashlib
import json
import logging
import os
import re
import subprocess  # nosec
import sys
import tempfile
import venv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap")


bootstrap_json_path = Path.cwd() / "bootstrap.json"
if bootstrap_json_path.exists():
    with bootstrap_json_path.open("r") as f:
        config = json.load(f)
    package_manager = config.get("python_package_manager", "uv>=0,<1")
    package_manager_args = config.get("python_package_manager_args", [])
else:
    package_manager = "uv>=0,<1"
    package_manager_args = ["sync"]


@total_ordering
class Version:
    def __init__(self, version_str: str) -> None:
        self.version = self.parse_version(version_str)

    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """Convert a version string into a tuple of integers for comparison."""
        return tuple(map(int, re.split(r"\D+", version_str)))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self.version == other.version

    def __lt__(self, other: object) -> bool:
        return isinstance(other, Version) and self.version < other.version

    def __repr__(self) -> str:
        return f"Version({'.'.join(map(str, self.version))})"


@dataclass
class PyPiSource:
    name: str
    url: str


@dataclass
class TomlSection:
    name: str
    content: str

    def __str__(self) -> str:
        return f"[{self.name}]\n{self.content}"


class PyPiSourceParser:
    @staticmethod
    def from_pyproject(project_dir: Path) -> Optional[PyPiSource]:
        pyproject_toml = project_dir / "pyproject.toml"
        pipfile = project_dir / "Pipfile"
        if pyproject_toml.exists():
            return PyPiSourceParser.from_toml_content(pyproject_toml.read_text(), "tool.poetry.source")
        elif pipfile.exists():
            return PyPiSourceParser.from_toml_content(pipfile.read_text(), "source")
        else:
            return None

    @staticmethod
    def from_toml_content(content: str, source_section_name: str) -> Optional[PyPiSource]:
        sections = PyPiSourceParser.get_toml_sections(content)
        for section in sections:
            if section.name == source_section_name:
                try:
                    parser = configparser.ConfigParser()
                    parser.read_string(str(section))
                    name = parser[section.name]["name"].strip('"')
                    url = parser[section.name]["url"].strip('"')
                    return PyPiSource(name, url)
                except KeyError:
                    raise UserNotificationException(
                        f"Could not parse PyPi source from section {section.name}. "
                        f"Please make sure the section has the following format:\n"
                        f"[{source_section_name}]\n"
                        f'name = "name"\n'
                        f'url = "https://url"\n'
                        f"verify_ssl = true"
                    ) from None
        return None

    @staticmethod
    def get_toml_sections(toml_content: str) -> List[TomlSection]:
        # Use a regular expression to find all sections with [ or [[ at the beginning of the line
        raw_sections = re.findall(r"^\[+.*\]+\n(?:[^[]*\n)*", toml_content, re.MULTILINE)

        # Process each section
        sections = []
        for section in raw_sections:
            # Split the lines, from the first line extract the section name
            # and merge all the other lines into the content
            lines = section.splitlines()
            name_match = re.match(r"^\[+([^]]*)\]+", lines[0])
            if name_match:
                name = name_match.group(1).strip()
                content = "\n".join(lines[1:]).strip()
                sections.append(TomlSection(name, content))

        return sections


class Runnable(ABC):
    @abstractmethod
    def run(self) -> int:
        """Run and return exit code."""

    @abstractmethod
    def get_name(self) -> str:
        """Get runnable name."""

    @abstractmethod
    def get_inputs(self) -> List[Path]:
        """Get runnable dependencies."""

    @abstractmethod
    def get_outputs(self) -> List[Path]:
        """Get runnable outputs."""


class RunInfoStatus(Enum):
    MATCH = (False, "Nothing has changed, previous execution information matches.")
    NO_INFO = (True, "No previous execution information found.")
    FILE_CHANGED = (True, "Dependencies have been changed.")

    def __init__(self, should_run: bool, message: str) -> None:
        self.should_run = should_run
        self.message = message


class Executor:
    """
    Accepts Runnable objects and executes them.
    It create a file with the same name as the runnable's name
    and stores the inputs and outputs with their hashes.
    If the file exists, it checks the hashes of the inputs and outputs
    and if they match, it skips the execution.
    """

    RUN_INFO_FILE_EXTENSION = ".deps.json"

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    @staticmethod
    def get_file_hash(path: Path) -> str:
        """
        Get the hash of a file.
        Returns an empty string if the file does not exist.
        """
        if path.is_file():
            with open(path, "rb") as file:
                bytes = file.read()
                readable_hash = hashlib.sha256(bytes).hexdigest()
                return readable_hash
        else:
            return ""

    def store_run_info(self, runnable: Runnable) -> None:
        file_info = {
            "inputs": {str(path): self.get_file_hash(path) for path in runnable.get_inputs()},
            "outputs": {str(path): self.get_file_hash(path) for path in runnable.get_outputs()},
        }

        run_info_path = self.get_runnable_run_info_file(runnable)
        run_info_path.parent.mkdir(parents=True, exist_ok=True)
        with run_info_path.open("w") as f:
            # pretty print the json file
            json.dump(file_info, f, indent=4)

    def get_runnable_run_info_file(self, runnable: Runnable) -> Path:
        return self.cache_dir / f"{runnable.get_name()}{self.RUN_INFO_FILE_EXTENSION}"

    def previous_run_info_matches(self, runnable: Runnable) -> RunInfoStatus:
        run_info_path = self.get_runnable_run_info_file(runnable)
        if not run_info_path.exists():
            return RunInfoStatus.NO_INFO

        with run_info_path.open() as f:
            previous_info = json.load(f)

        for file_type in ["inputs", "outputs"]:
            for path_str, previous_hash in previous_info[file_type].items():
                path = Path(path_str)
                if self.get_file_hash(path) != previous_hash:
                    return RunInfoStatus.FILE_CHANGED
        return RunInfoStatus.MATCH

    def execute(self, runnable: Runnable) -> int:
        run_info_status = self.previous_run_info_matches(runnable)
        if run_info_status.should_run:
            logger.info(f"Runnable '{runnable.get_name()}' must run. {run_info_status.message}")
            exit_code = runnable.run()
            self.store_run_info(runnable)
            return exit_code
        logger.info(f"Runnable '{runnable.get_name()}' execution skipped. {run_info_status.message}")

        return 0


class UserNotificationException(Exception):
    pass


class SubprocessExecutor:
    def __init__(
        self,
        command: List[str | Path],
        cwd: Optional[Path] = None,
        capture_output: bool = True,
    ):
        self.command = " ".join([str(cmd) for cmd in command])
        self.current_working_directory = cwd
        self.capture_output = capture_output

    def execute(self) -> None:
        result = None
        try:
            current_dir = (self.current_working_directory or Path.cwd()).as_posix()
            logger.info(f"Running command: {self.command} in {current_dir}")
            # print all virtual environment variables
            logger.debug(json.dumps(dict(os.environ), indent=4))
            result = subprocess.run(
                self.command.split(),
                cwd=current_dir,
                capture_output=self.capture_output,
                text=True,  # to get stdout and stderr as strings instead of bytes
            )  # nosec
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            raise UserNotificationException(f"Command '{self.command}' failed with:\n{result.stdout if result else ''}\n{result.stderr if result else e}") from e


class VirtualEnvironment(ABC):
    def __init__(self, venv_dir: Path) -> None:
        self.venv_dir = venv_dir

    def create(self) -> None:
        """
        Create a new virtual environment. This should configure the virtual environment such that
        subsequent calls to `pip` and `run` operate within this environment.
        """
        try:
            venv.create(env_dir=self.venv_dir, with_pip=True)
        except PermissionError as e:
            if "python.exe" in str(e):
                raise UserNotificationException(
                    f"Failed to create virtual environment in {self.venv_dir}.\n"
                    f"Virtual environment python.exe is still running. Please kill all instances and run again.\n"
                    f"Error: {e}"
                ) from e
            raise UserNotificationException(f"Failed to create virtual environment in {self.venv_dir}.\nPlease make sure you have the necessary permissions.\nError: {e}") from e

    def pip_configure(self, index_url: str, verify_ssl: bool = True) -> None:
        """
        Configure pip to use the given index URL and SSL verification setting. This method should
        behave as if the user had activated the virtual environment and run `pip config set
        global.index-url <index_url>` and `pip config set global.cert <verify_ssl>` from the
        command line.

        Args:
        ----
            index_url: The index URL to use for pip.
            verify_ssl: Whether to verify SSL certificates when using pip.

        """
        # The pip configuration file should be in the virtual environment directory %VIRTUAL_ENV%
        pip_ini_path = self.pip_config_path()
        with open(pip_ini_path, "w") as pip_ini_file:
            pip_ini_file.write(f"[global]\nindex-url = {index_url}\n")
            if not verify_ssl:
                pip_ini_file.write("cert = false\n")

    def pip(self, args: List[str]) -> None:
        SubprocessExecutor([self.pip_path().as_posix(), *args]).execute()

    @abstractmethod
    def pip_path(self) -> Path:
        """
        Get the path to the pip executable within the virtual environment.
        """

    @abstractmethod
    def pip_config_path(self) -> Path:
        """
        Get the path to the pip configuration file within the virtual environment.
        """

    @abstractmethod
    def run(self, args: List[str], capture_output: bool = True) -> None:
        """
        Run an arbitrary command within the virtual environment. This method should behave as if the
        user had activated the virtual environment and run the given command from the command line.

        Args:
        ----
            *args: Command-line arguments. For example, `run('python', 'setup.py', 'install')`
                   should behave similarly to `python setup.py install` at the command line.

        """


class WindowsVirtualEnvironment(VirtualEnvironment):
    def __init__(self, venv_dir: Path) -> None:
        super().__init__(venv_dir)
        self.activate_script = self.venv_dir.joinpath("Scripts/activate")

    def pip_path(self) -> Path:
        return self.venv_dir.joinpath("Scripts/pip.exe")

    def pip_config_path(self) -> Path:
        return self.venv_dir.joinpath("pip.ini")

    def run(self, args: List[str], capture_output: bool = True) -> None:
        SubprocessExecutor(
            command=[f"cmd /c {self.activate_script.as_posix()} && ", *args],
            capture_output=capture_output,
        ).execute()


class UnixVirtualEnvironment(VirtualEnvironment):
    def __init__(self, venv_dir: Path) -> None:
        super().__init__(venv_dir)
        self.activate_script = self.venv_dir.joinpath("bin/activate")

    def pip_path(self) -> Path:
        return self.venv_dir.joinpath("bin/pip")

    def pip_config_path(self) -> Path:
        return self.venv_dir.joinpath("pip.conf")

    def run(self, args: List[str], capture_output: bool = True) -> None:
        # Create a temporary shell script
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as f:
            f.write("#!/bin/bash\n")  # Add a shebang line
            f.write(f"source {self.activate_script.as_posix()}\n")  # Write the activate command
            f.write(" ".join(args))  # Write the provided command
            temp_script_path = f.name  # Get the path of the temporary script

        # Make the temporary script executable
        SubprocessExecutor(["chmod", "+x", temp_script_path]).execute()
        # Run the temporary script
        SubprocessExecutor(
            command=[f"{Path(temp_script_path).as_posix()}"],
            capture_output=capture_output,
        ).execute()
        # Delete the temporary script
        os.remove(temp_script_path)


class CreateVirtualEnvironment(Runnable):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.venv_dir = self.root_dir / ".venv"
        self.bootstrap_dir = self.root_dir / ".bootstrap"
        self.virtual_env = self.instantiate_os_specific_venv(self.venv_dir)

    @property
    def package_manager_name(self) -> str:
        match = re.match(r"^([a-zA-Z0-9_-]+)", package_manager)

        if match:
            return match.group(1)
        else:
            raise UserNotificationException(f"Could not extract the package manager name from {package_manager}")

    def run(self) -> int:
        # Create the virtual environment if pip executable does not exist
        if not self.virtual_env.pip_path().exists():
            self.virtual_env.create()

        # Get the PyPi source from pyproject.toml or Pipfile if it is defined
        pypi_source = PyPiSourceParser.from_pyproject(self.root_dir)
        if pypi_source:
            self.virtual_env.pip_configure(index_url=pypi_source.url, verify_ssl=True)
        # We need pip-system-certs in venv to use certificates, that are stored in the system's trust store,
        pip_args = ["install", package_manager, "pip-system-certs"]
        # but to install it, we need either a pip version with the trust store feature or to trust the host
        # (trust store feature enabled by default since 24.2)
        if Version(ensurepip.version()) < Version("24.2"):
            # Add trusted host of configured source for older Python versions
            if pypi_source:
                pip_args.extend(["--trusted-host", urlparse(pypi_source.url).hostname])
            else:
                pip_args.extend(["--trusted-host", "pypi.org", "--trusted-host", "pypi.python.org", "--trusted-host", "files.pythonhosted.org"])
        self.virtual_env.pip(pip_args)
        self.virtual_env.run(["python", "-m", self.package_manager_name, *package_manager_args])
        return 0

    @staticmethod
    def instantiate_os_specific_venv(venv_dir: Path) -> VirtualEnvironment:
        if sys.platform.startswith("win32"):
            return WindowsVirtualEnvironment(venv_dir)
        elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
            return UnixVirtualEnvironment(venv_dir)
        else:
            raise UserNotificationException(f"Unsupported operating system: {sys.platform}")

    def get_name(self) -> str:
        return "create-virtual-environment"

    def get_inputs(self) -> List[Path]:
        venv_relevant_files = [
            "uv.lock",
            "poetry.lock",
            "poetry.toml",
            "pyproject.toml",
            ".env",
            "Pipfile",
            "Pipfile.lock",
            "bootstrap.json",
            ".bootstrap/bootstrap.ps1",
            ".bootstrap/bootstrap.py",
            "bootstrap.ps1",
            "bootstrap.py",
        ]
        return [self.root_dir / file for file in venv_relevant_files]

    def get_outputs(self) -> List[Path]:
        return []


def print_environment_info() -> None:
    str_bar = "".join(["-" for _ in range(80)])
    logger.debug(str_bar)
    logger.debug("Environment: \n" + json.dumps(dict(os.environ), indent=4))
    logger.info(str_bar)
    logger.info(f"Arguments: {sys.argv[1:]}")
    logger.info(str_bar)


def main() -> int:
    try:
        # print_environment_info()
        creator = CreateVirtualEnvironment(Path.cwd())
        Executor(creator.venv_dir).execute(creator)
    except UserNotificationException as e:
        logger.error(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
