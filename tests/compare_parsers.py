"""
-----Purpose: Benchmarks the Geometric Binding Parser (GBP) performance.
"""
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser

def benchmark(filename):
    """
    -----Purpose: Runs a performance benchmark on the specified file.
    """
    with open(filename, 'r') as f:
        source = f.read()
    long_source = source * 500
    print(f"Benchmarking GBP on {len(long_source)} chars of code...")
    lexer = Lexer(long_source)
    tokens = lexer.tokenize()
    
    start = time.perf_counter()
    p_new = GeometricBindingParser(list(tokens))
    ast_new = p_new.parse()
    end = time.perf_counter()
    t_new = end - start
    print(f"Geometric-Binding: {t_new:.4f}s")
    print(f"Nodes Parsed: {len(ast_new)}")

if __name__ == "__main__":
    """
    -----Purpose: Benchmark entry point.
    """
    benchmark("tests/benchmark.shl")