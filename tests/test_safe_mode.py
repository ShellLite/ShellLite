import io
import os
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
    python_code = compile_code(source, str(tmp_path / "main.shl"), [str(tmp_path)])
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(python_code, {"__name__": "__main__"})
    assert buf.getvalue().strip().splitlines() == ["1", "2"]
