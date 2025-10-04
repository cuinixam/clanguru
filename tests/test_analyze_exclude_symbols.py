"""Tests for the analyze command with exclude symbol patterns."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from clanguru.main import app
from clanguru.object_analyzer import ObjectDependencies, Symbol, SymbolLinkage, filter_object_data_symbols

runner = CliRunner()


def test_filter_object_data_symbols_helper() -> None:
    """Test the filter_object_data_symbols function directly."""
    # Create test object data
    obj1 = ObjectDependencies(Path("test1.o"))
    obj1.symbols = [
        Symbol("main", SymbolLinkage.LOCAL),
        Symbol("_internal_func", SymbolLinkage.LOCAL),
        Symbol("printf", SymbolLinkage.EXTERN),
        Symbol("_debug_var", SymbolLinkage.EXTERN),
    ]

    obj2 = ObjectDependencies(Path("test2.o"))
    obj2.symbols = [
        Symbol("helper", SymbolLinkage.LOCAL),
        Symbol("_private_func", SymbolLinkage.LOCAL),
        Symbol("malloc", SymbolLinkage.EXTERN),
    ]

    object_data = [obj1, obj2]

    # Test with no exclude patterns
    filtered = filter_object_data_symbols(object_data, None)
    assert len(filtered) == 2
    assert len(filtered[0].symbols) == 4
    assert len(filtered[1].symbols) == 3

    # Test with exclude patterns
    filtered = filter_object_data_symbols(object_data, ["_*"])
    assert len(filtered) == 2
    # Should exclude _internal_func, _debug_var from obj1 and _private_func from obj2
    assert len(filtered[0].symbols) == 2
    assert len(filtered[1].symbols) == 2

    # Check that the correct symbols remain
    obj1_symbol_names = {s.name for s in filtered[0].symbols}
    assert obj1_symbol_names == {"main", "printf"}

    obj2_symbol_names = {s.name for s in filtered[1].symbols}
    assert obj2_symbol_names == {"helper", "malloc"}

    # Test with multiple patterns
    filtered = filter_object_data_symbols(object_data, ["_*", "printf"])
    assert len(filtered[0].symbols) == 1  # only main remains
    assert filtered[0].symbols[0].name == "main"


@pytest.mark.skip(reason="Integration test requiring compilation database")
def test_analyze_with_exclusion_option(tmp_path: Path) -> None:
    """Test the analyze command with exclude-symbol-pattern option."""
    # Create a mock compilation database
    compile_db = tmp_path / "compile_commands.json"
    compile_db.write_text(json.dumps([{"directory": str(tmp_path), "command": "gcc -c test.c -o test.o", "file": str(tmp_path / "test.c"), "output": str(tmp_path / "test.o")}]))

    # Mock object files
    obj_files = [tmp_path / "test.o"]
    for obj_file in obj_files:
        obj_file.write_bytes(b"fake object content")

    # Mock the parse_objects function to return predictable data
    mock_obj_data = [
        ObjectDependencies(
            path=tmp_path / "test.o",
            symbols=[
                Symbol("main", SymbolLinkage.LOCAL),
                Symbol("_internal_func", SymbolLinkage.LOCAL),
                Symbol("printf", SymbolLinkage.EXTERN),
                Symbol("_debug_var", SymbolLinkage.EXTERN),
            ],
        )
    ]

    output_file = tmp_path / "analysis_report.txt"

    with patch("clanguru.main.parse_objects", return_value=mock_obj_data):
        with patch("clanguru.main.CompilationDatabase.from_json_file") as mock_db:
            mock_db.return_value.get_output_files.return_value = obj_files

            result = runner.invoke(
                app,
                [
                    "analyze",
                    "--compilation-database",
                    str(compile_db),
                    "--output-file",
                    str(output_file),
                    "--exclude-symbol-pattern",
                    "_*",
                ],
            )

    # The command should succeed
    assert result.exit_code == 0

    # The output file should be created
    assert output_file.exists()

    # The report should contain filtered symbols (not the excluded ones)
    report_content = output_file.read_text()
    assert "main" in report_content
    assert "printf" in report_content
    # These should be excluded by the pattern
    assert "_internal_func" not in report_content
    assert "_debug_var" not in report_content
