"""Compiler-specific exceptions for the LLVM backend."""


class CompilerError(Exception):
    """Raised when the LLVM backend encounters an unrecoverable compilation error."""


class UnsupportedNodeError(CompilerError):
    """Raised when a visitor encounters an AST node type it cannot compile."""
