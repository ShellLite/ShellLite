import hashlib
import os
from typing import Dict, List, Set

from ..ast_nodes import *
from ..lexer import Lexer
from ..parser import Parser
from .base_visitor import BaseTransformer


class CompileError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"{message} (Line {line})" if line > 0 else message)
        self.line = line


class StaticLinker(BaseTransformer):
    def __init__(self, search_paths: List[str]):
        self.search_paths = search_paths
        self.modules: Dict[str, str] = {}
        self.module_symbols: Dict[str, Set[str]] = {}
        self.import_stack: List[str] = []
        self.current_rename_map: Dict[str, str] = {}
        self.current_aliases: Dict[str, str] = {}

    def _get_mod_id(self, abs_path: str) -> str:
        norm = os.path.normcase(os.path.normpath(abs_path))
        digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]
        return f"m_{digest}"

    def resolve_path(self, path: str) -> str:
        if not path.endswith(".shl"):
            path += ".shl"
        for p in self.search_paths:
            fp = os.path.join(p, path)
            if os.path.exists(fp):
                return fp
        raise CompileError(f"Linker Error: Cannot find module '{path}'")

    def link(self, statements: List[Node], current_file: str) -> List[Node]:
        abs_p = os.path.abspath(current_file) if current_file else ""
        mod_id = self._get_mod_id(abs_p) if abs_p else "main"

        if abs_p:
            if abs_p in self.import_stack:
                raise CompileError(f"Circular Dependency: {' -> '.join(self.import_stack + [abs_p])}")
            self.import_stack.append(abs_p)

        local_rename_map: Dict[str, str] = {}
        for stmt in statements:
            if isinstance(stmt, (FunctionDef, ClassDef, ModelDef, Assign, TypedAssign, ConstAssign)):
                old_name = stmt.name
                new_name = f"{mod_id}_{old_name}" if mod_id != "main" else old_name
                local_rename_map[old_name] = new_name

        self.module_symbols[mod_id] = set(local_rename_map.keys())

        linked_ast: List[Node] = []

        for stmt in statements:
            if isinstance(stmt, (Import, ImportAs)):
                path = stmt.path
                alias = stmt.alias if isinstance(stmt, ImportAs) else None
                fp = self.resolve_path(path)
                abs_mod = os.path.abspath(fp)

                if abs_mod not in self.modules:
                    new_mod_id = self._get_mod_id(abs_mod)
                    self.modules[abs_mod] = new_mod_id
                    with open(abs_mod, "r", encoding="utf-8") as f:
                        src = f.read()
                    nodes = Parser(Lexer(src).tokenize()).parse()

                    old_rename, old_aliases = self.current_rename_map, self.current_aliases
                    self.current_rename_map, self.current_aliases = {}, {}
                    mod_nodes = self.link(nodes, abs_mod)
                    self.current_rename_map, self.current_aliases = old_rename, old_aliases

                    linked_ast.extend(mod_nodes)

                target_mod_id = self.modules[abs_mod]
                if alias:
                    self.current_aliases[alias] = target_mod_id
                else:
                    for name in self.module_symbols.get(target_mod_id, set()):
                        local_rename_map[name] = f"{target_mod_id}_{name}"
            else:
                old_rename = self.current_rename_map
                self.current_rename_map = {**old_rename, **local_rename_map}
                linked_ast.append(self.visit(stmt))
                self.current_rename_map = old_rename

        if abs_p:
            self.import_stack.pop()
        return linked_ast

    def visit_FunctionDef(self, node: FunctionDef) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_body = [self.visit(s) for s in node.body]
        from dataclasses import replace

        return replace(node, name=new_name, body=new_body)

    def visit_ClassDef(self, node: ClassDef) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_props = [(p[0], self.visit(p[1]) if p[1] else None) for p in node.properties]
        new_methods = [self.visit(m) for m in node.methods]
        from dataclasses import replace

        return replace(node, name=new_name, properties=new_props, methods=new_methods)

    def visit_ModelDef(self, node: ModelDef) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        from dataclasses import replace

        return replace(node, name=new_name)

    def visit_Assign(self, node: Assign) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_val = self.visit(node.value)
        from dataclasses import replace

        return replace(node, name=new_name, value=new_val)

    def visit_TypedAssign(self, node: TypedAssign) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_val = self.visit(node.value)
        from dataclasses import replace

        return replace(node, name=new_name, value=new_val)

    def visit_ConstAssign(self, node: ConstAssign) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_val = self.visit(node.value)
        from dataclasses import replace

        return replace(node, name=new_name, value=new_val)

    def visit_VarAccess(self, node: VarAccess) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        from dataclasses import replace

        return replace(node, name=new_name)

    def visit_Call(self, node: Call) -> Node:
        new_name = self.current_rename_map.get(node.name, node.name)
        new_args = [self.visit(a) for a in node.args]
        from dataclasses import replace

        return replace(node, name=new_name, args=new_args)

    def visit_Instantiation(self, node: Instantiation) -> Node:
        new_class_name = self.current_rename_map.get(node.class_name, node.class_name)
        new_var_name = self.current_rename_map.get(node.var_name, node.var_name) if node.var_name else None
        new_args = [self.visit(a) for a in node.args]
        from dataclasses import replace

        return replace(node, class_name=new_class_name, var_name=new_var_name, args=new_args)

    def visit_BinOp(self, node: BinOp) -> Node:
        if node.op == ".":
            if isinstance(node.left, VarAccess) and node.left.name in self.current_aliases:
                target_mod_id = self.current_aliases[node.left.name]
                member_name = None
                if isinstance(node.right, VarAccess):
                    member_name = node.right.name
                elif isinstance(node.right, Call):
                    member_name = node.right.name

                if member_name and member_name in self.module_symbols.get(target_mod_id, set()):
                    renamed_member = f"{target_mod_id}_{member_name}"
                    if isinstance(node.right, VarAccess):
                        return VarAccess(name=renamed_member)
                    else:
                        from dataclasses import replace

                        return replace(node.right, name=renamed_member)
        return super().generic_visit(node)
