"""
-----Purpose: Unit tests for the Lexer.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.lexer import Lexer, Token

class TestLexer(unittest.TestCase):
    """
    -----Purpose: Test suite for Lexer functionality.
    """
    def test_lexer_initialization(self):
        lexer = Lexer("x = 1")
        self.assertEqual(lexer.source_code, "x = 1")
        self.assertEqual(lexer.line_number, 1)

    def test_basic_assignment(self):
        lexer = Lexer("x = 5")
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, 'ID')
        self.assertEqual(tokens[0].value, 'x')
        self.assertEqual(tokens[1].type, 'ASSIGN')
        self.assertEqual(tokens[2].type, 'NUMBER')
        self.assertEqual(tokens[2].value, '5')
        self.assertEqual(tokens[3].type, 'NEWLINE')
        self.assertEqual(tokens[4].type, 'EOF')

    def test_strings(self):
        lexer = Lexer('name = "ShellLite"')
        tokens = lexer.tokenize()
        self.assertEqual(tokens[2].type, 'STRING')
        self.assertEqual(tokens[2].value, 'ShellLite')

    def test_natural_math_comparisons(self):
        lexer = Lexer("if x is more than 5")
        tokens = lexer.tokenize()
        # [IF, ID(x), GT, NUMBER(5), NEWLINE, EOF]
        self.assertEqual(tokens[0].type, 'IF')
        self.assertEqual(tokens[1].type, 'ID')
        self.assertEqual(tokens[2].type, 'GT')
        self.assertEqual(tokens[3].type, 'NUMBER')
        
    def test_indentation_dedentation(self):
        code = '''if x > 5
    say "yes"
else
    say "no"'''
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type for t in tokens]
        self.assertIn('INDENT', types)
        self.assertIn('DEDENT', types)
        # Should end with EOF
        self.assertEqual(types[-1], 'EOF')
        
    def test_bracket_depth_ignores_indent(self):
        code = '''arr = [
    1,
    2,
    3
]'''
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type for t in tokens]
        # Should not produce INDENT or DEDENT inside brackets
        self.assertNotIn('INDENT', types)
        self.assertNotIn('DEDENT', types)

    def test_multiline_comments(self):
        code = '''x = 10 /*
this is a
multi-line comment
*/ y = 20'''
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type for t in tokens]
        # Check that x and y are lexed
        ids = [t.value for t in tokens if t.type == 'ID']
        self.assertEqual(ids, ['x', 'y'])

if __name__ == '__main__':
    unittest.main()
