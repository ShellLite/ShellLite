import sys

sys.path.insert(0, '.')
from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser

source = '''
to eat
begin
    say "eating"
end

eat
'''
lex = Lexer(source)
tokens = lex.tokenize()
parser = GeometricBindingParser(tokens)
ast = parser.parse()
interp = Interpreter()
for node in ast:
    interp.visit(node)