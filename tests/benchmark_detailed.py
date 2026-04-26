import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shell_lite.parser import Parser

from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser


def benchmark(filename, iterations=10):
    with open(filename, 'r') as f:
        source = f.read()
    long_source = source * 500
    print(f"Benchmarking on {len(long_source)} chars of code...")
    print(f"Running {iterations} iterations each...\n")
    lexer = Lexer(long_source)
    tokens = lexer.tokenize()
    rd_times = []
    for i in range(iterations):
        tokens_copy = list(tokens)
        start = time.perf_counter()
        p = Parser(tokens_copy)
        ast = p.parse()
        end = time.perf_counter()
        rd_times.append(end - start)
    gbp_times = []
    for i in range(iterations):
        tokens_copy = list(tokens)
        start = time.perf_counter()
        p = GeometricBindingParser(tokens_copy)
        ast = p.parse()
        end = time.perf_counter()
        gbp_times.append(end - start)
    rd_mean = statistics.mean(rd_times)
    rd_stdev = statistics.stdev(rd_times) if len(rd_times) > 1 else 0
    gbp_mean = statistics.mean(gbp_times)
    gbp_stdev = statistics.stdev(gbp_times) if len(gbp_times) > 1 else 0
    print("Recursive Descent:")
    print(f"  Mean: {rd_mean:.4f}s (+/- {rd_stdev:.4f}s)")
    print(f"  Min:  {min(rd_times):.4f}s")
    print(f"  Max:  {max(rd_times):.4f}s")
    print()
    print("Geometric-Binding Parser:")
    print(f"  Mean: {gbp_mean:.4f}s (+/- {gbp_stdev:.4f}s)")
    print(f"  Min:  {min(gbp_times):.4f}s")
    print(f"  Max:  {max(gbp_times):.4f}s")
    print()
    speedup = rd_mean / gbp_mean if gbp_mean > 0 else 0
    print(f"Speedup: {speedup:.2f}x")
    return speedup
if __name__ == "__main__":
    benchmark("tests/benchmark.shl", iterations=10)