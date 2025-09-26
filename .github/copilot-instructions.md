# Clanguru Copilot Instructions

Clanguru is a C/C++ analysis and utility tool built on `libclang` and `binutils`.
It provides documentation generation, mock generation, and object file dependency analysis.

## Architecture Overview

The project follows a modular design with five core components:

- **`cparser.py`**: Libclang wrapper providing AST parsing with custom `TranslationUnit`, `Function`, `Variable` classes
- **`doc_generator.py`**: Multi-format documentation generator (Myst/Markdown/RST) using Jinja2 templates
- **`mock_generator.py`**: C function mock generator supporting GMock with configurable exclusion patterns
- **`object_analyzer.py`**: Object file dependency analyzer using `nm` command for symbol extraction
- **`compilation_options_manager.py`**: Handles compilation database integration for complex build environments

## Key Patterns & Conventions

### Error Handling
- Use `UserNotificationException` from py-app-dev for user-facing errors
- All main functions wrapped with `@time_it` decorator for performance tracking
- Strict mode configuration controls failure behavior on missing symbols/parse errors

### CLI Structure
- Built with Typer following command-pattern: `docs`, `mock`, `parse`, `analyze`
- File paths use `Path` objects consistently
- Multi-value options use `list[Type] = typer.Option()` pattern
- Configuration files supported via dataclasses with `from_file()` methods

### Template System
- Jinja2 templates in `src/clanguru/templates/` with environment auto-escaping
- Mock generation uses template inheritance for different mock types
- HTML reports generated via `object_analyzer.html.jinja`

### Data Processing
- Symbol filtering uses glob patterns with `fnmatch.fnmatch()`
- Object data uses `@cached_property` for expensive computations
- Excel reports via openpyxl with consistent styling patterns

## Development Workflow

### Build System
```bash
# Bootstrap project and run full pipeline
pypeline run

# Individual steps (defined in pypeline.yaml)
.venv/Scripts/pypeline run --step CreateVEnv --step PyTest --single
```

### VS Code Tasks
Use predefined tasks instead of direct commands:
- "run tests" - runs pytest via pypeline
- "run pre-commit checks" - linters/formatters
- "generate docs" - Sphinx documentation

### Testing Patterns
- Test helpers in `conftest.py`: `assert_element_of_type()`, `assert_elements_of_type()`
- Test data in `tests/data/` directory
- Parse result validation using `FileParseResult` dataclass
- Mock generation testing via `MockGenerationIssues` collection

## Dependencies & Tools

- **UV**: Package manager (not pip/poetry) - use `.venv/Scripts/` prefix
- **Ruff**: Linting/formatting with 180 char line length
- **py-app-dev**: Core utilities for logging, exceptions, subprocess execution
- **libclang**: Version pinned to 18.1.x for C/C++ parsing
- **pypeline**: Build automation - configs in `pypeline.yaml`

## Common Integration Points

### Compilation Database Support
Most commands accept `--compilation-database` for complex header dependencies:
```python
CompilationOptionsManager(compilation_database_path)
```

### Symbol Management
- Use `NmExecutor.run()` for extracting symbols from object files
- Filter with glob patterns: `filter_object_data_symbols(object_data, patterns)`
- Distinguish between `SymbolLinkage.EXTERN` (required) vs `SymbolLinkage.LOCAL` (provided)

### File Processing
- Source files processed via `CLangParser.load()` returning custom `TranslationUnit`
- Multi-file processing using `ThreadPoolExecutor` for performance
- Output path validation considers file extensions (.xlsx for Excel, etc.)

## Coding Guidelines

- Always include full **type hints** (functions, methods, public attrs, constants).
- Prefer **pythonic** constructs: context managers, `pathlib`, comprehensions when clear, `enumerate`, `zip`, early returns, no over-nesting.
- Follow **SOLID**: single responsibility; prefer composition; program to interfaces (`Protocol`/ABC); inject dependencies.
- **Naming**: descriptive `snake_case` vars/funcs, `PascalCase` classes, `UPPER_SNAKE_CASE` constants. Avoid single-letter identifiers (including `i`, `j`, `a`, `b`) except in tight math helpers.
- Code should be **self-documenting**. Use docstrings only for public APIs or non-obvious rationale/constraints; avoid noisy inline comments.
- Errors: raise specific exceptions; never `except:` bare; add actionable context.
- Imports: no wildcard; group stdlib/third-party/local, keep modules small and cohesive.
- Testability: pure functions where possible; pass dependencies, avoid globals/singletons.
- tests: use `pytest`; keep the tests to a minimum; use parametrized tests when possible; do no add useless comments; the tests shall be self-explanatory.
- pytest fixtures: use them to avoid code duplication; use `conftest.py` for shared fixtures. Use `tmp_path` in case of file system operations.
- avoid code comments as much as possible; the code and tests shall be self-explanatory.
