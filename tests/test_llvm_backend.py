import llvmlite.binding as llvm
import pytest

from shell_lite.ast_nodes import *
from shell_lite.llvm_backend.codegen import LLVMCompiler


@pytest.fixture(scope="module", autouse=True)
def setup_llvm():
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()


@pytest.fixture
def compiler():
    return LLVMCompiler(filename="test_module")


def test_ast_number(compiler):
    assert compiler.visit(Number("42")).constant == 42


def test_ast_boolean(compiler):
    assert compiler.visit(Boolean("true")).constant == 1
    assert compiler.visit(Boolean("false")).constant == 0


def test_ast_string(compiler):
    val = compiler.visit(String("hello"))
    assert val.type == compiler.char_ptr


def test_ast_binop_add(compiler):
    val = compiler.visit(BinOp(Number("10"), "+", Number("20")))
    assert val is not None


def test_ast_binop_sub(compiler):
    val = compiler.visit(BinOp(Number("20"), "-", Number("10")))
    assert val is not None


def test_ast_binop_mul(compiler):
    val = compiler.visit(BinOp(Number("20"), "*", Number("10")))
    assert val is not None


def test_ast_binop_div(compiler):
    val = compiler.visit(BinOp(Number("20"), "/", Number("10")))
    assert val is not None


def test_integration_hello_world(compiler):
    stmts = [FunctionDef("main", [], [Print([String("Hello World")])])]
    module = compiler.compile(stmts, is_entry_point=True)
    ir_str = str(module)
    assert "define i32" in ir_str
    assert '@"main"()' in ir_str
    assert "Hello World" in ir_str


def test_integration_loop(compiler):
    stmts = [
        FunctionDef("main", [], [Repeat(Number("5"), [Print([String("Looping")])])])
    ]
    module = compiler.compile(stmts, is_entry_point=True)
    ir_str = str(module)
    assert "define i32" in ir_str
    assert '@"main"()' in ir_str
