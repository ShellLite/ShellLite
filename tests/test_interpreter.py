"""
-----Purpose: Unit tests for the Interpreter.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser
from shell_lite.interpreter import Interpreter

class TestInterpreter(unittest.TestCase):
    """
    -----Purpose: Test suite for Interpreter evaluation.
    """
    def run_code(self, code: str):
        lex = Lexer(code)
        tokens = lex.tokenize()
        parser = GeometricBindingParser(tokens)
        ast_nodes = parser.parse()
        interpreter = Interpreter()
        last_val = None
        for node in ast_nodes:
            last_val = interpreter.visit(node)
        return interpreter.global_env, last_val, interpreter

    def test_variable_assignment(self):
        env, val, _ = self.run_code("x = 10")
        self.assertEqual(env.get("x"), 10)
        self.assertEqual(val, 10)

    def test_binary_operations(self):
        env, val, _ = self.run_code("x = 5 + 5")
        self.assertEqual(env.get("x"), 10)
        
        env, val, _ = self.run_code("y = 10 - 2")
        self.assertEqual(env.get("y"), 8)
        
        env, val, _ = self.run_code("z = 10 * 2")
        self.assertEqual(env.get("z"), 20)
        
        env, val, _ = self.run_code("w = 10 / 2")
        self.assertEqual(env.get("w"), 5)

    def test_conditionals(self):
        code = '''x = 10
y = 0
if x > 5
    y = 1
else
    y = 2'''
        env, _, _ = self.run_code(code)
        self.assertEqual(env.get("y"), 1)

        code_else = '''x = 3
y = 0
if x > 5
    y = 1
elif x == 3
    y = 3
else
    y = 2'''
        env_else, _, _ = self.run_code(code_else)
        self.assertEqual(env_else.get("y"), 3)

    def test_while_loop(self):
        code = '''x = 0
while x < 5
    x = x + 1'''
        env, _, _ = self.run_code(code)
        self.assertEqual(env.get("x"), 5)

    def test_function_call(self):
        code = '''to get_num
    give 15
result = get_num'''
        env, val, _ = self.run_code(code)
        self.assertEqual(env.get("result"), 15)

    def test_list_operations(self):
        code = '''arr = [1, 2, 3]
val = arr[0]'''
        env, _, _ = self.run_code(code)
        self.assertEqual(env.get("arr"), [1, 2, 3])
        self.assertEqual(env.get("val"), 1)

if __name__ == '__main__':
    unittest.main()
