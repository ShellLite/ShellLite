# ShellLite

**A Natural Language Programming System**

ShellLite is a high level programming language designed to bridge the gap between natural language and executable code. It prioritizes readability without sacrificing the power of a modern general purpose language.

## Technical Foundation

ShellLite is built upon the research of Geometric Binding Parsing,

The project implements **Geometric Binding Parsing (GBP)**, an algorithm that decouples topographic structure (indentation geometry) from code semantics, allowing for a flexible, indentation sensitive syntax that feels natural to read and write.

## Key Features

*   **Natural Language Syntax:** Designed to be read like plain English or pseudocode, reducing the cognitive load for beginners.
*   **Python Interop:** Seamlessly import and utilize any Python module via a robust proxying layer.
*   **Cross Platform GUI:** A built in engine for creating desktop applications using an intuitive widget based syntax.
*   **Multi Backend Compilation:** Supports execution via a tree-walking interpreter or compilation to C, JavaScript, and WebAssembly (WASM). (TO BE REWRITTEN)
*   **Integrated Package Management:** Built in support for installing and managing dependencies directly from GitHub repositories.

## Quick Start

### Installation

```bash
pip install shell-lite
```

### Hello World

```shl
say "Hello, World!"

name = ask "What is your name? "
say "Welcome to ShellLite, " + name
```

### Number Guessing Game Example

```shl
use "random"

say "=== Number Guessing Game ==="
say "I'm thinking of a number between 1 and 100."

secret = randint(1, 100)
attempts = 0
max_attempts = 7

while attempts < max_attempts
    remaining = max_attempts - attempts
    say "\nAttempts remaining: " + str(remaining)
    
    guess = int(ask "Your guess: ")
    attempts += 1
    
    if guess == secret
        say in green "\nCongratulations! You got it in " + str(attempts) + " attempts!"
        exit
    elif guess < secret
        say "Too low!"
    else
        say "Too high!"

say in red "\nGame Over! The number was " + str(secret)
```

## Compilation (WIP)

ShellLite can be compiled to various targets for deployment:

```bash
shl compile script.shl --target c      # Transpile to C
shl compile script.shl --target js     # Transpile to JavaScript
shl compile script.shl --target wasm   # Build for WebAssembly
```

## Research & Documentation

For a deep dive into the underlying parsing theory, please refer to the papers on Zenodo By CERN:
- [Geometric Binding: A Topological Approach to Indentation Sensitive Parsing](https://zenodo.org/records/18722827)
- [ShellLite: White paper](https://zenodo.org/records/18228699)

Detailed language guides can be found in the `docs/` directory. (TO BE RE WRITTEN)

## License

GNU GPL V3 With Class Exception License - See [LICENSE](LICENSE) for details.
