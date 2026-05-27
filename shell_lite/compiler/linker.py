import os
from typing import Dict, List, Optional

from ..ast_nodes import Import, ImportAs, Node, PythonImport
from ..lexer import Lexer
from ..parser import Parser


class CompileError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"{message} (Line {line})" if line > 0 else message)
        self.line = line


class StaticLinker:
    def __init__(self, search_paths: List[str]):
        self.search_paths = search_paths
        self.module_asts: Dict[str, List[Node]] = {}
        self.import_stack: List[str] = []

    def resolve_path(self, path: str, base_dir: Optional[str] = None) -> Optional[str]:
        if not path.endswith(".shl"):
            path += ".shl"

        if base_dir:
            fp = os.path.join(base_dir, path)
            if os.path.exists(fp):
                return os.path.abspath(fp)

        for p in self.search_paths:
            fp = os.path.join(p, path)
            if os.path.exists(fp):
                return os.path.abspath(fp)
        return None

    def link(self, statements: List[Node], current_file: str) -> Dict[str, List[Node]]:
        abs_p = os.path.abspath(current_file)

        if abs_p in self.module_asts:
            return self.module_asts

        if abs_p in self.import_stack:
            raise CompileError(f"Circular Dependency: {' -> '.join(self.import_stack + [abs_p])}")

        self.import_stack.append(abs_p)

        current_module_ast: List[Node] = []

        for stmt in statements:
            if isinstance(stmt, (Import, ImportAs)):
                path = stmt.path
                alias = stmt.alias if isinstance(stmt, ImportAs) else None
                fp = self.resolve_path(path, base_dir=os.path.dirname(abs_p))

                if not fp:
                    current_module_ast.append(PythonImport(path, alias))
                    continue

                mod_name = os.path.splitext(os.path.basename(fp))[0]
                current_module_ast.append(PythonImport(f".{mod_name}", alias))

                if fp not in self.module_asts:
                    with open(fp, "r", encoding="utf-8") as f:
                        src = f.read()
                    nodes = Parser(Lexer(src).tokenize()).parse()
                    self.link(nodes, fp)
            else:
                current_module_ast.append(stmt)

        self.module_asts[abs_p] = current_module_ast
        self.import_stack.pop()
        return self.module_asts
