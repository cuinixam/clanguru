import textwrap
from pathlib import Path
from textwrap import dedent

import pytest

from clanguru.cparser import CLangParser, TranslationUnit
from clanguru.doc_generator import (
    CodeContent,
    DocsFormat,
    MarkdownFlavour,
    MarkdownFormatter,
    RSTFormatter,
    Section,
    TextContent,
    generate_doc_structure,
    generate_documentation,
)
from tests.conftest import assert_element_of_type, assert_elements_of_type, get_test_data_file


@pytest.fixture
def c_source(tmp_path: Path) -> TranslationUnit:
    file_content = dedent("""\
    /** @docs This is a test function @enddocs */
    int test_function() {
        return 0;
    }

    /**
     * \\docs
     * This is a multi-line
     * function description
     * \\enddocs
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
    doc_structure = generate_doc_structure(c_source, DocsFormat.md)
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
    :lineno-start: 12

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
    doc_structure = generate_doc_structure(c_source, DocsFormat.rst)
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
       :lineno-start: 12

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
    doc_structure = generate_doc_structure(c_source_with_traceability, DocsFormat.rst)
    assert doc_structure.title == "test.c"
    assert len(doc_structure.sections) == 1
    functions_section = doc_structure.sections[0]
    assert functions_section.title == "Functions"
    section = assert_element_of_type(functions_section.subsections, Section)
    assert section.title == "function_with_traceability"
    section_text = assert_element_of_type(section.content, TextContent)
    assert section_text.text == dedent("""\
        .. impl:: Function with Traceability
           :id: SWIMPL_FT-001
           :implements: SWDD_FT-101""")
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


def test_doc_structure_for_gtest_files() -> None:
    doc_structure = generate_doc_structure(CLangParser().load(get_test_data_file("test_gtest.cc")), DocsFormat.md)
    assert len(doc_structure.sections) == 1
    classes_section = doc_structure.sections[0]
    assert classes_section.title == "Classes"
    sections = assert_elements_of_type(classes_section.subsections, Section, 2)
    assert {section.title for section in sections} == {"MyMock", "power_signal_processing_test_power_stays_off"}
    test_section = assert_element_of_type(classes_section.subsections, Section, lambda s: s.title == "power_signal_processing_test_power_stays_off")

    # Check that we have both text content (description) and code content
    text_content = assert_element_of_type(test_section.content, TextContent)
    code_content = assert_element_of_type(test_section.content, CodeContent)

    # Verify the text content contains the test directive
    assert text_content.text == textwrap.dedent("""\
        ```{test} power_signal_processing.test_power_stays_off
           :id: TS_PSP-001
           :tests: SWDD_PSP-001

        ```""")

    # Verify the code content contains the test declaration
    assert code_content.code == "TEST(power_signal_processing, test_power_stays_off)"
    assert code_content.start_line == 30


def test_generate_documentation(c_source: TranslationUnit, tmp_path: Path) -> None:
    # Generate Markdown documentation
    md_file = tmp_path / "test.md"
    generate_documentation(c_source, formatter=MarkdownFormatter(), output_file=md_file)
    assert md_file.exists()
    md_content = md_file.read_text()
    assert "# test.c" in md_content


def test_end_to_end_c_source_to_markdown_file(tmp_path: Path) -> None:
    """
    End-to-end: parse a .c file, generate a .md file, and verify its exact content.

    Uses `@docs` (generic) and `@md` (format-specific) tagged blocks between `/* START DOCS */`
    and `/* END DOCS */` markers. Untagged comments are ignored. An `@rst` block would also be
    ignored when generating markdown.
    """
    c_file = tmp_path / "generated.c"
    c_file.write_text(
        dedent("""\
        /* START DOCS */
        /** @docs
         *   Adds two integers and returns the result.
         * @enddocs
         */
        /**
         * The following block is tagged with @md, so it should also be included in the output.
         * @md
         * **Note:** overflow is not checked.
         * @endmd
         */
        /**
         * This comment is not tagged and should be ignored.
         * @rst
         * .. impl:: Sum Implementation
         *    :id: IMPL-SUM-001
         * @endrst
         */
        /* END DOCS */
        int sum(int a, int b) {
            /* START CODE */
            return a + b;
            /* END CODE */
        }
        """),
        newline="\n",
    )
    tu = CLangParser().load(c_file)

    md_file = tmp_path / "generated.md"
    generate_documentation(tu, formatter=MarkdownFormatter(MarkdownFlavour.Myst), output_file=md_file)

    expected = dedent("""\
        # generated.c

        ## Functions

        ### sum

        Adds two integers and returns the result.

        **Note:** overflow is not checked.

        ```{code-block} c
        :linenos:
        :lineno-start: 20

        int sum(int a, int b) {
            /* START CODE */
            return a + b;
            /* END CODE */
        }
        ```
        """)
    assert md_file.read_text() == expected


def test_generated_code_with_multiple_tagged_doc_blocks(tmp_path: Path) -> None:
    file_content = dedent("""\
    /* START DOCS */
    /** @docs
     *   This function does something important.
     * @enddocs
     */
    /** @rst
     * .. impl:: MyCompMain Implementation
     *    :id: IMPL-001
     * @endrst
     */
    /* END DOCS */
    void MyCompMain() {
        /* START CODE */
        /* END CODE */
    }
    """)
    file_path = tmp_path / "generated.c"
    file_path.write_text(file_content, newline="\n")
    tu = CLangParser().load(file_path)

    # Only the two tagged comments are kept, in source order
    functions = CLangParser.get_functions(tu)
    func = next(f for f in functions if f.name == "MyCompMain")
    assert len(func.description_tokens) == 4

    # Doc structure: one TextContent per tagged block, then the code
    doc = generate_doc_structure(tu, DocsFormat.rst)
    func_section = doc.sections[0].subsections[0]
    assert func_section.title == "MyCompMain"
    text_blocks = [c for c in func_section.content if isinstance(c, TextContent)]
    code_blocks = [c for c in func_section.content if isinstance(c, CodeContent)]
    assert len(text_blocks) == 2
    assert len(code_blocks) == 1
    assert text_blocks[0].text == "This function does something important."
    assert text_blocks[1].text == dedent("""\
        .. impl:: MyCompMain Implementation
           :id: IMPL-001""")

    # Markdown output: both text blocks appear before the code block
    formatter = MarkdownFormatter(MarkdownFlavour.Myst)
    output = formatter.format(doc)
    func_output = output.split("### MyCompMain")[1]
    plain_idx = func_output.index("This function does something important.")
    rst_idx = func_output.index(".. impl::")
    code_idx = func_output.index("```{code-block}")
    assert plain_idx < rst_idx < code_idx


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


def test_crlf_line_endings_function_comment_extraction(tmp_path: Path) -> None:
    """
    Regression test: ensure CRLF line endings in function comments are normalized.

    We create two identical source files with multi-line comments differing only by
    newline style (LF vs CRLF) and confirm the extracted comment content is identical
    and uses normalized LF line endings.
    """
    lf_content = dedent("""\
        /*! This function does something important
         * @param value The input value
         * @return The result
         */
        int test_function(int value) {
            int result = value * 2;
            return result;
        }""")

    crlf_content = lf_content.replace("\n", "\r\n")

    lf_file = tmp_path / "sample_lf.c"
    crlf_file = tmp_path / "sample_crlf.c"

    # Write explicit newline styles
    lf_file.write_bytes(lf_content.encode("utf-8"))
    crlf_file.write_bytes(crlf_content.encode("utf-8"))

    parser = CLangParser()
    tu_lf = parser.load(lf_file)
    tu_crlf = parser.load(crlf_file)

    func_lf = {f.name: f for f in CLangParser.get_functions(tu_lf)}["test_function"]
    func_crlf = {f.name: f for f in CLangParser.get_functions(tu_crlf)}["test_function"]

    expected_description = "This function does something important\n@param value The input value\n@return The result"

    # Both functions should have the same description with normalized LF line endings
    assert func_lf.description == expected_description
    assert func_crlf.description == expected_description
    assert func_lf.description == func_crlf.description


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


def test_multiple_doc_blocks_in_single_comment(tmp_path: Path) -> None:
    file_content = dedent("""\
    /**
     * @docs
     * First block.
     * @enddocs
     *
     * @md
     * Second block.
     * @endmd
     *
     * @docs
     * Third block.
     * @enddocs
     */
    void my_flexible_function() {
    }
    """)
    file_path = tmp_path / "flexible.c"
    file_path.write_text(file_content, newline="\n")
    tu = CLangParser().load(file_path)

    doc = generate_doc_structure(tu, DocsFormat.md)
    func_section = doc.sections[0].subsections[0]

    text_blocks = [c.text for c in func_section.content if isinstance(c, TextContent)]
    assert text_blocks == ["First block.", "Second block.", "Third block."]
