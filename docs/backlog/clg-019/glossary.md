# New domain terms

Drafts. They land with the implementation.

## clanguru, in the `bind` section of `docs/features/index.md`

- **Binding**: the generated Python module that declares, with `ctypes`, the functions and variables a piece of C code defines, so Python code can call them in a shared library.
- **Python mock**: a function the C code calls but does not define, answered by a Python callable that the test sets.
