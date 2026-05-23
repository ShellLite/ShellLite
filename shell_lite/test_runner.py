"""
Test runner for ShellLite .shl test files.
Discovers and runs .shl test files using the ShellLite interpreter.
"""
import os
import sys
import glob
from typing import List, Tuple

from .lexer import Lexer
from .parser import Parser
from .interpreter import Interpreter


class TestResult:
    def __init__(self, file_path: str, passed: bool, error: str = None):
        self.file_path = file_path
        self.passed = passed
        self.error = error


class TestRunner:
    """
    Discovers and runs ShellLite test files (.shl) in a given directory.
    Test files are identified by being in a directory named 'tests' or
    by having '_test' in their name.
    """

    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir
        self.results: List[TestResult] = []

    def discover_and_run(self):
        """Discover .shl test files and run them."""
        test_files = self._discover_test_files()
        if not test_files:
            print(f"No .shl test files found in {self.target_dir}")
            return

        print(f"Running {len(test_files)} test file(s) from {self.target_dir}...\n")

        for test_file in test_files:
            self._run_test_file(test_file)

        self._print_summary()

    def _discover_test_files(self) -> List[str]:
        """Find all .shl test files in the target directory."""
        pattern = os.path.join(self.target_dir, "**", "*.shl")
        all_shl_files = glob.glob(pattern, recursive=True)

        test_files = [
            f for f in all_shl_files
            if "_test" in os.path.basename(f) or os.path.basename(os.path.dirname(f)) == "tests"
        ]
        return test_files

    def _run_test_file(self, file_path: str):
        """Run a single .shl test file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            lex = Lexer(code)
            tokens = lex.tokenize()
            parser = Parser(tokens)
            ast_nodes = parser.parse()

            interpreter = Interpreter()
            for node in ast_nodes:
                interpreter.visit(node)

            result = TestResult(file_path, passed=True)
            print(f"PASS: {os.path.relpath(file_path, self.target_dir)}")
        except Exception as e:
            result = TestResult(file_path, passed=False, error=str(e))
            print(f"FAIL: {os.path.relpath(file_path, self.target_dir)}")
            print(f"      Error: {e}")

        self.results.append(result)

    def _print_summary(self):
        """Print a summary of test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\n{'='*50}")
        print(f"Results: {passed}/{total} passed")

        if failed > 0:
            print(f"Failed: {failed}")
            sys.exit(1)
        else:
            print("All tests passed!")