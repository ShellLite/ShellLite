import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser
def check_gbp(code, name):
    print(f"--- Testing {name} ---")
    print(f"Code:\n{code}")
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = GeometricBindingParser(tokens)
    parser.topology_scan()
    print("\n[Phase 1] Topology Roots:")
    for node in parser.root_nodes:
        print(f"  {node}")
        for child in node.children:
            print(f"    -> {child}")
    ast = parser.parse()
    print("\n[Phase 2] AST:")
    for node in ast:
        print(f"  {node}")
    print("------------------------\n")
if __name__ == "__main__":
    code1 = """
x = 10
if x > 5:
    print x
    y = x + 1
"""
    check_gbp(code1, "Basic If")
    code2 = """
to greet name:
    print "Hello"
    print name
greet "Bob"
"""
    check_gbp(code2, "Function Def")