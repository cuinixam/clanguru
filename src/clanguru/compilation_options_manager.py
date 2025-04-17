import io
import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from mashumaro import DataClassDictMixin
from mashumaro.config import TO_DICT_ADD_OMIT_NONE_FLAG, BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.types import SerializableType
from py_app_dev.core.exceptions import UserNotificationException


class PathField(SerializableType):
    def _serialize(self) -> str:
        return str(self)

    @classmethod
    def _deserialize(cls, value: str) -> Path:
        return Path(value)


@dataclass
class CompileCommand(DataClassDictMixin):
    directory: Path
    file: Path
    arguments: list[str] = field(default_factory=list)
    command: str | None = None
    output: Path | None = None

    def get_compile_options(self) -> list[str]:
        options = []
        if self.arguments:
            options = self.arguments
        if self.command:
            options = self.command.split()
        return self.clean_up_arguments(options)

    def get_file_path(self) -> Path:
        return self.file if self.file.is_absolute() else self.directory / self.file

    def get_output_path(self) -> Path | None:
        return self.output if self.output and self.output.is_absolute() else (self.directory / self.output if self.output else None)

    def clean_up_arguments(self, arguments: list[str]) -> list[str]:
        """
        Clean up the command line to only get the compilation options.

        Ignore the first argument which is the compiler.
        Remove the options for the output and input files.
        Any arguments containing the input or output file names or paths are removed.
        For example: -DStuff -ISome/Path -o output.o input.c -> -DStuff -ISome/Path
        """
        cleaned_args = []
        skip_next = False
        input_filename = self.file.name
        output_filename = self.output.name if self.output else None

        for arg in arguments[1:]:  # Skip the first argument (compiler)
            if skip_next:
                skip_next = False
                continue

            # Skip -o and its value
            if arg == "-o":
                skip_next = True
                continue

            # Skip -c option
            if arg == "-c":
                continue

            # Skip arguments containing input or output file names or paths
            if input_filename in arg or (output_filename and output_filename in arg):
                continue

            # Keep all other arguments
            cleaned_args.append(arg)

        return cleaned_args


@dataclass
class CompilationDatabase(DataClassJSONMixin):
    commands: list[CompileCommand]

    def get_compile_commands(self, file: Path) -> list[CompileCommand]:
        return [command for command in self.commands if command.get_file_path() == file]

    def get_output_files(self) -> list[Path]:
        result = []
        for command in self.commands:
            output_path = command.get_output_path()
            if output_path and output_path not in result:
                result.append(output_path)
        return result

    class Config(BaseConfig):
        code_generation_options: ClassVar[list[str]] = [TO_DICT_ADD_OMIT_NONE_FLAG]

    @classmethod
    def from_json_file(cls, file_path: Path) -> "CompilationDatabase":
        try:
            result = cls.from_dict({"commands": json.loads(file_path.read_text())})
        except Exception as e:
            output = io.StringIO()
            traceback.print_exc(file=output)
            raise UserNotificationException(output.getvalue()) from e
        return result

    def to_json_string(self) -> str:
        return json.dumps(self.to_dict(omit_none=True), indent=2)

    def to_json_file(self, file_path: Path) -> None:
        file_path.write_text(self.to_json_string())


class CompilationOptionsManager:
    def __init__(self, compilation_database: Path | None = None, no_default: bool = False):
        self.compilation_database: CompilationDatabase | None = CompilationDatabase.from_json_file(compilation_database) if compilation_database else None
        self.no_default = no_default
        self.default_options = ["-std=c11"]

    def get_compile_options(self, file: Path) -> list[str]:
        if self.compilation_database:
            commands: list[CompileCommand] = self.compilation_database.get_compile_commands(file)
            # TODO: how to handle multiple commands for the same file?
            if commands:
                return commands[0].get_compile_options()
        return [] if self.no_default else self.default_options

    def set_default_options(self, options: list[str]) -> None:
        self.default_options = options
