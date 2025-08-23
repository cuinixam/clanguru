from pathlib import Path

import pytest
from typer.testing import CliRunner

from clanguru.main import app

runner = CliRunner()


@pytest.mark.skip(reason="exploratory test")
def test_generate(tmp_path: Path) -> None:
    output_file = tmp_path / "output.md"
    result = runner.invoke(
        app,
        [
            "generate",
            "--source-file",
            "D:/ateliere/spled/src/power_signal_processing/test/test_power_signal_processing.cc",
            "--output-file",
            output_file.as_posix(),
            "--compilation-database",
            "D:/ateliere/spled/build/CustA/Disco/test/compile_commands.json",
        ],
    )
    assert result.exit_code == 0


def test_mock(tmp_path: Path) -> None:
    header_file = tmp_path / "test.h"
    header_file.write_text("""
    extern int add(int a, int b);
    """)
    source_file = tmp_path / "test.c"
    source_file.write_text("""
    #include "test.h"
    int calculate(int x, int y) {
        return add(x, y);
    }
    """)
    result = runner.invoke(
        app,
        [
            "mock",
            "--source-file",
            source_file.as_posix(),
            "--output-dir",
            tmp_path.as_posix(),
            "--symbol",
            "add",
            "--filename",
            "my_mock",
        ],
    )
    assert result.exit_code == 0

    for mock_file in ["my_mock.h", "my_mock.cc"]:
        assert (tmp_path / mock_file).exists()


def test_mock_strict_mode(tmp_path: Path) -> None:
    header_file = tmp_path / "test.h"
    header_file.write_text("""
    extern int add(int a, int b);
    """)
    source_file = tmp_path / "test.c"
    source_file.write_text("""
    #include "test.h"
    #include "non_existent.h"
    int calculate(int x, int y) {
        return add(x, y);
    }
    """)
    result = runner.invoke(
        app,
        [
            "mock",
            "--source-file",
            source_file.as_posix(),
            "--output-dir",
            tmp_path.as_posix(),
            "--symbol",
            "non_existent_function",
            "--filename",
            "my_mock",
            "--strict",
        ],
    )
    # Expect failure with aggregated error message directing user to log file.
    assert result.exit_code != 0
    assert "Mock generation for 'my_mock' failed" in str(result.exception)
    log_file = tmp_path / "my_mock.log"
    assert log_file.exists()
    log_content = log_file.read_text()
    # Ensure the log captures parsing error and missing symbol summary.
    assert "non_existent.h" in log_content  # parsing error recorded
    assert "missing_symbol:non_existent_function" in log_content or "non_existent_function" in log_content
    assert "status: failed" in log_content
