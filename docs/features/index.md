# ✨ Features

Clanguru provides four main capabilities for C/C++ code analysis and utility operations:

## Documentation Generation

Clanguru offers a minimal yet effective way to generate documentation for your C/C++ code without relying on complex systems like Doxygen. It supports multiple output formats:

### Basic Usage

```shell
clanguru docs --source-file path/to/your/file.c --output-file path/to/output.md
```

### Output Formats

**Myst Markdown (default)**
```shell
clanguru docs --source-file src/example.c --output-file docs/example.md --format myst
```

**RestructuredText**
```shell
clanguru docs --source-file src/example.c --output-file docs/example.rst --format rst
```

### Compilation Database Support

For complex projects with external headers, specify a compilation database:

```shell
clanguru docs --source-file src/example.c --output-file docs/example.md --compilation-database compile_commands.json
```

This approach is ideal for projects that need quick, straightforward documentation without the overhead of more complex systems.

### Tagged Documentation Blocks

By default, the comment above a declaration is emitted verbatim. You can scope the output to specific blocks inside that comment by wrapping them in a tag pair:

| Opening | Closing     | When it is emitted                                     |
| ------- | ----------- | ------------------------------------------------------ |
| `@docs` | `@enddocs`  | Always (format-neutral).                               |
| `@md`   | `@endmd`    | Only when generating Markdown or Myst Markdown.        |
| `@rst`  | `@endrst`   | Only when generating RestructuredText.                 |

A comment may contain multiple tagged blocks; they are emitted in source order. Untagged prose is ignored when at least one tag is present. Tags also accept the backslash form (`\docs`/`\endrst`/…) to play nicely with Doxygen-flavoured comments.

```c
/**
 * @rst
 * .. impl:: Sum Implementation
 *    :id: IMPL-SUM-001
 * @endrst
 */
int sum(int a, int b) { return a + b; }
```

### Placeholder Expansion

Each tagged block is rendered as a [Jinja2](https://jinja.palletsprojects.com/) template before being emitted. A `gtest` namespace is exposed when the declaration is a GoogleTest macro call (`TEST`, `TEST_P`, `TEST_F`, `TYPED_TEST`, `TYPED_TEST_P`):

| Variable      | Value                                        |
| ------------- | -------------------------------------------- |
| `gtest.suite` | First argument of the macro (the suite name) |
| `gtest.case`  | Second argument (the case name)              |
| `gtest.test`  | Shorthand for `"<suite>.<case>"`             |

This lets a `sphinx-needs` `.. test::` directive match the JUnit `<testcase>` name by construction, so traceability holds without copy-pasting the identifiers:

```cpp
/**
 * @rst
 * .. test:: {{ gtest.test }}
 *    :id: TS_LC-006
 *    :tests: SWDD_LC-100, SWDD_LC-300
 * @endrst
 */
TEST(light_controller, test_light_stays_off) { /* ... */ }
```

Parameterised tests keep the `INSTANTIATE_TEST_SUITE_P` prefix as literal text — only the macro arguments are available to the template:

```cpp
/**
 * @rst
 * .. test:: BlinkPeriodTests/{{ gtest.test }}/*
 *    :id: TS_LC-003
 *    :tests: SWDD_LC-101
 * @endrst
 */
TEST_P(BlinkPeriodTest, CalculatesCorrectBlinkPeriod) { /* ... */ }
```

Undefined variables (for example, `{{ gtest.test }}` on a non-test function) raise an error that names the offending declaration, so mistakes surface at doc-generation time rather than downstream in the Sphinx build.

## Mock Generation

Generate C function mocks for unit testing with support for GMock and CMock frameworks.

### Basic Mock Generation

```shell
clanguru mock --source-file src/api.h \
  --symbol function1 --symbol function2 \
  --output-dir tests/mocks \
  --filename api_mock
```

### Extract Symbols from Object Files

Automatically extract symbols from partially linked object files:

```shell
clanguru mock --source-file src/api.h \
  --partial-object-file build/partial.o \
  --output-dir tests/mocks \
  --filename api_mock \
  --mock-type gmock
```

### Pattern-Based Symbol Exclusion

Exclude symbols using glob patterns:

```shell
clanguru mock --source-file src/api.h \
  --symbol function1 --symbol function2 \
  --output-dir tests/mocks \
  --filename api_mock \
  --exclude-symbol-pattern "_internal*" \
  --exclude-symbol-pattern "*_test"
```

### Configuration Files

Use YAML configuration for complex setups:

```yaml
# mock_config.yaml
mock_type: gmock
strict: true
exclude_symbol_patterns:
  - "_internal*"
  - "*_test"
  - "debug_*"
```

```shell
clanguru mock --source-file src/api.h \
  --output-dir tests/mocks \
  --filename api_mock \
  --config-file mock_config.yaml
```

## Object File Analysis

Analyze object file dependencies and generate comprehensive reports for understanding your project's symbol usage and dependencies.

### HTML Dependency Reports

Generate interactive HTML reports showing object dependencies:

```shell
clanguru analyze --compilation-database compile_commands.json --output-file dependencies.html
```

### Excel Reports

Create Excel spreadsheets for detailed analysis:

```shell
clanguru analyze --compilation-database compile_commands.json --output-file dependencies.xlsx
```

### Advanced Analysis Options

Include parent dependencies and create traceability matrices:

```shell
clanguru analyze --compilation-database compile_commands.json \
  --output-file dependencies.xlsx \
  --use-parent-deps \
  --create-traceability-matrix
```

### Symbol Filtering

Exclude specific symbol patterns from analysis:

```shell
clanguru analyze --compilation-database compile_commands.json \
  --output-file dependencies.html \
  --exclude-symbol-pattern "_internal*" \
  --exclude-symbol-pattern "test_*"
```

## Code Parsing

Parse C/C++ source code and examine the Abstract Syntax Tree (AST) for debugging and analysis.

### Basic Parsing

```shell
# Parse and print to console
clanguru parse --source-file src/example.c

# Parse and save to file
clanguru parse --source-file src/example.c --output-file parsed_output.txt
```

### Complex Project Parsing

```shell
clanguru parse --source-file src/example.c --compilation-database compile_commands.json
```

**Example**

Here's a simple example of how Clanguru generates documentation:

Given a C file `example.c`:

```c
// This function adds two integers
int add(int a, int b) {
    return a + b;
}

/*
 * This function multiplies two integers
 * and returns the result
 */
int multiply(int a, int b) {
    return a * b;
}
```

Running:

```
clanguru docs --source-file example.c --output-file example.md
```

Will produce `example.md`:

````{code} markdown
# example.c

## Functions

### add

This function adds two integers

```c
int add(int a, int b) {
    return a + b;
}
```

### multiply

This function multiplies two integers
and returns the result

```c
int multiply(int a, int b) {
    return a * b;
}
```

````
