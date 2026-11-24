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

### Source Links

Add `--source-links` to put a link to the source location right above the code block of each declaration. A free doc comment at file scope gets its link after its doc text, pointing at the first line of the comment.

```shell
clanguru docs --source-file src/example.c --output-file docs/example.md --source-links --project-root .
```

The link has the form `[<path>:<line>](source:<path>#<line>)`, for example:

```md
[components/light_controller/src/light_controller.c:42](source:components/light_controller/src/light_controller.c#42)
```

The line is the first line of the declaration. With `--project-root` the path is relative to that folder. Without it the path is absolute. The switch is off by default, so the output does not change unless you ask for it.

Source links work for Markdown and Myst Markdown only. With `--format rst` the command stops with an error.

Clanguru does not resolve the link. The tool that builds your report decides where it points. If you build with MyST, add `source` to `myst_url_schemes` in `conf.py`, or MyST drops the link.

### Tagged Documentation Blocks

Only tagged blocks (and `@trace` blocks, see below) reach the output. All other comment text is ignored. Wrap the text you want to emit in a tag pair:

| Opening | Closing     | When it is emitted                                     |
| ------- | ----------- | ------------------------------------------------------ |
| `@docs` | `@enddocs`  | Always (format-neutral).                               |
| `@md`   | `@endmd`    | Only when generating Markdown or Myst Markdown.        |
| `@rst`  | `@endrst`   | Only when generating RestructuredText.                 |

A comment may contain multiple tagged blocks; they are emitted in source order. Tags also accept the backslash form (`\docs`/`\endrst`/…) to play nicely with Doxygen-flavoured comments.

```c
/**
 * @rst
 * .. impl:: Sum Implementation
 *    :id: IMPL-SUM-001
 * @endrst
 */
int sum(int a, int b) { return a + b; }
```

#### Where blocks may stand

Tagged blocks work in any comment at file level, not only above a function or class:

- A block directly above a function definition or class appears once, in the section of that declaration.
- A block directly above the declaration of a function in a header also appears in the section of that function. See "Blocks in the header" below.
- Any other file-level block is a free block. This includes the file header and the comments above prototypes in the source file, variables, structs and typedefs.
- Free blocks appear under the file title, before `Functions`, in source order.
- Free blocks support `@md`, `@rst`, `@trace` and Jinja like declaration blocks. The `gtest` variables are not set. Errors name the source file and the line of the comment.
- Comments inside function bodies, struct or class bodies and other code are ignored.
- Comments in code that the preprocessor skips (`#if 0`, an `#ifdef` of a disabled feature) are ignored. A variant documents only what it compiles.

Source file `demo.c`:

```c
/**
 * @docs
 * Door driver overview.
 * @enddocs
 */
#include <stdint.h>

/** @docs
 * Timing rules for the door switch.
 * @enddocs */
static int timeout_ms;

/**
 * @docs
 * Debounces the switch.
 * @enddocs
 */
int debounce(void) { return 0; }
```

Output (Myst Markdown):

````md
# demo.c

Door driver overview.

Timing rules for the door switch.

## Functions

### debounce

Debounces the switch.

```{code-block} c
:linenos:
:lineno-start: 18

int debounce(void) { return 0; }
```
````

Known limit: a comment directly above the first function belongs to that function, even when you mean it as a file header. Blank lines do not separate them. Code such as `#include` does, as in the example above.

Known limit: a comment directly above an `#if` line is active code and stays a free block, even when the code under the `#if` is skipped. Put the block inside the `#if`.

#### Blocks in the header

You can keep the description and the traceability of a function next to its prototype in the header. Clanguru reads the blocks directly above every declaration of the function in an included header and puts them in the section of the function:

- The header blocks come first, then the blocks above the definition.
- Several headers that declare the function are read in include order.
- Errors name the header path relative to the source file, such as `../include/door.h:2`, and the line of the comment.

```c
/* door.h */
/** @docs Debounces the switch. @enddocs */
int debounce(void);
```

```c
/* door.c */
#include "door.h"
int debounce(void) { return 0; }
```

The section of `debounce` shows "Debounces the switch." above the code.

Known limit: in a C++ source, prototypes inside an `extern "C"` block are not read yet (CLG-010).

### Trace Blocks

A `@trace` block describes a `sphinx-needs` item in a format-neutral syntax. Clanguru renders it as an RST directive or as a MyST fence, so you do not rewrite the comment when you switch the output format.

```c
/**
 * @trace Debounce door switch
 * type: impl
 * id: SWIMPL_DS-001
 * implements: SWDD_DS-100,
 *   SWDD_DS-101
 */
int debounce(void) { return 0; }
```

RST output:

```rst
.. impl:: Debounce door switch
   :id: SWIMPL_DS-001
   :implements: SWDD_DS-100, SWDD_DS-101
```

MyST output (plain Markdown output gets the same fence):

````md
```{impl} Debounce door switch
:id: SWIMPL_DS-001
:implements: SWDD_DS-100, SWDD_DS-101
```
````

Rules:

