import ctypes
import gc
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from py_app_dev.core.subprocess import SubprocessExecutor
from typer.testing import CliRunner
from typer.testing import Result as CliResult

from clanguru.main import app

DATA_DIR = Path(__file__).parent / "data" / "bind"
SENSOR_SOURCE = DATA_DIR / "sensor.c"
LIBRARY_EXTENSION = {"win32": ".dll", "darwin": ".dylib"}.get(sys.platform, ".so")

runner = CliRunner()


def compile_object(output_dir: Path, source_file: Path = SENSOR_SOURCE) -> Path:
    object_file = output_dir / f"{source_file.stem}.o"
    SubprocessExecutor(["clang", "-c", "-fPIC", source_file, "-o", object_file]).execute()
    return object_file


def run_bind(source_file: Path, object_file: Path, output_dir: Path, *extra_args: str) -> CliResult:
    return runner.invoke(
        app,
        [
            "bind",
            "--source-file",
            source_file.as_posix(),
            "--partial-object-file",
            object_file.as_posix(),
            "--output-dir",
            output_dir.as_posix(),
            "--filename",
            "sensor_binding",
            "--library-name",
            "sensor_pytest",
            "--exclude-symbol-pattern",
            "_*",
            *extra_args,
        ],
    )


def build_library(output_dir: Path, object_file: Path, fakes: Path = DATA_DIR / "fakes.c") -> None:
    linux_flags = ["-Wl,-z,defs"] if sys.platform.startswith("linux") else []
    sources = [object_file, output_dir / "sensor_binding_mocks.c", fakes]
    library = output_dir / f"sensor_pytest{LIBRARY_EXTENSION}"
    SubprocessExecutor(["clang", "-shared", "-fPIC", *linux_flags, f"-I{DATA_DIR.as_posix()}", *sources, "-o", library]).execute()


