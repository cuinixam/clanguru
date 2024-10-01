from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

import pytest

from clanguru.compilation_options_manager import CompilationOptionsManager
from clanguru.cparser import CLangParser, Token


@pytest.fixture
def c_source_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "comp.c"
    file_path.write_text(
        dedent("""\
        extern void external_function();
        extern void used_external_function();

        extern int external_variable;
        extern int used_external_variable;

        /*
        This description is ignored
        */

        extern void local_function();
        int local_variable;

        // Some description for the call_external_functions function
        void call_external_functions()
        {
            local_function();
            used_external_function();
            used_external_variable++;
        }

        /*
        Some description for the local function
        */
        static void local_function()
        {
            local_variable++;
        }
    """)
    )
    return file_path


def test_cparser(c_source_file: Path) -> None:
    parser = CLangParser()
    translation_unit = parser.load(c_source_file)

    assert translation_unit.raw_tu is not None
    assert len(translation_unit.tokens) > 0
    assert len(translation_unit.nodes) > 0

    # Check the first token
    first_token = next(iter(translation_unit.tokens))
    assert first_token.raw_token.spelling == "extern"
    assert first_token.previous_token is None

    # Check the first node
    first_node = next(iter(translation_unit.nodes))
    assert first_node.raw_node.kind.name == "FUNCTION_DECL"
    assert first_node.previous_node is None

    # Check the function extraction
    functions = parser.get_functions(translation_unit)
    assert len(functions) == 5
    # Find the functions definitions
    function_decls = [func for func in functions if func.is_definition]
    assert len(function_decls) == 2
    assert [func.name for func in function_decls] == ["call_external_functions", "local_function"]
    assert function_decls[0].description_token is not None
    assert function_decls[0].description_token.raw_token.spelling == "// Some description for the call_external_functions function"
    assert function_decls[1].description_token is not None
    assert "Some description for the local function" in function_decls[1].description_token.raw_token.spelling


def test_ctokens_collection(c_source_file: Path) -> None:
    parser = CLangParser()
    tokens = parser.load(c_source_file).tokens
    assert len(tokens) > 0
    raw_tokens = [token.raw_token for token in tokens]
    found_token = tokens.find_matching_token(raw_tokens[0])
    assert found_token is not None


def test_parsing_function(tmp_path: Path) -> None:
    file = tmp_path / "function.c"
    file.write_text(
        dedent("""
        // This is a test function
        int test_function() {
            int x = 5;
            return x * 2;
        }""")
    )
    functions = CLangParser.get_functions(CLangParser().load(file))
    assert len(functions) == 1
    expected_body = dedent("""\
        int test_function() {
            int x = 5;
            return x * 2;
        }""")

    assert functions[0].body == expected_body


def create_comment_token(comment: str) -> Token:
    with TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "comment.c"
        file_path.write_text(comment, newline="\n")
        parser = CLangParser()
        translation_unit = parser.load(file_path)
        return next(iter(translation_unit.tokens))


@pytest.mark.parametrize(
    "comment,expected",
    [
        ("// This is a single-line comment", "This is a single-line comment"),
        ("/* This is a single-line block comment */", "This is a single-line block comment"),
        ("/* This is a\n * multi-line\n * comment\n */", "This is a\nmulti-line\ncomment"),
        ("// Comment with trailing spaces    ", "Comment with trailing spaces"),
        ("/* Comment with\n * asterisks\n * and spaces\n */", "Comment with\nasterisks\nand spaces"),
        ("// Empty comment", "Empty comment"),
        ("/**/", ""),
        ("// ", ""),
        ("/* Irregular\nformatting\n  * with\n   varying\n* indentation */", "Irregular\nformatting\nwith\nvarying\nindentation"),
    ],
)
def test_get_comment_content(comment: str, expected: str) -> None:
    token = create_comment_token(comment)
    result = CLangParser.get_comment_content(token)
    assert result == expected


def test_get_doxygen_comment_content() -> None:
    result = CLangParser.get_comment_content(
        create_comment_token(
            dedent("""\
    /*!
    * @rst
    *
    * .. impl:: Some implementation
    *    :id: SWIMPL-001
    * @endrst
    */
    """)
        )
    )
    assert result == dedent("""\
    @rst

    .. impl:: Some implementation
       :id: SWIMPL-001
    @endrst""")


@pytest.fixture
def cpp_test_file(tmp_path: Path) -> Path:
    # Create test.h
    test_h = tmp_path / "test.h"
    test_h.write_text(
        dedent("""\
        #define TEST_CLASS(test_suite_name, test_name) \
        extern int __test_class_dummy; \
        class test_suite_name##_##test_name##_Test { \
        public: \
            void TestBody(); \
        }; \
        void test_suite_name##_##test_name##_Test::TestBody()

        #define TEST(test_name) \
        extern int __test_dummy; \
        void test_name##_TestBody()
    """)
    )

    # Create test.cc
    test_cc = tmp_path / "test.cc"
    test_cc.write_text(
        dedent("""\
        #include "test.h"

        /*
        Description for my_test class
        */
        TEST_CLASS(my_comp, my_test)
        {
            // Test implementation
        }

        /*
        Description for my_test test
        */
        TEST(my_test)
        {
            // Test implementation
        }
    """)
    )

    return test_cc


def test_cparser_cpp_with_macros(cpp_test_file: Path) -> None:
    options_manager = CompilationOptionsManager()
    options_manager.set_default_options(["-x", "c++"])
    translation_unit = CLangParser().load(cpp_test_file, options_manager)

    print(translation_unit)
    functions = CLangParser.get_functions(translation_unit)
    assert len(functions) == 1
    assert functions[0].is_definition
    assert functions[0].name == "my_test_TestBody"
    assert functions[0].description_token is not None
    assert functions[0].description == "Description for my_test test"

    classes = CLangParser.get_classes(translation_unit)
    assert len(classes) == 1
    assert classes[0].name == "my_comp_my_test_Test"
    assert classes[0].description_token is not None
    assert classes[0].description == "Description for my_test class"


def test_parsing_variables(tmp_path: Path) -> None:
    file = tmp_path / "variable.c"
    file.write_text(
        dedent("""
        #define SWITCH 1
        #ifdef SWITCH
            #define INIT_VALUE 666
        #else
            #define INIT_VALUE 0
        #endif
        int my_var1 = INIT_VALUE;
        int my_var2 = 13;
        int my_var3 = my_var1;
    """)
    )
    variables = CLangParser.get_variables(CLangParser().load(file))
    assert len(variables) == 3
    assert variables[0].get_init_value() == "666"
    assert variables[1].get_init_value() == "13"
    assert variables[2].get_init_value() == "my_var1"

    file.write_text(
        dedent("""
        #ifdef SWITCH
            #define INIT_VALUE 666
        #else
            #define INIT_VALUE 0
        #endif
        int my_var1 = INIT_VALUE;
        int my_var2 = 13;
        int my_var3 = my_var1;
    """)
    )
    variables = CLangParser.get_variables(CLangParser().load(file))
    assert len(variables) == 3
    assert variables[0].get_init_value() == "0"
    assert variables[1].get_init_value() == "13"
    assert variables[2].get_init_value() == "my_var1"
