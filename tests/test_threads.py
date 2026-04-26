import unittest

import shell_lite

print(f"Test using shell_lite from: {shell_lite.__file__}")

from shell_lite.ast_nodes import *
from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser


class TestThreads(unittest.TestCase):
    def setUp(self):
        self.interpreter = Interpreter()

    def run_source(self, source):
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        res = None
        for stmt in statements:
            res = self.interpreter.visit(stmt)
        return res

    def test_parallel_gather(self):
        source = """
to slow_inc n
    wait 0.1
    give n + 1

tasks = parallel
    slow_inc(1)
    slow_inc(2)
    slow_inc(3)

results = gather tasks
"""
        self.run_source(source)
        results = self.interpreter.global_env.get('results')
        self.assertEqual(results, [2, 3, 4])

    def test_lock(self):
        source = """
count = 0
to worker
    repeat 10
        lock "counter"
            count = count + 1

t = parallel
    worker()
    worker()
    worker()

gather t
"""
        self.run_source(source)
        count = self.interpreter.global_env.get('count')
        self.assertEqual(count, 30)

    def test_channels(self):
        source = """
ch = channel
send ch "msg1"
send ch "msg2"
val1 = receive ch
val2 = receive ch
"""
        self.run_source(source)
        self.assertEqual(self.interpreter.global_env.get('val1'), "msg1")
        self.assertEqual(self.interpreter.global_env.get('val2'), "msg2")

if __name__ == '__main__':
    unittest.main()
