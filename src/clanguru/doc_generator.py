from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union

from clanguru.cparser import CLangParser, TranslationUnit


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

    def __init__(self, flavour: MarkdownFlavour = MarkdownFlavour.Raw) -> None:
        super().__init__()
        self.flavour = flavour

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

    def format_text(self, text: str) -> str:
        return text.strip()

    def format_code(self, content: CodeContent) -> str:
        if self.flavour is MarkdownFlavour.Myst:
            return self.format_code_block_myst(content)
        else:
            # Raw flavour - classic fenced block
            return f"```{content.language}\n{content.code}\n```"

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
        return "\n".join(body_parts)

    def format_table(self, headers: list[str], rows: list[list[str]]) -> str:
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        row_lines = ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join([header_line, separator_line, *row_lines]) + "\n"

    def file_extension(self) -> str:
        return "md"


class RSTFormatter(OutputFormatter):
    """reStructuredText output formatter for documentation."""

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

        return f".. code-block:: {content.language}{options_str}\n{self._indent_code(content.code)}\n"

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


def generate_doc_structure(translation_unit: TranslationUnit) -> DocStructure:
    """
    Generate documentation structure from a translation unit.

    Uses the CLangParser to extract functions and classes from the translation unit
    and creates a DocStructure object with the extracted information.
    """
    doc = DocStructure(translation_unit.source_file.name)
    functions = CLangParser.get_functions(translation_unit)
    if functions:
        functions_section = Section("Functions")
        doc.add_section(functions_section)

        for func in functions:
            if func.is_definition:
                func_section = Section(func.name)
                if func.description_token:
                    func_section.add_content(TextContent(CLangParser.get_comment_content(func.description_token)))
                func_section.add_content(CodeContent(code=func.body.content, start_line=func.body.start_line))
                functions_section.add_subsection(func_section)
    classes = CLangParser.get_classes(translation_unit)
    if classes:
        classes_section = Section("Classes")
        doc.add_section(classes_section)

        for cls in classes:
            cls_section = Section(cls.name)
            if cls.description_token:
                cls_section.add_content(TextContent(CLangParser.get_comment_content(cls.description_token)))
            classes_section.add_subsection(cls_section)

    return doc


def generate_documentation(translation_unit: TranslationUnit, formatter: OutputFormatter, output_file: Path) -> None:
    """Generate documentation from a translation unit and write it to a file using the specified formatter."""
    output_file.write_text(formatter.format(generate_doc_structure(translation_unit)))
