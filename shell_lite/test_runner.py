import os
import time

from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser


class TestRunner:
    def __init__(self, directory='.'):
        self.directory = directory
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.total_time = 0.0

    def discover_and_run(self):
        print("\n\033[1mShellLite Test Runner v0.6\033[0m")
        print(f"Discovering tests in {os.path.abspath(self.directory)}...\n")
        
        file_paths = []
        for root, _, files in os.walk(self.directory):
            for f in files:
                if f.endswith('.shl'):
                    file_paths.append(os.path.join(root, f))
                    
        if not file_paths:
            print("No .shl files found to test.")
            return

        start_time = time.time()
        
        for file_path in file_paths:
            self._run_file(file_path)
            
        self.total_time = time.time() - start_time
        self.print_summary()

    def _run_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            if 'test ' not in code:
                return
                
            lex = Lexer(code)
            tokens = lex.tokenize()
            parser = GeometricBindingParser(tokens)
            ast_nodes = parser.parse()
            
            interpreter = Interpreter()
            self._execute_tests(ast_nodes, interpreter, path)
            
        except Exception as e:
            print(f"\033[93m[WARN]\033[0m Failed to parse/check {path}: {e}")
            
    def _execute_tests(self, ast_nodes, interpreter, path):
        from shell_lite.ast_nodes import TestBlock
        tests_run_in_file = 0
        
        for node in ast_nodes:
            if isinstance(node, TestBlock):
                if tests_run_in_file == 0:
                     print(f"\033[1mRunning tests in \033[94m{path}\033[0m")
                tests_run_in_file += 1
                try:
                    for stmt in node.body:
                        interpreter.visit(stmt)
                    print(f"  \033[92m[PASS]\033[0m {node.name}")
                    self.passed += 1
                except AssertionError as e:
                    print(f"  \033[91m[FAIL]\033[0m {node.name}: {e}")
                    self.failed += 1
                except Exception as e:
                    print(f"  \033[91m[ERROR]\033[0m {node.name}: {e}")
                    self.errors += 1
            else:
                 try:
                     interpreter.visit(node)
                 except Exception:
                     pass

    def print_summary(self):
        total = self.passed + self.failed + self.errors
        print("\n" + "="*50)
        print("\033[1mTest Summary\033[0m")
        print("="*50)
        print(f"Executed: {total} tests in {self.total_time:.3f}s")
        if self.passed > 0:
            print(f"\033[92mPassed:   {self.passed}\033[0m")
        if self.failed > 0:
            print(f"\033[91mFailed:   {self.failed}\033[0m")
        if self.errors > 0:
            print(f"\033[91mErrors:   {self.errors}\033[0m")
            
        if self.failed == 0 and self.errors == 0 and total > 0:
            print("\n\033[1;92mAll tests passed successfully!\033[0m")
        elif total == 0:
            pass
        else:
            print("\n\033[1;91mSome tests failed. See results above.\033[0m")
