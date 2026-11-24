# 🚀 Getting Started

## Installation

Install Clanguru using pipx for isolated installation:

```shell
pipx install clanguru
```

Or using pip:

```shell
pip install clanguru
```

With a compilation database, clanguru runs the gcc or clang driver that a compile command names (`<compiler> -E -v`) to read its system include folders, so the parser finds system headers such as `stdint.h`; the compiler must be installed where clanguru runs. Only a program whose file name looks like a gcc or clang driver is run, wherever it lives, so use clanguru only with a compile database you trust. Without a database, or when that compiler cannot be run, system headers may not be found: their types read as `int`, `bind` leaves out the symbols whose structs use them, and `mock` fails in strict mode (the default) and otherwise writes `int` for them.

## Quick Start

To see available commands and options, use:

```shell
clanguru --help
```

The main commands available are:

- `docs`: Generate documentation for C/C++ source code
- `mock`: Generate mocks for C functions and variables
- `parse`: Parse C source code and print the translation unit
- `analyze`: Analyze object files dependencies

## Your First Documentation

Generate documentation from a C source file:

```shell
clanguru docs --source-file example.c --output-file example.md
```

## Your First Mock

Create mocks for testing:

```shell
clanguru mock --source-file api.h --symbol my_function --output-dir mocks --filename api_mock
```

## Analyze Dependencies

Generate a dependency report (requires compilation database):

```shell
clanguru analyze --compilation-database compile_commands.json --output-file dependencies.html
```

For detailed help on each command, use the `--help` option:

```shell
clanguru docs --help
clanguru mock --help
clanguru analyze --help
```
