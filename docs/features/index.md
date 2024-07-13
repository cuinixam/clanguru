# ✨ Features

## Documentation Generation

Clanguru offers a minimal yet effective way to generate documentation for your C code without relying on complex systems like Doxygen. Here's how it works:

Use the `generate` command to create documentation:

```
clanguru generate --source-file path/to/your/file.c --output-file path/to/output.md
```

**Format**
The documentation is generated in Markdown format, which is easy to read and can be converted to other formats if needed.

**Compilation Database Support**
If your project uses a compilation database, you can specify it to ensure correct parsing of complex projects:

```
clanguru generate --source-file path/to/your/file.c --output-file path/to/output.md --compilation-database path/to/compile_commands.json
```

This approach to documentation generation is ideal for projects that need quick, straightforward documentation without the overhead of more complex systems.
It's particularly useful for small to medium-sized projects or for generating internal documentation.

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
clanguru generate --source-file example.c --output-file example.md
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
