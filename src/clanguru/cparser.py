import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TypeVar

from clang.cindex import Cursor, CursorKind, Index, SourceRange
from clang.cindex import Token as _Token
from clang.cindex import TranslationUnit as _TranslationUnit

from clanguru.compilation_options_manager import CompilationOptionsManager


@dataclass
class Token:
    raw_token: _Token
    previous_token: Optional["Token"]
    next_token: Optional["Token"]

    @property
    def is_comment(self) -> bool:
        return self.raw_token.kind.name == "COMMENT"

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Token):
            return str(self) == str(other)
        return False

    def __str__(self) -> str:
        return f"{self.raw_token.kind.name} ('{self.raw_token.spelling}' at line {self.raw_token.location.line})"


class TokensCollection(list[Token]):
    def __init__(self, tokens: list[Token]) -> None:
        super().__init__(tokens)
        self.tokens_ordered_dict = OrderedDict((token, token) for token in tokens)

    def first(self) -> Token | None:
        """Get the first token in the collection."""
        return self[0] if self else None

    def find_matching_token(self, raw_token: _Token) -> Token | None:
        """Find the token in the collection by the raw token."""
        # TODO: Find a nicer way to do this. Currently we rely on the fact that the token previous and next tokens are ignored while hashing.
        return self.tokens_ordered_dict.get(Token(raw_token, None, None), None)


@dataclass
class Node:
    raw_node: Cursor
    previous_node: Optional["Node"]
    next_node: Optional["Node"]
    tokens: TokensCollection
    parent: "TranslationUnit"

    def is_function_definition(self) -> bool:
        """Check if the node type is function declaration and it is a definition."""
        return self.raw_node.kind.name == "FUNCTION_DECL" and self.raw_node.is_definition()

    def __str__(self) -> str:
        return f"{self.raw_node.kind.name} ('{self.raw_node.spelling}' at line {self.raw_node.location.line})"


@dataclass
class TranslationUnit:
    raw_tu: _TranslationUnit
    tokens: TokensCollection
    nodes: list[Node]

    @property
    def source_file(self) -> Path:
        return Path(self.raw_tu.spelling)

    def __str__(self) -> str:
        return "\n".join(
            [
                f"Translation unit for {self.source_file}",
                "Tokens:",
                *[str(token) for token in self.tokens],
                "Nodes:",
                *[str(node) for node in self.nodes],
            ]
        )

    def parsing_error(self) -> Optional[str]:
        """Check if there was a parsing error."""
        if self.raw_tu.diagnostics:
            return "\n".join(str(d) for d in self.raw_tu.diagnostics)
        return None


T = TypeVar("T", bound="Declaration")


class Declaration:
    def __init__(self, name: str, origin: Node, description_token: Token | None, body: str):
        self.name = name
        self.origin = origin
        self.description_token = description_token
        self.body = body

    @property
    def description(self) -> str | None:
        return CLangParser.get_comment_content(self.description_token) if self.description_token else None


class Function(Declaration):
    @property
    def is_definition(self) -> bool:
        return self.origin.is_function_definition()


class CppClass(Declaration):
    pass


class Variable(Declaration):
    def get_init_value(self) -> str | None:
        """Get the initialization value for the variable."""
        var_cursor = self.origin.raw_node

        # The initializer is usually represented as a child cursor
        for child in var_cursor.get_children():
            if child.kind.is_expression() or child.kind == CursorKind.INIT_LIST_EXPR:
                # Extract the initializer value from the child cursor
                init_value = self._extract_init_value(child)
                return init_value

        # If no initializer is found
        return None

    def _extract_init_value(self, expr_cursor: Cursor) -> str | None:
        """Recursively extract the initialization value from an expression cursor."""
        kind = expr_cursor.kind

        if kind in (
            CursorKind.INTEGER_LITERAL,
            CursorKind.FLOATING_LITERAL,
            CursorKind.STRING_LITERAL,
            CursorKind.CHARACTER_LITERAL,
        ):
            tokens = list(expr_cursor.get_tokens())
            return tokens[0].spelling if tokens else None

        elif kind in (
            CursorKind.UNARY_OPERATOR,
            CursorKind.BINARY_OPERATOR,
            CursorKind.COMPOUND_ASSIGNMENT_OPERATOR,
            CursorKind.CALL_EXPR,
            CursorKind.DECL_REF_EXPR,
            CursorKind.MEMBER_REF_EXPR,
            CursorKind.ARRAY_SUBSCRIPT_EXPR,
            CursorKind.CXX_BOOL_LITERAL_EXPR,
            CursorKind.CXX_NULL_PTR_LITERAL_EXPR,
            CursorKind.CXX_STATIC_CAST_EXPR,
            CursorKind.CXX_REINTERPRET_CAST_EXPR,
            CursorKind.CXX_CONST_CAST_EXPR,
            CursorKind.CXX_FUNCTIONAL_CAST_EXPR,
            CursorKind.PAREN_EXPR,
            CursorKind.INIT_LIST_EXPR,
        ):
            # For complex expressions, collect tokens recursively
            tokens = []
            for token in expr_cursor.get_tokens():
                tokens.append(token.spelling)
            value = "".join(tokens)
            return value
        else:
            # For other expressions, attempt to collect tokens
            tokens = []
            for child in expr_cursor.get_children():
                child_value = self._extract_init_value(child)
                if child_value is not None:
                    tokens.append(child_value)
            if tokens:
                return "".join(tokens)
            else:
                return None


