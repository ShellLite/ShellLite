"""
Unit tests for ShellLite built-in/stdlib behavior.
"""

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser import Parser


class TestStdLib(unittest.TestCase):
    """Test suite for built-in functions exposed by the interpreter."""

    def run_code(self, code: str):
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()

            parser = Parser(tokens)
            ast_nodes = parser.parse()

            interpreter = Interpreter()

            last_val = None
            for node in ast_nodes:
                last_val = interpreter.visit(node)

            return interpreter.global_env, last_val, interpreter
        except Exception as exc:
            self.fail(f"Failed to execute ShellLite code: {code}\n{exc}")

    def test_builtin_value_functions(self):
        cases = [
            ("items_len = len([1, 2, 3])", "items_len", 3),
            ("items = list([1, 2, 3])", "items", [1, 2, 3]),
            ("flag = bool(1)", "flag", True),
            ("decimal = float(7)", "decimal", 7.0),
            ("series = [1 to 4]", "series", [1, 2, 3]),
            ("kind = typeof(123)", "kind", "int"),
            ("magnitude = abs(0 - 9)", "magnitude", 9),
            ("text = str(42)", "text", "42"),
            ("whole = int(7.8)", "whole", 7),
        ]

        for code, variable, expected in cases:
            with self.subTest(code=code):
                env, _, _ = self.run_code(code)
                self.assertEqual(env.get(variable), expected)

    def test_print_function(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            _, last_val, _ = self.run_code('say "Hello ShellLite"')

        self.assertEqual(buffer.getvalue(), "Hello ShellLite\n")
        self.assertEqual(last_val, "Hello ShellLite")

    def test_input_function(self):
        with patch("builtins.input", return_value="ShellLite User") as mocked_input:
            env, _, _ = self.run_code('user_name = ask "Your name? "')

        self.assertEqual(env.get("user_name"), "ShellLite User")
        mocked_input.assert_called_once_with("Your name? ")

    def test_builtin_string_helpers(self):
        cases = [
            ('result = upper("hello")', "result", "HELLO"),
            ('result = lower("WORLD")', "result", "world"),
            ('result = split("a b c")', "result", ["a", "b", "c"]),
            ('result = split("a,b,c", ",")', "result", ["a", "b", "c"]),
            ('result = count("banana", "a")', "result", 3),
            ('result = ord("A")', "result", 65),
            ("result = char(65)", "result", "A"),
        ]

        for code, variable, expected in cases:
            with self.subTest(code=code):
                env, _, _ = self.run_code(code)
                self.assertEqual(env.get(variable), expected)

    def test_builtin_list_operations(self):
        cases = [
            ("result = sum([1, 2, 3])", "result", 6),
            ("result = sort([3, 1, 2])", "result", [1, 2, 3]),
            ("result = contains([1, 2, 3], 2)", "result", True),
            ("result = contains([1, 2, 3], 9)", "result", False),
            ("result = empty([])", "result", True),
            ("result = empty([1])", "result", False),
            ("result = tuple([1, 2, 3])", "result", (1, 2, 3)),
        ]

        for code, variable, expected in cases:
            with self.subTest(code=code):
                env, _, _ = self.run_code(code)
                self.assertEqual(env.get(variable), expected)

    def test_builtin_xor(self):
        env, _, _ = self.run_code("result = xor(5, 3)")
        self.assertEqual(env.get("result"), 6)

    def test_builtin_add_remove(self):
        code = "\n".join([
            "items = [1, 2, 3]",
            "add(items, 4)",
            "remove(items, 2)",
        ])
        env, _, _ = self.run_code(code)
        self.assertEqual(env.get("items"), [1, 3, 4])

    def test_builtin_json_roundtrip(self):
        code = "\n".join([
            'parsed = json_parse("{\\"a\\": 1, \\"b\\": [2, 3]}")',
            "text = json_stringify(parsed, 0)",
        ])
        env, _, _ = self.run_code(code)
        self.assertEqual(env.get("parsed"), {"a": 1, "b": [2, 3]})
        self.assertIn('"a"', env.get("text"))

    def test_builtin_io_helpers(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "sample.txt").replace("\\", "/")
            code = "\n".join([
                f'std_io_write("{path}", "hello ")',
                f'std_io_append("{path}", "world")',
                f'content = std_io_read("{path}")',
                f'flag = exists("{path}")',
            ])
            env, _, _ = self.run_code(code)
            self.assertEqual(env.get("content"), "hello world")
            self.assertTrue(env.get("flag"))


if __name__ == "__main__":
    unittest.main()
