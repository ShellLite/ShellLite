import os
import llvmlite.binding as llvm
from .codegen import LLVMCompiler
from ..lexer import Lexer
from ..parser_gbp import GeometricBindingParser as Parser

def build_llvm(filename: str):
    """
    -----Purpose: Main entry point for the LLVM compilation pipeline. 
    -----        Reads source, tokenizes, parses, and generates LLVM IR.
    """
    print(f"Compiling {filename} with LLVM Backend...")
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    statements = parser.parse()
    
    compiler = LLVMCompiler()
    module = compiler.compile(statements)
    llvm_ir = str(module)
    
    print("\n--- Generated LLVM IR ---")
    print(llvm_ir)
    print("-------------------------\n")
    
    ll_filename = os.path.splitext(filename)[0] + ".ll"
    with open(ll_filename, 'w') as f:
        f.write(llvm_ir)
    
    print(f"[SUCCESS] Generated LLVM IR: {ll_filename}")
    print("\nTo compile to executable, you can use Clang:")
    exe_name = os.path.splitext(filename)[0] + ".exe"
    print(f"  clang {ll_filename} -o {exe_name}")