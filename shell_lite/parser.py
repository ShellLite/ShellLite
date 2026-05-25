from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

from .ast_nodes import (
    Assertion,
    Assign,
    Await,
    BinOp,
    Boolean,
    Call,
    Channel,
    ClampNode,
    ClassDef,
    ConstAssign,
    CreateTable,
    Dictionary,
    Execute,
    Exit,
    FileRead,
    ForIn,
    FromImport,
    FunctionDef,
    Gather,
    If,
    Import,
    ImportAs,
    IndexAccess,
    IndexAssign,
    InsertRecord,
    Layout,
    LerpNode,
    ListComprehension,
    Listen,
    ListVal,
    Lock,
    Match,
    MaxNode,
    MinNode,
    ModelDef,
    Node,
    Number,
    OnRequest,
    Parallel,
    Print,
    PropertyAssign,
    PythonImport,
    Receive,
    Repeat,
    Return,
    Send,
    Skip,
    Slice,
    Spawn,
    Stop,
    String,
    TestBlock,
    Throw,
    Try,
    TryAlways,
    TypedAssign,
    UnaryOp,
    VarAccess,
    While,
    Widget,
)
from .lexer import Token


@dataclass
class GeoNode:
    line: int = 0
    indent_level: int = 0
    raw_text: str = ""
    head_token: Optional[Token] = None
    tokens: List[Token] = field(default_factory=list)
    children: List["GeoNode"] = field(default_factory=list)
    parent: Optional["GeoNode"] = None

    def __repr__(self):
        head_type = self.head_token.type if self.head_token else "None"
        return f"GeoNode(line={self.line}, indent={self.indent_level}, head={head_type})"


