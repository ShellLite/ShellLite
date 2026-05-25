from shell_lite.interpreter import Interpreter
from shell_lite.parser import Parser


def run_code(code: str):
    interpreter = Interpreter()
    nodes = Parser(code).parse()
    interpreter.visit_block(nodes)


def test_imported_class_instantiation(tmp_path, capsys):
    person_shl = tmp_path / "person.shl"
    person_shl.write_text(
        """
class Person {
    fn init(name) {
        self.name = name
    }
}
""",
        encoding="utf-8",
    )

    code = f"""
import "{person_shl.as_posix()}"
p = Person("John")
say p.name
"""
    run_code(code)
    captured = capsys.readouterr()
    assert captured.out.strip() == "John"


def test_imported_class_method_call(tmp_path, capsys):
    math_shl = tmp_path / "math_class.shl"
    math_shl.write_text(
        """
class Math {
    fn add(a, b) {
        return a + b
    }
}
""",
        encoding="utf-8",
    )

    code = f"""
import "{math_shl.as_posix()}"
m = Math()
say m.add(2, 3)
"""
    run_code(code)
    captured = capsys.readouterr()
    assert captured.out.strip() == "5"


def test_import_as_class_instantiation(tmp_path, capsys):
    module_shl = tmp_path / "module.shl"
    module_shl.write_text(
        """
class C {
    fn get() {
        return "it works"
    }
}
""",
        encoding="utf-8",
    )

    code = f"""
import "{module_shl.as_posix()}" as m
obj = m.C()
say obj.get()
"""
    run_code(code)
    captured = capsys.readouterr()
    assert captured.out.strip() == "it works"


def test_import_as_function_call(tmp_path, capsys):
    module_shl = tmp_path / "utils.shl"
    module_shl.write_text(
        """
fn greet(name) {
    return "Hello, " + name
}
""",
        encoding="utf-8",
    )

    code = f"""
import "{module_shl.as_posix()}" as u
say u.greet("World")
"""
    run_code(code)
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, World"
