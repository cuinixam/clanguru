from pathlib import Path
from textwrap import dedent

from clanguru.cparser import CLangParser
from clanguru.mock_generator import (
    FoundFunction,
    FoundVariable,
    FunctionArgument,
    MocksGenerator,
    MocksGeneratorConfig,
    MockType,
    extract_symbols_data,
    find_symbols,
)
from tests.conftest import assert_element_of_type, assert_elements_of_type


def test_find_symbols_functions_and_variables(tmp_path: Path) -> None:
    header = tmp_path / "api.h"
    header.write_text(
        dedent(
            """
            extern void foo(int x);
            extern int bar;
            """
        )
    )

    source = tmp_path / "impl.c"
    source.write_text(
        dedent(
            """
            #include "api.h"
            #include "more.h"
            static void my_func() {
                bar = 42;
                foo(bar);
            }
            """
        )
    )

    parser = CLangParser()
    tu = parser.load(source)

    # Act
    data = extract_symbols_data(find_symbols([tu], {"foo", "bar"}))

    # Assert
    assert len(data) == 2
    my_var = assert_element_of_type(data, FoundVariable)
    assert my_var.name == "bar"
    assert my_var.type == "int"
    my_func = assert_element_of_type(data, FoundFunction)
    assert my_func.name == "foo"
    assert my_func.return_type == "void"
    my_param = assert_element_of_type(my_func.parameters, FunctionArgument)
    assert my_param.name == "x"
    assert my_param.type == "int"


def test_symbol_not_found(tmp_path: Path) -> None:
    header = tmp_path / "api.h"
    header.write_text(
        dedent(
            """
            typedef float my_type;
            extern unsigned char foo(my_type*);
            """
        )
    )

    source = tmp_path / "impl.c"
    source.write_text(
        dedent(
            """
            #include "api.h"
            static void my_func() {
                my_type x;
                foo(&x);
                missing_symbol();
            }
            """
        )
    )

    parser = CLangParser()
    tu = parser.load(source)
    data = extract_symbols_data(find_symbols([tu], {"missing_symbol", "foo"}))
    my_func = assert_element_of_type(data, FoundFunction)
    assert my_func.name == "foo"
    assert my_func.return_type == "unsigned char"
    my_param = assert_element_of_type(my_func.parameters, FunctionArgument)
    assert my_param.name == ""
    assert my_param.type == "my_type *"
    assert my_param.is_pointer is True


def test_symbol_declared_in_source_file(tmp_path: Path) -> None:
    source = tmp_path / "impl.c"
    source.write_text(
        dedent(
            """
            extern void foo(void);
            static void my_func() {
                foo();
            }
            """
        )
    )

    parser = CLangParser()
    tu = parser.load(source)

    results = find_symbols([tu], {"foo"})
    assert [r.symbol.name for r in results] == ["foo"]
    foo = next(r for r in results if r.symbol.name == "foo")
    assert foo.header_file is None

    data = extract_symbols_data(results)
    my_func = assert_element_of_type(data, FoundFunction)
    assert my_func.name == "foo"


def write_source(tmp_path: Path) -> Path:
    header = tmp_path / "api.h"
    header.write_text(
        dedent(
            """
            extern int foo(int a, int b);
            extern int global_counter;
            """
        )
    )
    source = tmp_path / "impl.c"
    source.write_text(
        dedent(
            """
            #include "api.h"
            int foo(int a, int b) { return a + b; }
            int global_counter = 0;
            """
        )
    )
    return source


