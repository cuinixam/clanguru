# Clanguru Development Guide for AI Agents

## Project Overview

Clanguru is a C/C++ analysis toolkit providing four CLI commands:

- **`docs`** — Generate documentation from C/C++ sources (Myst Markdown, Markdown, RestructuredText)
- **`mock`** — Generate mock objects for unit testing (GMock, CMock)
- **`parse`** — Parse C source code and print the translation unit (AST)
- **`analyze`** — Analyze object file dependencies and generate reports (HTML, Excel)

### Architecture

Key modules in `src/clanguru/`:

| Module | Purpose |
|--------|---------|
| `main.py` | CLI entry point (Typer) — all four commands defined here |
| `cparser.py` | libclang-based C/C++ parser, produces `TranslationUnit` with chained tokens/nodes |
| `doc_generator.py` | Documentation generation with intermediate `DocStructure` format and pluggable formatters |
| `mock_generator.py` | Mock generation engine with Jinja2 templates (`templates/mock/gmock/`) |
| `object_analyzer.py` | Object file dependency analysis using `nm`, HTML/Excel report generation |
| `compilation_options_manager.py` | Compilation database (`compile_commands.json`) parsing and flag management |

### Dependencies

- **Core**: `typer` (CLI), `libclang` (parsing), `mashumaro` (serialization), `jinja2` (templates), `openpyxl` (Excel), `pyyaml`
- **Utilities**: `py-app-dev` (logging, exceptions, subprocess)
- **Dev**: `pytest`, `ruff`, `pre-commit`, `pypeline-runner`

## Development Guidelines

### ⚠️ MANDATORY: Plan Before Execution

**NEVER start making changes without presenting a plan first.** This is a critical rule.

1. **Create an implementation plan** documenting:
   - What files will be modified, created, or deleted
   - What changes will be made and why
   - How the changes will be verified
2. **Present the plan for user review** — output it as text and wait for the user's response
3. **Wait for explicit approval** before proceeding with any file modifications
4. **Only after approval**, begin execution

Skipping this step is unacceptable.

### ⚠️ MANDATORY: Never Change the Plan Without Approval

**NEVER deviate from the approved plan without asking the user first.** If the current approach hits a blocker (e.g., a tool doesn't work, a dependency is missing, a test fails unexpectedly), you MUST:

1. **Stop** — do not attempt an alternative approach on your own
2. **Report the problem** to the user with a clear description of what went wrong
3. **Propose alternatives** if you have ideas, but do NOT implement them
4. **Wait for explicit approval** before changing direction

This applies to all scope changes: switching libraries, replacing test targets, altering architecture, or any deviation from what was agreed upon. The user decides, not the agent.

### Running Tests and Verification

The project uses `pypeline-runner` for all automation. Key commands:

```bash
# Run full pipeline (lint + tests) - this is the primary verification command
pypeline run

# Run only linting (pre-commit hooks)
pypeline run --step PreCommit

# Run only tests with specific Python version
pypeline run --step CreateVEnv --step PyTest --single --input python_version=3.13
```

### CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

1. **Lint** (`PreCommit` step) - Runs ruff linting/formatting via pre-commit
2. **Commit Lint** - Enforces [conventional commits](https://www.conventionalcommits.org)
3. **Test** - Matrix: Python 3.10 & 3.13 on Ubuntu and Windows
4. **Release** - Semantic versioning with automatic PyPI publishing

### Code Quality

- **Ruff** handles linting/formatting (configured in `pyproject.toml`)
- **Pre-commit hooks** enforce code standards
- **Type hints** are required (`py.typed` marker present)
- Docstrings follow standard conventions but are not required for all functions

## Coding Guidelines

- **Less is more** — be concise and question every implementation that looks too complicated; if there is a simpler way, use it.
- **Never nester** — maximum three indentation levels are allowed. Use early returns, guard clauses, and extraction into helper functions to keep nesting shallow. The third level should only be used when truly necessary.
- **Use dataclasses for complex data structures**: Prefer using `dataclasses` over complex standard types (e.g. `tuple[list[str] | None, dict[str, str] | None]`) for function return values or internal data exchange to improve readability and extensibility.
- Always include full **type hints** (functions, methods, public attrs, constants).
- Prefer **pythonic** constructs: context managers, `pathlib`, comprehensions when clear, `enumerate`, `zip`, early returns, no over-nesting.
- Follow **SOLID**: single responsibility; prefer composition; program to interfaces (`Protocol`/ABC); inject dependencies.
- **Naming**: descriptive `snake_case` vars/funcs, `PascalCase` classes, `UPPER_SNAKE_CASE` constants. Avoid single-letter identifiers (including `i`, `j`, `a`, `b`) except in tight math helpers.
- Code should be **self-documenting**. Use docstrings only for public APIs or non-obvious rationale/constraints; avoid noisy inline comments.
- Errors: raise specific exceptions; never `except:` bare; add actionable context.
- Imports: no wildcard; group stdlib/third-party/local, keep modules small and cohesive.
- Testability: pure functions where possible; pass dependencies, avoid globals/singletons.
- Tests: use `pytest`; keep the tests to a minimum; use parametrized tests when possible; do not add useless comments; the tests shall be self-explanatory.
- Pytest fixtures: use them to avoid code duplication; use `conftest.py` for shared fixtures. Use `tmp_path` for file system operations.
- **Never suppress linter/type-checker warnings** by adding ignore rules to `pyproject.toml` or `# noqa` / `# type: ignore` comments. Always fix the underlying code instead.

## Definition of Done

Changes are NOT complete until:

- `pypeline run` executes with **zero failures**
- **All new functionality has tests** - never skip writing tests for new code
- Test coverage includes edge cases and error conditions
