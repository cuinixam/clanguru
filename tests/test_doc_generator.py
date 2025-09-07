from pathlib import Path
from textwrap import dedent

import pytest

from clanguru.cparser import CLangParser, TranslationUnit
from clanguru.doc_generator import (
    CodeContent,
    MarkdownFlavour,
    MarkdownFormatter,
    RSTFormatter,
    Section,
    TextContent,
    generate_doc_structure,
    generate_documentation,
)
from tests.conftest import assert_element_of_type


@pytest.fixture
def c_source(tmp_path: Path) -> TranslationUnit:
    file_content = dedent("""\
    // This is a test function
    int test_function() {
        return 0;
    }

    /*
     * This is a multi-line
     * function description
     */
    void another_function(int arg) {
        if (arg > 0) {
            // Do something
        }
    }
    """)
    file_path = tmp_path / "test.c"
    file_path.write_text(file_content, newline="\n")
    return CLangParser().load(file_path)


def test_doc_generator_generate_doc_structure(c_source: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source)
    assert doc_structure.title == "test.c"
    assert len(doc_structure.sections) == 1
    functions_section = doc_structure.sections[0]
    assert functions_section.title == "Functions"
    assert {section.title for section in functions_section.subsections} == {
        "test_function",
        "another_function",
    }


def test_markdown_formatter(c_source: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source)
    formatter = MarkdownFormatter(MarkdownFlavour.Myst)
    output = formatter.format(doc_structure)

    expected_output = dedent("""\
    # test.c

    ## Functions

    ### test_function

    This is a test function

    ```{code-block} c
    :linenos:
    :lineno-start: 2

    int test_function() {
        return 0;
    }
    ```

    ### another_function

    This is a multi-line
    function description

    ```{code-block} c
    :linenos:
    :lineno-start: 10

    void another_function(int arg) {
        if (arg > 0) {
            // Do something
        }
    }
    ```
    """)

    assert output.strip() == expected_output.strip()
    assert formatter.file_extension() == "md"


def test_rst_formatter(c_source: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source)
    formatter = RSTFormatter()
    output = formatter.format(doc_structure)

    expected_output = dedent("""\
    test.c
    ======

    Functions
    ---------

    test_function
    ~~~~~~~~~~~~~

    This is a test function

    .. code-block:: c
       :linenos:
       :lineno-start: 2

        int test_function() {
            return 0;
        }


    another_function
    ~~~~~~~~~~~~~~~~

    This is a multi-line
    function description

    .. code-block:: c
       :linenos:
       :lineno-start: 10

        void another_function(int arg) {
            if (arg > 0) {
                // Do something
            }
        }
    """)

    assert output.strip() == expected_output.strip()
    assert formatter.file_extension() == "rst"


@pytest.fixture
def c_source_with_traceability(tmp_path: Path) -> TranslationUnit:
    file_content = dedent("""\
// This is a test function
#define ENABLE_FEATURE 1

#if ENABLE_FEATURE
/**
* @rst
* .. impl:: Function with Traceability
*    :id: SWIMPL_FT-001
*    :implements: SWDD_FT-101
* @endrst
*/
STATIC float function_with_traceability(int a, int b) {
    float result = 0;
    if (a > 0) {
        result = a + b;
    }
    else {
        result = b;
    }
    return result;
}
#endif

// Just some comment
""")
    file_path = tmp_path / "test.c"
    file_path.write_text(file_content, newline="\n")
    return CLangParser().load(file_path)


def test_doc_structure_with_traceability(c_source_with_traceability: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source_with_traceability)
    assert doc_structure.title == "test.c"
    assert len(doc_structure.sections) == 1
    functions_section = doc_structure.sections[0]
    assert functions_section.title == "Functions"
    section = assert_element_of_type(functions_section.subsections, Section)
    assert section.title == "function_with_traceability"
    section_text = assert_element_of_type(section.content, TextContent)
    assert section_text.text == dedent("""\
        @rst
        .. impl:: Function with Traceability
           :id: SWIMPL_FT-001
           :implements: SWDD_FT-101
        @endrst""")
    section_code = assert_element_of_type(section.content, CodeContent)
    assert section_code.code == dedent("""\
        STATIC float function_with_traceability(int a, int b) {
            float result = 0;
            if (a > 0) {
                result = a + b;
            }
            else {
                result = b;
            }
            return result;
        }""")


def test_generate_documentation(c_source: TranslationUnit, tmp_path: Path) -> None:
    # Generate Markdown documentation
    md_file = tmp_path / "test.md"
    generate_documentation(c_source, formatter=MarkdownFormatter(), output_file=md_file)
    assert md_file.exists()
    md_content = md_file.read_text()
    assert "# test.c" in md_content


def test_crlf_line_endings_function_body_extraction(tmp_path: Path) -> None:
    """
    Regression test: ensure CRLF line endings don't truncate function bodies.

    We create two identical source files differing only by newline style (LF vs CRLF)
    and confirm the extracted function bodies are identical.
    """
    lf_content = """// Comment about function\nint sample() {\n    int x = 1;\n    return x;\n}\n"""
    crlf_content = lf_content.replace("\n", "\r\n")

    lf_file = tmp_path / "sample_lf.c"
    crlf_file = tmp_path / "sample_crlf.c"

    # Write explicit newline styles
    lf_file.write_bytes(lf_content.encode("utf-8"))
    crlf_file.write_bytes(crlf_content.encode("utf-8"))

    parser = CLangParser()
    tu_lf = parser.load(lf_file)
    tu_crlf = parser.load(crlf_file)

    func_lf = {f.name: f for f in CLangParser.get_functions(tu_lf)}["sample"]
    func_crlf = {f.name: f for f in CLangParser.get_functions(tu_crlf)}["sample"]

    assert func_lf.body.content == func_crlf.body.content == "int sample() {\n    int x = 1;\n    return x;\n}"


def test_markdown_formatter_format_table() -> None:
    formatter = MarkdownFormatter()
    headers = ["Name", "Age"]
    rows = [["Alice", "30"], ["Bob", "25"]]
    table = formatter.format_table(headers, rows)
    expected = dedent("""\
    | Name | Age |
    | --- | --- |
    | Alice | 30 |
    | Bob | 25 |
    """)
    assert table == expected


def test_rst_formatter_format_table() -> None:
    formatter = RSTFormatter()
    headers = ["Name", "Age"]
    rows = [["Alice", "30"], ["Bob", "25"], ["Very Very Long Name", "1000"]]
    table = formatter.format_table(headers, rows)
    expected = dedent("""\
    +---------------------+------+
    | Name                | Age  |
    +=====================+======+
    | Alice               | 30   |
    +---------------------+------+
    | Bob                 | 25   |
    +---------------------+------+
    | Very Very Long Name | 1000 |
    +---------------------+------+
    """)
    assert table == expected
