"""
Professional JavaScript transpiler for ShellLite.

Maps ShellLite constructs to modern JavaScript (ES6+).
Includes support for classes, async/await concurrency with channels,
and robust expression handling.
"""
from .ast_nodes import *


class JSCompiler:
    """
    Transpiles ShellLite AST nodes into JavaScript code.
    """

    def __init__(self):
        self.indent_level = 0

    def compile(self, statements):
        """
        Compiles a list of ShellLite statements into a JavaScript program.
        """
        prelude = """// ShellLite Concurrency Runtime
class Channel {
  constructor() {
    this.queue = [];
    this.waiters = [];
  }
  async send(val) {
    if (this.waiters.length > 0) {
      const resolve = this.waiters.shift();
      resolve(val);
    } else {
      this.queue.push(val);
    }
  }
  async receive() {
    if (this.queue.length > 0) {
      return this.queue.shift();
    } else {
      return new Promise(resolve => {
        this.waiters.push(resolve);
      });
    }
  }
}

"""
        code = prelude
        for stmt in statements:
            code += self.visit(stmt) + "\n"
        return code

    def visit(self, node):
        """
        Generic visitor dispatcher for AST nodes.
        """
        if node is None:
            return ""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """
        Raises an error for unsupported AST nodes.
        """
        raise NotImplementedError(f"No visit_{type(node).__name__} method for {type(node).__name__}")

    def _indent(self):
        return "  " * self.indent_level

    def visit_Print(self, node):
        """
        Compiles a print statement to console.log.
        """
        arg = self.visit(node.expression)
        return f"console.log({arg});"

    def visit_String(self, node):
        """
        Compiles a string literal.
        """
        # Escape double quotes and newlines
        val = node.value.replace('"', '\\"').replace('\n', '\\n')
        return f'"{val}"'

    def visit_Number(self, node):
        """
        Compiles a numeric literal.
        """
        return str(node.value)

    def visit_Boolean(self, node):
        """
        Compiles a boolean literal.
        """
        return "true" if node.value else "false"

    def visit_VarAccess(self, node):
        """
        Compiles a variable access.
        """
        return node.name

    def visit_Assign(self, node):
        """
        Compiles a variable assignment.
        """
        val = self.visit(node.value)
        return f"let {node.name} = {val};"

    def visit_TypedAssign(self, node):
        """
        Compiles a typed variable assignment.
        """
        # JS doesn't have native types, so this is same as Assign
        return self.visit_Assign(node)

    def visit_FunctionDef(self, node, is_method=False):
        """
        Compiles a function definition into an async JS function.
        """
        args = ", ".join([arg[0] for arg in node.args])
        
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"

        if is_method:
            return f"async {node.name}({args}){body_str}"
        
        func_code = f"async function {node.name}({args}){body_str}"
        if node.name == 'main':
            func_code += f"\n{node.name}();"
        return func_code

    def visit_Return(self, node):
        """
        Compiles a return statement.
        """
        if node.value:
            return f"return {self.visit(node.value)};"
        return "return;"

    def visit_Call(self, node):
        """
        Compiles a function call.
        """
        func_name = node.name
        args = [self.visit(arg) for arg in node.args]
        
        # Handle some built-ins or special mappings
        if func_name == 'document.getElementById':
            return f"document.getElementById({args[0]})"
        if func_name == 'alert':
            return f"alert({args[0]})"
        if func_name == 'fetch':
             return f"fetch({', '.join(args)})"
        
        return f"{func_name}({', '.join(args)})"

    def visit_MethodCall(self, node):
        """
        Compiles a method call.
        """
        obj_str = node.instance_name
        args = [self.visit(arg) for arg in node.args]
        return f"{obj_str}.{node.method_name}({', '.join(args)})"

    def visit_PropertyAccess(self, node):
        """
        Compiles a property access.
        """
        return f"{node.instance_name}.{node.property_name}"

    def visit_PropertyAssign(self, node):
        """
        Compiles a property assignment.
        """
        val = self.visit(node.value)
        return f"{node.instance_name}.{node.property_name} = {val};"

    def visit_Dictionary(self, node):
        """
        Compiles a dictionary into a JS object using computed property names.
        """
        items = []
        for k, v in node.pairs:
            key_expr = self.visit(k)
            val_expr = self.visit(v)
            items.append(f"[{key_expr}]: {val_expr}")
        return f"{{ {', '.join(items)} }}"

    def visit_ListVal(self, node):
        """
        Compiles a list into a JS array.
        """
        elements = ", ".join([self.visit(el) for el in node.elements])
        return f"[{elements}]"

    def visit_Await(self, node):
        """
        Compiles an await statement.
        """
        return f"await {self.visit(node.task)}"

    def visit_Parallel(self, node: Parallel):
        """
        Compiles a parallel block using Promise.all.
        """
        body_elements = []
        self.indent_level += 1
        for stmt in node.body:
            body_elements.append(f"{self._indent()}(async () => {{ {self.visit(stmt)} }})()")
        self.indent_level -= 1
        
        inner = ",\n".join(body_elements)
        return f"Promise.all([\n{inner}\n{self._indent()}])"

    def visit_Gather(self, node):
        """
        Compiles a gather expression.
        """
        return f"await Promise.all({self.visit(node.tasks)})"

    def visit_Lock(self, node):
        """
        Compiles a lock block. In JS (single-threaded), this is mostly a scope.
        """
        body_str = "{\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        return body_str

    def visit_Channel(self, node):
        """
        Creates a new Channel instance.
        """
        return "new Channel()"

    def visit_Send(self, node):
        """
        Compiles a channel send operation.
        """
        return f"await {self.visit(node.channel)}.send({self.visit(node.value)})"

    def visit_Receive(self, node):
        """
        Compiles a channel receive operation.
        """
        return f"await {self.visit(node.channel)}.receive()"

    def visit_Try(self, node):
        """
        Compiles a try/catch block.
        """
        body_str = "{\n"
        self.indent_level += 1
        for stmt in node.try_body:
             body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        
        catch_blk = ""
        if node.catch_body:
             catch_blk = f" catch({node.catch_var}) {{\n"
             self.indent_level += 1
             for stmt in node.catch_body:
                 catch_blk += self._indent() + self.visit(stmt) + "\n"
             self.indent_level -= 1
             catch_blk += self._indent() + "}"
        return f"try {body_str}{catch_blk}"

    def visit_TryAlways(self, node):
        """
        Compiles a try/catch/finally block.
        """
        try_part = self.visit_Try(node)
        
        finally_blk = " finally {\n"
        self.indent_level += 1
        for stmt in node.always_body:
             finally_blk += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        finally_blk += self._indent() + "}"
        
        return f"{try_part}{finally_blk}"

    def visit_If(self, node):
        """
        Compiles an if/else block.
        """
        cond = self.visit(node.condition)
        
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        
        else_blk = ""
        if node.else_body:
            else_blk = " else {\n"
            self.indent_level += 1
            for stmt in node.else_body:
                else_blk += self._indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
            else_blk += self._indent() + "}"
            
        return f"if ({cond}){body_str}{else_blk}"

    def visit_Unless(self, node):
        """
        Compiles an 'unless' (inverted if) conditional.
        """
        cond = self.visit(node.condition)
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        
        else_blk = ""
        if node.else_body:
            else_blk = " else {\n"
            self.indent_level += 1
            for stmt in node.else_body:
                else_blk += self._indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
            else_blk += self._indent() + "}"
            
        return f"if (!({cond})){body_str}{else_blk}"

    def visit_While(self, node):
        """
        Compiles a while loop.
        """
        cond = self.visit(node.condition)
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        return f"while ({cond}){body_str}"

    def visit_ForIn(self, node):
        """
        Compiles a for-in collection iteration loop.
        """
        iterable = self.visit(node.iterable)
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        return f"for (let {node.var_name} of {iterable}){body_str}"

    def visit_Repeat(self, node):
        """
        Compiles a 'repeat N times' loop.
        """
        count = self.visit(node.count)
        i_var = f"_i{self.indent_level}"
        body_str = " {\n"
        self.indent_level += 1
        for stmt in node.body:
            body_str += self._indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        body_str += self._indent() + "}"
        return f"for (let {i_var} = 0; {i_var} < {count}; {i_var}++){body_str}"

    def visit_BinOp(self, node):
        """
        Compiles a binary operation with a robust operator map.
        """
        op_map = {
            '+': '+', '-': '-', '*': '*', '/': '/', '%': '%',
            '==': '===', '!=': '!==', '<': '<', '>': '>', '<=': '<=', '>=': '>=',
            'and': '&&', 'or': '||',
            'plus': '+', 'minus': '-', 'star': '*', 'slash': '/', 'percent': '%',
            'is': '===', 'is not': '!==',
            '.': '.'
        }
        op = op_map.get(node.op, node.op)
        return f"({self.visit(node.left)} {op} {self.visit(node.right)})"

    def visit_UnaryOp(self, node):
        """
        Compiles a unary operation.
        """
        op_map = {
            'not': '!',
            '-': '-'
        }
        op = op_map.get(node.op, node.op)
        return f"{op}({self.visit(node.right)})"

    def visit_ClassDef(self, node):
        """
        Compiles a class definition.
        """
        extends = f" extends {node.parent}" if node.parent else ""
        code = f"class {node.name}{extends} {{\n"
        self.indent_level += 1
        
        # Constructor
        code += self._indent() + "constructor() {\n"
        self.indent_level += 1
        if node.parent:
            code += self._indent() + "super();\n"
        for prop_name, default_val in node.properties:
            val = self.visit(default_val) if default_val else "null"
            code += self._indent() + f"this.{prop_name} = {val};\n"
        self.indent_level -= 1
        code += self._indent() + "}\n\n"
        
        # Methods
        for method in node.methods:
            method_code = self.visit_FunctionDef(method, is_method=True)
            code += self._indent() + method_code + "\n"
            
        self.indent_level -= 1
        code += self._indent() + "}"
        return code

    def visit_Instantiation(self, node):
        """
        Compiles a class instantiation.
        """
        args = ", ".join([self.visit(arg) for arg in node.args])
        inst = f"new {node.class_name}({args})"
        if node.var_name:
            return f"let {node.var_name} = {inst};"
        return inst

    def visit_IndexAccess(self, node):
        """
        Compiles an index access.
        """
        return f"{self.visit(node.obj)}[{self.visit(node.index)}]"

    def visit_IndexAssign(self, node):
        """
        Compiles an index assignment.
        """
        return f"{self.visit(node.obj)}[{self.visit(node.index)}] = {self.visit(node.value)};"

    def visit_Throw(self, node):
        """
        Compiles a throw/error statement.
        """
        return f"throw new Error({self.visit(node.message)});"

    def visit_Stop(self, node):
        """
        Compiles a break statement.
        """
        return "break;"

    def visit_Skip(self, node):
        """
        Compiles a continue statement.
        """
        return "continue;"
