# ADR 0001: A Python binding and Python mocks through a `bind` command

**Status:** Accepted

## Context

A C component, built as a shared library, can be tested from Python through `ctypes`. Two things are missing for that:

- **Types.** A shared library exports symbol names only. A Python caller needs each function's argument and return types, and the structs and enums they use. Written by hand, these declarations drift from the C code.
- **The functions the code calls but does not define.** A shared library cannot leave them unresolved on Windows and macOS. For gtest, `clanguru mock` fills them with gmock classes, but Python cannot set an expectation or a return value on a gmock object.

clanguru already finds both symbol sets (`nm` on a partial-link object), finds their declarations with libclang and the project's compilation database, and renders Jinja templates.

## Decision

A new command, `clanguru bind`, beside `mock`. For one partial-link object it writes:

- `<filename>.py`, the **binding**: `ctypes` declarations of the functions and variables the code defines, the structs and enums they use, `load(path=None)`, which by default loads the library named by `--library-name` from the module's own folder (no `lib` prefix, extension per system), one **Python mock** slot per function the code calls but does not define (`lib.mocks.<function> = <callable>`), and each variable it uses but does not define;
- `<filename>_mocks.c`: one trampoline per such function and a zero-initialised definition of each such variable. A trampoline calls the Python callable the test set; with none set, it returns a zero-initialised value of the return type and records the call in `lib.mocks.unexpected_calls`;
- `<filename>.log`: the symbols it could not support.

Each trampoline reads an exported callback slot `clanguru_mock_<function>` and counts calls with no callback in `clanguru_unexpected_<function>`; the binding sets the slots and builds `unexpected_calls` from the counters.

Design points:

- **Same input options and the same symbol selection as `mock`,** with the same code: `--source-file`, `--partial-object-file`, `--compilation-database`, `--output-dir`, `--filename`, `--exclude-symbol-pattern`, `--strict/--no-strict` with `mock`'s default, plus `--library-name`. Both commands decide alike what the code defines and what it calls.
- **Strict means "the library cannot link".** In strict mode `bind` fails only when an undefined symbol has no declaration. Unsupported types never fail; they go to the log. A defined symbol without a declaration is left out of the binding and logged.
- **Templates inside clanguru,** like the gmock templates. Anyone who needs a Python binding for C uses the same ones.
- **The speed of `mock` does not change.** The extra type detail (the type behind a `typedef`, struct fields, enum values) is computed only by `bind`.
- **First version:** scalar, pointer, struct and enum types. Function pointers, unions, bit fields, variadic functions and functions that return a struct by value (a `ctypes` callback cannot return a struct) are listed in the log and get no Python mock.

## Rejected alternatives

- **Generated C stubs with call counters and return values.** No call leaves C, but every hard case (a value per call, out-parameters, callbacks) needs its own C design. A trampoline hands all of them to `unittest.mock`.
- **gmock mocks with their default action.** They link, but return 0 and cannot be set from Python.
- **cffi or a compiled extension instead of `ctypes`.** Both need a second compiler setup; `ctypes` is in the standard library.
- **`mock --mock-type python`.** A binding of the defined symbols is not a mock.
- **A `render` command with a template folder.** The folder option has no user; it can come when one exists.
- **Own symbol selection for `bind`.** The two commands would then treat the same code differently.
- **`mock`'s strict check for `bind`.** It also fails on unsupported types, which `bind` lists in the log instead.

## Consequences

- The binding's API (`load`, `lib.mocks`, `unexpected_calls`) is public; changing it breaks tests.
- A mocked call crosses into Python, which is slow for loops of millions of calls.
- The binding keeps every callback it was given alive; `ctypes` does not, and a collected callback would crash the process on the next call.