def test_generate_exclude_symbols(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    outdir = tmp_path / "out"
    config = MocksGeneratorConfig(
        mock_type=MockType.GMOCK,
        exclude_symbol_patterns=["_*", "mem_copy"],
    )
    gen = MocksGenerator(
        source_files=[source],
        symbols=["foo", "global_counter", "_global", "mem_copy"],
        output_dir=outdir,
        filename="mock_my_comp",
        compilation_database=None,
        config=config,
    )
    gen.generate()
    log_file = outdir / "mock_my_comp.log"
    assert log_file.exists()
    log_file_content = log_file.read_text()
    for symbol in ["_global", "mem_copy"]:
        assert f"{symbol} : reason=excluded_by_pattern" in log_file_content


def test_generate_with_config_file(tmp_path: Path) -> None:
    # Create source files
    source = write_source(tmp_path)
    outdir = tmp_path / "out"

    # Create config file
    config_file = tmp_path / "mock_config.yaml"
    config_file.write_text("""
strict: false
exclude_symbol_patterns:
  - "_*"
  - "mem_copy"
mock_type: gmock
""")

    # Load config from file and create generator
    config = MocksGeneratorConfig.from_file(config_file)
    gen = MocksGenerator(
        source_files=[source],
        symbols=["foo", "global_counter", "_global", "mem_copy"],
        output_dir=outdir,
        filename="mock_my_comp",
        compilation_database=None,
        config=config,
    )
    gen.generate()

    # Verify results
    log_file = outdir / "mock_my_comp.log"
    assert log_file.exists()
    log_file_content = log_file.read_text()
    for symbol in ["_global", "mem_copy"]:
        assert f"{symbol} : reason=excluded_by_pattern" in log_file_content
    assert "status: success" in log_file_content  # Should succeed since strict=false


def test_symbols_deduplication_across_multiple_translation_units(tmp_path: Path) -> None:
    """Test that duplicate symbols found across multiple source files are properly deduplicated."""
    # Create a shared header with function and variable declarations
    shared_header = tmp_path / "shared_api.h"
    shared_header.write_text(
        dedent(
            """
            #ifndef SHARED_API_H
            #define SHARED_API_H

            extern int shared_function(int param);
            extern void init_function(void);
            extern int shared_variable;

            #endif /* SHARED_API_H */
            """
        )
    )

    # Create multiple source files that all include the same header
    source_files = []
    for i in range(3):
        source = tmp_path / f"source{i + 1}.c"
        source.write_text(
            dedent(
                f"""
                #include "shared_api.h"

                static void local_function{i + 1}() {{
                    shared_variable = {i + 1};
                    shared_function(shared_variable);
                    init_function();
                }}
                """
            )
        )
        source_files.append(source)

    # Parse all source files
    parser = CLangParser()
    translation_units = [parser.load(source) for source in source_files]

    # Find symbols across all translation units
    symbols_to_find = {"shared_function", "init_function", "shared_variable"}
    found_symbols = find_symbols(translation_units, symbols_to_find)

    # Verify deduplication: each symbol should appear exactly once despite being in multiple TUs
    symbol_names = [fs.symbol.name for fs in found_symbols]
    name_counts = {name: symbol_names.count(name) for name in set(symbol_names)}

    assert name_counts["shared_function"] == 1, f"Expected 1 shared_function, got {name_counts['shared_function']}"
    assert name_counts["init_function"] == 1, f"Expected 1 init_function, got {name_counts['init_function']}"
    assert name_counts["shared_variable"] == 1, f"Expected 1 shared_variable, got {name_counts['shared_variable']}"

    # Verify extracted data is also deduplicated using helper functions
    symbols_data = extract_symbols_data(found_symbols)

    # Should find exactly 2 functions and 1 variable
    functions = assert_elements_of_type(symbols_data, FoundFunction, 2)
    variables = assert_elements_of_type(symbols_data, FoundVariable, 1)

    # Verify specific functions exist exactly once
    shared_func = assert_element_of_type(functions, FoundFunction, lambda f: f.name == "shared_function")
    init_func = assert_element_of_type(functions, FoundFunction, lambda f: f.name == "init_function")
    shared_var = assert_element_of_type(variables, FoundVariable, lambda v: v.name == "shared_variable")

    # Verify function properties
    assert shared_func.return_type == "int"
    assert len(shared_func.parameters) == 1
    assert shared_func.parameters[0].name == "param"
    assert shared_func.parameters[0].type == "int"

    assert init_func.return_type == "void"
    assert len(init_func.parameters) == 0

    # Verify variable properties
    assert shared_var.type == "int"
