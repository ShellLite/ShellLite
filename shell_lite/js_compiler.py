import random
from typing import List
from .ast_nodes import *
class JSCompiler:
    def __init__(self):
        self.indentation = 0
    def indent(self):
        return "    " * self.indentation
    def visit(self, node: Node) -> str:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    def generic_visit(self, node: Node):
        raise Exception(f"JSCompiler does not support {type(node).__name__}")
    def compile_block(self, statements: List[Node]) -> str:
        if not statements:
            return ""
        code = ""
        for stmt in statements:
            stmt_code = self.visit(stmt)
            if not stmt_code: continue
            indented_stmt = "\n".join([f"{self.indent()}{line}" for line in stmt_code.split('\n')])
            code += indented_stmt + "\n"
        return code.rstrip()
    def compile(self, statements: List[Node]) -> str:
        code = [
            "// ShellLite Runtime (JS)",
            "const fs = require('fs');",
            "const path = require('path');",
            "const https = require('https');",
            "const { execSync } = require('child_process');",
            "",
            "// Builtins",
            "const say = console.log;",
            "const print = console.log;",
            "const range = (n) => [...Array(n).keys()];",
            "const int = (x) => parseInt(x);",
            "const str = (x) => String(x);",
            "const float = (x) => parseFloat(x);",
            "const len = (x) => x.length;",
            "",
            "// Utils",
            "const _slang_download = (url) => { console.log('Download not impl in minimal JS runtime'); };",
            "",
            "// --- User Code ---",
            ""
        ]
        code.append(self.compile_block(statements))
        return "\n".join(code)
    def visit_Number(self, node: Number):
        return str(node.value)
    def visit_String(self, node: String):
        return repr(node.value) 
    def visit_Boolean(self, node: Boolean):
        return "true" if node.value else "false"
    def visit_Regex(self, node: Regex):
        return f"/{node.pattern}/"
    def visit_ListVal(self, node: ListVal):
        elements = [self.visit(e) for e in node.elements]
        return f"[{', '.join(elements)}]"
    def visit_Dictionary(self, node: Dictionary):
        pairs = [f"{self.visit(k)}: {self.visit(v)}" for k, v in node.pairs]
        return f"{{{', '.join(pairs)}}}"
    def visit_SetVal(self, node: SetVal):
        elements = [self.visit(e) for e in node.elements]
        return f"new Set([{', '.join(elements)}])"
    def visit_VarAccess(self, node: VarAccess):
        return node.name
    def visit_Assign(self, node: Assign):
        return f"var {node.name} = {self.visit(node.value)};"
    def visit_ConstAssign(self, node: ConstAssign):
        return f"const {node.name} = {self.visit(node.value)};"
    def visit_PropertyAssign(self, node: PropertyAssign):
        return f"{node.instance_name}.{node.property_name} = {self.visit(node.value)};"
    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        js_ops = {
            'matches': None, 
            'and': '&&',
            'or': '||',
            '==': '==='
        }
        if op == 'matches':
            return f"new RegExp({right}).test({left})"
        real_op = js_ops.get(op, op)
        return f"({left} {real_op} {right})"
    def visit_UnaryOp(self, node: UnaryOp):
        return f"({node.op} {self.visit(node.right)})"
    def visit_Print(self, node: Print):
        return f"console.log({self.visit(node.expression)});"
    def visit_Input(self, node: Input):
        return f"require('readline-sync').question({repr(node.prompt) if node.prompt else '\"\"'})"
    def visit_If(self, node: If):
        code = f"if ({self.visit(node.condition)}) {{\n"
        self.indentation += 1
        code += self.compile_block(node.body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        if node.else_body:
            code += f" else {{\n"
            self.indentation += 1
            code += self.compile_block(node.else_body)
            self.indentation -= 1
            code += f"\n{self.indent()}}}"
        return code
    def visit_While(self, node: While):
        code = f"while ({self.visit(node.condition)}) {{\n"
        self.indentation += 1
        code += self.compile_block(node.body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_For(self, node: For):
        count = self.visit(node.count)
        var = f"_i_{random.randint(0,1000)}"
        code = f"for (let {var} = 0; {var} < {count}; {var}++) {{\n"
        self.indentation += 1
        code += self.compile_block(node.body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_ForIn(self, node: ForIn):
        code = f"for (let {node.var_name} of {self.visit(node.iterable)}) {{\n"
        self.indentation += 1
        code += self.compile_block(node.body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_Repeat(self, node: Repeat):
        return self.visit_For(For(node.count, node.body))
    def visit_FunctionDef(self, node: FunctionDef):
        args = [arg[0] for arg in node.args] 
        code = f"function {node.name}({', '.join(args)}) {{\n"
        self.indentation += 1
        code += self.compile_block(node.body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_Return(self, node: Return):
        return f"return {self.visit(node.value)};"
    def visit_Call(self, node: Call):
        args = [self.visit(a) for a in node.args]
        return f"{node.name}({', '.join(args)})"
    def visit_ClassDef(self, node: ClassDef):
        parent = node.parent if node.parent else ""
        extends = f" extends {parent}" if parent else ""
        code = f"class {node.name}{extends} {{\n"
        self.indentation += 1
        if node.properties:
            props = []
            assigns = []
            for p in node.properties:
                if isinstance(p, tuple):
                    name, default = p
                    if default:
                        # JS 6 supports defaults in args
                        props.append(f"{name} = {self.visit(default)}")
                    else:
                        props.append(name)
                    assigns.append(f"self.{name} = {name};")
                else:
                    props.append(p)
                    assigns.append(f"self.{p} = {p};")
            
            code += f"{self.indent()}constructor({', '.join(props)}) {{\n"
            self.indentation += 1
            if parent: code += f"{self.indent()}super();\n"
            for assign in assigns:
                 code += f"{self.indent()}{assign}\n"
            self.indentation -= 1
            code += f"{self.indent()}}}\n"
        for m in node.methods:
             args = [arg[0] for arg in m.args]
             code += f"\n{self.indent()}{m.name}({', '.join(args)}) {{\n"
             self.indentation += 1
             code += self.compile_block(m.body)
             self.indentation -= 1
             code += f"\n{self.indent()}}}"
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_Instantiation(self, node: Instantiation):
        args = [self.visit(a) for a in node.args]
        return f"var {node.var_name} = new {node.class_name}({', '.join(args)});"
    def visit_MethodCall(self, node: MethodCall):
        args = [self.visit(a) for a in node.args]
        return f"{node.instance_name}.{node.method_name}({', '.join(args)})"
    def visit_PropertyAccess(self, node: PropertyAccess):
        return f"{node.instance_name}.{node.property_name}"
    def visit_Import(self, node: Import):
        base = node.path
        if base == 'vscode': return 'const vscode = require("vscode");'
        return f"const {base} = require('./{base}');"
    def visit_ImportAs(self, node: ImportAs):
        path = node.path
        if path == 'vscode': return f"const {node.alias} = require('vscode');"
        return f"const {node.alias} = require('./{path}');"
    def visit_Try(self, node: Try):
        code = f"try {{\n"
        self.indentation += 1
        code += self.compile_block(node.try_body)
        self.indentation -= 1
        code += f"\n{self.indent()}}} catch ({node.catch_var}) {{\n"
        self.indentation += 1
        code += self.compile_block(node.catch_body)
        self.indentation -= 1
        code += f"\n{self.indent()}}}"
        return code
    def visit_Throw(self, node: Throw):
        return f"throw new Error({self.visit(node.message)});"
    def visit_Skip(self, node: Skip):
        return "continue;"
    def visit_Stop(self, node: Stop):
        return "break;"
    def visit_Lambda(self, node: Lambda):
        return f"({', '.join(node.params)}) => {self.visit(node.body)}"
    def visit_Execute(self, node: Execute):
         pass
