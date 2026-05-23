"""
Unit tests for the TestRunner class.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shell_lite.test_runner import TestRunner, TestResult


class TestTestRunner(unittest.TestCase):
    """
    Test suite for ShellLite TestRunner.
    """

    def test_test_result_pass(self):
        """Test that a passed test result has correct attributes."""
        result = TestResult("/path/to/test.shl", passed=True)
        self.assertTrue(result.passed)
        self.assertIsNone(result.error)
        self.assertEqual(result.file_path, "/path/to/test.shl")

    def test_test_result_fail(self):
        """Test that a failed test result has correct attributes."""
        result = TestResult("/path/to/test.shl", passed=False, error="Some error")
        self.assertFalse(result.passed)
        self.assertEqual(result.error, "Some error")

    def test_discover_no_files(self):
        """Test discovery returns empty list when no test files exist."""
        runner = TestRunner("/nonexistent")
        files = runner._discover_test_files()
        self.assertEqual(files, [])

    def test_runner_init(self):
        """Test that TestRunner initializes with correct target_dir."""
        runner = TestRunner("/some/dir")
        self.assertEqual(runner.target_dir, "/some/dir")
        self.assertEqual(runner.results, [])