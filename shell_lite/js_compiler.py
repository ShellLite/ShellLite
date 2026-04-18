from .ast_nodes import *


class JSCompiler:
    def __init__(self):
        """
        -----Purpose: Initializes the JS compiler with zero indentation.
        """
        self.indent_level = 0

    def compile(self, statements):
        """
        -----Purpose: Transpiles a list of AST nodes into a JS source string.
        """
        code = ""
        for stmt in statements:
            code += self.visit(stmt) + "\n"
        return code

    def visit(self, node):
        """
        -----Purpose: Generic visitor dispatcher for AST nodes.
        """
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """
        -----Purpose: Raises an error for unsupported AST nodes.
        """
        raise NotImplementedError(f"No visit_{type(node).__name__} method")
    def visit_Print(self, node):
        arg = self.visit(node.expression)
        return f"console.log({arg});"
    def visit_String(self, node):
        return f'"{node.value}"'
    def visit_Number(self, node):
        return str(node.value)
    def visit_Boolean(self, node):
        return "true" if node.value else "false"
    def visit_VarAccess(self, node):
        return node.name
    def visit_Assign(self, node):
        val = self.visit(node.value)
        return f"let {node.name} = {val};"
    def visit_FunctionDef(self, node):
        """
        -----Purpose: Compiles a ShellLite function into an async JS function.
        """
        args = ", ".join([arg[0] for arg in node.args])
        body = "{\n"
        self.indent_level += 1
        for stmt in node.body:
            body += "  " * self.indent_level + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body += "}"
        if node.name == 'main':
            call = f"{node.name}();"
            return f"async function {node.name}({args}) {body}\n{call}"
        return f"async function {node.name}({args}) {body}"
    def visit_Return(self, node):
        if node.value:
            return f"return {self.visit(node.value)};"
        return "return;"
    def visit_Call(self, node):
        func_name = node.name
        args = [self.visit(arg) for arg in node.args]
        if func_name == 'document.getElementById':
            return f"document.getElementById({args[0]})"
        if func_name == 'alert':
            return f"alert({args[0]})"
        if func_name == 'fetch':
             return f"fetch({', '.join(args)})"
        return f"{func_name}({', '.join(args)})"
    def visit_MethodCall(self, node):
        obj_str = node.instance_name
        args = [self.visit(arg) for arg in node.args]
        return f"{obj_str}.{node.method_name}({', '.join(args)})"
    def visit_PropertyAccess(self, node):
        return f"{node.instance_name}.{node.property_name}"
    def visit_PropertyAssign(self, node):
        """
        -----Purpose: Compiles a property assignment (e.g. obj.prop = val).
        """
        val = self.visit(node.value)
        return f"{node.instance_name}.{node.property_name} = {val};"
    def visit_Dictionary(self, node):
        """
        -----Purpose: Compiles a ShellLite dictionary into a JS object.
        """
        items = []
        for k, v in node.pairs:
            key_str = k.value
            val_str = self.visit(v)
            items.append(f"'{key_str}': {val_str}")
        return f"{{ {', '.join(items)} }}"
    def visit_Await(self, node):
        return f"await {self.visit(node.task)}"
    def visit_Get(self, node):
        pass
    def visit_Try(self, node):
        """
        -----Purpose: Compiles a try/catch block into JavaScript.
        """
        body = "{\n"
        self.indent_level += 1
        for stmt in node.try_body:
             body += "  " * self.indent_level + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body += "}"
        catch_blk = ""
        if node.catch_body:
             catch_blk = f" catch({node.catch_var}) {{\n"
             self.indent_level += 1
             for stmt in node.catch_body:
                 catch_blk += "  " * self.indent_level + self.visit(stmt) + "\n"
             self.indent_level -= 1
             catch_blk += "}"
        return f"try {body}{catch_blk}"
    def visit_TryAlways(self, node):
        """
        -----Purpose: Compiles a try/catch/finally block into JavaScript.
        """
        body = "{\n"
        self.indent_level += 1
        for stmt in node.try_body:
             body += "  " * self.indent_level + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body += "}"
        catch_blk = ""
        if node.catch_body:
             catch_blk = f" catch({node.catch_var}) {{\n"
             self.indent_level += 1
             for stmt in node.catch_body:
                 catch_blk += "  " * self.indent_level + self.visit(stmt) + "\n"
             self.indent_level -= 1
             catch_blk += "}"
        finally_blk = " finally {\n"
        self.indent_level += 1
        for stmt in node.always_body:
             finally_blk += "  " * self.indent_level + self.visit(stmt) + "\n"
        self.indent_level -= 1
        finally_blk += "}"
        return f"try {body}{catch_blk}{finally_blk}"
    def visit_If(self, node):
        cond = self.visit(node.condition)
        body = "{\n"
        for stmt in node.body:
            body += self.visit(stmt) + "\n"
        body += "}"
        else_blk = ""
        if node.else_body:
            else_blk = " else {\n"
            for stmt in node.else_body:
                else_blk += self.visit(stmt) + "\n"
            else_blk += "}"
        return f"if ({cond}) {body}{else_blk}"
    def visit_Or(self, node):
        return f"({self.visit(node.left)} || {self.visit(node.right)})"
    def visit_BinOp(self, node):
        op_map = {
            'or': '||',
            'and': '&&',
            'is': '===',
            'plus': '+',
            'minus': '-',
            'star': '*',
            'slash': '/',
            'percent': '%'
        }
        op = op_map.get(node.op, node.op)
        return f"{self.visit(node.left)} {op} {self.visit(node.right)}"
    def visit_UnaryOp(self, node):
        op_map = {
            'not': '!'
        }
        op = op_map.get(node.op, node.op)
        return f"{op}{self.visit(node.right)}"