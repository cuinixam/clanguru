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
