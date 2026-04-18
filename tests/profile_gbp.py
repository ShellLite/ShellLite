import cProfile
import io
import os
import pstats
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser


def profile_gbp(filename):
    with open(filename, 'r') as f:
        source = f.read()
    long_source = source * 500
    print(f"Profiling GBP on {len(long_source)} chars of code...")
    lexer = Lexer(long_source)
    tokens = lexer.tokenize()
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(5):
        tokens_copy = list(tokens)
        p = GeometricBindingParser(tokens_copy)
        ast = p.parse()
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)
    print(s.getvalue())
if __name__ == "__main__":
    profile_gbp("tests/benchmark.shl")