class CLangParser:
    def __init__(self) -> None:
        self.index = Index.create()

    def load(self, file: Path, compilation_options_manager: CompilationOptionsManager | None = None) -> TranslationUnit:
        args = compilation_options_manager.get_compile_options(file) if compilation_options_manager else []
        translation_unit = TranslationUnit(raw_tu=self.index.parse(str(file), args=args), tokens=TokensCollection([]), nodes=[])
        translation_unit.tokens = self._extract_tokens(translation_unit.raw_tu.cursor)
        translation_unit.nodes = self._extract_nodes(translation_unit)
        return translation_unit

    def _extract_tokens(self, cursor: Cursor) -> TokensCollection:
        tokens: list[Token] = []
        for token in cursor.get_tokens():
            current_token = Token(raw_token=token, previous_token=None, next_token=None)
            if tokens:
                previous_token = tokens[-1]
                previous_token.next_token = current_token
                current_token.previous_token = previous_token
            tokens.append(current_token)
        return TokensCollection(tokens)

    def _extract_nodes(self, translation_unit: TranslationUnit) -> list[Node]:
        nodes: list[Node] = []
        for child in translation_unit.raw_tu.cursor.get_children():
            current_node = Node(raw_node=child, previous_node=None, next_node=None, tokens=self._collect_node_tokens(child, translation_unit.tokens), parent=translation_unit)
            if nodes:
                previous_node = nodes[-1]
                previous_node.next_node = current_node
                current_node.previous_node = previous_node
            nodes.append(current_node)
        return nodes

    def _collect_node_tokens(self, node: Cursor, tokens: TokensCollection) -> TokensCollection:
        """Get the raw tokens for the node and search for them in the given tokens list."""
        node_tokens = []
        # Do not use node.get_tokens() directly, as it may return an empty list for nodes generated from macros
        # Iterate over all the tokens in CTokensCollection and find the ones with their locations within the node extent
        for token in tokens:
            if node.extent.start.offset <= token.raw_token.extent.start.offset <= node.extent.end.offset:
                node_tokens.append(token)

        return TokensCollection(node_tokens)

    @staticmethod
    def _get_declarations(tu: TranslationUnit, declaration_type: str, declaration_class: type[T]) -> list[T]:
        declarations = []
        for node in tu.nodes:
            if node.raw_node.kind.name == declaration_type:
                name = node.raw_node.spelling
                description = CLangParser.search_description(node)
                source_code = CLangParser.get_node_source_code(node)
                declarations.append(declaration_class(name, node, description, source_code))
        return declarations

    @staticmethod
    def get_functions(tu: TranslationUnit) -> list[Function]:
        return CLangParser._get_declarations(tu, "FUNCTION_DECL", Function)

    @staticmethod
    def get_variables(tu: TranslationUnit) -> list[Variable]:
        return CLangParser._get_declarations(tu, "VAR_DECL", Variable)

    @staticmethod
    def get_classes(tu: TranslationUnit) -> list[CppClass]:
        return CLangParser._get_declarations(tu, "CLASS_DECL", CppClass)

    @staticmethod
    def search_description(node: Node) -> Token | None:
        """
        Get the description comment for a node.

        This method searches for a comment token immediately preceding the node's first token,
        but on a different line. If found, it returns the comment token, otherwise None.
        """
        if first_token := node.tokens.first():
            current_token = first_token
            while current_token.previous_token:
                prev_token = current_token.previous_token
                if prev_token.raw_token.location.line < current_token.raw_token.location.line:
                    if prev_token.is_comment:
                        return prev_token
                    else:
                        break
                current_token = prev_token
        return None

    @staticmethod
    def get_node_source_code(node: Node) -> str:
        if not isinstance(node.raw_node, Cursor):
            raise ValueError(f"The node {node} is not a valid cursor")

        # Get the function's extent (source range)
        extent = node.raw_node.extent

        if not isinstance(extent, SourceRange):
            raise ValueError(f"The node {node} extent is not a valid source range")

        # Get the start and end locations
        start = extent.start
        end = extent.end

        # Get the source file
        source_file = start.file

        if source_file is None or not source_file.name:
            raise ValueError(f"The source file is not available for node {node}")

        # Read the relevant part of the source file
        with open(source_file.name) as f:
            f.seek(start.offset)
            return f.read(end.offset - start.offset)

    @staticmethod
    def get_comment_content(token: Token) -> str:
        """
        Get the comment content from the token.

        This method extracts the comment content for single-line, multi-line,and Doxygen style comments.
        It removes the comment delimiters while preserving the internal structure and indentation.
        """
        if not token.is_comment:
            return ""

        content = token.raw_token.spelling.strip()

        # Single-line comment
        if content.startswith("//"):
            return content[2:].strip()

        # Multi-line comment (including Doxygen-style)
        if content == "/**/":
            return ""
        if content.startswith("/*"):
            # Remove the starting "/*", "/*!", or "/**" and the ending "*/" or "**/"
            content = re.sub(r"^\/\*+\!?|\*+\/$", "", content, flags=re.MULTILINE)

            lines = content.split("\n")

            # Find the minimum indentation (excluding empty lines)
            min_indent = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)

            # Remove the minimum indentation and leading asterisks, but preserve structure
            cleaned_lines = []
            for line in lines:
                if line.strip():
                    cleaned_line = line[min_indent:].lstrip()
                    if cleaned_line.startswith("* "):
                        cleaned_line = cleaned_line[2:]
                    elif cleaned_line.startswith("*"):
                        cleaned_line = cleaned_line[1:]
                    cleaned_lines.append(cleaned_line)
                else:
                    cleaned_lines.append("")

            return "\n".join(cleaned_lines).strip()

        # If it's neither a single-line nor a multi-line comment, return as is
        return content
