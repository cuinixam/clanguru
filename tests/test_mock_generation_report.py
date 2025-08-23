from pathlib import Path
from unittest.mock import Mock

import pytest

from clanguru.mock_generator import (
    FileParseResult,
    FoundFunction,
    FoundSymbol,
    FoundVariable,
    FunctionArgument,
    MockGenerationIssues,
    MockGenerationReport,
    MockType,
)


@pytest.fixture
def mock_translation_unit():
    mock_tu = Mock()
    mock_tu.source_file = Path("/fake/source.c")
    return mock_tu


@pytest.fixture
def sample_found_function(mock_translation_unit):
    # Create a mock symbol that behaves like a Function declaration
    mock_symbol = Mock()
    mock_symbol.kind.name = "FUNCTION_DECL"

    symbol = FoundSymbol(translation_unit=mock_translation_unit, symbol=mock_symbol, header_file="test.h")

    return FoundFunction(
        name="test_function", return_type="int", parameters=[FunctionArgument(name="param1", type="int"), FunctionArgument(name="param2", type="char*")], origin=symbol
    )


@pytest.fixture
def sample_found_variable(mock_translation_unit):
    # Create a mock symbol that behaves like a Variable declaration
    mock_symbol = Mock()
    mock_symbol.kind.name = "VAR_DECL"

    symbol = FoundSymbol(translation_unit=mock_translation_unit, symbol=mock_symbol, header_file="test.h")

    return FoundVariable(name="test_variable", type="int", origin=symbol)


def test_file_parse_result():
    # Successful parse
    success_result = FileParseResult(path=Path("test.c"), error=None)
    assert success_result.is_successful is True

    # Failed parse
    fail_result = FileParseResult(path=Path("test.c"), error="syntax error")
    assert fail_result.is_successful is False


def test_mock_generation_issues():
    # No issues
    no_issues = MockGenerationIssues(parse_errors=[FileParseResult(Path("test.c"), None)], missing_symbols=[], unsupported_functions=[], excluded_symbols=[])
    assert no_issues.has_any_issues is False
    assert len(no_issues.parse_errors_with_failures) == 0

    # With issues
    with_issues = MockGenerationIssues(
        parse_errors=[FileParseResult(Path("good.c"), None), FileParseResult(Path("bad.c"), "syntax error")],
        missing_symbols=["missing_func"],
        unsupported_functions=["variadic_func"],
        excluded_symbols=["excluded_func"],
    )
    assert with_issues.has_any_issues is True
    assert len(with_issues.parse_errors_with_failures) == 1
    assert with_issues.parse_errors_with_failures[0].path == Path("bad.c")


def test_mock_generation_report_success(sample_found_function, sample_found_variable):
    report_generator = MockGenerationReport(filename="test_mock", mock_type=MockType.GMOCK, requested_symbols={"test_function", "test_variable"})

    issues = MockGenerationIssues(parse_errors=[FileParseResult(Path("test.c"), None)], missing_symbols=[], unsupported_functions=[], excluded_symbols=[])

    report = report_generator.generate_report(issues=issues, rendered_functions=[sample_found_function], rendered_variables=[sample_found_variable], status="success")

    # Check key sections are present
    assert "mock generation report for: test_mock" in report
    assert "mock type: gmock" in report
    assert "test.c : OK" in report
    assert "requested symbols (2):" in report
    assert "test_function" in report
    assert "test_variable" in report
    assert "function test_function -> header=test.h" in report
    assert "variable test_variable -> header=test.h" in report
    assert "status: success" in report
    assert "functions mocked: 1" in report
    assert "variables mocked: 1" in report


def test_mock_generation_report_with_failures():
    report_generator = MockGenerationReport(filename="failed_mock", mock_type=MockType.GMOCK, requested_symbols={"existing_func", "missing_func", "variadic_func"})

    issues = MockGenerationIssues(
        parse_errors=[FileParseResult(Path("good.c"), None), FileParseResult(Path("bad.c"), "header not found")],
        missing_symbols=["missing_func"],
        unsupported_functions=["variadic_func"],
        excluded_symbols=[],
    )

    report = report_generator.generate_report(
        issues=issues,
        rendered_functions=[],  # No functions successfully rendered
        rendered_variables=[],
        status="failed",
    )

    # Check failure indicators
    assert "bad.c : ERROR - header not found" in report
    assert "missing_func : reason=not_found" in report
    assert "variadic_func : reason=variadic_not_supported" in report
    assert "status: failed" in report
    assert "functions mocked: 0" in report
    assert "variables mocked: 0" in report

    # Check raw issues section
    assert "issues (raw):" in report
    assert "parse_error:bad.c:header not found" in report
    assert "missing_symbol:missing_func" in report
    assert "unsupported_variadic:variadic_func" in report


def test_mock_generation_report_empty_case():
    report_generator = MockGenerationReport(filename="empty_mock", mock_type=MockType.GMOCK, requested_symbols=set())

    issues = MockGenerationIssues(parse_errors=[], missing_symbols=[], unsupported_functions=[], excluded_symbols=[])

    report = report_generator.generate_report(issues=issues, rendered_functions=[], rendered_variables=[], status="success")

    assert "(no sources processed)" in report
    assert "requested symbols (0):" in report
    assert "mocked symbols:" in report
    assert "(none)" in report
    assert "functions mocked: 0" in report
