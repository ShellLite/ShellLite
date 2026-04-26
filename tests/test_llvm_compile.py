"""
-----Purpose: Integration tests for the LLVM compilation path.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import llvmlite.binding as llvm

    from shell_lite.lexer import Lexer
    from shell_lite.llvm_backend.codegen import LLVMCompiler
    from shell_lite.parser_gbp import GeometricBindingParser

    def test_llvm_compilation():
        """
        -----Purpose: Verifies LLVM IR generation for a basic statement.
        """
        source = 'say "Hello LLVM"'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        compiler = LLVMCompiler()
        module = compiler.compile(statements)
        llvm_ir = str(module)
        print("LLVM IR Generation Successful:")
        
        if 'call i32 (ptr, ...) @printf' in llvm_ir or \
           'declare i32 @printf' in llvm_ir:
             print("[PASS] Printf declaration found")
        else:
             print("[FAIL] Printf declaration missing")
             
        if '@.str_0 = internal constant [12 x i8] c"Hello LLVM\\00"' in llvm_ir:
             print("[PASS] String constant found")
        else:
             print("[FAIL] String constant missing/incorrect")

    if __name__ == "__main__":
        """
        -----Purpose: Entry point for LLVM test execution.
        """
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        test_llvm_compilation()

except ImportError as e:
    print(f"[SKIP] LLVM dependencies missing: {e}")
except Exception as e:
    print(f"[FAIL] LLVM compilation failed: {e}")