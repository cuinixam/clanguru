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
