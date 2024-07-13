from pathlib import Path
from textwrap import dedent

import pytest

from clanguru.cparser import CLangParser, TranslationUnit
from clanguru.doc_generator import MarkdownFormatter, RSTFormatter, generate_doc_structure, generate_documentation


@pytest.fixture
def c_source_translation_unit(tmp_path: Path) -> TranslationUnit:
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


def test_doc_generator_generate_doc_structure(c_source_translation_unit: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source_translation_unit)
    assert doc_structure.title == "test.c"
    assert len(doc_structure.sections) == 1
    functions_section = doc_structure.sections[0]
    assert functions_section.title == "Functions"
    assert len(functions_section.subsections) == 2
    assert functions_section.subsections[0].title == "test_function"
    assert functions_section.subsections[1].title == "another_function"


def test_markdown_formatter(c_source_translation_unit: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source_translation_unit)
    formatter = MarkdownFormatter()
    output = formatter.format(doc_structure)

    expected_output = dedent("""\
    # test.c

    ## Functions

    ### test_function

    This is a test function

    ```c
    int test_function() {
        return 0;
    }
    ```

    ### another_function

    This is a multi-line
    function description

    ```c
    void another_function(int arg) {
        if (arg > 0) {
            // Do something
        }
    }
    ```
    """)

    assert output.strip() == expected_output.strip()
    assert formatter.file_extension() == "md"


def test_rst_formatter(c_source_translation_unit: TranslationUnit) -> None:
    doc_structure = generate_doc_structure(c_source_translation_unit)
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

        int test_function() {
            return 0;
        }


    another_function
    ~~~~~~~~~~~~~~~~

    This is a multi-line
    function description

    .. code-block:: c

        void another_function(int arg) {
            if (arg > 0) {
                // Do something
            }
        }
    """)

    assert output.strip() == expected_output.strip()
    assert formatter.file_extension() == "rst"


def test_generate_documentation(c_source_translation_unit: TranslationUnit, tmp_path: Path) -> None:
    # Generate Markdown documentation
    md_file = tmp_path / "test.md"
    generate_documentation(c_source_translation_unit, formatter=MarkdownFormatter(), output_file=md_file)
    assert md_file.exists()
    md_content = md_file.read_text()
    assert "# test.c" in md_content
