"""
-----Purpose: Unit tests for the Geometric Binding Parser (GBP).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shell_lite.ast_nodes as ast
from shell_lite.lexer import Lexer
from shell_lite.parser import Parser


class TestParser(unittest.TestCase):
    """
    -----Purpose: Test suite for GBP core functionality.
    """

    def parse_code(self, code: str):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
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
        self.assertEqual(len(nodes[0].else_body), 1)  # Contains ELIF block
        self.assertIsInstance(
            nodes[0].else_body[0], ast.If
        )  # ELIF is parsed as nested IF
        self.assertIsNotNone(nodes[0].else_body[0].else_body)  # ELSE block

    def test_repeat_loop(self):
        nodes = self.parse_code('repeat 5 times\n    say "hello"')
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Repeat)
        self.assertEqual(len(nodes[0].body), 1)
        self.assertIsInstance(nodes[0].body[0], ast.Print)

    def test_function_definition(self):
        code = """to greet name
    say "Hello " + name
    give name"""
        nodes = self.parse_code(code)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.FunctionDef)
        self.assertEqual(nodes[0].name, "greet")
        self.assertEqual(len(nodes[0].args), 1)
        self.assertEqual(nodes[0].args[0][0], "name")
        self.assertEqual(len(nodes[0].body), 2)
        self.assertIsInstance(nodes[0].body[1], ast.Return)

    def test_class_definition(self):
        code = """thing Person
    has name = "Unknown"
    can say_hi
        say self.name"""
        nodes = self.parse_code(code)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.ClassDef)
        self.assertEqual(nodes[0].name, "Person")
        self.assertEqual(nodes[0].properties[0][0], "name")
        self.assertEqual(nodes[0].methods[0].name, "say_hi")

    def test_a_list_assignment(self):
        nodes = self.parse_code("x = a list")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Assign)
        self.assertEqual(nodes[0].name, "x")
        self.assertIsInstance(nodes[0].value, ast.ListVal)
        self.assertEqual(len(nodes[0].value.elements), 0)

    def test_a_unique_set_assignment(self):
        nodes = self.parse_code("x = a unique set")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Assign)
        self.assertEqual(nodes[0].name, "x")
        self.assertIsInstance(nodes[0].value, ast.Call)
        self.assertEqual(nodes[0].value.name, "set")
        self.assertIsInstance(nodes[0].value.args[0], ast.ListVal)
        self.assertEqual(len(nodes[0].value.args[0].elements), 0)

    def test_colored_print(self):
        nodes = self.parse_code('say in green "hello"')
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Print)
        self.assertEqual(nodes[0].color, "green")
        self.assertIsNone(nodes[0].style)
        self.assertIsInstance(nodes[0].expression, ast.String)
        self.assertEqual(nodes[0].expression.value, "hello")

    def test_bold_colored_print(self):
        nodes = self.parse_code('say bold red "hello"')
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Print)
        self.assertEqual(nodes[0].color, "red")
        self.assertEqual(nodes[0].style, "bold")
        self.assertIsInstance(nodes[0].expression, ast.String)
        self.assertEqual(nodes[0].expression.value, "hello")

    def test_const_statement(self):
        nodes = self.parse_code('const FILE_NAME = "tasks.txt"')
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.ConstAssign)
        self.assertEqual(nodes[0].name, "FILE_NAME")
        self.assertIsInstance(nodes[0].value, ast.String)
        self.assertEqual(nodes[0].value.value, "tasks.txt")

    def test_augmented_assignment(self):
        nodes = self.parse_code("x += 5")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Assign)
        self.assertEqual(nodes[0].name, "x")
        self.assertIsInstance(nodes[0].value, ast.BinOp)
        self.assertEqual(nodes[0].value.op, "+")
        self.assertIsInstance(nodes[0].value.left, ast.VarAccess)
        self.assertEqual(nodes[0].value.left.name, "x")
        self.assertIsInstance(nodes[0].value.right, ast.Number)
        self.assertEqual(nodes[0].value.right.value, 5)

    def test_augmented_index_assignment(self):
        nodes = self.parse_code("x[0] += 5")
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.IndexAssign)
        self.assertIsInstance(nodes[0].obj, ast.VarAccess)
        self.assertEqual(nodes[0].obj.name, "x")
        self.assertIsInstance(nodes[0].index, ast.Number)
        self.assertEqual(nodes[0].index.value, 0)
        self.assertIsInstance(nodes[0].value, ast.BinOp)
        self.assertEqual(nodes[0].value.op, "+")
        self.assertIsInstance(nodes[0].value.left, ast.IndexAccess)
        self.assertEqual(nodes[0].value.left.obj.name, "x")
        self.assertEqual(nodes[0].value.left.index.value, 0)
        self.assertIsInstance(nodes[0].value.right, ast.Number)
        self.assertEqual(nodes[0].value.right.value, 5)

    def test_input_tag_parsing(self):
        nodes = self.parse_code('input type="text" placeholder="Your Name"')
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ast.Call)
        self.assertEqual(nodes[0].name, "input")
        self.assertEqual(len(nodes[0].kwargs), 2)
        self.assertEqual(nodes[0].kwargs[0][0], "type")
        self.assertEqual(nodes[0].kwargs[0][1].value, "text")


if __name__ == "__main__":
    unittest.main()
