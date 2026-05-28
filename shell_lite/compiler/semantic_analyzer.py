from enum import Enum, auto
from typing import Dict, List, Optional, Union

from ..ast_nodes import (
    Assign,
    BinOp,
    Boolean,
    Call,
    ClassDef,
    ConstAssign,
    Dictionary,
    ForIn,
    FunctionDef,
    If,
    IndexAccess,
    Instantiation,
    ListVal,
    Node,
    Number,
    PythonImport,
    Return,
    Skip,
    Stop,
    String,
    Try,
    TryAlways,
    TypedAssign,
    UnaryOp,
    VarAccess,
    While,
)
from .base_visitor import BaseTransformer
from .builtins import BUILTINS
from .symbol_table import Symbol, SymbolTable, SymbolType


class TypeKind(Enum):
    INT = auto()
    FLOAT = auto()
    STR = auto()
    BOOL = auto()
    LIST = auto()
    DICT = auto()
    OBJECT = auto()
    NONE = auto()
    UNKNOWN = auto()


class Type:
    def __init__(self, kind: TypeKind, class_name: Optional[str] = None):
        self.kind = kind
        self.class_name = class_name

    def __repr__(self):
        return f"{self.kind.name}" + (f"({self.class_name})" if self.class_name else "")


class CompileError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"{message} (Line {line})" if line > 0 else message)
        self.line = line


class SemanticAnalyzer(BaseTransformer):
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

        for name, mapping in BUILTINS.items():
            self.global_scope.define(
                name,
                Symbol(
                    name,
                    SymbolType.FUNCTION,
                    self.T_UNKNOWN,
                    {"min_args": mapping.min_args, "max_args": mapping.max_args},
                ),
            )

        self.global_scope.define("null", Symbol("null", SymbolType.VARIABLE, self.T_NONE))
        self.global_scope.define("request", Symbol("request", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("document", Symbol("document", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("window", Symbol("window", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define("JSON", Symbol("JSON", SymbolType.VARIABLE, self.T_UNKNOWN))
        self.global_scope.define(
            "fetch", Symbol("fetch", SymbolType.FUNCTION, self.T_UNKNOWN, {"min_args": 0, "max_args": None})
        )

    def analyze(self, ast_or_map: Union[List[Node], Dict[str, List[Node]]]):
        if isinstance(ast_or_map, dict):
            all_stmts = []
            for m_ast in ast_or_map.values():
                all_stmts.extend(m_ast)
            ast = all_stmts
        else:
            ast = ast_or_map

        for stmt in ast:
            if isinstance(stmt, FunctionDef):
                min_args = len([a for a in stmt.args if a[1] is None])
                max_args = len(stmt.args)
                self.global_scope.define(
                    stmt.name,
                    Symbol(
                        stmt.name,
                        SymbolType.FUNCTION,
                        self.T_UNKNOWN,
                        {"min_args": min_args, "max_args": max_args},
                        is_global=True,
                    ),
                )
            elif isinstance(stmt, ClassDef):
                self.classes[stmt.name] = stmt
                min_args = len([p for p in stmt.properties if p[1] is None])
                max_args = len(stmt.properties)
                self.global_scope.define(
                    stmt.name,
                    Symbol(
                        stmt.name,
                        SymbolType.CLASS,
                        Type(TypeKind.OBJECT, stmt.name),
                        {"min_args": min_args, "max_args": max_args},
                        is_global=True,
                    ),
                )

        for stmt in ast:
            self.visit(stmt)

    def generic_visit(self, node: Node) -> Type:
        super().generic_visit(node)
        return self.T_NONE

    def visit(self, node: Optional[Node]) -> Type:
        if node is None:
            return self.T_NONE
        res = super().visit(node)
        if node:
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

    def visit_Try(self, node: Try | TryAlways) -> Type:
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
        for stmt in node.try_body:
            self.visit(stmt)
        prev = self.current_scope
        self.current_scope = SymbolTable(parent=prev)
        self.current_scope.define(node.catch_var, Symbol(node.catch_var, SymbolType.VARIABLE, self.T_UNKNOWN))
        for stmt in node.catch_body:
            self.visit(stmt)
        self.current_scope = prev
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

    def visit_PythonImport(self, node: PythonImport) -> Type:
        name = node.alias if node.alias else node.module_name
        self.global_scope.define(name, Symbol(name, SymbolType.VARIABLE, self.T_UNKNOWN))
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

        min_args = sym.metadata.get("min_args")
        max_args = sym.metadata.get("max_args")
        if min_args is not None:
            if len(node.args) < min_args:
                raise CompileError(
                    f"'{node.class_name}' expects at least {min_args} args, got {len(node.args)}", node.line
                )
            if max_args is not None and len(node.args) > max_args:
                raise CompileError(
                    f"'{node.class_name}' expects at most {max_args} args, got {len(node.args)}", node.line
                )

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
                        if not any(p[0] == m_name for p in cls.properties) and not any(
                            m.name == m_name for m in cls.methods
                        ):
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

    def visit_Assign(self, node: Assign) -> Type:
        vt = self.visit(node.value)
        existing = self.current_scope.resolve(node.name)
        if existing and (existing.is_global or existing.is_property) and self.current_scope != self.global_scope:
            node.symbol_ref = existing
            return vt

        is_glob = self.current_scope == self.global_scope
        sym = Symbol(node.name, SymbolType.VARIABLE, vt, is_global=is_glob)
        self.current_scope.define(node.name, sym)
        node.symbol_ref = sym
        return vt

    def visit_TypedAssign(self, node: TypedAssign) -> Type:
        vt = self.visit(node.value)
        existing = self.current_scope.resolve(node.name)
        if existing and (existing.is_global or existing.is_property) and self.current_scope != self.global_scope:
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
        if existing and existing.is_global and self.current_scope != self.global_scope:
            node.symbol_ref = existing
            return vt

        is_glob = self.current_scope == self.global_scope
        sym = Symbol(node.name, SymbolType.VARIABLE, vt, is_global=is_glob)
        self.current_scope.define(node.name, sym)
        node.symbol_ref = sym
        return vt

    def visit_If(self, node: If) -> Type:
        self.visit(node.condition)
        for stmt in node.body:
            self.visit(stmt)
        if node.else_body:
            for stmt in node.else_body:
                self.visit(stmt)
        return self.T_NONE

    def visit_Call(self, node: Call) -> Type:
        sym = self.current_scope.resolve(node.name)
        if not sym:
            for name in self.global_scope.symbols:
                if name.endswith("_" + node.name):
                    sym = self.global_scope.symbols[name]
                    break

        if not sym:
            raise CompileError(f"Undeclared function '{node.name}'", node.line)

        min_args = sym.metadata.get("min_args")
        max_args = sym.metadata.get("max_args")

        if min_args is not None and sym.symbol_type != SymbolType.CLASS:
            if len(node.args) < min_args:
                raise CompileError(f"'{node.name}' expects at least {min_args} args, got {len(node.args)}", node.line)
            if max_args is not None and len(node.args) > max_args:
                raise CompileError(f"'{node.name}' expects at most {max_args} args, got {len(node.args)}", node.line)

        for a in node.args:
            self.visit(a)
        node.symbol_ref = sym
        return sym.type_info
