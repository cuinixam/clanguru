import json
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

from clanguru.compilation_options_manager import (
    CompilationDatabase,
    CompilationOptionsManager,
    CompileCommand,
    filter_compilation_database,
    parse_system_include_args,
)


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
    manager.set_default_options(["-std=c11"])
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
    assert options == []


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
        commands = db.get_compile_commands(Path("/home/user/project/main.c"))
        assert len(commands) == 1
        assert commands[0].file == Path("main.c")
        assert commands[0].arguments == ["gcc", "-c", "-I/usr/include", "main.c"]

        commands = db.get_compile_commands(Path("/home/user/project/helper.c"))
        assert len(commands) == 1
        assert commands[0].file == Path("helper.c")
        assert commands[0].command == "gcc -c -O2 helper.c"

        commands = db.get_compile_commands(Path("/home/user/project/nonexistent.c"))
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


@pytest.mark.parametrize(
    "arguments, expected",
    [
        pytest.param(
            ["gcc", "-DStuff", "-ISome/Path", "-Werror", "-Wall", "-std=c11", "-c", "/home/user/project/input.c", "-o", "/home/user/project/output.o"],
            ["-DStuff", "-ISome/Path"],
            id="mixed_flags",
        ),
        pytest.param(
            ["gcc", "-D", "STUFF", "-I", "Some/Path", "-Wall", "-c", "/home/user/project/input.c", "-o", "/home/user/project/output.o"],
            ["-D", "STUFF", "-I", "Some/Path"],
            id="separate_value_flags",
        ),
        pytest.param(
            ["gcc", '-DVERSION="1.0"', "-I/usr/include", "-I", "/usr/local/include", "-O2", "-c", "/home/user/project/input.c", "-o", "/home/user/project/output.o"],
            ['-DVERSION="1.0"', "-I/usr/include", "-I", "/usr/local/include"],
            id="combined_and_separate",
        ),
        pytest.param(
            ["gcc", "-Wall", "-Werror", "-O2", "-std=c11", "-c", "/home/user/project/input.c", "-o", "/home/user/project/output.o"],
            [],
            id="no_includes_or_defines",
        ),
        pytest.param(
            ["gcc", "-isystem", "/sys/inc", "-iquote/quoted", "-idirafter", "/after", "-include", "forced.h", "-imacros/macros.h", "-UNDEBUG", "-c", "/home/user/project/input.c"],
            ["-isystem", "/sys/inc", "-iquote/quoted", "-idirafter", "/after", "-include", "forced.h", "-imacros/macros.h", "-UNDEBUG"],
            id="system_includes_forced_includes_and_undefines",
        ),
    ],
)
def test_get_includes_and_defines(compile_command: CompileCommand, arguments: list[str], expected: list[str]) -> None:
    compile_command.arguments = arguments
    assert compile_command.get_includes_and_defines() == expected


def test_compilation_options_manager_get_includes_and_defines_with_database(temp_compilation_database: Path) -> None:
    manager = CompilationOptionsManager(temp_compilation_database)

    test1_path = Path(temp_compilation_database.parent) / "test1.c"
    test1_options = manager.get_includes_and_defines(test1_path)
    assert test1_options[:2] == ["-I/usr/include", "-DDEBUG"]
    assert len(test1_options) % 2 == 0
    assert all(option in ("-isystem", "-iframework") for option in test1_options[2::2])

    test2_path = Path(temp_compilation_database.parent) / "test2.c"
    test2_options = manager.get_includes_and_defines(test2_path)
    assert len(test2_options) % 2 == 0
    assert all(option in ("-isystem", "-iframework") for option in test2_options[::2])


def test_compilation_options_manager_get_includes_and_defines_without_database() -> None:
    manager = CompilationOptionsManager()
    manager.set_default_options(["-std=c11", "-I/usr/include", "-DDEBUG", "-Wall"])
    assert manager.get_includes_and_defines(Path("any_file.c")) == ["-I/usr/include", "-DDEBUG"]


def test_compilation_options_manager_get_includes_and_defines_no_default() -> None:
    manager = CompilationOptionsManager(no_default=True)
    assert manager.get_includes_and_defines(Path("any_file.c")) == []


def test_filter_compilation_database(tmp_path: Path) -> None:
    db_content = [
        {
            "directory": "C:/project/build",
            "command": f"g++.exe -std=gnu++14  -o {file_name}.obj -c C:/project/src/{file_name}",
            "file": f"{tmp_path}/{file_name}",
            "output": f"C:/project/build/{file_name}.obj",
        }
        for file_name in ["a.c", "b.c", "c.c"]
    ]
    db_content.append(
        {
            "directory": "C:/project",
            "command": "g++.exe -std=gnu++14  -o d.cc.obj -c C:/project/src/d.cc",
            "file": "src/d.cc",
            "output": "C:/project/build/d.cc.obj",
        }
    )
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text(json.dumps(db_content))

    db = CompilationDatabase.from_json_file(db_file)

    # Filter for a.c and c.c
    filtered = filter_compilation_database(db, [tmp_path / "a.c", Path("b.c"), Path("C:/project/src/d.cc")])
    assert len(filtered.commands) == 3
    kept_files = sorted(cmd.get_file_path().name for cmd in filtered.commands)
    assert kept_files == ["a.c", "b.c", "d.cc"]


