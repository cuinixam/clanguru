# clanguru

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

C language utils and tools based on the clang and binutils modules.

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
