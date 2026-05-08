import re
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError, select_autoescape
from py_app_dev.core.exceptions import UserNotificationException

from clanguru.cparser import CLangParser, Token, TranslationUnit

GTEST_MACROS = ("TEST", "TEST_P", "TEST_F", "TYPED_TEST", "TYPED_TEST_P")
_GTEST_DECL_RE = re.compile(rf"^\s*(?:{'|'.join(GTEST_MACROS)})\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")
_TEMPLATE_ENV = Environment(undefined=StrictUndefined, autoescape=select_autoescape(enabled_extensions=()))


@dataclass
class GTestInfo:
    suite: str
    case: str

    @property
    def test(self) -> str:
        return f"{self.suite}.{self.case}"


class DocsFormat(Enum):
    myst = "myst"
    md = "md"
    rst = "rst"

    @property
    def format_tag(self) -> str:
        """Return the tag used in source comments for this format."""
        if self == DocsFormat.myst:
            return "md"
        return self.value


@dataclass
class TextContent:
    text: str


@dataclass
class CodeContent:
    code: str
    language: str = "c"
    linenos: bool = True
    highlight_lines: list[int] | None = None
    start_line: int | None = None


SectionContent = Union[TextContent, CodeContent]


class Section:
    def __init__(self, title: str):
        self.title = title
        self.content: list[SectionContent] = []
        self.subsections: list[Section] = []

    def add_content(self, content: SectionContent) -> None:
        self.content.append(content)

    def add_subsection(self, subsection: "Section") -> None:
        self.subsections.append(subsection)