@pytest.mark.parametrize(
    "command, expected_compiler, expected_options",
    [
        pytest.param(
            'gcc -DEMPTY="" -DSTUFF -I/usr/include -c input.c -o output.o',
            Path("gcc"),
            ["-DEMPTY=", "-DSTUFF", "-I/usr/include"],
            id="quoted_empty_define",
        ),
        pytest.param(
            r'"C:\Program Files\gcc\bin\gcc.exe" -DSTUFF -c input.c -o output.o',
            Path(r"C:\Program Files\gcc\bin\gcc.exe"),
            ["-DSTUFF"],
            id="windows_compiler_path_with_spaces",
        ),
        pytest.param(
            r'C:\tools\gcc.exe -DVERSION="1.0" -IC:\inc -c input.c -o output.o',
            Path(r"C:\tools\gcc.exe"),
            ["-DVERSION=1.0", r"-IC:\inc"],
            marks=pytest.mark.skipif(os.name != "nt", reason="an unquoted backslash is an escape outside Windows"),
            id="windows_backslashes_kept",
        ),
        pytest.param(
            r"gcc -DVERSION=\"1.0\" -I/usr/include -c input.c -o output.o",
            Path("gcc"),
            ['-DVERSION="1.0"', "-I/usr/include"],
            marks=pytest.mark.skipif(os.name == "nt", reason="Windows has no backslash escape to resolve"),
            id="posix_escaped_string_define",
        ),
    ],
)
def test_command_string_is_split_with_shell_quoting(command: str, expected_compiler: Path, expected_options: list[str]) -> None:
    compile_command = CompileCommand(directory=Path("/project"), file=Path("input.c"), command=command, output=Path("output.o"))
    assert compile_command.get_compiler() == expected_compiler
    assert compile_command.get_compile_options() == expected_options


def test_to_json(tmp_path: Path) -> None:
    db_content = [
        {
            "directory": str(Path("/home/user/project")),
            "file": "main.c",
            "arguments": ["gcc", "-c", "-I/usr/include", "main.c"],
            "output": "main.o",
        },
        {
            "directory": str(Path("/home/user/project")),
            "file": "helper.c",
            "command": "gcc -c -O2 helper.c",
            "output": "helper.o",
        },
    ]
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text(json.dumps(db_content))

    db = CompilationDatabase.from_json_file(db_file)
    json_output = db.to_json_string()

    expected_output = json.dumps(db_content, indent=2)
    assert json.loads(json_output) == json.loads(expected_output)


GCC_LINUX_OUTPUT = """Using built-in specs.
COLLECT_GCC=gcc
Target: x86_64-linux-gnu
gcc version 13.2.0 (Ubuntu 13.2.0-23ubuntu4)
ignoring nonexistent directory "/usr/local/include/x86_64-linux-gnu"
ignoring nonexistent directory "/usr/lib/gcc/x86_64-linux-gnu/13/include-fixed"
#include "..." search starts here:
#include <...> search starts here:
 /usr/lib/gcc/x86_64-linux-gnu/13/include
 /usr/local/include
 /usr/include/x86_64-linux-gnu
 /usr/include
End of search list.
COMPILER_PATH=/usr/libexec/gcc/x86_64-linux-gnu/13/
"""

APPLE_CLANG_OUTPUT = """Apple clang version 17.0.0 (clang-1700.0.13.5)
Target: arm64-apple-darwin25.0.0
Thread model: posix
clang -cc1 version 17.0.0 based upon LLVM 17.0.0 default target arm64-apple-darwin25.0.0
ignoring nonexistent directory "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/local/include"
#include "..." search starts here:
#include <...> search starts here:
 /Library/Developer/CommandLineTools/usr/lib/clang/17/include
 /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include
 /Library/Developer/CommandLineTools/usr/include
 /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/System/Library/Frameworks (framework directory)
End of search list.
"""


