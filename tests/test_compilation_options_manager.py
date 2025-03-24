import json
from collections.abc import Generator
from pathlib import Path

import pytest

from clanguru.compilation_options_manager import CompilationDatabase, CompilationOptionsManager, CompileCommand


@pytest.fixture
def temp_compilation_database(tmp_path: Path) -> Generator[Path, None, None]:
    db_content = [
        {"directory": tmp_path.as_posix(), "file": "test1.c", "arguments": ["gcc", "-I/usr/include", "-DDEBUG", "test1.c"]},
        {"directory": tmp_path.as_posix(), "file": "test2.c", "command": "gcc -c -O2 test2.c"},
    ]
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text(json.dumps(db_content))
    yield db_file


def test_compilation_options_manager_without_database() -> None:
    manager = CompilationOptionsManager()
    assert manager.get_compile_options(Path("any_file.c")) == ["-std=c11"]


def test_compilation_options_manager_with_database(temp_compilation_database: Path) -> None:
    manager = CompilationOptionsManager(temp_compilation_database)

    # Test for file in the database
    test1_path = Path(temp_compilation_database.parent) / "test1.c"
    options = manager.get_compile_options(test1_path)
    assert options == ["-I/usr/include", "-DDEBUG"]

    # Test for file in the database with command string
    test2_path = Path(temp_compilation_database.parent) / "test2.c"
    options = manager.get_compile_options(test2_path)
    assert options == ["-O2"]

    # Test for file not in the database
    not_in_db_path = Path(temp_compilation_database.parent) / "not_in_db.c"
    options = manager.get_compile_options(not_in_db_path)
    assert options == ["-std=c11"]


def test_compilation_options_manager_no_default() -> None:
    manager = CompilationOptionsManager(no_default=True)
    options = manager.get_compile_options(Path("any_file.c"))
    assert options == []


def test_set_default_options() -> None:
    manager = CompilationOptionsManager()
    new_defaults = ["-std=c99", "-Wall"]
    manager.set_default_options(new_defaults)
    assert manager.get_compile_options(Path("any_file.c")) == new_defaults


def test_compilation_database_from_json() -> None:
    json_data = """
    [
        {
            "directory": "/home/user/project",
            "file": "main.c",
            "arguments": ["gcc", "-c", "-I/usr/include", "main.c"]
        }
    ]
    """
    tmp_file = Path("temp_compile_commands.json")
    tmp_file.write_text(json_data)

    try:
        db = CompilationDatabase.from_json_file(tmp_file)
        assert len(db.commands) == 1
        assert db.commands[0].directory == Path("/home/user/project")
        assert db.commands[0].file == Path("main.c")
        assert db.commands[0].arguments == ["gcc", "-c", "-I/usr/include", "main.c"]
    finally:
        tmp_file.unlink()


def test_get_compile_commands() -> None:
    json_data = """
    [
        {
            "directory": "/home/user/project",
            "file": "main.c",
            "arguments": ["gcc", "-c", "-I/usr/include", "main.c"]
        },
        {
            "directory": "/home/user/project",
            "file": "helper.c",
            "command": "gcc -c -O2 helper.c"
        }
    ]
    """
    tmp_file = Path("temp_compile_commands.json")
    tmp_file.write_text(json_data)

    try:
        db = CompilationDatabase.from_json_file(tmp_file)
        commands = db.getCompileCommands(Path("/home/user/project/main.c"))
        assert len(commands) == 1
        assert commands[0].file == Path("main.c")
        assert commands[0].arguments == ["gcc", "-c", "-I/usr/include", "main.c"]

        commands = db.getCompileCommands(Path("/home/user/project/helper.c"))
        assert len(commands) == 1
        assert commands[0].file == Path("helper.c")
        assert commands[0].command == "gcc -c -O2 helper.c"

        commands = db.getCompileCommands(Path("/home/user/project/nonexistent.c"))
        assert len(commands) == 0
    finally:
        tmp_file.unlink()


@pytest.fixture
def compile_command():
    return CompileCommand(directory=Path("/home/user/project"), file=Path("/home/user/project/input.c"), output=Path("/home/user/project/output.o"))


def test_clean_up_arguments_basic(compile_command):
    arguments = ["gcc", "-DStuff", "-ISome/Path", "-o", "/home/user/project/output.o", "/home/user/project/input.c"]
    expected = ["-DStuff", "-ISome/Path"]
    assert compile_command.clean_up_arguments(arguments) == expected


def test_clean_up_arguments_with_c_option(compile_command):
    arguments = ["gcc", "-DStuff", "-ISome/Path", "-c", "-o", "/home/user/project/output.o", "/home/user/project/input.c"]
    expected = ["-DStuff", "-ISome/Path"]
    assert compile_command.clean_up_arguments(arguments) == expected


def test_clean_up_arguments_with_combined_options(compile_command):
    arguments = ["gcc", "-DStuff", "-ISome/Path", "-c", "-o/home/user/project/output.o", "/home/user/project/input.c"]
    expected = ["-DStuff", "-ISome/Path"]
    assert compile_command.clean_up_arguments(arguments) == expected


def test_clean_up_arguments_with_multiple_input_files(compile_command):
    arguments = ["gcc", "-DStuff", "-ISome/Path", "-c", "/home/user/project/input.c", "/home/user/project/helper.c", "-o", "/home/user/project/output.o"]
    expected = ["-DStuff", "-ISome/Path", "/home/user/project/helper.c"]
    assert compile_command.clean_up_arguments(arguments) == expected


def test_clean_up_arguments_with_complex_options(compile_command):
    arguments = ["gcc", "-DStuff", "-ISome/Path", "-Werror", "-Wall", "-std=c11", '-DVERSION="1.0"', "-c", "/home/user/project/input.c", "-o", "/home/user/project/output.o"]
    expected = ["-DStuff", "-ISome/Path", "-Werror", "-Wall", "-std=c11", '-DVERSION="1.0"']
    assert compile_command.clean_up_arguments(arguments) == expected


def test_clean_up_arguments_with_partial_paths(compile_command):
    arguments = ["gcc", "-DStuff", "-I/home/user/project", "-Werror", "-Wall", "-c", "project/input.c", "-o", "project/output.o"]
    expected = ["-DStuff", "-I/home/user/project", "-Werror", "-Wall"]
    assert compile_command.clean_up_arguments(arguments) == expected