class DocStructure:
    """Format independent documentation structure."""

    def __init__(self, title: str):
        self.title = title
        self.sections: list[Section] = []

    def add_section(self, section: Section) -> None:
        self.sections.append(section)


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @property
    @abstractmethod
    def docs_format(self) -> DocsFormat:
        """Return the documentation format for this formatter."""
        ...

    @abstractmethod
    def format(self, doc: DocStructure) -> str:
        """Format the entire documentation structure."""
        pass

    @abstractmethod
    def format_text(self, text: str) -> str:
        """Format a text block."""
        pass

    @abstractmethod
    def format_code(self, content: CodeContent) -> str:
        """Format a code block."""
        pass

    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for the formatter."""
        pass

    @abstractmethod
    def format_table(self, headers: list[str], rows: list[list[str]]) -> str:
        """Format a table with headers and rows."""
        pass


class MarkdownFlavour(Enum):
    Myst = "myst"
    Raw = "raw"


class MarkdownFormatter(OutputFormatter):
    """
    Markdown output formatter for documentation.

    Two flavours are supported:
    * Raw: plain GitHub style fenced code blocks.
    * Myst: MystParser extended ``code-block`` directive with options (linenos & highlight lines).
    """

    def __init__(self, flavour: MarkdownFlavour = MarkdownFlavour.Raw, *, jinja_raw_tags: bool = False) -> None:
        super().__init__()
        self.flavour = flavour
        self.jinja_raw_tags = jinja_raw_tags

    def format(self, doc: DocStructure) -> str:
        output = f"# {doc.title}\n\n"
        for section in doc.sections:
            output += self._format_section(section, 2)
        return output.rstrip() + "\n"

    def _format_section(self, section: Section, level: int) -> str:
        output = f"{'#' * level} {section.title}\n\n"
        for content in section.content:
            if isinstance(content, TextContent):
                output += self.format_text(content.text) + "\n\n"
            elif isinstance(content, CodeContent):
                output += self.format_code(content) + "\n\n"
        for subsection in section.subsections:
            output += self._format_section(subsection, level + 1)
        return output

    @property
    def docs_format(self) -> DocsFormat:
        return DocsFormat.myst if self.flavour is MarkdownFlavour.Myst else DocsFormat.md

    def format_text(self, text: str) -> str:
        return text.strip()

    def format_code(self, content: CodeContent) -> str:
        if self.flavour is MarkdownFlavour.Myst:
            return self.format_code_block_myst(content)
        code_block = f"```{content.language}\n{content.code}\n```"
        if self.jinja_raw_tags:
            return f"{{% raw %}}\n{code_block}\n{{% endraw %}}"
        return code_block

    def format_code_block_myst(self, content: CodeContent) -> str:
        """
        Return a fenced code block or Myst code-block directive.

        Myst format example::

            ```{code-block} c
            :linenos:
            :lineno-start: 5
            :emphasize-lines: 2,4

            int main() {}
            ```
        """
        options: list[str] = []
        if content.linenos:
            options.append(":linenos:")
        if content.start_line is not None:
            options.append(f":lineno-start: {content.start_line}")
        if content.highlight_lines:
            # myst expects a comma separated list
            highlighted = ",".join(str(n) for n in content.highlight_lines)
            options.append(f":emphasize-lines: {highlighted}")
        # Build directive header
        header = f"```{{code-block}} {content.language}".rstrip()
        body_parts = [header]
        body_parts.extend(options)
        # Blank line separating options from code per myst recommendations
        body_parts.append("")
        body_parts.append(content.code)
        body_parts.append("```")
        result = "\n".join(body_parts)
        if self.jinja_raw_tags:
            return f"{{% raw %}}\n{result}\n{{% endraw %}}"
        return result

    def format_table(self, headers: list[str], rows: list[list[str]]) -> str:
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        row_lines = ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join([header_line, separator_line, *row_lines]) + "\n"

    def file_extension(self) -> str:
        return "md"


class RSTFormatter(OutputFormatter):
    """reStructuredText output formatter for documentation."""

    def __init__(self, *, jinja_raw_tags: bool = False) -> None:
        super().__init__()
        self.jinja_raw_tags = jinja_raw_tags

    def format(self, doc: DocStructure) -> str:
        output = f"{doc.title}\n{'=' * len(doc.title)}\n\n"
        for section in doc.sections:
            output += self._format_section(section, 1)
        return output.rstrip() + "\n"

    def _format_section(self, section: Section, level: int) -> str:
        underlines = "=-~^"
        output = f"{section.title}\n{underlines[level] * len(section.title)}\n\n"
        for content in section.content:
            if isinstance(content, TextContent):
                output += self.format_text(content.text) + "\n\n"
            elif isinstance(content, CodeContent):
                output += self.format_code(content) + "\n\n"
        for subsection in section.subsections:
            output += self._format_section(subsection, level + 1)
        return output

    @property
    def docs_format(self) -> DocsFormat:
        return DocsFormat.rst

    def format_text(self, text: str) -> str:
        return text.strip()

    def format_code(self, content: CodeContent) -> str:
        options = []
        if content.linenos:
            options.append("   :linenos:")
        if content.start_line is not None:
            options.append(f"   :lineno-start: {content.start_line}")
        if content.highlight_lines:
            highlighted = ",".join(str(n) for n in content.highlight_lines)
            options.append(f"   :emphasize-lines: {highlighted}")

        options_str = "\n".join(options)
        if options_str:
            options_str = "\n" + options_str + "\n"

        code_block = f".. code-block:: {content.language}{options_str}\n{self._indent_code(content.code)}\n"
        if self.jinja_raw_tags:
            return f"{{% raw %}}\n{code_block}{{% endraw %}}\n"
        return code_block

    def _indent_code(self, code: str) -> str:
        return "\n".join(f"    {line}" for line in code.split("\n"))

    def file_extension(self) -> str:
        return "rst"

    def format_table(self, headers: list[str], rows: list[list[str]]) -> str:
        """Format a simple grid table in reStructuredText."""
        if not headers:
            return ""

        # Determine column widths based on headers and rows
        col_widths: list[int] = []
        for i, header in enumerate(headers):
            max_cell = max((len(row[i]) for row in rows), default=0)
            col_widths.append(max(len(header), max_cell))

        def sep(char: str) -> str:
            return "+" + "+".join(char * (w + 2) for w in col_widths) + "+"

        def make_row(columns: list[str]) -> str:
            return "|" + "|".join(f" {c.ljust(w)} " for c, w in zip(columns, col_widths)) + "|"

        top = sep("-")
        header_sep = sep("=")
        row_sep = sep("-")

        lines: list[str] = [top, make_row(headers), header_sep]
        for row in rows:
            lines.append(make_row(row))
            lines.append(row_sep)
        return "\n".join(lines) + "\n"


def _extract_doc_contents(raw_content: str, accepted_tags: list[str]) -> list[str]:
    """
    Extract and dedent all content blocks matching any of the accepted tags.

    The opening tag must appear at the start of a line (or the start of the string)
    to avoid matching tags that appear mid-sentence in prose text.
    """
    if not accepted_tags:
        return []
    tags_pattern = "|".join(re.escape(tag) for tag in accepted_tags)
    pattern = rf"(?:^|(?<=\n))(?:@|\\)({tags_pattern})\s*(.*?)\s*(?:@|\\)end\1"
    matches = re.finditer(pattern, raw_content, flags=re.DOTALL)
    return [textwrap.dedent(match.group(2)) for match in matches]


def _detect_gtest(body_code: str) -> GTestInfo | None:
    """Return `GTestInfo` if `body_code` starts with a recognized GTest macro call."""
    match = _GTEST_DECL_RE.match(body_code)
    if not match:
        return None
    return GTestInfo(suite=match.group(1), case=match.group(2))


def _render_doc_template(content: str, declaration_name: str, gtest: GTestInfo | None) -> str:
    """
    Render a doc block as a Jinja2 template.

    Undefined variables raise `UserNotificationException` with the declaration name so
    authors can locate the faulty placeholder. Content without `{{`/`{%` is returned
    verbatim (cheap short-circuit).
    """
    if "{{" not in content and "{%" not in content:
        return content
    context = {"gtest": gtest} if gtest is not None else {}
    try:
        return _TEMPLATE_ENV.from_string(content).render(context)
    except UndefinedError as error:
        raise UserNotificationException(f"Undefined template variable in doc block of '{declaration_name}': {error.message}") from error
    except TemplateError as error:
        raise UserNotificationException(f"Template error in doc block of '{declaration_name}': {error}") from error


def _build_declaration_section(name: str, description_tokens: list[Token], body_code: str, body_start_line: int, tags: list[str]) -> Section:
    section = Section(name)
    gtest = _detect_gtest(body_code)
    for token in description_tokens:
        raw = CLangParser.get_comment_content(token)
        for content in _extract_doc_contents(raw, tags):
            section.add_content(TextContent(_render_doc_template(content, name, gtest)))
    section.add_content(CodeContent(code=body_code, start_line=body_start_line))
    return section


def generate_doc_structure(translation_unit: TranslationUnit, docs_format: DocsFormat = DocsFormat.md) -> DocStructure:
    """
    Generate documentation structure from a translation unit.

    Uses the CLangParser to extract functions and classes from the translation unit
    and creates a DocStructure object with the extracted information.
    """
    tags = [docs_format.format_tag, "docs"]

    doc = DocStructure(translation_unit.source_file.name)
    functions = [f for f in CLangParser.get_functions(translation_unit) if f.is_definition]
    if functions:
        functions_section = Section("Functions")
        doc.add_section(functions_section)
        for func in functions:
            functions_section.add_subsection(_build_declaration_section(func.name, func.description_tokens, func.body.content, func.body.start_line, tags))

    classes = CLangParser.get_classes(translation_unit)
    if classes:
        classes_section = Section("Classes")
        doc.add_section(classes_section)
        for cls in classes:
            classes_section.add_subsection(_build_declaration_section(cls.name, cls.description_tokens, cls.body.content, cls.body.start_line, tags))

    return doc


def generate_documentation(translation_unit: TranslationUnit, formatter: OutputFormatter, output_file: Path) -> None:
    """Generate documentation from a translation unit and write it to a file using the specified formatter."""
    output_file.write_text(formatter.format(generate_doc_structure(translation_unit, formatter.docs_format)), encoding="utf-8")
