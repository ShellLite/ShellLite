"""
-----Purpose: Unit tests for the Geometric Binding Parser (GBP).
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser

class TestParser(unittest.TestCase):
    """
    -----Purpose: Test suite for GBP core functionality.
    """
    def test_parser_initialization(self):
        """
        -----Purpose: Verifies that the parser initializes correctly with tokens.
        """
        lex = Lexer("x = 1")
        tokens = lex.tokenize()
        parser = GeometricBindingParser(tokens)
        self.assertEqual(len(parser.tokens), 5) # ID, ASSIGN, NUMBER, NEWLINE, EOF

    def test_parse_expression(self):
        """
        -----Purpose: Verifies basic expression parsing into AST nodes.
        """
        lex = Lexer("1 + 1")
        tokens = lex.tokenize()
        parser = GeometricBindingParser(tokens)
        ast = parser.parse()
        self.assertEqual(len(ast), 1)

if __name__ == '__main__':
    """
    -----Purpose: Entry point for parser unit tests.
    """
    unittest.main()