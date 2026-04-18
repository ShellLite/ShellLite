from dataclasses import dataclass, field
from typing import Any, List, Optional

from .ast_nodes import *
from .lexer import Token


@dataclass
class GeoNode:
    """
    -----Purpose: Represents a topological node in the source code geometry.
                  Stores indentation level and relationship to parent/children.
    """
    head_token: Token
    line: int
    indent_level: int
    tokens: List[Token] = field(default_factory=list)
    children: List['GeoNode'] = field(default_factory=list)
    parent: Optional['GeoNode'] = None
    def __repr__(self):
        return f"GeoNode(line={self.line}, indent={self.indent_level}, head={self.head_token.type})"
class GeometricBindingParser:
    """
    -----Purpose: Parses tokens topologically using indentation binding rules 
                  rather than traditional recursive descent.
    """
    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != 'COMMENT']
        self.root_nodes: List[GeoNode] = []
        self.precedence = {
            'OR': 1, 'AND': 2, 'NOT': 3,
            'EQ': 4, 'NEQ': 4, 'LT': 5, 'GT': 5, 'LE': 5, 'GE': 5, 'IS': 5,
            'IN': 5, 'NOTIN': 5,
            'PLUS': 6, 'MINUS': 6,
            'MUL': 7, 'DIV': 7, 'MOD': 7,
            'POW': 8,
            'DOT': 9, 'LPAREN': 10, 'LBRACKET': 10
        }
    def parse(self) -> List[Node]:
        """
        -----Purpose: Main entry point for Geometric Binding Parser. Orchestrates 
                      the scan and semantic binding phases to produce an AST.
        """
        self.topology_scan()
        return self.bind_statement_list(self.root_nodes)

    def bind_statement_list(self, geo_nodes: List[GeoNode]) -> List[Node]:
        """
        -----Purpose: Binds a sequence of GeoNodes into a list of AST nodes,
                      handling grouping for IF-ELIF-ELSE and TRY-CATCH-ALWAYS.
        """
        ast_nodes = []
        i = 0
        while i < len(geo_nodes):
            geo_node = geo_nodes[i]
            head_type = geo_node.head_token.type
            if head_type == 'IF':
                if_node = self.bind_if(geo_node)
                j = i + 1
                curr = if_node
                while j < len(geo_nodes):
                    next_geo = geo_nodes[j]
                    if next_geo.head_token.type == 'ELIF':
                        elif_node = self.bind_if(next_geo)
                        curr.else_body = [elif_node]
                        curr = elif_node
                        j += 1
                    elif next_geo.head_token.type == 'ELSE':
                        curr.else_body = self.bind_statement_list(next_geo.children)
                        j += 1
                        break
                    else:
                        break
                ast_nodes.append(if_node)
                i = j
                continue
            if head_type == 'TRY':
                try_body = self.bind_statement_list(geo_node.children)
                catch_body = []
                catch_var = "e"
                always_body = None
                j = i + 1
                while j < len(geo_nodes):
                    next_geo = geo_nodes[j]
                    if next_geo.head_token.type == 'CATCH':
                        if len(next_geo.tokens) > 1:
                            catch_var = next_geo.tokens[1].value
                        catch_body = self.bind_statement_list(next_geo.children)
                        j += 1
                    elif next_geo.head_token.type == 'ALWAYS':
                        always_body = self.bind_statement_list(next_geo.children)
                        j += 1
                    else:
                        break
                if always_body is not None:
                    ast_nodes.append(
                        TryAlways(try_body, catch_var, catch_body, always_body)
                    )
                else:
                    ast_nodes.append(Try(try_body, catch_var, catch_body))
                i = j
                continue
            
            ast_node = self.bind_node(geo_node)
            if ast_node:
                ast_nodes.append(ast_node)
            i += 1
        return ast_nodes
    def topology_scan(self):
        """
        -----Purpose: Scans tokens topologically to build GeoNodes and link 
        -----        them into a tree based on indentation geometry.
        """
        current_node: Optional[GeoNode] = None
        last_line_node: Optional[GeoNode] = None
        block_stack: List[GeoNode] = []
        for token in self.tokens:
            if token.type == 'EOF':
                break
            if token.type == 'INDENT':
                p_push = current_node if current_node else last_line_node
                if p_push:
                    block_stack.append(p_push)
                current_node = None
                continue
            if token.type == 'DEDENT':
                if block_stack:
                    block_stack.pop()
                continue
            if token.type == 'NEWLINE':
                last_line_node = current_node
                current_node = None
                continue
            if current_node is None:
                current_node = GeoNode(
                    head_token=token,
                    line=token.line,
                    indent_level=len(block_stack),
                    tokens=[token]
                )
                if block_stack:
                    parent = block_stack[-1]
                    parent.children.append(current_node)
                    current_node.parent = parent
                else:
                    self.root_nodes.append(current_node)
            else:
                current_node.tokens.append(token)
    def bind_node(self, node: GeoNode) -> Node:
        """
        -----Purpose: Semantic Binding Dispatcher. Converts a topological 
        -----        GeoNode into a logical AST Node based on its head token.
        """
        head_type = node.head_token.type
        bind_map = {
            'IF': self.bind_if, 'WHILE': self.bind_while,
            'FOR': self.bind_for, 'LOOP': self.bind_for,
            'REPEAT': self.bind_repeat, 'FOREVER': self.bind_forever,
            'USE': self.bind_use, 'SERVE': self.bind_serve,
            'DEFINE': self.bind_define, 'STRUCTURE': self.bind_structure,
            'WHEN': self.bind_when, 'DB': self.bind_db,
            'TRY': self.bind_try, 'UNLESS': self.bind_unless,
            'UNTIL': self.bind_until, 'ON': self.bind_on,
            'FUNCTION': self.bind_func, 'TO': self.bind_func,
            'PRINT': self.bind_print, 'SAY': self.bind_print,
            'MAKE': self.bind_assignment,
            'RETURN': self.bind_return,
            'ALERT': self.bind_alert, 'PROMPT': self.bind_prompt,
            'CONFIRM': self.bind_confirm, 'EXECUTE': self.bind_execute,
            'EXIT': self.bind_exit, 'STOP': self.bind_stop,
            'SKIP': self.bind_skip, 'ERROR': self.bind_error,
            'SPAWN': self.bind_spawn, 'AWAIT': self.bind_await,
            'EVERY': self.bind_every, 'AFTER': self.bind_after_in,
            'IN': self.bind_after_in, 'WRITE': self.bind_file_op,
            'APPEND': self.bind_file_op, 'READ': self.bind_file_op,
            'COPY': self.bind_clipboard_op, 'PASTE': self.bind_clipboard_op,
            'CLIPBOARD': self.bind_clipboard_op, 'CSV': self.bind_csv_op,
            'COMPRESS': self.bind_archive_op, 'EXTRACT': self.bind_archive_op,
            'PRESS': self.bind_automation, 'TYPE': self.bind_automation,
            'CLICK': self.bind_automation, 'NOTIFY': self.bind_automation,
            'DOWNLOAD': self.bind_download, 'APP': self.bind_app,
            'IMPORT': self.bind_import_enhanced,
            'FROM': self.bind_from_import,
            'SET': self.bind_expression_statement,
            'ADD': self.bind_add,
            'INCREMENT': self.bind_natural_math,
            'DECREMENT': self.bind_natural_math,
            'PUT': self.bind_expression_statement,
            'PUSH': self.bind_expression_statement,
            'JSON': self.bind_expression_statement,
            'HTTP': self.bind_expression_statement,
            'INT': self.bind_expression_statement,
            'STR': self.bind_expression_statement,
            'LEN': self.bind_expression_statement,
            'KEYS': self.bind_expression_statement,
            'REMOVE': self.bind_remove,
            'TEST': self.bind_test,
            'EXPECT': self.bind_assert,
            'ENSURE': self.bind_assert,
        }
        
        if head_type in bind_map:
            return bind_map[head_type](node)
            
        if head_type == 'BEFORE' and len(node.tokens) > 1:
            if node.tokens[1].type == 'REQUEST':
                return self.bind_middleware(node)
                
        if head_type == 'ID':
            val = node.head_token.value.lower()
            if val == 'a' and len(node.tokens) > 1:
                t1 = node.tokens[1].type
                if t1 == 'LIST':
                    return self.bind_natural_list(node)
                if t1 == 'UNIQUE' and len(node.tokens) > 2:
                    if node.tokens[2].type == 'SET':
                        return self.bind_natural_set(node)
            
            # Check for regular assignment (x = 1) or index assignment (x[0] = 1)
            assign_idx = -1
            for k, tok in enumerate(node.tokens):
                if tok.type in ('ASSIGN', 'IS'):
                    assign_idx = k
                    break
            
            if assign_idx != -1:
                if len(node.tokens) > 1 and node.tokens[1].type == 'LBRACKET':
                    return self.bind_index_assignment(node, assign_idx)
                return self.bind_assignment(node)
            
            return self.bind_call_or_expr(node)
            
        return self.bind_expression_statement(node)

    def bind_expression_statement(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds a GeoNode to an expression node (e.g. function call).
        """
        return self.parse_expr_iterative(node.tokens)
    def peek_type(self, node: GeoNode, offset: int) -> str:
        if offset < len(node.tokens):
            return node.tokens[offset].type
        return ""
    def bind_if(self, node: GeoNode) -> If:
        """
        -----Purpose: Binds an IF block GeoNode to an AST If node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        body = self.bind_statement_list(node.children)
        return If(condition, body, None)
    def bind_unless(self, node: GeoNode) -> Unless:
        """
        -----Purpose: Binds an UNLESS block GeoNode to an AST Unless node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        body = self.bind_statement_list(node.children)
        return Unless(condition, body)
    def bind_until(self, node: GeoNode) -> Until:
        """
        -----Purpose: Binds an UNTIL block GeoNode to an AST Until node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        body = self.bind_statement_list(node.children)
        return Until(condition, body)
    def bind_try(self, node: GeoNode) -> Try:
        # Dummy; handled by parse() grouping
        return None
    def bind_structure(self, node: GeoNode) -> ClassDef:
        """
        -----Purpose: Binds a STRUCTURE block GeoNode to an AST ClassDef node.
        """
        tokens = node.tokens
        name = tokens[1].value
        parent = None
        if len(tokens) > 2:
            if tokens[2].type == 'EXTENDS':
                parent = tokens[3].value
            elif tokens[2].type == 'LPAREN':
                parent = tokens[3].value
        properties = []
        methods = []
        for child in node.children:
            head = child.head_token.type
            if head == 'HAS' or head == 'ID':
                start = 1 if head == 'HAS' else 0
                prop_name = child.tokens[start].value
                default_val = None
                assign_idx = -1
                for i, t in enumerate(child.tokens):
                    if t.type == 'ASSIGN':
                        assign_idx = i
                        break
                if assign_idx != -1:
                    default_val = self.parse_expr_iterative(
                        child.tokens[assign_idx + 1:]
                    )
                properties.append((prop_name, default_val))
            elif head == 'TO' or head == 'FUNCTION':
                methods.append(self.bind_func(child))
        return ClassDef(name, properties, methods, parent)
    def bind_db(self, node: GeoNode) -> DatabaseOp:
        """
        -----Purpose: Binds a DB block GeoNode to an AST DatabaseOp node.
        """
        tokens = node.tokens
        op = 'open'
        i = 1
        if i < len(tokens):
            t = tokens[i]
            if t.type == 'OPEN':
                i += 1
            elif t.type == 'QUERY':
                op = 'query'
                i += 1
            elif t.type == 'EXEC':
                op = 'exec'
                i += 1
            elif t.type == 'CLOSE':
                op = 'close'
                i += 1
        args = []
        if op != 'close':
            remaining = tokens[i:]
            if remaining:
                args.append(self.parse_expr_iterative(remaining))
        return DatabaseOp(op, args)
    def bind_while(self, node: GeoNode) -> While:
        """
        -----Purpose: Binds a WHILE block GeoNode to an AST While node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        body = self.bind_statement_list(node.children)
        return While(condition, body)
    def bind_repeat(self, node: GeoNode) -> Repeat:
        """
        -----Purpose: Binds a REPEAT block GeoNode to an AST Repeat node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        if expr_tokens and expr_tokens[-1].type == 'TIMES':
            expr_tokens.pop()
        count = self.parse_expr_iterative(expr_tokens)
        body = self.bind_statement_list(node.children)
        return Repeat(count, body)
    def bind_forever(self, node: GeoNode) -> Forever:
        """
        -----Purpose: Binds a FOREVER block GeoNode to an AST Forever node.
        """
        body = self.bind_statement_list(node.children)
        return Forever(body)
    def bind_for(self, node: GeoNode) -> Optional[Node]:
        """
        -----Purpose: Binds a FOR-IN or LOOP block GeoNode to an AST ForIn or 
        -----        Repeat node.
        """
        if len(node.tokens) < 3:
            return None
        
        start_idx = 1
        if node.tokens[1].type == 'EACH':
            start_idx = 2
            if len(node.tokens) < 4:
                return None
        
        var_name = node.tokens[start_idx].value
        in_idx = -1
        for i, t in enumerate(node.tokens):
            if t.type == 'IN':
                in_idx = i
                break
        if in_idx == -1:
            if node.head_token.type == 'LOOP':
                if node.tokens[-1].type == 'TIMES':
                    e_tokens = self._extract_expr_tokens(node.tokens, 1)
                    e_tokens.pop()
                    count = self.parse_expr_iterative(e_tokens)
                    body = self.bind_statement_list(node.children)
                    return Repeat(count, body)
            return None
        body = self.bind_statement_list(node.children)
        # Check for range(...) special case FIRST, before
        # generic parse_expr_iterative which can't handle
        # the RANGE keyword token.
        if node.tokens[in_idx + 1].type == 'RANGE':
            args_tokens = self._extract_expr_tokens(node.tokens, in_idx+2)
            filtered = [
                t for t in args_tokens
                if t.type not in ('LPAREN', 'RPAREN', 'COMMA')
            ]
            range_args = []
            for t in filtered:
                if t.type == 'NUMBER':
                    val = Number(
                        int(t.value) if '.' not in t.value else float(t.value)
                    )
                elif t.type == 'STRING':
                    val = String(t.value)
                elif t.type == 'ID':
                    val = VarAccess(t.value)
                else:
                    msg = f"Invalid token '{t.value}' in range expression."
                    raise SyntaxError(msg)
                if val:
                    range_args.append(val)
            iterable = Call('range', range_args)
        else:
            iter_tokens = self._extract_expr_tokens(
                node.tokens, in_idx + 1
            )
            iterable = self.parse_expr_iterative(iter_tokens)
        return ForIn(var_name, iterable, body)
    def bind_print(self, node: GeoNode) -> Print:
        """
        -----Purpose: Binds a PRINT GeoNode to an AST Print node.
        """
        ...

        """
        -----Purpose: Binds a PRINT block GeoNode to an AST Print node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        expr = self.parse_expr_iterative(expr_tokens)
        return Print(expr)
    def bind_return(self, node: GeoNode) -> Return:
        """
        -----Purpose: Binds a RETURN block GeoNode to an AST Return node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        expr = self.parse_expr_iterative(expr_tokens)
        return Return(expr)
    def bind_assignment(self, node: GeoNode) -> Assign:
        """
        -----Purpose: Binds an Assignment GeoNode to an AST Assign/TypedAssign node.
        """
        tokens = node.tokens
        assign_idx = -1
        for i, t in enumerate(tokens):
            if t.type in ('ASSIGN', 'IS', 'BE'):
                assign_idx = i
                break
        
        if assign_idx == -1:
            raise SyntaxError("Assignment operator missing")

        if node.head_token.type == 'MAKE':
            name = tokens[1].value
        else:
            name = tokens[0].value
        
        # Detect optional type hint: x as int = 5
        # tokens[0]=ID(x), tokens[1]=AS, tokens[2]=ID(int), tokens[3]=ASSIGN
        type_hint = None
        if assign_idx >= 3 and tokens[1].type == 'AS':
            type_hint = tokens[2].value.lower()
            
        expr_tokens = tokens[assign_idx + 1:]
        value = self.parse_expr_iterative(expr_tokens)
        if type_hint:
            return TypedAssign(name, type_hint, value)
        return Assign(name, value)
        
    def bind_index_assignment(self, node: GeoNode, assign_idx: int) -> Any:
        """
        -----Purpose: Binds an array/dict assignment (e.g. board[x] = y)
        """
        lhs_tokens = node.tokens[:assign_idx]
        value_tokens = node.tokens[assign_idx + 1:]
        
        lhs_expr = self.parse_expr_iterative(lhs_tokens)
        value_expr = self.parse_expr_iterative(value_tokens)
        
        if type(lhs_expr).__name__ == "IndexAccess":
            return IndexAssign(lhs_expr.obj, lhs_expr.index, value_expr)
        
        raise SyntaxError("Invalid index assignment syntax")
    def bind_expression_stmt(self, node: GeoNode) -> Any:
        """
        -----Purpose: Binds an expression GeoNode to an AST expression.
        """
        return self.parse_expr_iterative(node.tokens)
    def bind_start(self, node: GeoNode) -> Listen:
        """
        -----Purpose: Binds a START block GeoNode (server startup).
        """
        return Listen(Number(8080))
    def bind_listen(self, node: GeoNode) -> Listen:
        """
        -----Purpose: Binds a LISTEN block GeoNode to an AST Listen node.
        """
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        if expr_tokens and expr_tokens[0].type == 'PORT':
            expr_tokens.pop(0)
        port = self.parse_expr_iterative(expr_tokens)
        return Listen(port)
    def bind_func(self, node: GeoNode) -> FunctionDef:
        """
        -----Purpose: Binds a FUNCTION definition GeoNode to AST FunctionDef.
                      Supports typed args: `to add a as int b as str`.
        """
        start = 1
        if node.tokens[0].type == 'DEFINE':
            start = 2
        name = node.tokens[start].value
        args = []
        token_slice = node.tokens[start + 1:]
        i = 0
        while i < len(token_slice):
            t = token_slice[i]
            if t.type == 'USING' or t.type == 'COMMA':
                i += 1
                continue
            if t.type == 'COLON':
                break
            if t.type == 'ID':
                arg_name = t.value
                # Check for `arg as type` pattern
                if (i + 2 < len(token_slice)
                        and token_slice[i + 1].type == 'AS'
                        and token_slice[i + 2].type == 'ID'):
                    type_hint = token_slice[i + 2].value.lower()
                    args.append((arg_name, None, type_hint))
                    i += 3
                else:
                    args.append((t.value, None, None))
                    i += 1
            else:
                i += 1
        body = self.bind_statement_list(node.children)
        return FunctionDef(name, args, body)
    def bind_alert(self, node: GeoNode) -> Alert:
        """
        -----Purpose: Binds an ALERT block GeoNode to an AST Alert node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Alert(expr)
    def bind_prompt(self, node: GeoNode) -> Prompt:
        """
        -----Purpose: Binds a PROMPT block GeoNode to an AST Prompt node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Prompt(expr)
    def bind_confirm(self, node: GeoNode) -> Confirm:
        """
        -----Purpose: Binds a CONFIRM block GeoNode to an AST Confirm node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Confirm(expr)
    def bind_execute(self, node: GeoNode) -> Execute:
        """
        -----Purpose: Binds an EXECUTE block GeoNode to an AST Execute node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Execute(expr)
    def bind_exit(self, node: GeoNode) -> Exit:
        """
        -----Purpose: Binds an EXIT block GeoNode to an AST Exit node.
        """
        expr = None
        if len(node.tokens) > 1:
            expr = self.parse_expr_iterative(node.tokens[1:])
        return Exit(expr)
    def bind_stop(self, node: GeoNode) -> Stop:
        """
        -----Purpose: Binds a STOP block GeoNode to an AST Stop node.
        """
        return Stop()
    def bind_skip(self, node: GeoNode) -> Skip:
        """
        -----Purpose: Binds a SKIP block GeoNode to an AST Skip node.
        """
        return Skip()
    def bind_error(self, node: GeoNode) -> Throw:
        """
        -----Purpose: Binds an ERROR block GeoNode to an AST Throw node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Throw(expr)
    def bind_spawn(self, node: GeoNode) -> Spawn:
        """
        -----Purpose: Binds a SPAWN block GeoNode to an AST Spawn node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Spawn(expr)
    def bind_await(self, node: GeoNode) -> Await:
        """
        -----Purpose: Binds an AWAIT block GeoNode to an AST Await node.
        """
        expr = self.parse_expr_iterative(node.tokens[1:])
        return Await(expr)
    def bind_every(self, node: GeoNode) -> Every:
        """
        -----Purpose: Binds an EVERY block GeoNode to an AST Every node.
        """
        tokens = node.tokens
        interval = self.parse_expr_iterative([tokens[1]])
        unit = 'seconds'
        if len(tokens) > 2:
            if tokens[2].type == 'MINUTE':
                unit = 'minutes'
        body = self.bind_statement_list(node.children)
        return Every(interval, unit, body)
    def bind_after_in(self, node: GeoNode) -> After:
        """
        -----Purpose: Binds an AFTER/IN block GeoNode to an AST After node.
        """
        tokens = node.tokens
        delay = self.parse_expr_iterative([tokens[1]])
        unit = 'seconds'
        if len(tokens) > 2:
            if tokens[2].type == 'MINUTE':
                unit = 'minutes'
        body = self.bind_statement_list(node.children)
        return After(delay, unit, body)
    def bind_add(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds an ADD statement
        """
        tokens = node.tokens
        # ADD [item] TO [target]
        to_idx = -1
        for i, t in enumerate(tokens):
            if t.type == 'TO':
                to_idx = i
                break
        
        if to_idx != -1:
            item = self.parse_expr_iterative(tokens[1:to_idx])
            target = self.parse_expr_iterative(tokens[to_idx + 1:])
            return Call('add', [target, item])
        
        return self.bind_expression_statement(node)

    def bind_natural_math(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds natural math
        """
        tokens = node.tokens
        head = tokens[0].type
        by_idx = -1
        for i, t in enumerate(tokens):
            if t.type == 'BY':
                by_idx = i
                break
        
        if by_idx != -1:
            var_name = tokens[1].value
            val = self.parse_expr_iterative(tokens[by_idx + 1:])
            op = '+' if head == 'INCREMENT' else '-'
            return Assign(var_name, BinOp(VarAccess(var_name), op, val))
            
        return self.bind_expression_statement(node)

    def bind_remove(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds a REMOVE statement
        """
        tokens = node.tokens
        from_idx = -1
        for i, t in enumerate(tokens):
            if t.type == 'FROM':
                from_idx = i
                break
        
        if from_idx != -1:
            item = self.parse_expr_iterative(tokens[1:from_idx])
            target = self.parse_expr_iterative(tokens[from_idx + 1:])
            return Call('remove', [target, item])
            
        return self.bind_expression_statement(node)

    def bind_file_op(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds a File I/O block GeoNode (Read/Write/Append).
        """
        tokens = node.tokens
        head = tokens[0].type
        if head == 'READ':
            return FileRead(self.parse_expr_iterative(tokens[1:]))
        mode = 'w' if head == 'WRITE' else 'a'
        content = self.parse_expr_iterative([tokens[1]])
        path_tokens = tokens[3:] if len(tokens) > 3 else []
        path = (
            self.parse_expr_iterative(path_tokens) if path_tokens
            else String('output.txt')
        )
        return FileWrite(path, content, mode)
    def bind_csv_op(self, node: GeoNode) -> CsvOp:
        """
        -----Purpose: Binds a CSV operation GeoNode.
        """
        path = self.parse_expr_iterative(node.tokens[2:])
        return CsvOp('load', None, path)

    def bind_clipboard_op(self, node: GeoNode) -> ClipboardOp:
        """
        -----Purpose: Binds a Clipboard operation GeoNode.
        """
        op = node.tokens[0].value.lower()
        return ClipboardOp(op, None)
    def bind_archive_op(self, node: GeoNode) -> ArchiveOp:
        """
        -----Purpose: Binds an Archive operation GeoNode (Compress/Extract).
        """
        return ArchiveOp(
            node.tokens[0].value.lower(),
            self.parse_expr_iterative([node.tokens[1]]),
            self.parse_expr_iterative(node.tokens[3:])
        )
    def bind_automation(self, node: GeoNode) -> AutomationOp:
        """
        -----Purpose: Binds an Automation operation GeoNode (Click/Type/Press).
        """
        return AutomationOp(
            node.tokens[0].value.lower(),
            [self.parse_expr_iterative(node.tokens[1:])]
        )
    def bind_download(self, node: GeoNode) -> Download:
        """
        -----Purpose: Binds a DOWNLOAD operation GeoNode.
        """
        return Download(self.parse_expr_iterative(node.tokens[1:]))
    def bind_app(self, node: GeoNode) -> App:
        """
        -----Purpose: Binds an APP block GeoNode to an AST App node.
        """
        tokens = node.tokens
        title = tokens[1].value
        width, height = 500, 400
        for i, t in enumerate(tokens):
            if t.type == 'SIZE' and i + 2 < len(tokens):
                width = int(tokens[i + 1].value)
                height = int(tokens[i + 2].value)
        body = self.bind_statement_list(node.children)
        return App(title, width, height, body)
    def bind_ui_block(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds a UI element GeoNode (Layout or Widget).
        """
        head = node.head_token.type
        if head in ('COLUMN', 'ROW'):
            return Layout(
                head.lower(),
                self.bind_statement_list(node.children)
            )
        elif head in ('BUTTON', 'INPUT', 'HEADING'):
            label = node.tokens[1].value if len(node.tokens) > 1 else ""
            var_name = None
            handler = None
            for i, t in enumerate(node.tokens):
                if t.type == 'AS' and i + 1 < len(node.tokens):
                    var_name = node.tokens[i + 1].value
                if t.type == 'DO':
                    handler = self.bind_statement_list(node.children)
            return Widget(head.lower(), label, var_name, handler)
        return self.bind_node(node)
    def bind_middleware(self, node: GeoNode) -> OnRequest:
        """
        -----Purpose: Binds a BEFORE REQUEST block (middleware).
        """
        return OnRequest(
            String('__middleware__'),
            self.bind_statement_list(node.children)
        )
    def bind_use(self, node: GeoNode) -> Node:
        """
        -----Purpose: Legacy stub for 'using' keyword.
        """
        return self.bind_import_enhanced(node)
    def bind_import_enhanced(self, node: GeoNode) -> Node:
        """
        -----Purpose: Binds an IMPORT/USE block GeoNode (including Python 
                      imports).
        """
        tokens = node.tokens
        if len(tokens) > 2 and tokens[1].value.lower() == 'python':
            module = tokens[2].value
            alias = None
            if len(tokens) > 4 and tokens[3].type == 'AS':
                alias = tokens[4].value
            return PythonImport(module, alias)
        path = tokens[1].value
        if len(tokens) > 3 and tokens[2].type == 'AS':
            return ImportAs(path, tokens[3].value)
        return Import(path)
    def bind_from_import(self, node: GeoNode) -> FromImport:
        """
        -----Purpose: Binds a FROM...IMPORT block GeoNode.
        """
        tokens = node.tokens
        module = tokens[1].value
        return FromImport(module, [])
    def bind_natural_list(self, node: GeoNode) -> ListVal:
        """
        -----Purpose: Binds a natural language list ('a list of...') GeoNode.
        """
        idx = -1
        for i, t in enumerate(node.tokens):
            if t.type == 'OF':
                idx = i
                break
        
        if idx == -1:
            return ListVal([])
            
        items_tokens = node.tokens[idx + 1:]
        if not items_tokens:
            return ListVal([])
            
        # Parse items as a comma separated list of expressions
        elements_tokens = []
        current_elem = []
        for t in items_tokens:
            if t.type == 'COMMA':
                if current_elem:
                    elements_tokens.append(current_elem)
                    current_elem = []
            else:
                current_elem.append(t)
        if current_elem:
            elements_tokens.append(current_elem)
            
        items = [
            self.parse_expr_iterative(elem)
            for elem in elements_tokens if elem
        ]
        return ListVal(items)

    def bind_test(self, node: GeoNode) -> TestBlock:
        """
        -----Purpose: Binds a TEST block.
        """
        name = "unnamed test"
        if len(node.tokens) > 1:
            name_val = self.parse_expr_iterative(node.tokens[1:])
            if hasattr(name_val, 'value'):
                name = str(name_val.value)
        body = self.bind_statement_list(node.children)
        return TestBlock(name, body)

    def bind_assert(self, node: GeoNode) -> Assertion:
        """
        -----Purpose: Binds EXPECT or ENSURE assertions.
        """
        tokens = node.tokens
        to_idx = -1
        is_not = False
        op_str = "=="
        
        for i, t in enumerate(tokens):
            if t.type in ('TO', 'IS', 'BE'):
                to_idx = i
            if t.type == 'NOT':
                is_not = True
                
        if to_idx == -1:
            left = self.parse_expr_iterative(tokens[1:])
            return Assertion(left, "truthy", None)
            
        left_tokens = tokens[1:to_idx]
        if is_not:
            op_str = "!="
            
        right_tokens = []
        for t in tokens[to_idx+1:]:
            if t.type not in ('BE', 'NOT'):
                right_tokens.append(t)
                
        left = self.parse_expr_iterative(left_tokens)
        right = self.parse_expr_iterative(right_tokens) if right_tokens else None
        
        return Assertion(left, op_str, right)
    def bind_natural_set(self, node: GeoNode) -> Call:
        """
        -----Purpose: Binds a natural language set ('a unique set of...') GeoNode.
        """
        l_val = self.bind_natural_list(node)
        return Call('set', [l_val])
    def bind_serve(self, node: GeoNode) -> ServeStatic:
        """
        -----Purpose: Binds a SERVE block GeoNode (static file serving).
        """
        folder = String('public')
        url = String('/static')
        tokens = node.tokens
        for i, t in enumerate(tokens):
            if t.type == 'FROM' and i + 1 < len(tokens):
                folder = self.parse_expr_iterative([tokens[i + 1]])
            if t.type == 'AT' and i + 1 < len(tokens):
                url = self.parse_expr_iterative([tokens[i + 1]])
        return ServeStatic(folder, url)
    def bind_define(self, node: GeoNode) -> FunctionDef:
        """
        -----Purpose: Binds a DEFINE PAGE GeoNode (Web layout).
        """
        tokens = node.tokens
        name = ''
        args = []
        i = 1
        if i < len(tokens) and tokens[i].type == 'PAGE':
            i += 1
        if i < len(tokens) and tokens[i].type == 'ID':
            name = tokens[i].value
            i += 1
        if i < len(tokens) and tokens[i].type == 'USING':
            i += 1
            while i < len(tokens):
                if tokens[i].type == 'ID':
                    args.append((tokens[i].value, None, None))
                elif tokens[i].type == 'COMMA':
                    pass
                else:
                    break
                i += 1
        body = self.bind_statement_list(node.children)
        return FunctionDef(name, args, body)
    def bind_when(self, node: GeoNode) -> OnRequest:
        """
        -----Purpose: Binds a WHEN block GeoNode (HTTP route handler).
        """
        tokens = node.tokens
        path = String('/')
        for i, t in enumerate(tokens):
            if t.type == 'STRING':
                path = String(t.value)
                break
        body = self.bind_statement_list(node.children)
        return OnRequest(path, body)
    def bind_on(self, node: GeoNode) -> OnRequest:
        """
        -----Purpose: Binds an ON block GeoNode (Event handler).
        """
        tokens = node.tokens
        path = String('/')
        for t in tokens:
            if t.type == 'STRING':
                path = String(t.value)
                break
        body = self.bind_statement_list(node.children)
        return OnRequest(path, body)
    def bind_call_or_expr(self, node: GeoNode) -> Any:
        """
        -----Purpose: Binds a GeoNode to either a function Call or an expression.
        """
        tokens = node.tokens
        if len(tokens) >= 1 and tokens[0].type == 'ID':
            name = tokens[0].value
            args = []
            kwargs = []
            i = 1
            while i < len(tokens):
                t = tokens[i]
                is_attr_key = t.type in (
                    'ID', 'STRUCTURE', 'HREF', 'REL', 'NAME', 'STYLE',
                    'CONTENT', 'CHARSET', 'SRC', 'ALT', 'TYPE', 'VALUE',
                    'PLACEHOLDER', 'METHOD', 'ACTION'
                )
                is_kwarg = (
                    is_attr_key and i + 2 < len(tokens) and 
                    tokens[i + 1].type == 'ASSIGN'
                )
                if is_kwarg:
                    key = t.value
                    val_token = tokens[i + 2]
                    if val_token.type == 'STRING':
                        kwargs.append((key, String(val_token.value)))
                    elif val_token.type == 'NUMBER':
                        val = Number(
                            int(val_token.value) if '.' not in val_token.value
                            else float(val_token.value)
                        )
                        kwargs.append((key, val))
                    else:
                        kwargs.append((key, VarAccess(val_token.value)))
                    i += 3
                    continue
                elif t.type == 'STRING':
                    args.append(String(t.value))
                elif t.type == 'NUMBER':
                    val = Number(
                        int(t.value) if '.' not in t.value
                        else float(t.value)
                    )
                    args.append(val)
                elif t.type == 'ID':
                    args.append(VarAccess(t.value))
                i += 1
            body = None
            if node.children:
                body = self.bind_statement_list(node.children)
            return Call(name, args, kwargs=kwargs, body=body)
        return self.parse_expr_iterative(tokens)
    def _extract_expr_tokens(
        self, tokens: List[Token], start: int = 0
    ) -> List[Token]:
        """
        -----Purpose: Extracts a subset of tokens for expression parsing, 
                      stripping trailing colons.
        """
        end = len(tokens)
        if tokens[-1].type == 'COLON':
            end -= 1
        return tokens[start:end]
    def parse_expr_iterative(self, tokens: List[Token]) -> Optional[Node]:
        """
        -----Purpose: Shunting-yard variant to produce an AST directly from a 
                      flat list of tokens.
        """
        if not tokens:
            return None
        values: List[Node] = []
        ops: List[str] = []


        def apply_op():
            """Applies the top operator to the top two values."""
            if not ops:
                return
            op_type = ops.pop()
            if len(values) >= 2:
                right = values.pop()
                left = values.pop()
                op_map = {
                    'PLUS': '+', 'MINUS': '-', 'MUL': '*', 'DIV': '/', 
                    'MOD': '%', 'LT': '<', 'GT': '>', 'LE': '<=', 
                    'GE': '>=', 'EQ': '==', 'NEQ': '!=', 'AND': 'and', 
                    'OR': 'or', 'IS': '==', 'IN': 'in', 'NOTIN': 'not in'
                }
                op_str = op_map.get(op_type, op_type)
                values.append(BinOp(left, op_str, right))
            else:
                raise SyntaxError(
                    f"Invalid expression: missing operands for {op_type}"
                )

        def precedence(op_type):
            """Returns operator precedence level."""
            return self.precedence.get(op_type, 0)

        i = 0
        while i < len(tokens):
            t = tokens[i]
            # Unary minus: if MINUS appears at the start
            # or after an operator / open-paren / comma,
            # treat it as negation: 0 - <next value>.
            if t.type == 'MINUS':
                is_unary = (
                    i == 0 or
                    tokens[i - 1].type in (
                        'LPAREN', 'COMMA', 'ASSIGN',
                        'PLUS', 'MINUS', 'MUL', 'DIV',
                        'MOD', 'LT', 'GT', 'LE', 'GE',
                        'EQ', 'NEQ', 'AND', 'OR',
                    )
                )
                if is_unary:
                    values.append(Number(0))
                    ops.append('MINUS')
                    i += 1
                    continue
            if t.type == 'NUMBER':
                val = Number(
                    int(t.value) if '.' not in t.value else float(t.value)
                )
                values.append(val)
            elif t.type == 'STRING':
                values.append(String(t.value))
            elif t.type == 'LBRACKET':
                is_indexing = False
                if i > 0 and tokens[i - 1].type in ('ID', 'RBRACKET', 'RPAREN', 'STRING'):
                    is_indexing = True
                    
                depth = 1
                j = i + 1
                elements_tokens = []
                current_elem = []
                while j < len(tokens):
                    if tokens[j].type == 'LBRACKET':
                        depth += 1
                    elif tokens[j].type == 'RBRACKET':
                        depth -= 1
                    if depth == 0:
                        if current_elem:
                            elements_tokens.append(current_elem)
                        break
                    if tokens[j].type == 'COMMA' and depth == 1:
                        elements_tokens.append(current_elem)
                        current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                items = [
                    self.parse_expr_iterative(elem) 
                    for elem in elements_tokens if elem
                ]
                
                if is_indexing:
                    obj = values.pop() if values else None
                    if items:
                        values.append(IndexAccess(obj, items[0]))
                else:
                    values.append(ListVal(items))
                i = j
            elif t.type == 'LBRACE':
                depth = 1
                j = i + 1
                pairs_tokens = []
                current_pair = []
                while j < len(tokens):
                    if tokens[j].type == 'LBRACE':
                        depth += 1
                    elif tokens[j].type == 'RBRACE':
                        depth -= 1
                    if depth == 0:
                        if current_pair:
                            pairs_tokens.append(current_pair)
                        break
                    if tokens[j].type == 'COMMA' and depth == 1:
                        pairs_tokens.append(current_pair)
                        current_pair = []
                    else:
                        current_pair.append(tokens[j])
                    j += 1
                
                pairs = []
                for p_tokens in pairs_tokens:
                    if not p_tokens: continue
                    colon_idx = -1
                    for k, pt in enumerate(p_tokens):
                        if pt.type == 'COLON':
                            colon_idx = k
                            break
                    if colon_idx != -1:
                        key_expr = self.parse_expr_iterative(p_tokens[:colon_idx])
                        val_expr = self.parse_expr_iterative(p_tokens[colon_idx+1:])
                        if key_expr and val_expr:
                            pairs.append((key_expr, val_expr))
                
                values.append(Dictionary(pairs))
                i = j
            elif t.type == 'LIST' and i + 1 < len(tokens) and tokens[i + 1].type == 'OF':
                j = i + 2
                elements_tokens = []
                current_elem = []
                while j < len(tokens):
                    if tokens[j].type == 'COMMA':
                        if current_elem:
                            elements_tokens.append(current_elem)
                            current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                if current_elem:
                    elements_tokens.append(current_elem)
                
                items = [
                    self.parse_expr_iterative(elem)
                    for elem in elements_tokens if elem
                ]
                values.append(ListVal(items))
                i = j
                continue
            elif t.type == 'UNIQUE' and i + 2 < len(tokens) and tokens[i + 1].type == 'SET' and tokens[i + 2].type == 'OF':
                # Natural set: [a] unique set of item1, item2...
                j = i + 3
                elements_tokens = []
                current_elem = []
                while j < len(tokens):
                    if tokens[j].type == 'COMMA':
                        if current_elem:
                            elements_tokens.append(current_elem)
                            current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                if current_elem:
                    elements_tokens.append(current_elem)
                
                items = [
                    self.parse_expr_iterative(elem)
                    for elem in elements_tokens if elem
                ]
                values.append(Call('set', [ListVal(items)]))
                i = j
                continue
            elif t.type == 'ASK' and i + 1 < len(tokens) and tokens[i + 1].type == 'STRING':
                # Natural ask: ask "Question"
                values.append(Call('ask', [String(tokens[i + 1].value)]))
                i += 2
                continue
            elif t.type in (
                'ID', 'ADD', 'REMOVE', 'SAY', 'PRINT', 'ASK',
                'CONVERT', 'WAIT', 'LOAD', 'SAVE',
                'SET', 'LIST', 'SIZE', 'INT', 'STR', 'LEN', 'KEYS',
                'UPPER', 'LOWER', 'SORT',
                'CONTAINS', 'EMPTY', 'JSON', 'HTTP',
            ):
                if i + 1 < len(tokens) and tokens[i + 1].type == 'LPAREN':
                    name = t.value
                    depth = 1
                    j = i + 2
                    elements_tokens = []
                    current_elem = []
                    if j < len(tokens) and tokens[j].type == 'RPAREN':
                        i = j
                        values.append(Call(name, []))
                    else:
                        while j < len(tokens):
                            t_type = tokens[j].type
                            if t_type in ('LPAREN', 'LBRACKET', 'LBRACE'):
                                depth += 1
                            elif t_type in ('RPAREN', 'RBRACKET', 'RBRACE'):
                                depth -= 1
                            
                            if depth == 0:
                                if current_elem:
                                    elements_tokens.append(current_elem)
                                break
                            if t_type == 'COMMA' and depth == 1:
                                elements_tokens.append(current_elem)
                                current_elem = []
                            else:
                                current_elem.append(tokens[j])
                            j += 1
                        args = [
                            self.parse_expr_iterative(elem)
                            for elem in elements_tokens if elem
                        ]
                        values.append(Call(name, args))
                        i = j
                else:
                    values.append(VarAccess(t.value))
            elif t.type == 'LPAREN':
                ops.append('LPAREN')
            elif t.type == 'RPAREN':
                while ops and ops[-1] != 'LPAREN':
                    apply_op()
                if ops:
                    ops.pop()
            elif t.type in self.precedence:
                while (ops and ops[-1] != 'LPAREN' and
                       precedence(ops[-1]) >= precedence(t.type)):
                    apply_op()
                ops.append(t.type)
            i += 1
        while ops:
            apply_op()
        if len(values) > 1:
            raise SyntaxError("Invalid expression: too many operands")
        return values[0] if values else None
