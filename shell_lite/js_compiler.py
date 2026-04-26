from .ast_nodes import *

class JSCompiler:
    def __init__(self):
        self.indent_level = 0

    def compile(self, statements):
        code = ""
        for stmt in statements:
            code += self.visit(stmt) + "\n"
        return code

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    def visit_Print(self, node):
        # Maps 'say' or 'print' to console.log or alert?
        # ShellLite 'alert' maps to alert(). 'print' maps to console.log?
        # User JS used: outputDiv.innerText = ...
        # Standard ShellLite mapping:
        arg = self.visit(node.expression)
        return f"console.log({arg});"

    def visit_String(self, node):
        return f'"{node.value}"'

    def visit_Number(self, node):
        return str(node.value)
    
    def visit_Boolean(self, node):
        return "true" if node.value else "false"

    def visit_VarAccess(self, node):
        # Check if it's a DOM element ID? or variable.
        # JS is flexible.
        return node.name

    def visit_Assign(self, node):
        val = self.visit(node.value)
        return f"let {node.name} = {val};"

    def visit_FunctionDef(self, node):
        args = ", ".join([arg[0] for arg in node.args])
        body = "{\n"
        self.indent_level += 1
        for stmt in node.body:
            body += "  " * self.indent_level + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body += "}"
        if node.name == 'main':
            # Auto-run main?
            return f"async function {node.name}({args}) {body}\n{node.name}();"
        return f"async function {node.name}({args}) {body}"

    def visit_Return(self, node):
        if node.value:
            return f"return {self.visit(node.value)};"
        return "return;"

    def visit_Call(self, node):
        # Special mappings for JS DOM or Fetch
        func_name = node.name
        args = [self.visit(arg) for arg in node.args]
        
        if func_name == 'document.getElementById':
            return f"document.getElementById({args[0]})"
        if func_name == 'alert':
            return f"alert({args[0]})"
        if func_name == 'fetch':
             # Simple fetch wrapper?
             # fetch(url, options)
             return f"fetch({', '.join(args)})"
        
        return f"{func_name}({', '.join(args)})"

    def visit_MethodCall(self, node):
        obj_str = node.instance_name
        args = [self.visit(arg) for arg in node.args]
        return f"{obj_str}.{node.method_name}({', '.join(args)})"

    def visit_PropertyAccess(self, node):
        return f"{node.instance_name}.{node.property_name}"

    def visit_PropertyAssign(self, node):
        # e.g. element.innerText = "value"
        return f"{node.instance_name}.{node.property_name} = {self.visit(node.value)};"

    def visit_Dictionary(self, node):
        items = []
        for k, v in node.pairs:
            # key is String node usually
            key_str = k.value
            val_str = self.visit(v)
            items.append(f"'{key_str}': {val_str}")
        return f"{{ {', '.join(items)} }}"

    # Async/Await support
    def visit_Await(self, node):
        return f"await {self.visit(node.task)}"
        
    def visit_Get(self, node):
        # Helper for user-friendly "Get element" -> document.querySelector?
        pass

    def visit_Try(self, node):
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
         

