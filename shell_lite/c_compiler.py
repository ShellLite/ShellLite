from .ast_nodes import *


class CCompiler:
    def __init__(self):
        self.indent_level = 0
        self.vars = set()

    def indent(self):
        return "    " * self.indent_level

    def compile(self, statements):
        """
        -----Purpose: Transpiles AST to a complete C source file.
        """
        body = ""
        for stmt in statements:
            body += self.visit(stmt) + "\n"
        header = (
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <stdbool.h>\n"
            "#include <string.h>\n\n"
            "// --- ShellLite Runtime Helpers ---\n"
            "void slang_print_num(double n) { printf(\"%g\\n\", n); }\n"
            "void slang_print_str(const char* s) { printf(\"%s\\n\", s); }\n\n"
        )    
        main_func = (
            "int main(int argc, char** argv) {\n"
            + body
            + "    return 0;\n"
            + "}\n"
        )
        return header + main_func
    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return self.indent() + visitor(node)

    def generic_visit(self, node):
        return f"// Unsupported: {type(node).__name__}"

    def visit_Number(self, node):
        return str(node.value)

    def visit_String(self, node):
        return f"\"{node.value}\""

    def visit_Boolean(self, node):
        return "true" if node.value else "false"

    def visit_VarAccess(self, node):
        return node.name

    def visit_Assign(self, node):
        val = self.visit_expr(node.value)
        if node.name not in self.vars:
            self.vars.add(node.name)
            return f"double {node.name} = {val};"
        return f"{node.name} = {val};"

    def visit_Print(self, node):
        expr = self.visit_expr(node.expression)
        return f"slang_print_num({expr});"

    def visit_If(self, node):
        cond = self.visit_expr(node.condition)
        self.indent_level += 1
        body = "\n".join([self.visit(s) for s in node.body])
        self.indent_level -= 1
        
        code = f"if ({cond}) {{\n{body}\n{self.indent()}}}"
        if node.else_body:
            self.indent_level += 1
            else_body = "\n".join([self.visit(s) for s in node.else_body])
            self.indent_level -= 1
            code += f" else {{\n{else_body}\n{self.indent()}}}"
        return code

    def visit_While(self, node):
        cond = self.visit_expr(node.condition)
        self.indent_level += 1
        body = "\n".join([self.visit(s) for s in node.body])
        self.indent_level -= 1
        return f"while ({cond}) {{\n{body}\n{self.indent()}}}"

    def visit_BinOp(self, node):
        left = self.visit_expr(node.left)
        right = self.visit_expr(node.right)
        op_map = {'plus': '+', 'minus': '-', 'star': '*', 'slash': '/'}
        op = op_map.get(node.op, node.op)
        return f"({left} {op} {right})"

    def visit_expr(self, node):
        """Helper to visit without indentation and newline"""
        old_indent = self.indent_level
        self.indent_level = 0
        res = self.visit(node).strip().replace('\n', ' ')
        self.indent_level = old_indent
        return res