@pytest.mark.parametrize(
    "compiler_output, expected",
    [
        pytest.param(
            GCC_LINUX_OUTPUT,
            [
                "-isystem",
                os.path.normpath("/usr/lib/gcc/x86_64-linux-gnu/13/include"),
                "-isystem",
                os.path.normpath("/usr/local/include"),
                "-isystem",
                os.path.normpath("/usr/include/x86_64-linux-gnu"),
                "-isystem",
                os.path.normpath("/usr/include"),
            ],
            id="linux_gcc",
        ),
        pytest.param(
            APPLE_CLANG_OUTPUT,
            [
                "-isystem",
                os.path.normpath("/Library/Developer/CommandLineTools/usr/lib/clang/17/include"),
                "-isystem",
                os.path.normpath("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include"),
                "-isystem",
                os.path.normpath("/Library/Developer/CommandLineTools/usr/include"),
                "-iframework",
                os.path.normpath("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/System/Library/Frameworks"),
            ],
            id="apple_clang",
        ),
        pytest.param("gcc: error: unrecognized command-line option\n", [], id="no_markers"),
    ],
)
def test_parse_system_include_args(compiler_output: str, expected: list[str]) -> None:
    assert parse_system_include_args(compiler_output) == expected


def test_get_includes_and_defines_adds_nothing_when_compiler_cannot_run(tmp_path: Path) -> None:
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text(json.dumps([{"directory": tmp_path.as_posix(), "file": "a.c", "command": "does-not-exist-cc -Iinc -DX=1 -c a.c"}]))
    manager = CompilationOptionsManager(db_file)
    assert manager.get_includes_and_defines(tmp_path / "a.c") == ["-Iinc", "-DX=1"]


FAKE_COMPILER_SH = """#!/bin/sh
touch "$(dirname "$0")/ran.marker"
while [ "$1" != "-x" ]; do shift; done
if [ "$LC_ALL" = "C" ]; then
    echo "#include <...> search starts here:" >&2
else
    echo "la ricerca di #include <...> inizia qui:" >&2
fi
echo " /opt/fake/lib/gcc/x/1/include" >&2
echo " /opt/fake/bin/../lib/gcc/x/1/../../../../x/include" >&2
echo " /opt/fake/bin/../lib/gcc/x/1/include-fixed" >&2
echo " /opt/fake/include-$2" >&2
if [ "$LC_ALL" = "C" ]; then
    echo "End of search list." >&2
else
    echo "Fine dell'elenco di ricerca." >&2
fi
"""

FAKE_COMPILER_CMD = """@echo off
type nul > "%~dp0ran.marker"
if "%LC_ALL%"=="C" (
    1>&2 echo #include ^<...^> search starts here:
) else (
    1>&2 echo la ricerca di #include ^<...^> inizia qui:
)
1>&2 echo  /opt/fake/lib/gcc/x/1/include
1>&2 echo  /opt/fake/bin/../lib/gcc/x/1/../../../../x/include
1>&2 echo  /opt/fake/bin/../lib/gcc/x/1/include-fixed
1>&2 echo  /opt/fake/include-%4
if "%LC_ALL%"=="C" (
    1>&2 echo End of search list.
) else (
    1>&2 echo Fine dell'elenco di ricerca.
)
"""

SCRIPT_SUFFIX = ".cmd" if sys.platform == "win32" else ""


def write_fake_compiler(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FAKE_COMPILER_CMD if sys.platform == "win32" else FAKE_COMPILER_SH)
    path.chmod(0o755)


def write_database(tmp_path: Path, compiler: str, file_name: str) -> CompilationOptionsManager:
    db_file = tmp_path / "compile_commands.json"
    db_file.write_text(json.dumps([{"directory": tmp_path.as_posix(), "file": file_name, "arguments": [compiler, "-Iinc", "-c", file_name]}]))
    return CompilationOptionsManager(db_file)


@pytest.mark.parametrize("file_name, language", [("a.c", "c"), ("a.hpp", "c++")])
def test_compiler_search_list_reaches_the_options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_name: str, language: str) -> None:
    monkeypatch.setenv("LC_ALL", "it_IT.UTF-8")
    write_fake_compiler(tmp_path / "tools" / f"gcc{SCRIPT_SUFFIX}")
    manager = write_database(tmp_path, f"tools/gcc{SCRIPT_SUFFIX}", file_name)
    folders = [
        "/opt/fake/lib/gcc/x/1/include",
        "/opt/fake/bin/../lib/gcc/x/1/../../../../x/include",
        "/opt/fake/bin/../lib/gcc/x/1/include-fixed",
        f"/opt/fake/include-{language}",
    ]
    expected = ["-Iinc"] + [arg for folder in folders for arg in ("-isystem", os.path.normpath(folder))]
    assert manager.get_includes_and_defines(tmp_path / file_name) == expected


def test_program_not_named_like_a_compiler_is_never_run(tmp_path: Path) -> None:
    script = tmp_path / f"build{SCRIPT_SUFFIX}"
    write_fake_compiler(script)
    manager = write_database(tmp_path, script.as_posix(), "a.c")
    assert manager.get_includes_and_defines(tmp_path / "a.c") == ["-Iinc"]
    assert not (tmp_path / "ran.marker").exists()
