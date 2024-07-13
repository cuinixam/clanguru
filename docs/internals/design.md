# Design

This document outlines the architecture and key design decisions made in the implementation of Clanguru.
I've tried to keep things simple while adhering to good software design principles where appropriate.

## CLangParser

`CLangParser` is responsible for parsing C/C++ source files using libclang and creating an internal representation that can be used for documentation generation.
It's designed to be flexible and extensible, with special consideration for handling tokens, nodes, and their relationships.

```{mermaid}
classDiagram
    class CLangParser {
        +load(file: Path, compilation_options_manager: CompilationOptionsManager) TranslationUnit
    }
    class TranslationUnit {
        +raw_tu: _TranslationUnit
        +tokens: TokensCollection
        +nodes: List[Node]
        +source_file: Path
    }
    class Token {
        +raw_token: _Token
        +previous_token: Token
        +next_token: Token
        +is_comment: bool
    }
    class Node {
        +raw_node: Cursor
        +previous_node: Node
        +next_node: Node
        +tokens: TokensCollection
        +parent: TranslationUnit
        +is_function_definition() bool
    }
    class Function {
        +name: str
        +origin: Node
        +description_token: Token
        +body: str
        +is_definition: bool
    }
    class CppClass {
        +name: str
        +origin: Node
        +description_token: Token
        +body: str
    }

    CLangParser --> TranslationUnit : creates
    TranslationUnit --> Token : contains
    TranslationUnit --> Node : contains
    Node --> Token : contains
    Function --|> Node : extends
    CppClass --|> Node : extends
```

### Decorator Pattern for Chained Lists

I've implemented a decorator pattern to create chained lists of tokens and nodes.
This design allows us to easily traverse the token and node lists in both directions,
which is particularly useful for context-aware operations like finding description comments.

```python
@dataclass
class Token:
    raw_token: _Token
    previous_token: Optional["Token"]
    next_token: Optional["Token"]
```

### Handling Function and CppClass Nodes

`Function` and `CppClass` are currently the only node types that are documented. They are handled as follows:

1. When parsing, we identify nodes that represent functions or classes.
2. For each of these nodes, we look for a description token:
   - We search for the first token above the node's first token.
   - If this token is a comment, it's considered the description token.
3. The description token, along with other relevant information, is stored in the `Function` or `CppClass` object.

### Handling Macro Expansions

The implementation is designed to work correctly even when declarations are expanded from macros, and intermediate tokens are inserted.
The `_collect_node_tokens` method in `CLangParser` which collects tokens for a node based on their source locations rather than relying on the exact token sequence from `libclang`.

## Documentation Generator

The `doc_generator` uses an intermediate format for storing documentation before rendering it in a specific output format. This design allows for flexibility in adding new output formats without modifying existing code.

Here's a class diagram illustrating the relationships between these components:

```{mermaid}
classDiagram
    class DocStructure {
        +title: str
        +sections: List[Section]
        +add_section(section: Section)
    }
    class Section {
        +title: str
        +content: List[SectionContent]
        +subsections: List[Section]
        +add_content(content: SectionContent)
        +add_subsection(subsection: Section)
    }
    class SectionContent {
        <<interface>>
    }
    class TextContent {
        +text: str
    }
    class CodeContent {
        +code: str
        +language: str
    }
    class OutputFormatter {
        <<abstract>>
        +format(doc: DocStructure) str
        +format_text(text: str) str
        +format_code(code: str, language: str) str
        +file_extension() str
    }
    class MarkdownFormatter {
        +format(doc: DocStructure) str
        +format_text(text: str) str
        +format_code(code: str, language: str) str
        +file_extension() str
    }
    class RSTFormatter {
        +format(doc: DocStructure) str
        +format_text(text: str) str
        +format_code(code: str, language: str) str
        +file_extension() str
    }

    DocStructure --> "1..*" Section
    Section --> "0..*" SectionContent
    Section --> "0..*" Section : subsections
    TextContent --|> SectionContent
    CodeContent --|> SectionContent
    MarkdownFormatter --|> OutputFormatter
    RSTFormatter --|> OutputFormatter
```

### Design Principles

#### Open/Closed Principle

The doc_generator adheres to the Open/Closed Principle in several ways:

1. **Intermediate Format**: By using `DocStructure` as an intermediate representation, we can add new output formats without modifying the existing parsing or structure generation code.

2. **OutputFormatter Interface**: The `OutputFormatter` abstract base class allows for the addition of new formatting styles (e.g., HTML, LaTeX) without changing the core documentation generation logic.

### Dependency Injection

Dependency Injection is utilized in the `generate_documentation` function:

```python
def generate_documentation(translation_unit: TranslationUnit, formatter: OutputFormatter, output_file: Path) -> None:
    doc_structure = generate_doc_structure(translation_unit)
    output_file.write_text(formatter.format(doc_structure))
```

This function takes an `OutputFormatter` as a parameter, allowing the caller to inject the desired formatter. This decouples the documentation generation process from the specific output format, making the system more flexible and easier to extend.

### Workflow

1. `generate_doc_structure` creates a `DocStructure` from a `TranslationUnit`.
2. `DocStructure` is populated with `Section` objects, which in turn contain `SectionContent` (either `TextContent` or `CodeContent`).
3. `generate_documentation` takes this `DocStructure` and an `OutputFormatter`.
4. The `OutputFormatter` traverses the `DocStructure`, formatting each section and its content according to the specific output format.

### Extending the System

To add a new output format:

1. Create a new class that inherits from `OutputFormatter`.
2. Implement the required methods (`format`, `format_text`, `format_code`, `file_extension`).
3. Use the new formatter with the existing `generate_documentation` function.

No changes to existing classes or the core generation logic are required, demonstrating the flexibility of this design.
