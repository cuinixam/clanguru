from pathlib import Path
from textwrap import dedent

from clanguru.cparser import CLangParser
from clanguru.mock_generator import (
    FoundFunction,
    FoundVariable,
    FunctionArgument,
    extract_symbols_data,
    find_symbols,
)
from tests.conftest import assert_element_of_type


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
