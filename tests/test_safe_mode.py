import io
import os
import shutil
from contextlib import redirect_stdout

import pytest

from shell_lite.compiler.ast_compiler import ASTCompiler
from shell_lite.compiler.linker import StaticLinker
from shell_lite.compiler.optimizer import Optimizer
from shell_lite.compiler.semantic_analyzer import SemanticAnalyzer
from shell_lite.interpreter import Interpreter
from shell_lite.lexer import Lexer
from shell_lite.parser import Parser
from shell_lite.runtime_policy import PolicyError, reset_policy_cache


def run_code(code: str):
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    nodes = parser.parse()
    interpreter = Interpreter()
    last_val = None
    for node in nodes:
        last_val = interpreter.visit(node)
    return last_val


def compile_code(source: str, filename: str, search_paths):
    lexer = Lexer(source)
    parser = Parser(lexer.tokenize())
    initial_ast = parser.parse()
    linker = StaticLinker(search_paths=search_paths)
    linked = linker.link(initial_ast, os.path.abspath(filename))
    SemanticAnalyzer().analyze(linked)
    optimized = Optimizer().optimize(linked)
    if isinstance(optimized, dict):
        main_path = os.path.abspath(filename)
        return ASTCompiler().compile(optimized[main_path])
    return ASTCompiler().compile(optimized)


def test_safe_mode_blocks_fs_read(monkeypatch):
    monkeypatch.setenv("SHL_SAFE", "1")
    monkeypatch.delenv("SHL_ALLOW_FS_READ", raising=False)
    monkeypatch.delenv("SHL_ALLOW_FS", raising=False)
    reset_policy_cache()
    with pytest.raises(PolicyError):
        run_code('read "blocked.txt"')


def test_safe_mode_allows_fs_read_allowlist(monkeypatch, tmp_path):
    target = tmp_path / "allowed.txt"
    target.write_text("ok", encoding="utf-8")
    monkeypatch.setenv("SHL_SAFE", "1")
    monkeypatch.setenv("SHL_ALLOW_FS_READ", "1")
    monkeypatch.setenv("SHL_FS_ALLOW", str(tmp_path))
    reset_policy_cache()
    result = run_code(f'read "{target.as_posix()}"')
    assert result == "ok"


def test_safe_mode_blocks_python_import(monkeypatch):
    monkeypatch.setenv("SHL_SAFE", "1")
    monkeypatch.delenv("SHL_ALLOW_PY_IMPORT", raising=False)
    reset_policy_cache()
    with pytest.raises(PolicyError):
        run_code('use python "os"')


def test_safe_mode_blocks_execute(monkeypatch):
    monkeypatch.setenv("SHL_SAFE", "1")
    monkeypatch.delenv("SHL_ALLOW_EXEC", raising=False)
    reset_policy_cache()
    with pytest.raises(PolicyError):
        run_code('execute "whoami"')


def test_compiled_namespace_import_shared_state(tmp_path, monkeypatch):
    monkeypatch.delenv("SHL_SAFE", raising=False)
    reset_policy_cache()
    mod_path = tmp_path / "mod.shl"
    mod_path.write_text(
        "counter = 0\nfn inc() {\n    counter = counter + 1\n    return counter\n}\n",
        encoding="utf-8",
    )
    source = f'''
import "{mod_path.as_posix()}" as a
import "{mod_path.as_posix()}" as b
say a.inc()
say b.inc()
'''
    # Create a build directory to simulate a package
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "__init__.py").write_text("")

    lexer = Lexer(source)
    parser = Parser(lexer.tokenize())
    initial_ast = parser.parse()
    linker = StaticLinker(search_paths=[str(tmp_path)])
    linked = linker.link(initial_ast, os.path.abspath(str(tmp_path / "main.shl")))

    SemanticAnalyzer().analyze(linked)
    optimizer = Optimizer()
    optimized = optimizer.optimize(linked)

    compiler = ASTCompiler()
    # Copy runtime library
    runtime_src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shell_lite", "compiler", "runtime_lib.py")
    shutil.copy(runtime_src, build_dir / "__shl_runtime__.py")

    for path, ast_nodes in optimized.items():
        m_name = os.path.splitext(os.path.basename(path))[0]
        (build_dir / f"{m_name}.py").write_text(compiler.compile(ast_nodes))

    import sys

    monkeypatch.syspath_prepend(str(tmp_path))

    import importlib

    for m in ["build.main", "build.mod", "build.__shl_runtime__"]:
        if m in sys.modules:
            del sys.modules[m]

    # Import the generated main module from the 'build' package
    buf = io.StringIO()
    with redirect_stdout(buf):
        importlib.import_module("build.main")

    assert buf.getvalue().strip().splitlines() == ["1", "2"]
