"""
-----Purpose: Unit tests for the Geometric Binding Parser (GBP).
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser
import shell_lite.ast_nodes as ast

class TestParser(unittest.TestCase):
    """
    -----Purpose: Test suite for GBP core functionality.
    """
    def parse_code(self, code: str):
        lex = Lexer(code)
        tokens = lex.tokenize()
        parser = GeometricBindingParser(tokens)
        return parser.parse()

    def test_basic_assignment(self):
        nodes = self.parse_code("x = 5")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Assign)
        self.assertEqual(nodes[0].name, "x")
        self.assertIsInstance(nodes[0].value, ast.Number)

    def test_if_elif_else_grouping(self):
        code = '''if x > 5
    say "big"
elif x > 2
    say "medium"
else
    say "small"'''
        nodes = self.parse_code(code)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.If)
        self.assertEqual(len(nodes[0].else_body), 1) # Contains ELIF block
        self.assertIsInstance(nodes[0].else_body[0], ast.If) # ELIF is parsed as nested IF
        self.assertIsNotNone(nodes[0].else_body[0].else_body) # ELSE block
        
    def test_repeat_loop(self):
        nodes = self.parse_code("repeat 5 times\n    say \"hello\"")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Repeat)
        self.assertEqual(len(nodes[0].body), 1)
        self.assertIsInstance(nodes[0].body[0], ast.Print)

    def test_function_definition(self):
        code = '''to greet name
    say "Hello " + name
    give name'''
        nodes = self.parse_code(code)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.FunctionDef)
        self.assertEqual(nodes[0].name, "greet")
        self.assertEqual(len(nodes[0].args), 1)
        self.assertEqual(nodes[0].args[0][0], "name")
        self.assertEqual(len(nodes[0].body), 2)
        self.assertIsInstance(nodes[0].body[1], ast.Return)

    def test_class_definition(self):
        code = '''thing Person
    has name = "Unknown"
    can say_hi
        say self.name'''
        nodes = self.parse_code(code)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.ClassDef)
        self.assertEqual(nodes[0].name, "Person")
        self.assertEqual(nodes[0].properties[0][0], "name")
        self.assertEqual(nodes[0].methods[0].name, "say_hi")

if __name__ == '__main__':
    unittest.main()