def import_binding(binding_file: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(binding_file.stem, binding_file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bind_binding_calls_python_mock(tmp_path: Path) -> None:
    object_file = compile_object(tmp_path)
    result = run_bind(SENSOR_SOURCE, object_file, tmp_path)
    assert result.exit_code == 0, result.output
    for generated in ["sensor_binding.py", "sensor_binding_mocks.c", "sensor_binding.log"]:
        assert (tmp_path / generated).exists()

    build_library(tmp_path, object_file)
    binding = import_binding(tmp_path / "sensor_binding.py")
    lib = binding.load()

    lib.sensor_offset.value = 2
    assert lib.measure(3) == 2
    assert lib.mocks.unexpected_calls == ["read_sensor"]

    read_sensor = Mock(return_value=40)
    lib.mocks.read_sensor = read_sensor
    assert lib.measure(3) == 42
    read_sensor.assert_called_once_with(3)

    assert lib.point_sum(ctypes.byref(binding.Point(1, 2))) == 3

    second = binding.node(None, 2)
    first = binding.node(ctypes.pointer(second), 1)
    assert lib.list_length(ctypes.byref(first)) == 2

    assert lib.current_mode.value == binding.Mode.MODE_ON
    assert lib.handle_is_null(None) == 1

    buffer = ctypes.create_string_buffer(b"temp")
    lib.mocks.sensor_name = Mock(return_value=ctypes.addressof(buffer))
    assert ctypes.cast(lib.current_sensor_name(), ctypes.c_char_p).value == b"temp"


def test_bind_logs_unsupported_symbols(tmp_path: Path) -> None:
    result = run_bind(SENSOR_SOURCE, compile_object(tmp_path), tmp_path)
    assert result.exit_code == 0, result.output

    log = (tmp_path / "sensor_binding.log").read_text()
    assert "log_message" in log
    assert "register_callback" in log

    mocks_source = (tmp_path / "sensor_binding_mocks.c").read_text()
    assert "clanguru_mock_read_sensor" in mocks_source
    assert "clanguru_unexpected_read_sensor" in mocks_source
    assert "clanguru_mock_log_message" not in mocks_source
    assert "clanguru_mock_register_callback" not in mocks_source


@pytest.mark.parametrize("strict", [True, False])
def test_bind_strict_fails_on_undefined_symbol_without_declaration(tmp_path: Path, strict: bool) -> None:
    unrelated_source = tmp_path / "unrelated.c"
    unrelated_source.write_text("int unrelated(void) { return 0; }\n")

    result = run_bind(unrelated_source, compile_object(tmp_path), tmp_path, "--strict" if strict else "--no-strict")

    assert (result.exit_code != 0) == strict
    assert "read_sensor" in (tmp_path / "sensor_binding.log").read_text()


def bind_and_load(tmp_path: Path, source_file: Path, fakes: Path = DATA_DIR / "fakes.c") -> ModuleType:
    object_file = compile_object(tmp_path, source_file)
    result = run_bind(source_file, object_file, tmp_path)
    assert result.exit_code == 0, result.output
    build_library(tmp_path, object_file, fakes)
    return import_binding(tmp_path / "sensor_binding.py")


def test_bind_load_resets_python_mocks(tmp_path: Path) -> None:
    binding = bind_and_load(tmp_path, SENSOR_SOURCE)
    first = binding.load()
    first.measure(3)
    first.mocks.read_sensor = Mock(return_value=40)

    second = binding.load()
    assert second.mocks.read_sensor is None
    assert second.mocks.unexpected_calls == []

    del first
    gc.collect()
    assert second.measure(3) == 0
    assert second.mocks.unexpected_calls == ["read_sensor"]


def test_bind_skips_function_with_anonymous_nested_struct(tmp_path: Path) -> None:
    lib = bind_and_load(tmp_path, DATA_DIR / "anon.c").load()

    assert not hasattr(lib, "anon_sum")
    assert "anon_sum" in (tmp_path / "sensor_binding.log").read_text()


def test_bind_passes_array_parameters_as_pointers(tmp_path: Path) -> None:
    lib = bind_and_load(tmp_path, DATA_DIR / "arrays.c").load()

    lib.mocks.fill = lambda buffer: buffer[0] + buffer[3]
    assert lib.fill_sum() == 5
    assert lib.sum4((ctypes.c_int * 4)(1, 2, 3, 4)) == 10


def test_bind_defines_undefined_array_variable(tmp_path: Path) -> None:
    lib = bind_and_load(tmp_path, DATA_DIR / "table.c", DATA_DIR / "table_fakes.c").load()

    lib.table[1] = 7
    assert lib.table_at(1) == 7
    assert "handler" in (tmp_path / "sensor_binding.log").read_text()
    assert "handler" not in (tmp_path / "sensor_binding_mocks.c").read_text()


def test_bind_finds_system_headers_with_gcc_compile_database(tmp_path: Path) -> None:
    source_file = DATA_DIR / "color.c"
    compilation_database = tmp_path / "compile_commands.json"
    compilation_database.write_text(
        json.dumps([{"directory": tmp_path.as_posix(), "file": source_file.as_posix(), "command": f"gcc -I{DATA_DIR.as_posix()} -c {source_file.as_posix()}"}])
    )

    result = run_bind(source_file, compile_object(tmp_path, source_file), tmp_path, "--compilation-database", compilation_database.as_posix())
    assert result.exit_code == 0, result.output

    log = (tmp_path / "sensor_binding.log").read_text()
    assert f"{source_file} : OK" in log
    unsupported = log.split("unsupported symbols:")[1].split("excluded symbols:")[0]
    assert "color_red" not in unsupported
    assert "set_light" not in unsupported
    binding = import_binding(tmp_path / "sensor_binding.py")
    assert binding.RGBColor._fields_ == [("red", ctypes.c_ubyte), ("green", ctypes.c_ubyte), ("blue", ctypes.c_ubyte)]
