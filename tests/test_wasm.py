import os
import shutil
import unittest

from shell_lite.c_compiler import CCompiler
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser
from shell_lite.wasm_builder import WASMBuilder


class TestWASM(unittest.TestCase):
    def test_c_transpilation(self):
        source = """
x = 10
y = 20
if x < y
    say x + y
"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        
        compiler = CCompiler()
        c_code = compiler.compile(statements)
        
        self.assertIn("double x = 10;", c_code)
        self.assertIn("double y = 20;", c_code)
        self.assertIn("if ((x < y))", c_code)
        self.assertIn("slang_print_num((x + y));", c_code)

    def test_wasm_builder_generation(self):
        source = "say 42"
        lexer = Lexer(source)
        statements = GeometricBindingParser(lexer.tokenize()).parse()
        
        builder = WASMBuilder(output_dir="test_wasm_out")
        # should work even without emcc (it will just return False but generate .c)
        builder.build(statements, "test_file")
        
        self.assertTrue(os.path.exists("test_wasm_out/test_file.c"))
        
        # cleanup
        shutil.rmtree("test_wasm_out")

if __name__ == '__main__':
    unittest.main()