- The first line is the title. `key: value` option lines follow. A trace without a title is allowed and renders as `.. impl::`.
- The trace ends at the first empty line, at `@enddocs`, or at the end of the comment. There is no end tag.
- A line indented deeper than the keys continues the previous value. Clanguru joins the parts with one space, so each option stays on one line.
- `type` is required. It is the directive name. Any name is accepted; clanguru does not read the `needs_types` of your project.
- Type and links are separate options, because a link name does not tell the type.
- A trace has no content.
- A `@trace` block works inside and outside a `@docs` block, in source order. The backslash form `\trace` also works.
- A `@trace` inside an `@rst` or `@md` block belongs to that block and appears only in that output format.
- Jinja placeholders are resolved before the trace is rendered, as in the other blocks.
- A trace without `type`, or with a line that is neither `key: value` nor a continuation, stops the run with an error that names the declaration.

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

Undefined variables (for example, `{{ gtest.test }}` on a non-test function) raise an error that names the offending declaration and the line of the comment, so mistakes surface at doc-generation time rather than downstream in the Sphinx build.

`gtest` is set only for a block directly above a GoogleTest macro. Nothing may stand between the comment and the macro: no code and no preprocessor line. A comment above an `#ifdef` line does not belong to the test inside it. Put the comment inside the `#ifdef`, directly above the test.

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

## Python Binding

Test C code from Python through a shared library, without declaring C signatures by hand.

- **Binding**: the generated Python module that declares, with `ctypes`, the functions and variables a piece of C code defines, so Python code can call them in a shared library.
- **Python mock**: a function the C code calls but does not define, answered by a Python callable that the test sets.

```shell
clanguru bind --source-file src/sensor.c \
  --partial-object-file build/sensor_partial.o \
  --compilation-database build/compile_commands.json \
  --output-dir build/sensor \
  --filename sensor_binding \
  --library-name sensor_pytest
```

`bind` writes three files into the output directory:

- `sensor_binding.py`: the binding. It declares the defined functions and variables, the structs and enums they use, one Python mock per undefined function, and each undefined variable.
- `sensor_binding_mocks.c`: one trampoline per undefined function and a zero-initialised definition of each undefined variable. Build it into the shared library together with the code; without it the library does not link.
- `sensor_binding.log`: the symbols `bind` could not support, the excluded ones and the missing ones.

Build the shared library as `sensor_pytest.so` (`.dylib` on macOS, `.dll` on Windows, no `lib` prefix) in the same folder and use it from a test:

```python
from unittest.mock import Mock

import sensor_binding

lib = sensor_binding.load()  # or load(path) for a library somewhere else
lib.sensor_offset.value = 2  # variables are ctypes objects
lib.mocks.read_sensor = Mock(return_value=40)
assert lib.measure(3) == 42
lib.mocks.read_sensor.assert_called_once_with(3)
assert lib.mocks.unexpected_calls == []
```

A call to an undefined function with no Python mock set returns a zero value and is recorded: `lib.mocks.unexpected_calls` lists the function name once per such call. A Python mock of a function that returns a pointer returns an address (an `int`) or `None`, because a `ctypes` callback can only return simple types. Setting a Python mock to `None` removes it. The library is loaded once per process, so every `load()` removes the Python mocks and clears `unexpected_calls`: call it at the start of each test.

An array parameter is passed as a pointer, as in C: give the binding a `ctypes` array, and index the pointer a Python mock receives. Arrays of arrays as parameters and pointers to arrays are not supported. A `const` variable, defined or undefined, can be read but never written: it lives in read-only memory, and writing it ends the process. An undefined `const` variable is always zero. An anonymous struct or enum that is not the target of a `typedef` has no name to bind; a symbol that uses one is listed in the log.

**Which symbols.** `bind` takes the same options as `mock` and chooses symbols with the same code: every symbol of the partial-link object whose declaration clanguru finds in the source files, minus the `--exclude-symbol-pattern` matches. Undefined symbols get Python mocks, defined symbols go into the binding.

**Strict mode** (`--strict`, the default) fails only when an undefined symbol has no declaration, because the library cannot link then. Unsupported types never fail: the symbol goes to the log. A defined symbol without a declaration is left out of the binding and listed in the log.

**Supported types.** Scalars, pointers, structs and enums. Not supported yet: function pointers, unions, bit fields, variadic functions, and functions that return a struct by value. A function with an unsupported type gets no Python mock; write a C fake for it and link it into the library, or the link fails and names it.

## Object File Analysis

Analyze object file dependencies and generate comprehensive reports for understanding your project's symbol usage and dependencies.

### HTML Dependency Reports

Generate interactive HTML reports showing object dependencies:

```shell
clanguru analyze --compilation-database compile_commands.json --output-file dependencies.html
```

Symbols are read with the toolchain's own `nm`: for a compiler named `<prefix>-gcc` (or
`-g++`, `-cc`, `-c++`) the `<prefix>-nm` next to it is used, so cross-compiled objects work
without any option. Otherwise `nm` from the PATH is used.

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
