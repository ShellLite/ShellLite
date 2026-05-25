"""
Test runner for ShellLite .shl test files.
Specifically designed to handle TestBlock and Assertion nodes.
"""

import os
from typing import List

from .ast_nodes import TestBlock
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser


class TestRunner:
    __test__ = False

    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir

    def discover_and_run(self):
        print(f"\n{'=' * 50}")
        print("  ShellLite Test Runner")
        print(f"  Target: {os.path.abspath(self.target_dir)}")
        print(f"{'=' * 50}\n")

        test_files = self._find_shl_files(self.target_dir)
        if not test_files:
            print("No .shl files found to test.")
            return

        total_tests = 0
        total_passed = 0
        total_failed = 0

        for file_path in test_files:
            rel_path = os.path.relpath(file_path, self.target_dir)
            print(f"FILE: {rel_path}")

            file_passed, file_failed = self._run_test_file(file_path)
            total_passed += file_passed
            total_failed += file_failed
            total_tests += file_passed + file_failed
            print()

        print(f"{'=' * 50}")
        print("FINAL RESULTS")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Total:  {total_tests}")
        print(f"{'=' * 50}\n")

        if total_failed > 0:
            exit(1)

    def _find_shl_files(self, directory: str) -> List[str]:
        shl_files = []
        for root, _, files in os.walk(directory):
            if "modules" in root or ".cache" in root:
                continue
            for file in files:
                if file.endswith(".shl") and ("test" in file or "test" in root):
                    shl_files.append(os.path.join(root, file))
        return shl_files

    def _run_test_file(self, file_path: str) -> tuple[int, int]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            nodes = parser.parse()

            interpreter = Interpreter()

            passed = 0
            failed = 0

            # Find explicit test blocks
            test_blocks = [n for n in nodes if isinstance(n, TestBlock)]

            if not test_blocks:
                # If no test blocks, run the whole file as a single test
                print("  [RUNNING] Entire file as test...", end=" ", flush=True)
                try:
                    for node in nodes:
                        interpreter.visit(node)
                    print("PASSED")
                    return 1, 0
                except AssertionError as e:
                    print(f"FAILED\n    > {e}")
                    return 0, 1
                except Exception as e:
                    print(f"ERROR\n    > {e}")
                    return 0, 1

            # Run each test block
            for block in test_blocks:
                if interpreter.visit(block):
                    passed += 1
                else:
                    failed += 1

            return passed, failed

        except Exception as e:
            print(f"  [CRITICAL ERROR] Could not parse or execute file: {e}")
            return 0, 1
