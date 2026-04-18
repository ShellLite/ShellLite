import sys

sys.path.insert(0, '.')
from shell_lite.ast_nodes import Call, FunctionDef
from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser

source = """to first
begin
say "1"
end

to other
begin
say "2"
end

first
other
"""
lex = Lexer(source)
tokens = lex.tokenize()
parser = GeometricBindingParser(tokens)
ast = parser.parse()
print("=== AST ===")
for i, node in enumerate(ast):
    print(f"Node {i}: {type(node).__name__}")
    if isinstance(node, FunctionDef):
        print(f"  Name: '{node.name}'")
        print(f"  Args: {node.args}")
        print(f"  Body: {node.body}")
        for j, stmt in enumerate(node.body):
            print(f"    stmt[{j}]: {type(stmt).__name__} = {stmt}")
    else:
        print(f"  {node}")
print("\n=== Manual Function Calls ===")
interp = Interpreter()
for node in ast:
    if isinstance(node, FunctionDef):
        interp.visit(node)
print(f"Registered functions: {list(interp.functions.keys())}")
print(f"'first' function body: {interp.functions['first'].body}")
print(f"'other' function body: {interp.functions['other'].body}")
print("\nCalling first:")
interp.visit_Call(Call('first', []))
print("\nCalling other:")
interp.visit_Call(Call('other', []))