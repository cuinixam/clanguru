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
