"""
Unit tests for ShellLite standard library builtins.
Tests all built-in functions provided by the interpreter.
"""
import os
import sys
import unittest
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser import Parser


class TestStdLib(unittest.TestCase):
    """
    Test suite for ShellLite standard library builtins.
    """

    def run_code(self, code: str):
        """Helper to run ShellLite code and return the global env."""
        lex = Lexer(code)
        tokens = lex.tokenize()
        parser = Parser(tokens)
        ast_nodes = parser.parse()
        interpreter = Interpreter()
        last_val = None
        for node in ast_nodes:
            last_val = interpreter.visit(node)
        return interpreter.global_env, last_val, interpreter

    def run_code_capture(self, code: str):
        """Helper to run ShellLite code and capture stdout output."""
        old_stdout = sys.stdout
        sys.stdout = captured = StringIO()
        try:
            lex = Lexer(code)
            tokens = lex.tokenize()
            parser = Parser(tokens)
            ast_nodes = parser.parse()
            interpreter = Interpreter()
            for node in ast_nodes:
                interpreter.visit(node)
        finally:
            sys.stdout = old_stdout
        return captured.getvalue()

    # Type conversion builtins

    def test_str_function(self):
        env, _, _ = self.run_code("x = str(123)")
        self.assertEqual(env.get("x"), "123")
        self.assertIsInstance(env.get("x"), str)

    def test_int_function(self):
        env, _, _ = self.run_code("x = int(123)")
        self.assertEqual(env.get("x"), 123)
        self.assertIsInstance(env.get("x"), int)

    def test_float_function(self):
        env, _, _ = self.run_code("x = float(123)")
        self.assertEqual(env.get("x"), 123.0)
        self.assertIsInstance(env.get("x"), float)

    def test_bool_function(self):
        env, _, _ = self.run_code("x = bool(1); y = bool(0)")
        self.assertTrue(env.get("x"))
        self.assertFalse(env.get("y"))

    def test_list_function(self):
        env, _, _ = self.run_code("x = list(1, 2, 3)")
        self.assertEqual(env.get("x"), [1, 2, 3])
        self.assertIsInstance(env.get("x"), list)

    def test_tuple_function(self):
        env, _, _ = self.run_code("x = tuple([1, 2, 3])")
        self.assertEqual(env.get("x"), (1, 2, 3))
        self.assertIsInstance(env.get("x"), tuple)

    # Math builtins

    def test_abs_function(self):
        env, _, _ = self.run_code("x = abs(-5)")
        self.assertEqual(env.get("x"), 5)

    def test_len_function(self):
        env, _, _ = self.run_code("x = len([1, 2, 3])")
        self.assertEqual(env.get("x"), 3)
        env2, _, _ = self.run_code('x = len("hello")')
        self.assertEqual(env2.get("x"), 5)

    def test_sum_function(self):
        env, _, _ = self.run_code("x = sum([1, 2, 3, 4])")
        self.assertEqual(env.get("x"), 10)

    # String builtins

    def test_upper_function(self):
        env, _, _ = self.run_code('x = upper("hello")')
        self.assertEqual(env.get("x"), "HELLO")

    def test_lower_function(self):
        env, _, _ = self.run_code('x = lower("HELLO")')
        self.assertEqual(env.get("x"), "hello")

    def test_split_function(self):
        env, _, _ = self.run_code('x = split("a,b,c", ",")')
        self.assertEqual(env.get("x"), ["a", "b", "c"])

    def test_split_default_separator(self):
        env, _, _ = self.run_code('x = split("hello world")')
        self.assertEqual(env.get("x"), ["hello", "world"])

    def test_count_on_string(self):
        env, _, _ = self.run_code('x = count("hello", "l")')
        self.assertEqual(env.get("x"), 2)

    def test_count_on_list(self):
        env, _, _ = self.run_code("x = count([1, 2, 2, 3], 2)")
        self.assertEqual(env.get("x"), 2)

    def test_ord_function(self):
        env, _, _ = self.run_code('x = ord("a")')
        self.assertEqual(env.get("x"), 97)

    def test_char_function(self):
        env, _, _ = self.run_code("x = char(97)")
        self.assertEqual(env.get("x"), "a")

    # Collection builtins

    def test_contains_true(self):
        env, _, _ = self.run_code('x = contains("hello", "ell")')
        self.assertTrue(env.get("x"))

    def test_contains_false(self):
        env, _, _ = self.run_code('x = contains("hello", "xyz")')
        self.assertFalse(env.get("x"))

    def test_empty_true(self):
        env, _, _ = self.run_code("x = empty([])")
        self.assertTrue(env.get("x"))

    def test_empty_false(self):
        env, _, _ = self.run_code("x = empty([1])")
        self.assertFalse(env.get("x"))

    def test_sort_function(self):
        env, _, _ = self.run_code("x = sort([3, 1, 2])")
        self.assertEqual(env.get("x"), [1, 2, 3])

    # Boolean constants

    def test_true_constant(self):
        env, _, _ = self.run_code("x = true")
        self.assertIs(env.get("x"), True)

    def test_false_constant(self):
        env, _, _ = self.run_code("x = false")
        self.assertIs(env.get("x"), False)

    def test_yes_constant(self):
        env, _, _ = self.run_code("x = yes")
        self.assertIs(env.get("x"), True)

    def test_no_constant(self):
        env, _, _ = self.run_code("x = no")
        self.assertIs(env.get("x"), False)

    def test_null_constant(self):
        env, _, _ = self.run_code("x = null")
        self.assertIsNone(env.get("x"))

    # Type checking

    def test_typeof_number(self):
        env, _, _ = self.run_code("x = typeof(123)")
        self.assertEqual(env.get("x"), "int")

    def test_typeof_string(self):
        env, _, _ = self.run_code('x = typeof("hello")')
        self.assertEqual(env.get("x"), "str")

    def test_typeof_list(self):
        env, _, _ = self.run_code("x = typeof([1, 2, 3])")
        self.assertEqual(env.get("x"), "list")

    def test_typeof_bool(self):
        env, _, _ = self.run_code("x = typeof(true)")
        self.assertEqual(env.get("x"), "bool")

    # Print / say builtins (capture stdout)

    def test_print_captures_output(self):
        output = self.run_code_capture('say "hello"')
        self.assertEqual(output.strip(), "hello")

    def test_say_builtin(self):
        output = self.run_code_capture('say "world"')
        self.assertEqual(output.strip(), "world")


if __name__ == '__main__':
    unittest.main()