class Parser:
    source_code: Optional[str]
    legacy_tokens: Optional[List[Token]]
    tokens: List[Token]
    root_nodes: List[GeoNode]

    def __init__(self, source_or_tokens: Any = None, tokens: Optional[List[Token]] = None):
        self.loop_depth = 0

        if isinstance(source_or_tokens, str):
            self.source_code = source_or_tokens
            self.legacy_tokens = tokens
        elif isinstance(source_or_tokens, list):
            self.source_code = None
            self.legacy_tokens = source_or_tokens
        else:
            self.source_code = None
            self.legacy_tokens = tokens

        self.root_nodes = []
        self.precedence = {
            "OR": 1,
            "AND": 2,
            "NOT": 3,
            "EQ": 4,
            "NEQ": 4,
            "LT": 5,
            "GT": 5,
            "LE": 5,
            "GE": 5,
            "IS": 5,
            "IN": 5,
            "NOTIN": 5,
            "PLUS": 6,
            "MINUS": 6,
            "MUL": 7,
            "DIV": 7,
            "MOD": 7,
            "POW": 8,
            "DOT": 9,
            "LPAREN": 10,
            "LBRACKET": 10,
        }

    def parse(self) -> List[Node]:
        if self.legacy_tokens is not None and self.source_code is None:
            self.tokens = [t for t in self.legacy_tokens if t.type != "COMMENT"]
            self.topology_scan()
            return self.bind_statement_list(self.root_nodes)

        if self.source_code is None:
            return []

        flat_nodes = self.phase1_topography_scan(self.source_code)
        if not flat_nodes:
            return []

        self.root_nodes = self.phase2_topology_linking(flat_nodes)

        from .lexer import Lexer

        for node in flat_nodes:
            lexer = Lexer(node.raw_text)
            lexer.line_number = node.line
            node.tokens = lexer.tokenize_line_only()
            for t in node.tokens:
                if t.type != "NOISE":
                    node.head_token = t
                    break
            if not node.head_token and node.tokens:
                node.head_token = node.tokens[0]

        return self.bind_statement_list(self.root_nodes)

    def phase1_topography_scan(self, source: str) -> List[GeoNode]:
        nodes = []
        lines = source.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent_level = len(line) - len(line.lstrip())
            nodes.append(GeoNode(line=i + 1, indent_level=indent_level, raw_text=line))
        return nodes

    def phase2_topology_linking(self, nodes: List[GeoNode]) -> List[GeoNode]:
        if not nodes:
            return []
        root = GeoNode(0, -1, "")
        stack = [root]
        for node in nodes:
            while node.indent_level <= stack[-1].indent_level:
                stack.pop()
            node.parent = stack[-1]
            stack[-1].children.append(node)
            stack.append(node)
        return root.children

    def topology_scan(self):
        current_node: Optional[GeoNode] = None
        last_line_node: Optional[GeoNode] = None
        block_stack: List[GeoNode] = []
        for token in self.tokens:
            if token.type == "EOF":
                break
            if token.type == "INDENT":
                p_push = current_node if current_node else last_line_node
                if p_push:
                    block_stack.append(p_push)
                current_node = None
                continue
            if token.type == "DEDENT":
                if block_stack:
                    block_stack.pop()
                continue
            if token.type == "NEWLINE":
                last_line_node = current_node
                current_node = None
                continue
            if current_node is None:
                current_node = GeoNode(
                    line=token.line, indent_level=len(block_stack), raw_text="", head_token=token, tokens=[token]
                )
                if block_stack:
                    parent = block_stack[-1]
                    parent.children.append(current_node)
                    current_node.parent = parent
                else:
                    self.root_nodes.append(current_node)
            else:
                current_node.tokens.append(token)

    def bind_statement_list(self, geo_nodes: List[GeoNode]) -> List[Node]:
        ast_nodes: List[Node] = []
        i = 0
        while i < len(geo_nodes):
            geo_node = geo_nodes[i]

            # Find first non-noise token for dispatch
            effective_head = geo_node.head_token
            for t in geo_node.tokens:
                if t.type != "NOISE":
                    effective_head = t
                    break

            if effective_head is None:
                raise SyntaxError(f"Unexpected empty statement at line {geo_node.line}")
            head_type = effective_head.type

            if head_type == "IF":
                if_node = self.bind_if(geo_node)
                j = i + 1
                curr = if_node
                while j < len(geo_nodes):
                    next_geo = geo_nodes[j]

                    next_effective_head = next_geo.head_token
                    for t in next_geo.tokens:
                        if t.type != "NOISE":
                            next_effective_head = t
                            break

                    if next_effective_head is None:
                        j += 1
                        continue

                    if next_effective_head.type == "ELIF":
                        elif_node = self.bind_if(next_geo)
                        curr.else_body = [elif_node]
                        curr = elif_node
                        j += 1
                    elif next_effective_head.type == "ELSE":
                        curr.else_body = self.bind_statement_list(next_geo.children)
                        j += 1
                        break
                    else:
                        break
                ast_nodes.append(if_node)
                i = j
                continue
            if head_type == "TRY":
                try_body = self.bind_statement_list(geo_node.children)
                catch_body: List[Node] = []
                catch_var = "e"
                always_body: Optional[List[Node]] = None
                j = i + 1
                while j < len(geo_nodes):
                    next_geo = geo_nodes[j]

                    next_effective_head = next_geo.head_token
                    for t in next_geo.tokens:
                        if t.type != "NOISE":
                            next_effective_head = t
                            break

                    if next_effective_head is None:
                        j += 1
                        continue

                    if next_effective_head.type == "CATCH":
                        if len(next_geo.tokens) > 1:
                            catch_var = next_geo.tokens[1].value
                        catch_body = self.bind_statement_list(next_geo.children)
                        j += 1
                    elif next_effective_head.type == "ALWAYS":
                        always_body = self.bind_statement_list(next_geo.children)
                        j += 1
                    else:
                        break
                if always_body is not None:
                    ast_nodes.append(TryAlways(try_body, catch_var, catch_body, always_body))
                else:
                    ast_nodes.append(Try(try_body, catch_var, catch_body))
                i = j
                continue

            ast_node = self.bind_node(geo_node)
            if ast_node:
                ast_nodes.append(ast_node)
            i += 1
        return ast_nodes

    def _set_node_loc(self, ast_node: Optional[Node], geo_node: GeoNode) -> Optional[Node]:
        """Helper to set location on an AST node from a GeoNode."""
        if not ast_node or not isinstance(ast_node, Node):
            return ast_node
        ast_node.line = geo_node.line
        if geo_node.head_token is not None:
            ast_node.col = geo_node.head_token.column
        # Determine end line/col from children or tokens
        if geo_node.children:
            last_child = geo_node.children[-1]
            ast_node.end_line = last_child.line
            ast_node.end_col = 999
        elif geo_node.tokens:
            last_tok = geo_node.tokens[-1]
            ast_node.end_line = last_tok.line
            ast_node.end_col = last_tok.column + len(str(last_tok.value))
        return ast_node

    def bind_node(self, node: GeoNode) -> Optional[Node]:
        # Find first non-noise token for dispatch
        effective_head = node.head_token
        for t in node.tokens:
            if t.type != "NOISE":
                effective_head = t
                break

        if effective_head is None:
            return None

        head_type = effective_head.type
        bind_map = {
            "IF": self.bind_if,
            "WHILE": self.bind_while,
            "FOR": self.bind_for,
            "LOOP": self.bind_for,
            "REPEAT": self.bind_repeat,
            "FOREVER": self.bind_forever,
            "USE": self.bind_use,
            "SERVE": self.bind_dsl_lowering,
            "DEFINE": self.bind_define,
            "STRUCTURE": self.bind_structure,
            "WHEN": self.bind_dsl_lowering,
            "DB": self.bind_dsl_lowering,
            "TRY": self.bind_try,
            "UNLESS": self.bind_unless,
            "UNTIL": self.bind_until,
            "ON": self.bind_dsl_lowering,
            "FUNCTION": self.bind_func,
            "TO": self.bind_func,
            "PRINT": self.bind_print,
            "SAY": self.bind_print,
            "MAKE": self.bind_assignment,
            "CONST": self.bind_const,
            "RETURN": self.bind_return,
            "ALERT": self.bind_dsl_lowering,
            "PROMPT": self.bind_dsl_lowering,
            "CONFIRM": self.bind_dsl_lowering,
            "EXECUTE": self.bind_dsl_lowering,
            "EXIT": self.bind_exit,
            "STOP": self.bind_stop,
            "SKIP": self.bind_skip,
            "ERROR": self.bind_dsl_lowering,
            "SPAWN": self.bind_spawn,
            "AWAIT": self.bind_await,
            "EVERY": self.bind_dsl_lowering,
            "AFTER": self.bind_dsl_lowering,
            "IN": self.bind_dsl_lowering,
            "WRITE": self.bind_dsl_lowering,
            "APPEND": self.bind_dsl_lowering,
            "READ": self.bind_dsl_lowering,
            "COPY": self.bind_dsl_lowering,
            "PASTE": self.bind_dsl_lowering,
            "CLIPBOARD": self.bind_dsl_lowering,
            "CSV": self.bind_dsl_lowering,
            "COMPRESS": self.bind_dsl_lowering,
            "EXTRACT": self.bind_dsl_lowering,
            "PRESS": self.bind_dsl_lowering,
            "TYPE": self.bind_dsl_lowering,
            "CLICK": self.bind_dsl_lowering,
            "NOTIFY": self.bind_dsl_lowering,
            "DOWNLOAD": self.bind_dsl_lowering,
            "APP": self.bind_dsl_lowering,
            "IMPORT": self.bind_import_enhanced,
            "FROM": self.bind_from_import,
            "SET": self.bind_expression_statement,
            "ADD": self.bind_add,
            "INCREMENT": self.bind_natural_math,
            "DECREMENT": self.bind_natural_math,
            "PUT": self.bind_expression_statement,
            "PUSH": self.bind_expression_statement,
            "JSON": self.bind_expression_statement,
            "HTTP": self.bind_expression_statement,
            "INT": self.bind_expression_statement,
            "STR": self.bind_expression_statement,
            "LEN": self.bind_expression_statement,
            "KEYS": self.bind_expression_statement,
            "REMOVE": self.bind_remove,
            "TEST": self.bind_test,
            "EXPECT": self.bind_assert,
            "ENSURE": self.bind_assert,
            "PARALLEL": self.bind_parallel,
            "GATHER": self.bind_expression_statement,
            "LOCK": self.bind_lock,
            "CHANNEL": self.bind_expression_statement,
            "SEND": self.bind_send,
            "RECEIVE": self.bind_expression_statement,
            "MODEL": self.bind_dsl_lowering,
            "CREATE": self.bind_dsl_lowering,
            "INSERT": self.bind_dsl_lowering,
            "FIND": self.bind_dsl_lowering,
            "UPDATE": self.bind_dsl_lowering,
            "DELETE": self.bind_dsl_lowering,
            "START": self.bind_dsl_lowering,
        }

        if head_type in bind_map:
            ast_node = bind_map[head_type](node)
            return self._set_node_loc(ast_node, node)

        if head_type == "BEFORE" and len(node.tokens) > 1:
            if node.tokens[1].type == "REQUEST":
                ast_node = self.bind_middleware(node)
                return self._set_node_loc(ast_node, node)

        if head_type in (
            "ID",
            "COUNT",
            "MAX",
            "MIN",
            "LERP",
            "CLAMPED",
            "BUTTON",
            "HEADING",
            "PARAGRAPH",
            "IMAGE",
            "START",
            "SERVER",
            "INPUT",
        ):
            if node.head_token is not None:
                val = node.head_token.value.lower()
                if val == "a" and len(node.tokens) > 1:
                    t1 = node.tokens[1].type
                    if t1 == "LIST":
                        ast_node = self.bind_natural_list(node)
                        return self._set_node_loc(ast_node, node)
                    if t1 == "UNIQUE" and len(node.tokens) > 2:
                        if node.tokens[2].type == "SET":
                            ast_node = self.bind_natural_set(node)
                            return self._set_node_loc(ast_node, node)

            # Check for regular assignment (x = 1) or index assignment (x[0] = 1)
            assign_idx = -1
            first_non_noise_idx = -1
            for k, tok in enumerate(node.tokens):
                if tok.type != "NOISE" and first_non_noise_idx == -1:
                    first_non_noise_idx = k
                if tok.type in ("ASSIGN", "IS", "BE", "PLUSEQ", "MINUSEQ", "MULEQ", "DIVEQ", "MODEQ"):
                    assign_idx = k
                    break

            if assign_idx != -1:
                is_real_assignment = False
                if assign_idx == first_non_noise_idx + 1:
                    is_real_assignment = True
                elif assign_idx == first_non_noise_idx + 2 and node.tokens[first_non_noise_idx].type == "MAKE":
                    is_real_assignment = True
                elif (
                    assign_idx == first_non_noise_idx + 3
                    and len(node.tokens) > first_non_noise_idx + 1
                    and node.tokens[first_non_noise_idx + 1].type == "AS"
                ):
                    is_real_assignment = True
                elif any(t.type in ("LBRACKET", "DOT") for t in node.tokens[first_non_noise_idx:assign_idx]):
                    is_real_assignment = True

                if is_real_assignment:
                    if any(t.type in ("LBRACKET", "DOT") for t in node.tokens[first_non_noise_idx:assign_idx]):
                        ast_node = self.bind_complex_assignment(node, assign_idx)
                    else:
                        ast_node = self.bind_assignment(node)
                    return self._set_node_loc(ast_node, node)

            if any(t.type == "DOT" for t in node.tokens):
                ast_node = self.bind_expression_statement(node)
            else:
                ast_node = self.bind_call_or_expr(node)
            return self._set_node_loc(ast_node, node)

        ast_node = self.bind_expression_statement(node)
        return self._set_node_loc(ast_node, node)

    def bind_expression_statement(self, node: GeoNode) -> Optional[Node]:
        return self.parse_expr_iterative(node.tokens, node.children)

    def peek_type(self, node: GeoNode, offset: int) -> str:
        if offset < len(node.tokens):
            return node.tokens[offset].type
        return ""

    def bind_if(self, node: GeoNode) -> If:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        if condition is None:
            raise SyntaxError(f"Missing condition for 'if' statement at line {node.line}")
        body = self.bind_statement_list(node.children)
        return If(condition, body, None)

    def bind_unless(self, node: GeoNode) -> Node:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        if condition is None:
            raise SyntaxError(f"Missing condition for 'unless' statement at line {node.line}")
        body = self.bind_statement_list(node.children)
        return If(UnaryOp("not", condition), body)

    def bind_until(self, node: GeoNode) -> Node:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        if condition is None:
            raise SyntaxError(f"Missing condition for 'until' statement at line {node.line}")
        body = self.bind_statement_list(node.children)
        return While(UnaryOp("not", condition), body)

    def bind_try(self, node: GeoNode) -> Try:
        try_body = self.bind_statement_list(node.children)
        # Default fallback if catch/always aren't grouped by bind_statement_list
        return Try(try_body, "e", [])

    def bind_structure(self, node: GeoNode) -> ClassDef:
        tokens = node.tokens
        name = tokens[1].value
        parent = None
        properties: List[tuple[str, Optional[Node]]] = []
        methods: List[FunctionDef] = []

        # Check for extends
        extends_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "EXTENDS" or t.type == "LPAREN":
                extends_idx = i
                break
        if extends_idx != -1 and extends_idx + 1 < len(tokens):
            parent = tokens[extends_idx + 1].value

        # Check for inline 'has'
        has_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "HAS":
                has_idx = i
                break
        if has_idx != -1:
            i = has_idx + 1
            while i < len(tokens) and tokens[i].type != "COLON":
                if tokens[i].type == "ID":
                    properties.append((tokens[i].value, None))
                i += 1

        for child in node.children:
            head_tok = child.head_token
            if head_tok is None:
                continue
            head = head_tok.type
            if head == "HAS" or head == "ID":
                start = 1 if head == "HAS" else 0
                prop_name = child.tokens[start].value
                default_val = None
                assign_idx = -1
                for i, t in enumerate(child.tokens):
                    if t.type == "ASSIGN":
                        assign_idx = i
                        break
                if assign_idx != -1:
                    default_val = self.parse_expr_iterative(child.tokens[assign_idx + 1 :])
                properties.append((prop_name, default_val))
            elif head == "TO" or head == "FUNCTION":
                methods.append(self.bind_func(child))
        return ClassDef(name, properties, methods, parent)

    def bind_while(self, node: GeoNode) -> While:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        condition = self.parse_expr_iterative(expr_tokens)
        if condition is None:
            raise SyntaxError(f"Missing condition for 'while' statement at line {node.line}")
        
        self.loop_depth += 1

        try:
            body = self.bind_statement_list(node.children)
        finally:
            self.loop_depth -= 1

        return While(condition, body)

    def bind_repeat(self, node: GeoNode) -> Node:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        if expr_tokens and expr_tokens[-1].type == "TIMES":
            expr_tokens.pop()
        count = self.parse_expr_iterative(expr_tokens)
        if count is None:
            raise SyntaxError(f"Missing count for 'repeat' statement at line {node.line}")
        
        self.loop_depth += 1

        try:
            body = self.bind_statement_list(node.children)
        finally:
            self.loop_depth -= 1

        return Repeat(count, body)

    def bind_forever(self, node: GeoNode) -> Node:
        self.loop_depth += 1

        try:
            body = self.bind_statement_list(node.children)
        finally:
            self.loop_depth -= 1

        return While(Boolean(True), body)

    def bind_for(self, node: GeoNode) -> Optional[Node]:
        if len(node.tokens) < 3:
            return None

        start_idx = 1
        if node.tokens[1].type == "EACH":
            start_idx = 2
            if len(node.tokens) < 4:
                return None

        var_name = node.tokens[start_idx].value
        in_idx = -1
        for i, t in enumerate(node.tokens):
            if t.type == "IN":
                in_idx = i
                break
        if in_idx == -1:
            if node.head_token is not None and node.head_token.type == "LOOP":
                if node.tokens[-1].type == "TIMES":
                    e_tokens = self._extract_expr_tokens(node.tokens, 1)
                    e_tokens.pop()
                    count = self.parse_expr_iterative(e_tokens)
                    if count is None:
                        raise SyntaxError(f"Missing count for 'loop' statement at line {node.line}")
                    self.loop_depth += 1

                    try:
                        body = self.bind_statement_list(node.children)
                    finally:
                        self.loop_depth -= 1

                    return Repeat(count, body)
            return None
        self.loop_depth += 1
        try:
            body = self.bind_statement_list(node.children)
        finally:
            self.loop_depth -= 1
        if node.tokens[in_idx + 1].type == "RANGE":
            args_tokens = self._extract_expr_tokens(node.tokens, in_idx + 2)
            filtered = [t for t in args_tokens if t.type not in ("LPAREN", "RPAREN", "COMMA")]
            range_args: List[Node] = []
            for t in filtered:
                val: Optional[Node] = None
                if t.type == "NUMBER":
                    val = Number(int(t.value) if "." not in t.value else float(t.value))
                elif t.type == "STRING":
                    val = String(t.value)
                elif t.type == "ID":
                    val = VarAccess(t.value)
                else:
                    msg = f"Invalid token '{t.value}' in range expression."
                    raise SyntaxError(msg)
                if val:
                    range_args.append(val)
            iterable: Node = Call("range", range_args)
        else:
            iter_tokens = self._extract_expr_tokens(node.tokens, in_idx + 1)
            res_iter = self.parse_expr_iterative(iter_tokens)
            if res_iter is None:
                raise SyntaxError(f"Missing iterable for 'for' loop at line {node.line}")
            iterable = res_iter
        return ForIn(var_name, iterable, body)

    def bind_print(self, node: GeoNode) -> Print:
        tokens = node.tokens[1:]
        style = None
        color = None
        i = 0
        if i < len(tokens) and tokens[i].type == "IN":
            if i + 1 < len(tokens) and tokens[i + 1].type in ("RED", "GREEN", "BLUE", "YELLOW", "CYAN", "MAGENTA"):
                color = tokens[i + 1].value
                i += 2
        if i < len(tokens) and tokens[i].type == "BOLD":
            style = "bold"
            i += 1
        if i < len(tokens) and tokens[i].type in ("RED", "GREEN", "BLUE", "YELLOW", "CYAN", "MAGENTA"):
            color = tokens[i].value
            i += 1

        expr_tokens = self._extract_expr_tokens(tokens, start=i)
        expr = self.parse_expr_iterative(expr_tokens)
        if expr is None:
            raise SyntaxError(f"Missing expression for 'say'/'print' at line {node.line}")
        return Print(expr, style=style, color=color)

    def bind_return(self, node: GeoNode) -> Return:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        if node.children:
            for child in node.children:
                expr_tokens.extend(child.tokens)
        expr = self.parse_expr_iterative(expr_tokens)
        if expr is None:
            raise SyntaxError(f"Missing expression for 'return' at line {node.line}")
        return Return(expr)

    def bind_assignment(self, node: GeoNode) -> Union[Assign, TypedAssign]:
        tokens = node.tokens

        # Find assignment operator while ignoring noise
        assign_idx = -1
        for i, t in enumerate(tokens):
            if t.type in ("ASSIGN", "IS", "BE", "PLUSEQ", "MINUSEQ", "MULEQ", "DIVEQ", "MODEQ"):
                assign_idx = i
                break

        if assign_idx == -1:
            raise SyntaxError(f"Assignment operator missing at line {node.line}")

        # Find variable name (first ID before assignment)
        name = None
        for i in range(assign_idx):
            if tokens[i].type == "ID":
                name = tokens[i].value
                break

        if not name:
            raise SyntaxError(f"LHS of assignment must contain an identifier at line {node.line}. Tokens: {tokens}")

        # Check for type hint: ID AS ID ASSIGN
        type_hint = None
        for i in range(assign_idx - 2):
            if tokens[i].type == "ID" and tokens[i + 1].type == "AS" and tokens[i + 2].type == "ID":
                type_hint = tokens[i + 2].value.lower()
                break

        expr_tokens = tokens[assign_idx + 1 :]
        if node.children:
            for child in node.children:
                expr_tokens.extend(child.tokens)
        # print(f"DEBUG bind_assignment: expr_tokens={[t.value for t in expr_tokens]}")
        value = self.parse_expr_iterative(expr_tokens, node.children)
        if value is None:
            raise SyntaxError(f"Missing value in assignment at line {node.line}")

        op_tok = tokens[assign_idx]
        if op_tok.type in ("PLUSEQ", "MINUSEQ", "MULEQ", "DIVEQ", "MODEQ"):
            op_map = {"PLUSEQ": "+", "MINUSEQ": "-", "MULEQ": "*", "DIVEQ": "/", "MODEQ": "%"}
            op_str = op_map[op_tok.type]
            left_node = VarAccess(name)
            if node.head_token is not None:
                left_node.line = node.head_token.line
                left_node.col = node.head_token.column
            value = BinOp(left_node, op_str, value)
            value.line = op_tok.line
            value.col = op_tok.column

        if type_hint:
            return TypedAssign(name, type_hint, value)
        return Assign(name, value)

    def bind_const(self, node: GeoNode) -> ConstAssign:
        tokens = node.tokens
        if len(tokens) < 4:
            raise SyntaxError(f"Invalid constant assignment syntax at line {node.line}")

        name = tokens[1].value
        assign_idx = -1
        for i in range(2, len(tokens)):
            if tokens[i].type in ("ASSIGN", "IS", "BE"):
                assign_idx = i
                break

        if assign_idx == -1:
            raise SyntaxError(f"Assignment operator missing in constant assignment at line {node.line}")

        expr_tokens = tokens[assign_idx + 1 :]
        value = self.parse_expr_iterative(expr_tokens)
        if value is None:
            raise SyntaxError(f"Missing value for constant '{name}' at line {node.line}")
        return ConstAssign(name, value)

    def bind_complex_assignment(self, node: GeoNode, assign_idx: int) -> Node:
        lhs_tokens = node.tokens[:assign_idx]
        value_tokens = node.tokens[assign_idx + 1 :]

        lhs_expr = self.parse_expr_iterative(lhs_tokens)
        value_expr = self.parse_expr_iterative(value_tokens)
        if lhs_expr is None:
            raise SyntaxError(f"Invalid LHS for complex assignment at line {node.line}")
        if value_expr is None:
            raise SyntaxError(f"Missing value for complex assignment at line {node.line}")

        op_tok = node.tokens[assign_idx]
        if op_tok.type in ("PLUSEQ", "MINUSEQ", "MULEQ", "DIVEQ", "MODEQ"):
            op_map = {"PLUSEQ": "+", "MINUSEQ": "-", "MULEQ": "*", "DIVEQ": "/", "MODEQ": "%"}
            op_str = op_map[op_tok.type]
            value_expr = BinOp(lhs_expr, op_str, value_expr)
            value_expr.line = op_tok.line
            value_expr.col = op_tok.column

        if isinstance(lhs_expr, IndexAccess):
            return IndexAssign(lhs_expr.obj, lhs_expr.index, value_expr)
        if isinstance(lhs_expr, BinOp) and lhs_expr.op == ".":
            # self.source -> BinOp(left=VarAccess(self), op='.', right=VarAccess(source))
            instance_name = lhs_expr.left.name if hasattr(lhs_expr.left, "name") else str(lhs_expr.left)
            property_name = lhs_expr.right.name if hasattr(lhs_expr.right, "name") else str(lhs_expr.right)
            return PropertyAssign(instance_name, property_name, value_expr)

        return Assign(str(lhs_expr), value_expr)

    def bind_dsl_lowering(self, node: GeoNode) -> Node:
        """Lowers DSL keywords (db, web, gui) into standard library Call nodes."""
        tokens = node.tokens
        head = tokens[0].type

        if head == "DB":
            op = tokens[1].value.lower() if len(tokens) > 1 else "query"
            args: List[Node] = []
            if len(tokens) > 2:
                res_arg = self.parse_expr_iterative(tokens[2:])
                if res_arg:
                    args.append(res_arg)
            return Call(f"std_db_{op}", args)

        if head == "ON" or (head == "WHEN" and any(t.type == "VISITS" for t in tokens)):
            # when someone visits "/path" -> on_visit("/", handler)
            path = String("/")
            for t in tokens:
                if t.type == "STRING":
                    path = String(t.value)
                    break
            body = self.bind_statement_list(node.children)
            return Call("std_web_on_request", [path], body=body)

        if head == "SERVE":
            # serve files from "public" at "/static" -> serve_static("/static", "public")
            folder: Node = String("public")
            url: Node = String("/static")
            for i, t in enumerate(tokens):
                if t.type == "FROM" and i + 1 < len(tokens):
                    res_f = self.parse_expr_iterative([tokens[i + 1]])
                    if res_f:
                        folder = res_f
                if t.type == "AT" and i + 1 < len(tokens):
                    res_u = self.parse_expr_iterative([tokens[i + 1]])
                    if res_u:
                        url = res_u
            return Call("std_web_serve_static", [url, folder])

        if head == "START" and len(tokens) > 1:
            if tokens[1].type == "SERVER":
                # start server on port 8080 -> listen(8080)
                port: Node = Number(8080)
                for i, t in enumerate(tokens):
                    if t.type == "PORT" and i + 1 < len(tokens):
                        res_p = self.parse_expr_iterative([tokens[i + 1]])
                        if res_p:
                            port = res_p
                return Call("std_web_listen", [port])
            if tokens[1].type == "ID" and tokens[1].value.lower() == "website":
                return Call("std_web_listen", [Number(8080)])

        if head in ("WRITE", "APPEND", "READ"):
            # write content to file path -> std_io_write(path, content)
            op = head.lower()
            if head == "READ":
                res_r = self.parse_expr_iterative(tokens[1:])
                if res_r is None:
                    raise SyntaxError(f"Missing path for 'read' statement at line {node.line}")
                return Call("std_io_read", [res_r])

            res_c = self.parse_expr_iterative([tokens[1]])
            if res_c is None:
                raise SyntaxError(f"Missing content for '{op}' statement at line {node.line}")
            content = res_c
            target_path: Node = String("output.txt")
            for i, t in enumerate(tokens):
                if t.type == "FILE" and i + 1 < len(tokens):
                    res_tp = self.parse_expr_iterative(tokens[i + 1 :])
                    if res_tp:
                        target_path = res_tp
            return Call(f"std_io_{op}", [target_path, content])

        if head == "ERROR":
            res_e = self.parse_expr_iterative(tokens[1:])
            if res_e is None:
                raise SyntaxError(f"Missing message for 'error' statement at line {node.line}")
            return Throw(res_e)

        if head == "EXECUTE":
            res_ex = self.parse_expr_iterative(tokens[1:])
            if res_ex is None:
                raise SyntaxError(f"Missing command for 'execute' statement at line {node.line}")
            return Execute(res_ex)

        if head == "MODEL":
            name = tokens[1].value
            fields = []
            for child in node.children:
                if len(child.tokens) >= 2:
                    fields.append((child.tokens[0].value, child.tokens[1].value))
            return ModelDef(name, fields)

        if head == "CREATE" and len(tokens) > 1 and tokens[1].type == "TABLE":
            return CreateTable(tokens[2].value)

        if head == "INSERT" and len(tokens) > 1 and tokens[1].type == "INTO":
            model_name = tokens[2].value
            values: List[tuple[str, Node]] = []
            for child in node.children:
                k = child.tokens[0].value
                v = self.parse_expr_iterative(child.tokens[1:])
                if v:
                    values.append((k, v))
            return InsertRecord(model_name, values)

        # Fallback for other keywords
        return self.bind_call_or_expr(node)

    def bind_expression_stmt(self, node: GeoNode) -> Optional[Node]:
        return self.parse_expr_iterative(node.tokens)

    def bind_start(self, node: GeoNode) -> Listen:
        return Listen(Number(8080))

    def bind_listen(self, node: GeoNode) -> Listen:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        if expr_tokens and expr_tokens[0].type == "PORT":
            expr_tokens.pop(0)
        port = self.parse_expr_iterative(expr_tokens)
        if port is None:
            raise SyntaxError(f"Missing port for 'listen' statement at line {node.line}")
        return Listen(port)

    def bind_func(self, node: GeoNode) -> FunctionDef:
        start = 1
        if node.tokens[0].type == "DEFINE":
            start = 2
        name = node.tokens[start].value
        args: List[tuple[str, Optional[Node], Optional[str]]] = []
        token_slice = node.tokens[start + 1 :]
        i = 0
        while i < len(token_slice):
            t = token_slice[i]
            if t.type == "USING" or t.type == "COMMA":
                i += 1
                continue
            if t.type == "COLON":
                break
            if t.type in ("ID", "FOLDER", "FILE", "PORT", "SERVER", "NAME", "TYPE", "VALUE", "CONTENT"):
                arg_name = t.value
                # Check for `arg as type` pattern
                if i + 2 < len(token_slice) and token_slice[i + 1].type == "AS" and token_slice[i + 2].type == "ID":
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

    def bind_natural_math(self, node: GeoNode) -> Node:
        tokens = node.tokens
        head = tokens[0].type
        by_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "BY":
                by_idx = i
                break

        if by_idx != -1:
            var_name = tokens[1].value
            val = self.parse_expr_iterative(tokens[by_idx + 1 :])
            if val is None:
                raise SyntaxError(f"Missing value for '{head}' statement at line {node.line}")
            op = "+" if head == "INCREMENT" else "-"
            return Assign(var_name, BinOp(VarAccess(var_name), op, val))

        res_expr = self.bind_expression_statement(node)
        if res_expr is None:
            raise SyntaxError(f"Invalid math expression at line {node.line}")
        return res_expr

    def bind_add(self, node: GeoNode) -> Node:
        tokens = node.tokens
        to_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "TO":
                to_idx = i
                break
        if to_idx != -1:
            item = self.parse_expr_iterative(tokens[1:to_idx])
            target = self.parse_expr_iterative(tokens[to_idx + 1 :])
            if item is None or target is None:
                raise SyntaxError(f"Malformed 'add' statement at line {node.line}")
            return Call("add", [target, item])

        res_expr = self.bind_expression_statement(node)
        if res_expr is None:
            raise SyntaxError(f"Invalid 'add' expression at line {node.line}")
        return res_expr

    def bind_exit(self, node: GeoNode) -> Exit:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        code = self.parse_expr_iterative(expr_tokens) if expr_tokens else None
        return Exit(code)

    def bind_stop(self, node: GeoNode) -> Stop:
        if self.loop_depth <= 0:
            raise SyntaxError(f"'Stop' statement used outside a Loop at line {node.line}")
        return Stop()

    def bind_skip(self, node: GeoNode) -> Skip:
        if self.loop_depth <= 0:
            raise SyntaxError(f"'Skip' statement used outside a Loop at line {node.line}")
        return Skip()

    def bind_spawn(self, node: GeoNode) -> Spawn:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        call = self.parse_expr_iterative(expr_tokens)
        if call is None:
            raise SyntaxError(f"Missing call for 'spawn' statement at line {node.line}")
        return Spawn(call)

    def bind_await(self, node: GeoNode) -> Await:
        expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
        task = self.parse_expr_iterative(expr_tokens)
        if task is None:
            raise SyntaxError(f"Missing task for 'await' statement at line {node.line}")
        return Await(task)

    def bind_remove(self, node: GeoNode) -> Node:
        tokens = node.tokens
        from_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "FROM":
                from_idx = i
                break

        if from_idx != -1:
            item = self.parse_expr_iterative(tokens[1:from_idx])
            target = self.parse_expr_iterative(tokens[from_idx + 1 :])
            if item is None or target is None:
                raise SyntaxError(f"Malformed 'remove' statement at line {node.line}")
            return Call("remove", [target, item])

        res_expr = self.bind_expression_statement(node)
        if res_expr is None:
            raise SyntaxError(f"Invalid 'remove' expression at line {node.line}")
        return res_expr

    def bind_ui_block(self, node: GeoNode) -> Node:
        head_tok = node.head_token
        if head_tok is None:
            return self.bind_node(node)  # type: ignore
        head = head_tok.type
        if head in ("COLUMN", "ROW"):
            return Layout(head.lower(), self.bind_statement_list(node.children))
        elif head in ("BUTTON", "INPUT", "HEADING"):
            label = node.tokens[1].value if len(node.tokens) > 1 else ""
            var_name = None
            handler = None
            for i, t in enumerate(node.tokens):
                if t.type == "AS" and i + 1 < len(node.tokens):
                    var_name = node.tokens[i + 1].value
                if t.type == "DO":
                    handler = self.bind_statement_list(node.children)
            return Widget(head.lower(), label, var_name, handler)
        return self.bind_node(node)  # type: ignore

    def bind_middleware(self, node: GeoNode) -> OnRequest:
        return OnRequest(String("__middleware__"), self.bind_statement_list(node.children))

    def bind_use(self, node: GeoNode) -> Node:
        return self.bind_import_enhanced(node)

    def bind_import_enhanced(self, node: GeoNode) -> Node:
        tokens = node.tokens
        if len(tokens) > 2 and tokens[1].value.lower() == "python":
            module = tokens[2].value
            alias = None
            if len(tokens) > 4 and tokens[3].type == "AS":
                alias = tokens[4].value
            return PythonImport(module, alias)
        path = tokens[1].value
        if len(tokens) > 3 and tokens[2].type == "AS":
            return ImportAs(path, tokens[3].value)
        return Import(path)

    def bind_from_import(self, node: GeoNode) -> FromImport:
        tokens = node.tokens
        module = tokens[1].value
        names: List[tuple[str, Optional[str]]] = []
        import_idx = -1
        for i, t in enumerate(tokens):
            if t.type == "IMPORT":
                import_idx = i
                break

        if import_idx != -1:
            name_tokens = tokens[import_idx + 1 :]
            i = 0
            while i < len(name_tokens):
                t = name_tokens[i]
                if t.type == "ID":
                    name = t.value
                    alias = None
                    if i + 2 < len(name_tokens) and name_tokens[i + 1].type == "AS" and name_tokens[i + 2].type == "ID":
                        alias = name_tokens[i + 2].value
                        i += 3
                    else:
                        i += 1
                    names.append((name, alias))
                else:
                    i += 1

        return FromImport(module, names)

    def bind_natural_list(self, node: GeoNode) -> ListVal:
        idx = -1
        for i, t in enumerate(node.tokens):
            if t.type == "OF":
                idx = i
                break

        if idx == -1:
            return ListVal([])

        items_tokens = node.tokens[idx + 1 :]
        if not items_tokens:
            return ListVal([])

        # Parse items as a comma separated list of expressions
        elements_tokens: List[List[Token]] = []
        current_elem: List[Token] = []
        for t in items_tokens:
            if t.type == "COMMA":
                if current_elem:
                    elements_tokens.append(current_elem)
                    current_elem = []
            else:
                current_elem.append(t)
        if current_elem:
            elements_tokens.append(current_elem)

        items: List[Node] = []
        for elem in elements_tokens:
            if elem:
                res = self.parse_expr_iterative(elem)
                if res:
                    items.append(res)
        return ListVal(items)

    def bind_test(self, node: GeoNode) -> TestBlock:
        name = "unnamed test"
        if len(node.tokens) > 1:
            name_val = self.parse_expr_iterative(node.tokens[1:])
            if name_val and hasattr(name_val, "value"):
                name = str(name_val.value)
        body = self.bind_statement_list(node.children)
        return TestBlock(name, body)

    def bind_assert(self, node: GeoNode) -> Assertion:
        tokens = node.tokens
        to_idx = -1
        is_not = False
        op_str = "=="

        for i, t in enumerate(tokens):
            if t.type in ("TO", "IS", "BE"):
                to_idx = i
            if t.type == "NOT":
                is_not = True

        if to_idx == -1:
            left_res = self.parse_expr_iterative(tokens[1:])
            if left_res is None:
                raise SyntaxError(f"Missing expression for assertion at line {node.line}")
            return Assertion(left_res, "truthy", None)

        left_tokens = tokens[1:to_idx]
        if is_not:
            op_str = "!="

        right_tokens = []
        for t in tokens[to_idx + 1 :]:
            if t.type not in ("BE", "NOT"):
                right_tokens.append(t)

        left = self.parse_expr_iterative(left_tokens)
        if left is None:
            raise SyntaxError(f"Missing LHS for assertion at line {node.line}")
        right = self.parse_expr_iterative(right_tokens) if right_tokens else None

        return Assertion(left, op_str, right)

    def bind_parallel(self, node: GeoNode) -> Parallel:
        body = self.bind_statement_list(node.children)
        return Parallel(body)

    def bind_lock(self, node: GeoNode) -> Lock:
        name = "default"
        if len(node.tokens) > 1:
            name_val = self.parse_expr_iterative(node.tokens[1:])
            if name_val and hasattr(name_val, "value"):
                name = str(name_val.value)
        body = self.bind_statement_list(node.children)
        return Lock(name, body)

    def bind_send(self, node: GeoNode) -> Send:
        tokens = node.tokens[1:]
        if len(tokens) < 2:
            raise SyntaxError(f"send requires a channel and a value at line {node.line}")
        channel = self.parse_expr_iterative([tokens[0]])
        value = self.parse_expr_iterative(tokens[1:])
        if channel is None or value is None:
            raise SyntaxError(f"Malformed 'send' statement at line {node.line}")
        return Send(channel, value)

    def bind_natural_set(self, node: GeoNode) -> Call:
        l_val = self.bind_natural_list(node)
        return Call("set", [l_val])

    def bind_define(self, node: GeoNode) -> FunctionDef:
        tokens = node.tokens
        name = ""
        args: List[tuple[str, Optional[Node], Optional[str]]] = []
        i = 1
        if i < len(tokens) and tokens[i].type == "PAGE":
            i += 1
        if i < len(tokens) and tokens[i].type == "ID":
            name = tokens[i].value
            i += 1
        if i < len(tokens) and tokens[i].type == "USING":
            i += 1
            while i < len(tokens):
                if tokens[i].type in ("ID", "FOLDER", "FILE"):
                    args.append((tokens[i].value, None, None))
                elif tokens[i].type == "COMMA":
                    pass
                else:
                    break
                i += 1
        body = self.bind_statement_list(node.children)
        return FunctionDef(name, args, body)

    def bind_when(self, node: GeoNode) -> Node:
        is_match = False
        for child in node.children:
            head_tok = child.head_token
            if head_tok is None:
                continue
            if head_tok.type in ("IS", "OTHERWISE"):
                is_match = True
                break

        if is_match:
            expr_tokens = self._extract_expr_tokens(node.tokens, start=1)
            match_expr = self.parse_expr_iterative(expr_tokens)
            if match_expr is None:
                raise SyntaxError(f"Missing expression for 'when' match at line {node.line}")
            cases: List[tuple[Node, List[Node]]] = []
            default_case: Optional[List[Node]] = None

            for child in node.children:
                child_head = child.head_token
                if child_head is None:
                    continue
                if child_head.type == "IS":
                    case_expr_tokens = self._extract_expr_tokens(child.tokens, start=1)
                    case_expr = self.parse_expr_iterative(case_expr_tokens)
                    if case_expr is None:
                        raise SyntaxError(f"Missing case expression at line {child.line}")
                    case_body = self.bind_statement_list(child.children)
                    cases.append((case_expr, case_body))
                elif child_head.type == "OTHERWISE":
                    default_case = self.bind_statement_list(child.children)
            return Match(match_expr, cases, default_case)

        # Default to HTTP route handler
        tokens = node.tokens
        path: Node = String("/")
        for i, t in enumerate(tokens):
            if t.type == "STRING":
                path = String(t.value)
                break
        body = self.bind_statement_list(node.children)
        return OnRequest(path, body)

    def bind_on(self, node: GeoNode) -> OnRequest:
        tokens = node.tokens
        path: Node = String("/")
        for t in tokens:
            if t.type == "STRING":
                path = String(t.value)
                break
        body = self.bind_statement_list(node.children)
        return OnRequest(path, body)

    def bind_call_or_expr(self, node: GeoNode) -> Node:
        tokens = node.tokens
        if len(tokens) >= 1 and tokens[0].type in (
            "ID",
            "BUTTON",
            "HEADING",
            "PARAGRAPH",
            "IMAGE",
            "START",
            "SERVER",
            "INPUT",
        ):
            name = tokens[0].value
            args: List[Node] = []
            kwargs: List[tuple[str, Node]] = []
            i = 1
            while i < len(tokens):
                t = tokens[i]
                is_attr_key = t.type in (
                    "ID",
                    "STRUCTURE",
                    "HREF",
                    "REL",
                    "NAME",
                    "STYLE",
                    "CONTENT",
                    "CHARSET",
                    "SRC",
                    "ALT",
                    "TYPE",
                    "VALUE",
                    "PLACEHOLDER",
                    "METHOD",
                    "ACTION",
                )
                is_kwarg = is_attr_key and i + 2 < len(tokens) and tokens[i + 1].type == "ASSIGN"
                if is_kwarg:
                    key = t.value
                    val_token = tokens[i + 2]
                    if val_token.type == "STRING":
                        kwargs.append((key, String(val_token.value)))
                    elif val_token.type == "NUMBER":
                        val_num: Node = Number(int(val_token.value) if "." not in val_token.value else float(val_token.value))
                        kwargs.append((key, val_num))
                    else:
                        kwargs.append((key, VarAccess(val_token.value)))
                    i += 3
                    continue
                elif t.type == "STRING":
                    args.append(String(t.value))
                elif t.type == "NUMBER":
                    val_num = Number(int(t.value) if "." not in t.value else float(t.value))
                    args.append(val_num)
                elif t.type == "ID":
                    args.append(VarAccess(t.value))
                i += 1
            body = None
            if node.children:
                body = self.bind_statement_list(node.children)
            return Call(name, args, kwargs=kwargs, body=body)
        res = self.parse_expr_iterative(tokens)
        if res is None:
            raise SyntaxError(f"Invalid call or expression at line {node.line}")
        return res

    def _extract_expr_tokens(self, tokens: List[Token], start: int = 0) -> List[Token]:
        end = len(tokens)
        if tokens and tokens[-1].type == "COLON":
            end -= 1
        return tokens[start:end]

    def parse_expr_iterative(self, tokens: List[Token], children: Optional[List[GeoNode]] = None) -> Optional[Node]:
        if not tokens:
            return None

        values: List[Node] = []
        ops: List[str] = []

        # Local precedence for shunting-yard (fallback if not in self.precedence)
        local_precedence = {
            "PLUS": 10,
            "MINUS": 10,
            "MUL": 20,
            "DIV": 20,
            "MOD": 20,
            "GT": 5,
            "LT": 5,
            "EQ": 4,
            "AND": 2,
            "OR": 1,
            "MATCHES": 5,
            "IS": 4,
            "BE": 4,
            "CONTAINS": 5,
            "DOT": 30,
            "NOT": 15,
            "LBRACKET": 30,
        }

        def apply_op():
            """Applies the top operator to the top two values."""
            if not ops:
                return
            op_type = ops.pop()
            unary_ops = ("NOT", "MINUS_UNARY")
            if op_type in unary_ops:
                if len(values) >= 1:
                    right = values.pop()
                    op_str = "not" if op_type == "NOT" else "-"
                    values.append(UnaryOp(op_str, right))
                else:
                    raise SyntaxError(f"Invalid expression: missing operand for unary {op_type}")
            elif len(values) >= 2:
                right = values.pop()
                left = values.pop()
                op_map = {
                    "PLUS": "+",
                    "MINUS": "-",
                    "MUL": "*",
                    "DIV": "/",
                    "MOD": "%",
                    "LT": "<",
                    "GT": ">",
                    "LE": "<=",
                    "GE": ">=",
                    "EQ": "==",
                    "NEQ": "!=",
                    "AND": "and",
                    "OR": "or",
                    "IS": "==",
                    "IN": "in",
                    "NOTIN": "not in",
                    "DOT": ".",
                }
                op_str = op_map.get(op_type, op_type)
                values.append(BinOp(left, op_str, right))
            else:
                print(f"DEBUG: missing operands for {op_type}, values={values}, ops={ops}")
                raise SyntaxError(f"Invalid expression: missing operands for {op_type}")

        def get_precedence(op_type):
            """Returns operator precedence level."""
            if op_type in local_precedence:
                return local_precedence[op_type]
            return self.precedence.get(op_type, 0)

        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.type == "NOISE":
                i += 1
                continue

            # Match natural list, unique set, and dictionary builders
            new_idx, natural_node = self._parse_natural_list_or_set_or_dict(tokens, i)
            if natural_node is not None:
                values.append(natural_node)
                i = new_idx
                continue

            if t.type == "MINUS":
                is_unary = i == 0 or tokens[i - 1].type in (
                    "LPAREN",
                    "COMMA",
                    "ASSIGN",
                    "PLUS",
                    "MINUS",
                    "MUL",
                    "DIV",
                    "MOD",
                    "LT",
                    "GT",
                    "LE",
                    "GE",
                    "EQ",
                    "NEQ",
                    "AND",
                    "OR",
                )
                if is_unary:
                    values.append(Number(0))
                    ops.append("MINUS_UNARY")
                    i += 1
                    continue
            if t.type == "NOT":
                ops.append("NOT")
                i += 1
                continue
            if t.type == "NUMBER":
                val_node: Node = Number(int(t.value) if "." not in t.value else float(t.value))
                val_node.line = t.line
                val_node.col = t.column
                val_node.end_line = t.line
                val_node.end_col = t.column + len(str(t.value))
                values.append(val_node)
            elif t.type == "STRING":
                val_node = String(t.value)
                val_node.line = t.line
                val_node.col = t.column
                val_node.end_line = t.line
                val_node.end_col = t.column + len(t.value) + 2  # +2 for quotes
                values.append(val_node)
            elif t.type in ("YES", "NO"):
                val_node = Boolean(t.type == "YES")
                val_node.line = t.line
                val_node.col = t.column
                val_node.end_line = t.line
                val_node.end_col = t.column + len(t.value)
                values.append(val_node)
            elif t.type == "LBRACKET":
                is_indexing = False
                if i > 0 and tokens[i - 1].type in ("ID", "RBRACKET", "RPAREN", "STRING"):
                    is_indexing = True

                if is_indexing:
                    while ops and ops[-1] != "LPAREN" and get_precedence(ops[-1]) >= 30:
                        apply_op()

                depth = 1
                j = i + 1
                elements_tokens: List[List[Token]] = []
                current_elem: List[Token] = []
                has_comma = False
                to_idx = -1
                while j < len(tokens):
                    if tokens[j].type == "LBRACKET":
                        depth += 1
                    elif tokens[j].type == "RBRACKET":
                        depth -= 1
                    if depth == 0:
                        if current_elem:
                            elements_tokens.append(current_elem)
                        break
                    if tokens[j].type == "COMMA" and depth == 1:
                        elements_tokens.append(current_elem)
                        current_elem = []
                        has_comma = True
                    else:
                        if tokens[j].type == "TO" and depth == 1:
                            to_idx = len(current_elem)
                        current_elem.append(tokens[j])
                    j += 1

                if depth > 0 and current_elem:
                    last_split: List[List[Token]] = []
                    last_curr: List[Token] = []
                    for t_last in current_elem:
                        if t_last.type == "COMMA":
                            if last_curr:
                                last_split.append(last_curr)
                                last_curr = []
                        else:
                            last_curr.append(t_last)
                    if last_curr:
                        last_split.append(last_curr)
                    elements_tokens.extend(last_split)

                if not has_comma and to_idx != -1 and len(elements_tokens) == 1:
                    elem = elements_tokens[0]
                    start_expr = self.parse_expr_iterative(elem[:to_idx], children)
                    end_expr = self.parse_expr_iterative(elem[to_idx + 1 :], children)
                    if start_expr is None or end_expr is None:
                        raise SyntaxError(f"Malformed range expression in brackets at line {t.line}")
                    node_call = Call("list", [Call("range", [start_expr, end_expr])])
                    node_call.line = t.line
                    node_call.col = t.column
                    values.append(node_call)
                    i = j + 1
                    continue
                items: List[Node] = []
                for elem in elements_tokens:
                    if elem:
                        res_item = self.parse_expr_iterative(elem)
                        if res_item:
                            items.append(res_item)

                if is_indexing:
                    if not values:
                        raise SyntaxError(f"Unexpected index access without object at line {t.line}")
                    obj = values.pop()

                    slice_parts: List[List[Token]] = []
                    current_part: List[Token] = []

                    has_colon = False

                    for tok in current_elem:
                        if tok.type == "COLON":
                            has_colon = True
                            slice_parts.append(current_part)
                            current_part = []
                        else:
                            current_part.append(tok)

                    slice_parts.append(current_part)

                    node_idx: Node
                    if has_colon:
                        start = (
                            self.parse_expr_iterative(slice_parts[0], children)
                            if len(slice_parts) > 0 and slice_parts[0]
                            else None
                        )

                        stop = (
                            self.parse_expr_iterative(slice_parts[1], children)
                            if len(slice_parts) > 1 and slice_parts[1]
                            else None
                        )

                        step = (
                            self.parse_expr_iterative(slice_parts[2], children)
                            if len(slice_parts) > 2 and slice_parts[2]
                            else None
                        )

                        slice_node = Slice(start, stop, step)

                        node_idx = IndexAccess(obj, slice_node)
                    else:
                        idx_expr = self.parse_expr_iterative(current_elem, children) if current_elem else None
                        if idx_expr is None:
                            raise SyntaxError(f"Missing index expression at line {t.line}")
                        node_idx = IndexAccess(obj, idx_expr)

                    node_idx.line = t.line
                    node_idx.col = t.column
                    values.append(node_idx)
                else:
                    node_list = ListVal(items)
                    node_list.line = t.line
                    node_list.col = t.column
                    values.append(node_list)
                i = j + 1
                continue
            elif t.type == "LBRACE":
                depth = 1
                bracket_depth = 0
                paren_depth = 0
                j = i + 1
                pairs_tokens: List[List[Token]] = []
                current_pair: List[Token] = []
                while j < len(tokens):
                    if tokens[j].type == "LBRACE":
                        depth += 1
                    elif tokens[j].type == "RBRACE":
                        depth -= 1
                    elif tokens[j].type == "LBRACKET":
                        bracket_depth += 1
                    elif tokens[j].type == "RBRACKET":
                        bracket_depth -= 1
                    elif tokens[j].type == "LPAREN":
                        paren_depth += 1
                    elif tokens[j].type == "RPAREN":
                        paren_depth -= 1

                    if depth == 0:
                        if current_pair:
                            pairs_tokens.append(current_pair)
                        break
                    if tokens[j].type == "COMMA" and depth == 1 and bracket_depth == 0 and paren_depth == 0:
                        pairs_tokens.append(current_pair)
                        current_pair = []
                    else:
                        current_pair.append(tokens[j])
                    j += 1

                if depth > 0 and current_pair:
                    pairs_tokens.append(current_pair)

                pairs: List[tuple[Node, Node]] = []
                for p_tokens in pairs_tokens:
                    if not p_tokens:
                        continue
                    colon_idx = -1
                    for k, pt in enumerate(p_tokens):
                        if pt.type == "COLON":
                            colon_idx = k
                            break
                    if colon_idx != -1:
                        key_expr = self.parse_expr_iterative(p_tokens[:colon_idx])
                        val_expr = self.parse_expr_iterative(p_tokens[colon_idx + 1 :])
                        if key_expr and val_expr:
                            pairs.append((key_expr, val_expr))

                values.append(Dictionary(pairs))
                i = j
            elif t.type == "ASK" and i + 1 < len(tokens) and tokens[i + 1].type == "STRING":
                values.append(Call("ask", [String(tokens[i + 1].value)]))
                i += 2
                continue
            elif t.type == "GATHER":
                i += 1
                res_g = self.parse_expr_iterative(tokens[i:])
                if res_g is None:
                    raise SyntaxError(f"Missing task for 'gather' at line {t.line}")
                values.append(Gather(res_g))
                break
            elif t.type == "RECEIVE":
                i += 1
                res_rc = self.parse_expr_iterative(tokens[i:])
                if res_rc is None:
                    raise SyntaxError(f"Missing channel for 'receive' at line {t.line}")
                values.append(Receive(res_rc))
                break
            elif t.type == "CHANNEL":
                values.append(Channel())
                i += 1
                continue
            elif t.type in ("MAX", "MIN"):
                values.append(self._parse_min_max(tokens, i, t.type))
                break
            elif t.type == "CLAMPED":
                values.append(self._parse_clamped(tokens, i))
                break
            elif t.type == "LERP":
                values.append(self._parse_lerp(tokens, i))
                break
            elif t.type == "FIND":
                tmp_node = GeoNode(head_token=t, line=t.line, indent_level=0, tokens=tokens[i:], children=[])
                values.append(self.bind_dsl_lowering(tmp_node))
                break
            elif t.type == "PARALLEL":
                if children:
                    values.append(Parallel(self.bind_statement_list(children)))
                else:
                    values.append(Parallel([]))
                break
            elif t.type == "ID" and t.value.lower() == "sum" and i + 1 < len(tokens) and tokens[i + 1].type == "OF":
                res_sum = self.parse_expr_iterative(tokens[i + 2 :], children)
                if res_sum is None:
                    raise SyntaxError(f"Missing expression for 'sum of' at line {t.line}")
                values.append(Call("sum", [res_sum]))
                break
            elif t.type == "ID" and i + 1 < len(tokens) and tokens[i + 1].type == "FROM":
                values.append(self._parse_comprehension(tokens, i, t, children))
                break
            elif (
                (t.type == "ID" and t.value.lower() in ("split", "len", "length", "count")) or t.type in ("UPPER", "LOWER")
            ) and (i + 1 >= len(tokens) or tokens[i + 1].type != "LPAREN"):
                values.append(self._parse_unparenthesized_fn(tokens, i, t, children))
                break
            elif t.type == "READ" and (i + 1 >= len(tokens) or tokens[i + 1].type != "LPAREN"):
                res_read = self.parse_expr_iterative(tokens[i + 1 :], children)
                if res_read is None:
                    raise SyntaxError(f"Missing path for 'read' at line {t.line}")
                values.append(FileRead(res_read))
                break
            elif t.type in (
                "ID",
                "ADD",
                "REMOVE",
                "FOLDER",
                "FILE",
                "CONVERT",
                "LOAD",
                "SAVE",
                "SET",
                "LIST",
                "SIZE",
                "INT",
                "STR",
                "LEN",
                "KEYS",
                "UPPER",
                "LOWER",
                "SORT",
                "CONTAINS",
                "EMPTY",
                "JSON",
                "HTTP",
                "BUTTON",
                "HEADING",
                "PARAGRAPH",
                "IMAGE",
                "START",
                "SERVER",
                "READ",
                "WRITE",
                "OPEN",
                "CLOSE",
                "UPDATE",
                "DELETE",
                "FIND",
                "CREATE",
                "COUNT",
                "INSERT",
                "ERROR",
                "EXECUTE",
                "COPY",
                "LISTEN",
                "PORT",
                "NAME",
                "TYPE",
                "VALUE",
                "CONTENT",
            ):
                new_idx, node_val = self._parse_id_or_call(tokens, i, t)
                values.append(node_val)
                i = new_idx
            elif t.type == "LPAREN":
                ops.append("LPAREN")
            elif t.type == "RPAREN":
                while ops and ops[-1] != "LPAREN":
                    apply_op()
                if ops:
                    ops.pop()
            elif t.type in self.precedence:
                while ops and ops[-1] != "LPAREN" and get_precedence(ops[-1]) >= get_precedence(t.type):
                    apply_op()
                ops.append(t.type)
            i += 1
        while ops:
            apply_op()
        if len(values) > 1:
            raise SyntaxError(f"Invalid expression: too many operands. Tokens: {tokens}, Values: {values}")
        return values[0] if values else None

    def _parse_natural_list_or_set_or_dict(self, tokens: List[Token], i: int) -> tuple[int, Optional[Node]]:
        t = tokens[i]
        # Match "a list of ..." or "a list"
        if t.type == "ID" and t.value.lower() == "a" and i + 1 < len(tokens) and tokens[i + 1].type == "LIST":
            if i + 2 < len(tokens) and tokens[i + 2].type == "OF":
                j = i + 3
                elements_tokens: List[List[Token]] = []
                current_elem: List[Token] = []
                while j < len(tokens):
                    if tokens[j].type == "COMMA":
                        if current_elem:
                            elements_tokens.append(current_elem)
                            current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                if current_elem:
                    elements_tokens.append(current_elem)

                items: List[Node] = []
                for elem in elements_tokens:
                    if elem:
                        res = self.parse_expr_iterative(elem)
                        if res:
                            items.append(res)
                return j, ListVal(items)
            else:
                return i + 2, ListVal([])

        # Match "a unique set of ..." or "a unique set"
        if (
            t.type == "ID"
            and t.value.lower() == "a"
            and i + 2 < len(tokens)
            and tokens[i + 1].type == "UNIQUE"
            and tokens[i + 2].type == "SET"
        ):
            if i + 3 < len(tokens) and tokens[i + 3].type == "OF":
                j = i + 4
                elements_tokens = []
                current_elem = []
                while j < len(tokens):
                    if tokens[j].type == "COMMA":
                        if current_elem:
                            elements_tokens.append(current_elem)
                            current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                if current_elem:
                    elements_tokens.append(current_elem)

                items = []
                for elem in elements_tokens:
                    if elem:
                        res = self.parse_expr_iterative(elem)
                        if res:
                            items.append(res)
                return j, Call("set", [ListVal(items)])
            else:
                return i + 3, Call("set", [ListVal([])])

        # Match "a dictionary"
        if (
            t.type == "ID"
            and t.value.lower() == "a"
            and i + 1 < len(tokens)
            and tokens[i + 1].type == "ID"
            and tokens[i + 1].value.lower() == "dictionary"
        ):
            return i + 2, Dictionary([])

        # Match "list of ..."
        if t.type == "LIST" and i + 1 < len(tokens) and tokens[i + 1].type == "OF":
            j = i + 2
            elements_tokens = []
            current_elem = []
            while j < len(tokens):
                if tokens[j].type == "COMMA":
                    if current_elem:
                        elements_tokens.append(current_elem)
                        current_elem = []
                else:
                    current_elem.append(tokens[j])
                j += 1
            if current_elem:
                elements_tokens.append(current_elem)

            items = []
            for elem in elements_tokens:
                if elem:
                    res = self.parse_expr_iterative(elem)
                    if res:
                        items.append(res)
            return j, ListVal(items)

        # Match "unique set of ..."
        if t.type == "UNIQUE" and i + 2 < len(tokens) and tokens[i + 1].type == "SET" and tokens[i + 2].type == "OF":
            j = i + 3
            elements_tokens = []
            current_elem = []
            while j < len(tokens):
                if tokens[j].type == "COMMA":
                    if current_elem:
                        elements_tokens.append(current_elem)
                        current_elem = []
                else:
                    current_elem.append(tokens[j])
                j += 1
            if current_elem:
                elements_tokens.append(current_elem)

            items = []
            for elem in elements_tokens:
                if elem:
                    res = self.parse_expr_iterative(elem, [])
                    if res:
                        items.append(res)
            return j, Call("set", [ListVal(items)])

        return i, None

    def _parse_clamped(self, tokens: List[Token], i: int) -> ClampNode:
        i += 1
        bet_idx = -1
        and_idx = -1
        depth = 0
        for k in range(i, len(tokens)):
            tt = tokens[k].type
            if tt in ("LPAREN", "LBRACKET", "LBRACE"):
                depth += 1
            elif tt in ("RPAREN", "RBRACKET", "RBRACE"):
                depth -= 1
            elif depth == 0:
                if tt == "BETWEEN":
                    bet_idx = k
                elif tt == "AND" and bet_idx != -1:
                    and_idx = k
                    break
        if bet_idx != -1 and and_idx != -1:
            val_res = self.parse_expr_iterative(tokens[i:bet_idx])
            min_res = self.parse_expr_iterative(tokens[bet_idx + 1 : and_idx])
            max_res = self.parse_expr_iterative(tokens[and_idx + 1 :])
            if val_res is None or min_res is None or max_res is None:
                raise SyntaxError(f"Malformed 'clamped' expression at line {tokens[i - 1].line}")
            return ClampNode(val_res, min_res, max_res)
        else:
            raise SyntaxError(f"Malformed 'clamped' expression at line {tokens[i - 1].line}")

    def _parse_lerp(self, tokens: List[Token], i: int) -> LerpNode:
        i += 1
        from_idx = -1
        to_idx = -1
        by_idx = -1
        depth = 0
        for k in range(i, len(tokens)):
            tt = tokens[k].type
            if tt in ("LPAREN", "LBRACKET", "LBRACE"):
                depth += 1
            elif tt in ("RPAREN", "RBRACKET", "RBRACE"):
                depth -= 1
            elif depth == 0:
                if tt == "FROM":
                    from_idx = k
                elif tt == "TO":
                    to_idx = k
                elif tt == "BY":
                    by_idx = k
        if from_idx != -1 and to_idx != -1 and by_idx != -1:
            a_res = self.parse_expr_iterative(tokens[from_idx + 1 : to_idx])
            b_res = self.parse_expr_iterative(tokens[to_idx + 1 : by_idx])
            t_res = self.parse_expr_iterative(tokens[by_idx + 1 :])
            if a_res is None or b_res is None or t_res is None:
                raise SyntaxError(f"Malformed 'lerp' expression at line {tokens[i - 1].line}")
            return LerpNode(a_res, b_res, t_res)
        else:
            to_idx = -1
            by_idx = -1
            for k in range(i, len(tokens)):
                tt = tokens[k].type
                if tt == "TO":
                    to_idx = k
                elif tt == "BY":
                    by_idx = k
            if to_idx != -1 and by_idx != -1:
                a_res = self.parse_expr_iterative(tokens[i:to_idx])
                b_res = self.parse_expr_iterative(tokens[to_idx + 1 : by_idx])
                t_res = self.parse_expr_iterative(tokens[by_idx + 1 :])
                if a_res is None or b_res is None or t_res is None:
                    raise SyntaxError(f"Malformed 'lerp' expression at line {tokens[i - 1].line}")
                return LerpNode(a_res, b_res, t_res)
            raise SyntaxError(f"Malformed 'lerp' expression at line {tokens[i - 1].line}")

    def _parse_min_max(self, tokens: List[Token], i: int, t_type: str) -> Union[MaxNode, MinNode]:
        node_class: Any = MaxNode if t_type == "MAX" else MinNode
        i += 1
        if i < len(tokens) and tokens[i].type == "OF":
            i += 1
        and_idx = -1
        depth = 0
        for k in range(i, len(tokens)):
            tt = tokens[k].type
            if tt in ("LPAREN", "LBRACKET", "LBRACE"):
                depth += 1
            elif tt in ("RPAREN", "RBRACKET", "RBRACE"):
                depth -= 1
            elif tt == "AND" and depth == 0:
                and_idx = k
                break

        if and_idx != -1:
            left_tokens = tokens[i:and_idx]
            right_tokens = tokens[and_idx + 1 :]
            left_expr = self.parse_expr_iterative(left_tokens)
            right_expr = self.parse_expr_iterative(right_tokens)
            if left_expr is None or right_expr is None:
                raise SyntaxError(f"Malformed {t_type} expression at line {tokens[i - 1].line}")
            return node_class(left_expr, right_expr)
        else:
            inner_tokens = tokens[i:]
            expr_node = self.parse_expr_iterative(inner_tokens)
            if expr_node is None:
                raise SyntaxError(f"Missing expression for {t_type} at line {tokens[i - 1].line}")
            return node_class(expr_node, None)

    def _parse_comprehension(
        self, tokens: List[Token], i: int, t: Token, children: Optional[List[GeoNode]]
    ) -> ListComprehension:
        var_name = t.value
        from_idx = i + 1
        to_idx = -1
        when_idx = -1
        for k in range(from_idx, len(tokens)):
            if tokens[k].type == "TO":
                to_idx = k
            elif tokens[k].type in ("WHEN", "THAT") or (tokens[k].type == "ID" and tokens[k].value.lower() == "that"):
                when_idx = k
                break

        if to_idx != -1:
            start_expr = self.parse_expr_iterative(tokens[from_idx + 1 : to_idx], children)
            end_expr_tokens = tokens[to_idx + 1 : when_idx] if when_idx != -1 else tokens[to_idx + 1 :]
            end_expr = self.parse_expr_iterative(end_expr_tokens, children)
            if start_expr is None or end_expr is None:
                raise SyntaxError(f"Malformed list comprehension range at line {t.line}")
            iterable = Call("range", [start_expr, end_expr])

            condition = None
            if when_idx != -1:
                cond_start = when_idx + 1
                if cond_start < len(tokens) and tokens[cond_start].type == "ID" and tokens[cond_start].value.lower() == "are":
                    cond_start += 1
                condition = self.parse_expr_iterative(tokens[cond_start:], children)
            return ListComprehension(VarAccess(var_name), var_name, iterable, condition)
        raise SyntaxError(f"Malformed list comprehension at line {t.line}")

    def _parse_unparenthesized_fn(self, tokens: List[Token], i: int, t: Token, children: Optional[List[GeoNode]]) -> Call:
        func_name = t.value.lower()
        i += 1
        only_letters = False
        only_idx = -1
        for k in range(i, len(tokens)):
            if (
                tokens[k].type == "ID"
                and tokens[k].value.lower() == "only"
                and k + 1 < len(tokens)
                and tokens[k + 1].type == "ID"
                and tokens[k + 1].value.lower() == "letters"
            ):
                only_idx = k
                only_letters = True
                break

        expr_tokens = tokens[i:only_idx] if only_idx != -1 else tokens[i:]
        expr = self.parse_expr_iterative(expr_tokens, children)
        if expr is None:
            raise SyntaxError(f"Missing expression for function '{func_name}' at line {t.line}")

        args = [expr]
        kwargs: List[tuple[str, Node]] = []
        if only_letters:
            kwargs.append(("only", String("letters")))

        return Call(func_name, args, kwargs=kwargs)

    def _parse_id_or_call(self, tokens: List[Token], i: int, t: Token) -> tuple[int, Node]:
        name = t.value
        if i + 1 < len(tokens) and tokens[i + 1].type == "LPAREN":
            depth = 1
            j = i + 2
            elements_tokens: List[List[Token]] = []
            current_elem: List[Token] = []
            if j < len(tokens) and tokens[j].type == "RPAREN":
                return j, Call(name, [])
            else:
                while j < len(tokens):
                    t_type = tokens[j].type
                    if t_type in ("LPAREN", "LBRACKET", "LBRACE"):
                        depth += 1
                    elif t_type in ("RPAREN", "RBRACKET", "RBRACE"):
                        depth -= 1

                    if depth == 0:
                        if current_elem:
                            elements_tokens.append(current_elem)
                        break
                    if t_type == "COMMA" and depth == 1:
                        elements_tokens.append(current_elem)
                        current_elem = []
                    else:
                        current_elem.append(tokens[j])
                    j += 1
                args: List[Node] = []
                kwargs: List[tuple[str, Node]] = []
                for elem in elements_tokens:
                    if not elem:
                        continue
                    is_kw = len(elem) >= 2 and elem[0].type == "ID" and elem[1].type == "ASSIGN"
                    if is_kw:
                        key = elem[0].value
                        val = self.parse_expr_iterative(elem[2:], [])
                        if val is not None:
                            kwargs.append((key, val))
                    else:
                        res_arg = self.parse_expr_iterative(elem, [])
                        if res_arg is not None:
                            args.append(res_arg)
                return j, Call(name, args, kwargs=kwargs)

        # Check for unparenthesized builtin call (greedy single argument)
        if name.lower() in ("str", "int", "float", "bool", "len", "typeof", "char", "ord"):
            if i + 1 < len(tokens):
                next_t = tokens[i + 1]
                if next_t.type in ("ID", "NUMBER", "STRING", "YES", "NO", "NULL"):
                    arg_node: Node
                    if next_t.type == "NUMBER":
                        arg_node = Number(int(next_t.value) if "." not in next_t.value else float(next_t.value))
                    elif next_t.type == "STRING":
                        arg_node = String(next_t.value)
                    elif next_t.type in ("YES", "NO"):
                        arg_node = Boolean(next_t.type == "YES")
                    elif next_t.type == "NULL":
                        arg_node = VarAccess("null")
                    else:  # ID
                        arg_node = VarAccess(next_t.value)

                    arg_node.line = next_t.line
                    arg_node.col = next_t.column

                    call_node = Call(name.lower(), [arg_node])
                    call_node.line = t.line
                    call_node.col = t.column
                    return i + 1, call_node

        val = VarAccess(t.value)
        val.line = t.line
        val.col = t.column
        val.end_line = t.line
        val.end_col = t.column + len(t.value)
        return i, val
