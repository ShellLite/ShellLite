from enum import Enum, auto
from typing import Dict, List, Optional

from ..ast_nodes import *
from .base_visitor import BaseVisitor
from .symbol_table import Symbol, SymbolTable, SymbolType


class TypeKind(Enum):
    INT = auto()
    STR = auto()
    BOOL = auto()
    FLOAT = auto()
    OBJECT = auto()
    LIST = auto()
    DICT = auto()
    NONE = auto()
    UNKNOWN = auto()


class Type:
    def __init__(self, kind: TypeKind, class_name: Optional[str] = None, element_type: Optional["Type"] = None):
        self.kind = kind
        self.class_name = class_name
        self.element_type = element_type

    def __eq__(self, other):
        if not isinstance(other, Type):
            return False
        return self.kind == other.kind and self.class_name == other.class_name and self.element_type == other.element_type

    def __repr__(self):
        res = f"{self.kind.name}"
        if self.class_name:
            res += f"({self.class_name})"
        if self.element_type:
            res += f"[{self.element_type}]"
        return res


class CompileError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"{message} (Line {line})" if line > 0 else message)
        self.line = line


class SemanticAnalyzer(BaseVisitor):
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.classes: Dict[str, ClassDef] = {}
        self.context_stack: List[str] = ["GLOBAL"]

        self.T_INT = Type(TypeKind.INT)
        self.T_STR = Type(TypeKind.STR)
        self.T_BOOL = Type(TypeKind.BOOL)
        self.T_FLOAT = Type(TypeKind.FLOAT)
        self.T_NONE = Type(TypeKind.NONE)
        self.T_UNKNOWN = Type(TypeKind.UNKNOWN)

        builtins = {
            "print": -1,
            "say": -1,
            "ask": 1,
            "len": 1,
            "str": 1,
            "int": 1,
            "float": 1,
            "bool": 1,
            "abs": 1,
            "typeof": 1,
            "range": -1,
            "max": -1,
            "min": -1,
            "add": 2,
            "remove": 2,
            "xor": 2,
            "empty": 1,
            "contains": 2,
            "split": -1,
            "upper": 1,
            "lower": 1,
            "sort": 1,
            "count": -1,
            "ord": 1,
            "char": 1,
            "json_parse": 1,
            "json_stringify": -1,
            "pop": -1,
            "clear_dict": 1,
            "add": 2,
            "remove": 2,
            "shl_execute": 1,
            "shl_parallel": 1,
            "std_io_read": 1,
            "std_io_write": 2,
            "std_io_append": 2,
            "std_io_exists": 1,
            "std_io_delete": 1,
            "std_io_copy": 2,
            "std_io_rename": 2,
            "std_io_mkdir": 1,
            "std_io_listdir": 1,
            "std_net_get": 1,
            "std_net_post": 2,
            "std_web_on_request": -1,
            "std_web_listen": 1,
            "std_web_serve_static": 2,
            "std_db_query": -1,
            "std_db_open": 1,
            "std_db_close": 0,
            "std_db_exec": -1,
            "std_db_query_rows": -1,
            "std_db_model": 2,
            "std_db_create_table": 1,
            "std_db_insert": 2,
            "std_db_find": -1,
            "std_db_update": 3,
            "std_db_delete": 2,
            "automation_click": 2,
            "automation_type": 1,
            "automation_press": 1,
            "automation_notify": 2,
            "clipboard_copy": 1,
            "clipboard_paste": 0,
            "html": -1,
            "head": -1,
            "body": -1,
            "div": -1,
            "span": -1,
            "a": -1,
            "img": -1,
            "ul": -1,
            "ol": -1,
            "li": -1,
            "button": -1,
            "input": -1,
            "form": -1,
            "table": -1,
            "tr": -1,
            "td": -1,
            "h1": -1,
            "h2": -1,
            "h3": -1,
            "h4": -1,
            "h5": -1,
            "h6": -1,
            "link": -1,
            "meta": -1,
            "script": -1,
            "footer": -1,
            "header": -1,
            "nav": -1,
            "textarea": -1,
            "label": -1,
            "section": -1,
            "article": -1,
            "main": -1,
            "aside": -1,
            "p": -1,
            "strong": -1,
            "br": -1,
            "hr": -1,
            "title": -1,
            "style": -1,
            "blockquote": -1,
            "pre": -1,
            "code": -1,
            "redirect": 1,
            "render": 1,
        }
        for name, count in builtins.items():
            self.global_scope.define(name, Symbol(name, SymbolType.FUNCTION, self.T_UNKNOWN, {"arg_count": count}))

        self.global_scope.define("null", Symbol("null", SymbolType.VARIABLE, self.T_NONE))
        self.global_scope.define("request", Symbol("request", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("document", Symbol("document", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("window", Symbol("window", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("JSON", Symbol("JSON", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("fetch", Symbol("fetch", SymbolType.FUNCTION, self.T_UNKNOWN, {"arg_count": -1}))

    def analyze(self, ast: List[Node]):
        for stmt in ast:
            if isinstance(stmt, FunctionDef):
                self.global_scope.define(
                    stmt.name,
                    Symbol(stmt.name, SymbolType.FUNCTION, self.T_UNKNOWN, {"arg_count": len(stmt.args)}, is_global=True),
                )
            elif isinstance(stmt, ClassDef):
                self.classes[stmt.name] = stmt
                self.global_scope.define(
                    stmt.name,
                    Symbol(
                        stmt.name,
                        SymbolType.CLASS,
                        Type(TypeKind.OBJECT, stmt.name),
                        {"arg_count": len(stmt.properties)},
                        is_global=True,
                    ),
                )

        for stmt in ast:
            self.visit(stmt)

    def generic_visit(self, node: Node) -> Type:
        super().generic_visit(node)
        return self.T_NONE

    def visit(self, node: Node) -> Type:
        if node is None:
            return self.T_NONE
        res = super().visit(node)
        node.type_info = res
        return res

    def visit_Number(self, node: Number) -> Type:
        return self.T_FLOAT if isinstance(node.value, float) else self.T_INT

    def visit_String(self, node: String) -> Type:
        return self.T_STR

    def visit_Boolean(self, node: Boolean) -> Type:
        return self.T_BOOL

    def visit_VarAccess(self, node: VarAccess) -> Type:
        sym = self.current_scope.resolve(node.name)
        if not sym:
            for name in self.global_scope.symbols:
                if name.endswith("_" + node.name):
                    sym = self.global_scope.symbols[name]
                    break
        if not sym:
            raise CompileError(f"Undeclared variable '{node.name}'", node.line)
        node.symbol_ref = sym
        return sym.type_info

    def visit_IndexAccess(self, node: IndexAccess) -> Type:
        self.visit(node.obj)
        self.visit(node.index)
        return self.T_UNKNOWN

    def visit_ListVal(self, node: ListVal) -> Type:
        for e in node.elements:
            self.visit(e)
        return Type(TypeKind.LIST)

    def visit_Dictionary(self, node: Dictionary) -> Type:
        for k, v in node.pairs:
            self.visit(k)
            self.visit(v)
        return Type(TypeKind.DICT)

    def visit_UnaryOp(self, node: UnaryOp) -> Type:
        return self.visit(node.right)

    def visit_Try(self, node: Try) -> Type:
        for stmt in node.try_body:
            self.visit(stmt)
        prev = self.current_scope
        self.current_scope = SymbolTable(parent=prev)
        self.current_scope.define(node.catch_var, Symbol(node.catch_var, SymbolType.VARIABLE, self.T_UNKNOWN))
        for stmt in node.catch_body:
            self.visit(stmt)
        self.current_scope = prev
        return self.T_NONE

    def visit_TryAlways(self, node: TryAlways) -> Type:
        self.visit_Try(node)
        for stmt in node.always_body:
            self.visit(stmt)
        return self.T_NONE

    def visit_FunctionDef(self, node: FunctionDef) -> Type:
        self.context_stack.append("FUNCTION")
        prev = self.current_scope
        self.current_scope = SymbolTable(parent=prev)
        for arg_name, _, _ in node.args:
            self.current_scope.define(arg_name, Symbol(arg_name, SymbolType.VARIABLE, self.T_UNKNOWN))
        for stmt in node.body:
            self.visit(stmt)
        self.current_scope = prev
        self.context_stack.pop()
        return self.T_NONE

    def visit_Return(self, node: Return) -> Type:
        if "FUNCTION" not in self.context_stack:
            raise CompileError("'Return' used outside of a function", node.line)
        return self.visit(node.value)

    def visit_While(self, node: While) -> Type:
        self.visit(node.condition)
        self.context_stack.append("LOOP")
        for stmt in node.body:
            self.visit(stmt)
        self.context_stack.pop()
        return self.T_NONE

    def visit_ForIn(self, node: ForIn) -> Type:
        self.visit(node.iterable)
        self.context_stack.append("LOOP")
        prev = self.current_scope
        self.current_scope = SymbolTable(parent=prev)
        self.current_scope.define(node.var_name, Symbol(node.var_name, SymbolType.VARIABLE, self.T_UNKNOWN))
        for stmt in node.body:
            self.visit(stmt)
        self.current_scope = prev
        self.context_stack.pop()
        return self.T_NONE

    def visit_Stop(self, node: Stop) -> Type:
        if "LOOP" not in self.context_stack:
            raise CompileError("'Stop' used outside of a loop", node.line)
        return self.T_NONE

    def visit_Skip(self, node: Skip) -> Type:
        if "LOOP" not in self.context_stack:
            raise CompileError("'Skip' used outside of a loop", node.line)
        return self.T_NONE

    def visit_ClassDef(self, node: ClassDef) -> Type:
        prev = self.current_scope
        self.current_scope = SymbolTable(parent=prev)
        self.current_scope.define("self", Symbol("self", SymbolType.VARIABLE, Type(TypeKind.OBJECT, node.name)))
        for prop, _ in node.properties:
            self.current_scope.define(prop, Symbol(prop, SymbolType.VARIABLE, self.T_UNKNOWN, is_property=True))
        for method in node.methods:
            self.visit(method)
        self.current_scope = prev
        return self.T_NONE

    def visit_Instantiation(self, node: Instantiation) -> Type:
        sym = self.current_scope.resolve(node.class_name)
        if not sym:
            for name in self.global_scope.symbols:
                if name.endswith("_" + node.class_name):
                    sym = self.global_scope.symbols[name]
                    break
        if not sym:
            raise CompileError(f"Undeclared class '{node.class_name}'", node.line)
        for a in node.args:
            self.visit(a)

        target_type = Type(TypeKind.OBJECT, node.class_name)
        if node.var_name:
            existing = self.current_scope.resolve(node.var_name)
            if existing and existing.is_global:
                node.symbol_ref = existing
            else:
                is_glob = self.current_scope == self.global_scope
                sym_inst = Symbol(node.var_name, SymbolType.VARIABLE, target_type, is_global=is_glob)
                self.current_scope.define(node.var_name, sym_inst)
                node.symbol_ref = sym_inst
        return target_type

    def visit_BinOp(self, node: BinOp) -> Type:
        lt = self.visit(node.left)
        if node.op == ".":
            if lt.kind not in (TypeKind.OBJECT, TypeKind.UNKNOWN):
                raise CompileError("Cannot access member on non-object type", node.line)
            if lt.kind == TypeKind.OBJECT and lt.class_name:
                cls = self.classes.get(lt.class_name)
                if cls:
                    m_name = node.right.name if isinstance(node.right, (VarAccess, Call)) else None
                    if m_name:
                        if not any(p[0] == m_name for p in cls.properties) and not any(m.name == m_name for m in cls.methods):
                            raise CompileError(f"Type '{lt.class_name}' has no member '{m_name}'", node.line)
            return self.T_UNKNOWN

        rt = self.visit(node.right)
        if node.op in ("+", "-", "*", "/"):
            if lt.kind not in (TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN) or rt.kind not in (
                TypeKind.INT,
                TypeKind.FLOAT,
                TypeKind.UNKNOWN,
            ):
                if node.op == "+" and (lt.kind == TypeKind.STR or rt.kind == TypeKind.STR):
                    return self.T_STR
                raise CompileError(f"Invalid types for operator '{node.op}'", node.line)
        return self.T_UNKNOWN

    def visit_Call(self, node: Call) -> Type:
        sym = self.current_scope.resolve(node.name)
        if not sym:
            for name in self.global_scope.symbols:
                if name.endswith("_" + node.name):
                    sym = self.global_scope.symbols[name]
                    break

        if not sym:
            raise CompileError(f"Undeclared function '{node.name}'", node.line)
        arg_count = sym.metadata.get("arg_count")
        if arg_count is not None and arg_count != -1 and sym.symbol_type != SymbolType.CLASS:
            if len(node.args) != arg_count:
                raise CompileError(f"'{node.name}' expects {arg_count} args, got {len(node.args)}", node.line)
        for a in node.args:
            self.visit(a)
        node.symbol_ref = sym
        return sym.type_info

    def visit_PythonImport(self, node: PythonImport) -> Type:
        name = node.alias or node.module_name
        self.current_scope.define(name, Symbol(name, SymbolType.VARIABLE, self.T_UNKNOWN))
        return self.T_NONE

    def visit_TypedAssign(self, node: TypedAssign) -> Type:
        vt = self.visit(node.value)
        existing = self.current_scope.resolve(node.name)
        if existing and existing.is_global:
            node.symbol_ref = existing
            return vt
        is_glob = self.current_scope == self.global_scope
        sym = Symbol(node.name, SymbolType.VARIABLE, vt, is_global=is_glob)
        self.current_scope.define(node.name, sym)
        node.symbol_ref = sym
        return vt

    def visit_ConstAssign(self, node: ConstAssign) -> Type:
        vt = self.visit(node.value)
        existing = self.current_scope.resolve(node.name)
        if existing and existing.is_global:
            node.symbol_ref = existing
            return vt
        is_glob = self.current_scope == self.global_scope
        sym = Symbol(node.name, SymbolType.CONSTANT, vt, is_global=is_glob)
        self.current_scope.define(node.name, sym)
        node.symbol_ref = sym
        return vt

    def visit_Assign(self, node: Assign) -> Type:
        vt = self.visit(node.value)

        existing = self.current_scope.resolve(node.name)
        if existing and (existing.is_global or existing.is_property):
            node.symbol_ref = existing
            return vt

        is_glob = self.current_scope == self.global_scope
        sym = Symbol(node.name, SymbolType.VARIABLE, vt, is_global=is_glob)
        self.current_scope.define(node.name, sym)
        node.symbol_ref = sym
        return vt
