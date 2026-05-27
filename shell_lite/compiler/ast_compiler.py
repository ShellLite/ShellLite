import ast
from typing import List, Optional

from ..ast_nodes import *
from .base_visitor import BaseVisitor


class ASTCompiler(BaseVisitor):
    def __init__(self):
        self.tmp_counter = 0

    def get_tmp(self):
        self.tmp_counter += 1
        return f"__shl_tmp_{self.tmp_counter}"

    def compile(self, statements: List[Node], preamble: Optional[List[ast.stmt]] = None) -> str:
        if preamble is None:
            preamble = [
                ast.ImportFrom(module="__shl_runtime__", names=[ast.alias(name="*", asname=None)], level=1),
                ast.Assign(targets=[ast.Name(id="__SHL_MODULES", ctx=ast.Store())], value=ast.Dict(keys=[], values=[])),
            ]

        module_body = list(preamble)
        module_body.extend(self.visit_block(statements))
        
        module = ast.Module(body=module_body, type_ignores=[])
        ast.fix_missing_locations(module)
        return ast.unparse(module)

    def generic_visit(self, node: Node):
        raise NotImplementedError(f"ASTCompiler: No visitor for {type(node).__name__}")

    def visit_block(self, body: List[Node]) -> List[ast.stmt]:
        result = []
        for stmt in body:
            compiled = self.visit(stmt)
            if compiled:
                if isinstance(compiled, list):
                    result.extend(compiled)
                elif isinstance(compiled, ast.expr):
                    result.append(ast.Expr(value=compiled))
                else:
                    result.append(compiled)
        if not result:
            result.append(ast.Pass())
        return result

    def visit_Number(self, node: Number):
        return ast.Constant(value=node.value)

    def visit_String(self, node: String):
        return ast.Constant(value=node.value)

    def visit_Boolean(self, node: Boolean):
        return ast.Constant(value=node.value)

    def visit_VarAccess(self, node: VarAccess):
        if node.name == "null":
            return ast.Constant(value=None)
        if hasattr(node, "symbol_ref") and node.symbol_ref and getattr(node.symbol_ref, "is_property", False):
            return ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=node.name, ctx=ast.Load())
        return ast.Name(id=node.name, ctx=ast.Load())

    def visit_FileRead(self, node: FileRead):
        return ast.Call(func=ast.Name(id="std_io_read", ctx=ast.Load()), args=[self.visit(node.path)], keywords=[])

    def visit_FileWrite(self, node: FileWrite):
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="std_io_write", ctx=ast.Load()),
                args=[self.visit(node.path), self.visit(node.content)],
                keywords=[],
            )
        )

    def visit_FileExists(self, node: FileExists):
        return ast.Call(func=ast.Name(id="std_io_exists", ctx=ast.Load()), args=[self.visit(node.path)], keywords=[])

    def visit_Execute(self, node: Execute):
        return ast.Call(func=ast.Name(id="shl_execute", ctx=ast.Load()), args=[self.visit(node.command)], keywords=[])

    def visit_TypedAssign(self, node: TypedAssign):
        if hasattr(node, "symbol_ref") and node.symbol_ref and getattr(node.symbol_ref, "is_global", False):
            return ast.Assign(
                targets=[
                    ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=node.name, ctx=ast.Store())
                    if getattr(node.symbol_ref, "is_property", False)
                    else ast.Name(id=node.name, ctx=ast.Store())
                ],
                value=self.visit(node.value),
            )
        return ast.Assign(targets=[ast.Name(id=node.name, ctx=ast.Store())], value=self.visit(node.value))

    def visit_ConstAssign(self, node: ConstAssign):
        if hasattr(node, "symbol_ref") and node.symbol_ref and getattr(node.symbol_ref, "is_global", False):
            return ast.Assign(targets=[ast.Name(id=node.name, ctx=ast.Store())], value=self.visit(node.value))
        return ast.Assign(targets=[ast.Name(id=node.name, ctx=ast.Store())], value=self.visit(node.value))

    def visit_Assign(self, node: Assign):
        if hasattr(node, "symbol_ref") and node.symbol_ref and getattr(node.symbol_ref, "is_property", False):
            return ast.Assign(
                targets=[ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=node.name, ctx=ast.Store())],
                value=self.visit(node.value),
            )
        return ast.Assign(targets=[ast.Name(id=node.name, ctx=ast.Store())], value=self.visit(node.value))

    def visit_Print(self, node: Print):
        return ast.Expr(
            value=ast.Call(func=ast.Name(id="print", ctx=ast.Load()), args=[self.visit(node.expression)], keywords=[])
        )

    def visit_Assertion(self, node: Assertion):
        test = self.visit(node.left)
        if node.op != "truthy":
            op_map = {"==": ast.Eq(), "!=": ast.NotEq(), "<": ast.Lt(), ">": ast.Gt(), "<=": ast.LtE(), ">=": ast.GtE()}
            test = ast.Compare(left=test, ops=[op_map.get(node.op, ast.Eq())], comparators=[self.visit(node.right)])
        return ast.Assert(test=test, msg=ast.Constant(value="Assertion failed"))

    def visit_ListVal(self, node: ListVal):
        return ast.List(elts=[self.visit(e) for e in node.elements], ctx=ast.Load())

    def visit_Dictionary(self, node: Dictionary):
        return ast.Dict(keys=[self.visit(k) for k, v in node.pairs], values=[self.visit(v) for k, v in node.pairs])

    def visit_BinOp(self, node: BinOp):
        left, right = self.visit(node.left), self.visit(node.right)

        lt = getattr(node.left, "type_info", None)
        rt = getattr(node.right, "type_info", None)

        is_numeric = False
        if lt and rt:
            from .semantic_analyzer import TypeKind

            if lt.kind in (TypeKind.INT, TypeKind.FLOAT) and rt.kind in (TypeKind.INT, TypeKind.FLOAT):
                is_numeric = True

        if node.op == "+":
            if is_numeric:
                return ast.BinOp(left=left, op=ast.Add(), right=right)
            return ast.Call(func=ast.Name(id="mixed_concat", ctx=ast.Load()), args=[left, right], keywords=[])

        if node.op == ".":
            if isinstance(node.right, VarAccess):
                return ast.Attribute(value=left, attr=node.right.name, ctx=ast.Load())
            if isinstance(node.right, Call):
                attr = ast.Attribute(value=left, attr=node.right.name, ctx=ast.Load())
                keywords = [ast.keyword(arg=k, value=self.visit(v)) for k, v in (node.right.kwargs or [])]
                return ast.Call(func=attr, args=[self.visit(a) for a in node.right.args], keywords=keywords)
            raise Exception("Invalid dot access")

        op_map = {
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.Div(),
            "%": ast.Mod(),
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "<": ast.Lt(),
            ">": ast.Gt(),
            "<=": ast.LtE(),
            ">=": ast.GtE(),
        }
        if node.op in ("and", "or"):
            return ast.BoolOp(op=ast.And() if node.op == "and" else ast.Or(), values=[left, right])
        mapped = op_map.get(node.op, ast.Eq())
        return (
            ast.Compare(left=left, ops=[mapped], comparators=[right])
            if isinstance(mapped, ast.cmpop)
            else ast.BinOp(left=left, op=mapped, right=right)
        )

    def visit_UnaryOp(self, node: UnaryOp):
        right = self.visit(node.right)
        if node.op == "not":
            return ast.UnaryOp(op=ast.Not(), operand=right)
        if node.op == "-":
            return ast.UnaryOp(op=ast.USub(), operand=right)
        return right

    def visit_FunctionDef(self, node: FunctionDef):
        body = []
        global_vars = set()

        def find_globals(stmts):
            for s in stmts:
                if isinstance(s, (Assign, TypedAssign, ConstAssign, Instantiation)):
                    if hasattr(s, "symbol_ref") and s.symbol_ref and getattr(s.symbol_ref, "is_global", False):
                        name = s.name if not isinstance(s, Instantiation) else s.var_name
                        if name:
                            global_vars.add(name)
                elif hasattr(s, "body") and isinstance(s.body, list):
                    find_globals(s.body)
                elif hasattr(s, "else_body") and isinstance(s.else_body, list):
                    find_globals(s.else_body)

        find_globals(node.body)
        if global_vars:
            body.append(ast.Global(names=list(global_vars)))

        body.extend(self.visit_block(node.body))

        # Handle default arguments
        args = []
        defaults = []
        for arg_name, default_node, type_hint in node.args:
            args.append(ast.arg(arg=arg_name))
            if default_node is not None:
                defaults.append(self.visit(default_node))

        return ast.FunctionDef(
            name=node.name,
            args=ast.arguments(
                posonlyargs=[],
                args=args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=defaults,
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

    def visit_Call(self, node: Call):
        from .builtins import BUILTINS
        
        # Check registry for name mapping
        mapping = BUILTINS.get(node.name)
        py_func_name = mapping.py_name if mapping else node.name
        
        # Handle special cases that translate to operators/expressions
        if node.name == "xor" and len(node.args) == 2:
            return ast.BinOp(left=self.visit(node.args[0]), op=ast.BitXor(), right=self.visit(node.args[1]))
        if node.name == "empty" and len(node.args) == 1:
            return ast.Compare(
                left=ast.Call(func=ast.Name(id="len", ctx=ast.Load()), args=[self.visit(node.args[0])], keywords=[]),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=0)],
            )
        if node.name == "contains" and len(node.args) == 2:
            return ast.Compare(
                left=self.visit(node.args[1]), ops=[ast.In()], comparators=[self.visit(node.args[0])]
            )

        args = [self.visit(a) for a in node.args]
        keywords = [ast.keyword(arg=k, value=self.visit(v)) for k, v in (node.kwargs or [])]

        if node.body:
            body_func_name = self.get_tmp() + "_body"
            body_stmts = self.visit_block(node.body)
            body_def = ast.FunctionDef(
                name=body_func_name,
                args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
                body=body_stmts,
                decorator_list=[],
                returns=None,
            )
            keywords.append(ast.keyword(arg="body", value=ast.Name(id=body_func_name, ctx=ast.Load())))
            
            if "." in py_func_name:
                parts = py_func_name.split(".")
                func_obj = ast.Attribute(value=ast.Name(id=parts[0], ctx=ast.Load()), attr=parts[1], ctx=ast.Load())
            else:
                func_obj = ast.Name(id=py_func_name, ctx=ast.Load())

            return [
                body_def,
                ast.Expr(
                    value=ast.Call(
                        func=func_obj, args=args, keywords=keywords
                    )
                ),
            ]

        if "." in py_func_name:
            parts = py_func_name.split(".")
            # Special case for str.upper/str.lower - call on the object
            if parts[0] == "str" and len(args) == 1:
                return ast.Call(func=ast.Attribute(value=args[0], attr=parts[1], ctx=ast.Load()), args=[], keywords=[])
            func_obj = ast.Attribute(value=ast.Name(id=parts[0], ctx=ast.Load()), attr=parts[1], ctx=ast.Load())
        else:
            func_obj = ast.Name(id=py_func_name, ctx=ast.Load())

        return ast.Call(func=func_obj, args=args, keywords=keywords)

    def visit_If(self, node: If):
        return ast.If(
            test=self.visit(node.condition),
            body=self.visit_block(node.body),
            orelse=self.visit_block(node.else_body) if node.else_body else [],
        )

    def visit_Try(self, node: Try):
        return ast.Try(
            body=self.visit_block(node.try_body),
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()), name=node.catch_var, body=self.visit_block(node.catch_body)
                )
            ],
            orelse=[],
            finalbody=[],
        )

    def visit_TryAlways(self, node: TryAlways):
        return ast.Try(
            body=self.visit_block(node.try_body),
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()), name=node.catch_var, body=self.visit_block(node.catch_body)
                )
            ],
            orelse=[],
            finalbody=self.visit_block(node.always_body),
        )

    def visit_While(self, node: While):
        return ast.While(test=self.visit(node.condition), body=self.visit_block(node.body), orelse=[])

    def visit_Forever(self, node: Forever):
        return ast.While(test=ast.Constant(value=True), body=self.visit_block(node.body), orelse=[])

    def visit_Repeat(self, node: Repeat):
        limit = self.visit(node.count)
        return ast.For(
            target=ast.Name(id=self.get_tmp(), ctx=ast.Store()),
            iter=ast.Call(func=ast.Name(id="range", ctx=ast.Load()), args=[limit], keywords=[]),
            body=self.visit_block(node.body),
            orelse=[],
        )

    def visit_PythonImport(self, node: PythonImport):
        level = 1 if node.module_name.startswith(".") else 0
        mod_name = node.module_name.lstrip(".") if level > 0 else node.module_name
        return ast.ImportFrom(
            module=mod_name,
            names=[ast.alias(name="*", asname=None)] if node.alias is None else [ast.alias(name=mod_name, asname=node.alias)],
            level=level
        ) if node.alias is None and level > 0 else (
            ast.Import(names=[ast.alias(name=node.module_name, asname=node.alias)])
        )

    def visit_FromImport(self, node: FromImport):
        return ast.ImportFrom(
            module=node.module_name,
            names=[ast.alias(name=n, asname=a) for n, a in node.names],
            level=0
        )

    def visit_ForIn(self, node: ForIn):
        return ast.For(
            target=ast.Name(id=node.var_name, ctx=ast.Store()),
            iter=self.visit(node.iterable),
            body=self.visit_block(node.body),
            orelse=[],
        )

    def visit_Return(self, node: Return):
        return ast.Return(value=self.visit(node.value))

    def visit_Stop(self, node: Stop):
        return ast.Break()

    def visit_Skip(self, node: Skip):
        return ast.Continue()

    def visit_IndexAccess(self, node: IndexAccess):
        return ast.Subscript(value=self.visit(node.obj), slice=self.visit(node.index), ctx=ast.Load())

    def visit_IndexAssign(self, node: IndexAssign):
        return ast.Assign(
            targets=[ast.Subscript(value=self.visit(node.obj), slice=self.visit(node.index), ctx=ast.Store())],
            value=self.visit(node.value),
        )

    def visit_PropertyAssign(self, node: PropertyAssign):
        return ast.Assign(
            targets=[
                ast.Attribute(value=ast.Name(id=node.instance_name, ctx=ast.Load()), attr=node.property_name, ctx=ast.Store())
            ],
            value=self.visit(node.value),
        )

    def visit_ClassDef(self, node: ClassDef):
        init_args = [ast.arg(arg="self")]
        init_defaults = []
        init_body = []
        for prop_name, default_node in node.properties:
            init_args.append(ast.arg(arg=prop_name))
            init_defaults.append(self.visit(default_node) if default_node else ast.Constant(value=None))
            init_body.append(
                ast.Assign(
                    targets=[ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=prop_name, ctx=ast.Store())],
                    value=ast.Name(id=prop_name, ctx=ast.Load()),
                )
            )

        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(posonlyargs=[], args=init_args, kwonlyargs=[], kw_defaults=[], defaults=init_defaults),
            body=init_body or [ast.Pass()],
            decorator_list=[],
            returns=None,
        )

        body = [init_method]
        for m in node.methods:
            m_args = [ast.arg(arg="self")] + [ast.arg(arg=a[0]) for a in m.args]
            m_body = self.visit_block(m.body)
            body.append(
                ast.FunctionDef(
                    name=m.name,
                    args=ast.arguments(posonlyargs=[], args=m_args, kwonlyargs=[], kw_defaults=[], defaults=[]),
                    body=m_body,
                    decorator_list=[],
                    returns=None,
                )
            )
        return ast.ClassDef(
            name=node.name,
            bases=[ast.Name(id=node.parent or "ShellLiteObject", ctx=ast.Load())],
            keywords=[],
            body=body,
            decorator_list=[],
        )

    def visit_Instantiation(self, node: Instantiation):
        call = ast.Call(
            func=ast.Name(id=node.class_name, ctx=ast.Load()), args=[self.visit(a) for a in node.args], keywords=[]
        )
        return (
            ast.Assign(targets=[ast.Name(id=node.var_name, ctx=ast.Store())], value=call)
            if node.var_name
            else ast.Expr(value=call)
        )

    def visit_MethodCall(self, node: MethodCall):
        func = ast.Attribute(value=ast.Name(id=node.instance_name, ctx=ast.Load()), attr=node.method_name, ctx=ast.Load())
        return ast.Call(func=func, args=[self.visit(a) for a in node.args], keywords=[])
