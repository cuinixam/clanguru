<p align="center">
<a href="https://clanguru.readthedocs.io">
<img align="center" src="https://github.com/cuinixam/clanguru/raw/main/logo.png" width="400"/>
</a>
</p>

<p align="center">
  <a href="https://github.com/cuinixam/clanguru/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/cuinixam/clanguru/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status" >
  </a>
  <a href="https://clanguru.readthedocs.io">
    <img src="https://img.shields.io/readthedocs/clanguru.svg?logo=read-the-docs&logoColor=fff&style=flat-square" alt="Documentation Status">
  </a>
  <a href="https://codecov.io/gh/cuinixam/clanguru">
    <img src="https://img.shields.io/codecov/c/github/cuinixam/clanguru.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
</p>
<p align="center">
  <a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="ruff">
  </a>
  <a href="https://github.com/cuinixam/pypeline">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cuinixam/pypeline/refs/heads/main/assets/badge/v0.json" alt="pypeline">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat-square" alt="pre-commit">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/clanguru/">
    <img src="https://img.shields.io/pypi/v/clanguru.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/clanguru.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/clanguru.svg?style=flat-square" alt="License">
</p>

C language utils and tools based on the `clang` and `binutils` modules.

## Installation

Install clanguru using `pipx` for isolated installation:

```shell
pipx install clanguru
```

## Usage

Clanguru provides four main commands for C/C++ code analysis and utility operations:

- **Documentation**: Generate (minimal) documentation for C/C++ sources functions and classes.
  It supports multiple output formats including Myst Markdown, standard Markdown, and RestructuredText.
- **Testing**: Create mock objects for unit testing C functions
- **Analysis**: Understand object file dependencies and symbol usage. It can generate HTML and Excel reports.

Check the help message for more details:

```shell
clanguru --help


 Usage: clanguru [OPTIONS] COMMAND [ARGS]...

 C language utils and tools based on the libclang module.

╭─ Options ────────────────────────────────────────────────────────────╮
│ --version  -v        Show version and exit.                          │
│ --help               Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────╮
│ docs      Generate documentation for C/C++ source code.              │
│ mock      Generate mocks for C functions and variables.              │
│ parse     Parse C source code and print the translation unit.        │
│ analyze   Analyze object files dependencies.                         │
╰──────────────────────────────────────────────────────────────────────╯

```

For detailed help on each command, use the `--help` option with the command name.

```shell
clanguru analyze --help
```

### Object File Analysis

Clanguru can analyze object files to understand their dependencies and symbol usage.
For this, you need to build your project and provide the compilation database (`compile_commands.json`).
Also, ensure that the `nm` command-line tool is available in your system PATH.

To generate an html dynamic dependency report, run the following command:

```shell
clanguru analyze --compilation-database compile_commands.json --output-file dependencies.html --use-parent-deps
```

> [!NOTE]
> Here is the generated HTML report for my smart home temperature sensor project: https://maxiniuc.com/objects_deps/index.html.
> I only wrote some lines of code to make a temperature sensor available as a `matter` device but the esp32 modules, matter stack,
> and all the libraries bring a lot of code and dependencies. 🫣
> Feel free to move the nodes around and explore the dependencies.


If the output file ends with `.xlsx`, an Excel report will be generated instead of an HTML one.

## Contributing

The project uses UV for dependencies management and packaging and the [pypeline](https://github.com/cuinixam/pypeline) for streamlining the development workflow.
Use pipx (or your favorite package manager) to install the `pypeline` in an isolated environment:

```shell
pipx install pypeline-runner
```

To bootstrap the project and run all the steps configured in the `pypeline.yaml` file, execute the following command:

```shell
pypeline run
```

For those using [VS Code](https://code.visualstudio.com/) there are tasks defined for the most common commands:

- run tests
- run pre-commit checks (linters, formatters, etc.)
- generate documentation

See the `.vscode/tasks.json` for more details.
