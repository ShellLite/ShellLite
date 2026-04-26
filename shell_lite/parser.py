from typing import List, Optional
from .lexer import Token, Lexer
from .ast_nodes import *
import re
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != 'COMMENT']
        self.pos = 0
    def peek(self, offset: int = 0) -> Token:
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return self.tokens[-1]
    def consume(self, expected_type: str = None) -> Token:
        token = self.peek()
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type} but got {token.type} on line {token.line}")
        self.pos += 1
        return token
    def check(self, token_type: str) -> bool:
        return self.peek().type == token_type
    def parse(self) -> List[Node]:
        statements = []
        while not self.check('EOF'):
            while self.check('NEWLINE'):
                self.consume()
                if self.check('EOF'): break
            if self.check('EOF'): break
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return statements
    def parse_statement(self) -> Node:
        if self.check('USE'):
            return self.parse_import()
        elif self.check('APP'):
            return self.parse_app()
        elif self.check('ON'):
            return self.parse_on()
        elif self.check('CONST'):
            return self.parse_const()
        elif self.check('PRINT') or self.check('SAY'):
            return self.parse_print()
        elif self.check('ALERT'):
            return self.parse_alert()
        elif self.check('IF'):
            return self.parse_if()
        elif self.check('UNLESS'):
            return self.parse_unless()
        elif self.check('WHILE'):
            return self.parse_while()
        elif self.check('UNTIL'):
            return self.parse_until()
        elif self.check('FOREVER'):
            return self.parse_forever()
        elif self.check('TRY'):
            return self.parse_try()
        elif self.check('FOR') or self.check('LOOP'):
            return self.parse_for()
        elif self.check('REPEAT'):
            return self.parse_repeat()
        elif self.check('WHEN'):
            return self.parse_when()
        elif self.check('TO'):
            return self.parse_function_def()
        elif self.check('STRUCTURE'):
            return self.parse_class_def()
        elif self.check('RETURN'):
            return self.parse_return()
        elif self.check('STOP'):
            return self.parse_stop()
        elif self.check('SKIP'):
            return self.parse_skip()
        elif self.check('EXIT'):
            return self.parse_exit()
        elif self.check('ERROR'):
            return self.parse_error()
        elif self.check('EXECUTE'):
            return self.parse_execute()
        elif self.check('MAKE'):
            return self.parse_make()
        elif self.check('INPUT'):
            next_t = self.peek(1)
            if next_t.type in ('ID', 'TYPE', 'STRING', 'NAME', 'VALUE', 'CLASS', 'STYLE', 'ONCLICK', 'SRC', 'HREF', 'ACTION', 'METHOD'):
                input_token = self.consume()
                return self.parse_id_start_statement(passed_name_token=input_token)
            return self.parse_expression_stmt()
        elif self.check('ID'):
            return self.parse_id_start_statement()
        elif self.check('SPAWN'):
             expr = self.parse_expression()
             self.consume('NEWLINE')
             return Print(expr) 
             pass
        elif self.check('WAIT'):
            return self.parse_wait()
        elif self.check('EVERY'):
            return self.parse_every()
        elif self.check('IN'):
             return self.parse_after()
        elif self.check('LISTEN'):
            return self.parse_listen()
        elif self.check('SERVE'):
            return self.parse_serve()
        elif self.check('DOWNLOAD'):
             return self.parse_download()
        elif self.check('COMPRESS') or self.check('EXTRACT'):
             return self.parse_archive()
        elif self.check('LOAD') or self.check('SAVE'):
             if self.check('LOAD') and self.peek(1).type == 'CSV':
                 return self.parse_csv_load()
             if self.check('SAVE'):
                 return self.parse_csv_save() 
             return self.parse_expression_stmt() 
        elif self.check('COPY') or self.check('PASTE'):
             return self.parse_clipboard()
        elif self.check('WRITE'):
             return self.parse_write()
        elif self.check('APPEND'):
             return self.parse_append()
        elif self.check('DB'):
             return self.parse_db_op()
        elif self.check('PRESS') or self.check('TYPE') or self.check('CLICK') or self.check('NOTIFY'):
             return self.parse_automation()
        elif self.check('BEFORE'):
             return self.parse_middleware()
        elif self.check('DEFINE'):
            return self.parse_define_page()
        elif self.check('ADD'):
            return self.parse_add_to()
        elif self.check('START'):
            return self.parse_start_server()
        elif self.check('HEADING'):
            return self.parse_heading()
        elif self.check('PARAGRAPH'):
            return self.parse_paragraph()
        else:
            return self.parse_expression_stmt()
    def parse_alert(self) -> Alert:
        token = self.consume('ALERT')
        message = self.parse_expression()
        self.consume('NEWLINE')
        node = Alert(message)
        node.line = token.line
        return node
    def parse_const(self) -> ConstAssign:
        token = self.consume('CONST')
        name = self.consume('ID').value
        self.consume('ASSIGN')
        value = self.parse_expression()
        self.consume('NEWLINE')
        node = ConstAssign(name, value)
        node.line = token.line
        return node
    def parse_on(self) -> Node:
        token = self.consume('ON')
        if self.check('REQUEST') or (self.check('ID') and self.peek().value == 'request'):
            self.consume()
            if self.check('TO'): self.consume('TO')
            path = self.parse_expression() 
            self.consume('NEWLINE')
            self.consume('INDENT')
            body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                body.append(self.parse_statement())
            self.consume('DEDENT')
            node = OnRequest(path, body)
            node.line = token.line
            return node
        event_type = self.consume('ID').value
        path = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        return FileWatcher(path, body)
    def _parse_natural_list(self) -> ListVal:
        self.consume('ID') 
        self.consume('LIST')
        self.consume('OF')
        elements = []
        if not self.check('NEWLINE') and not self.check('EOF'):
            elements.append(self.parse_expression())
            while self.check('COMMA'):
                self.consume('COMMA')
                if self.check('NEWLINE'): break 
                elements.append(self.parse_expression())
        node = ListVal(elements)
        return node
    def _parse_natural_set(self) -> Node:
        self.consume('ID') 
        self.consume('UNIQUE')
        self.consume('SET')
        self.consume('OF')
        elements = []
        if not self.check('NEWLINE') and not self.check('EOF'):
            elements.append(self.parse_expression())
            while self.check('COMMA'):
                self.consume('COMMA')
                if self.check('NEWLINE'): break
                elements.append(self.parse_expression())
        list_node = ListVal(elements)
        return Call('Set', [list_node])
    def parse_wait(self) -> Node:
        token = self.consume('WAIT')
        if self.check('FOR'):
            self.consume('FOR')
        time_expr = self.parse_expression()
        if self.check('SECOND'):
            self.consume()
        self.consume('NEWLINE')
        return Call('wait', [time_expr])
    def parse_stop(self) -> Stop:
        token = self.consume('STOP')
        self.consume('NEWLINE')
        node = Stop()
        node.line = token.line
        return node
    def parse_skip(self) -> Skip:
        token = self.consume('SKIP')
        self.consume('NEWLINE')
        node = Skip()
        node.line = token.line
        return node
    def parse_error(self) -> Throw:
        token = self.consume('ERROR')
        message = self.parse_expression()
        self.consume('NEWLINE')
        node = Throw(message)
        node.line = token.line
        return node
    def parse_execute(self) -> Execute:
        token = self.consume('EXECUTE')
        code = self.parse_expression()
        self.consume('NEWLINE')
        node = Execute(code)
        node.line = token.line
        return node
    def parse_unless(self) -> Unless:
        token = self.consume('UNLESS')
        condition = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        else_body = None
        if self.check('ELSE'):
            self.consume('ELSE')
            self.consume('NEWLINE')
            self.consume('INDENT')
            else_body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                else_body.append(self.parse_statement())
            self.consume('DEDENT')
        node = Unless(condition, body, else_body)
        node.line = token.line
        return node
    def parse_until(self) -> Until:
        token = self.consume('UNTIL')
        condition = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = Until(condition, body)
        node.line = token.line
        return node
    def parse_forever(self) -> Forever:
        token = self.consume('FOREVER')
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = Forever(body)
        node.line = token.line
        return node
    def parse_exit(self) -> Exit:
        token = self.consume('EXIT')
        code = None
        if not self.check('NEWLINE'):
            code = self.parse_expression()
        self.consume('NEWLINE')
        node = Exit(code)
        node.line = token.line
        return node
    def parse_make(self) -> Node:
        node = self.parse_make_expr()
        self.consume('NEWLINE')
        return node

    def parse_make_expr(self) -> Make:
        token = self.consume('MAKE')
        class_name = self.consume('ID').value
        args = []
        if self.check('LPAREN'):
            self.consume('LPAREN')
            if not self.check('RPAREN'):
                args.append(self.parse_expression())
                while self.check('COMMA'):
                    self.consume('COMMA')
                    args.append(self.parse_expression())
            self.consume('RPAREN')
        else:
            while not self.check('NEWLINE') and not self.check('EOF'):
                args.append(self.parse_expression())
        node = Make(class_name, args)
        node.line = token.line
        return node
    def parse_repeat(self) -> Repeat:
        token = self.consume('REPEAT')
        if self.check('NEWLINE'):
            raise SyntaxError(f"repeat requires a count on line {token.line}")
        count = self.parse_expression()
        if self.check('TIMES'):
            self.consume('TIMES')
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = Repeat(count, body)
        node.line = token.line
        return node
        return node
    def parse_db_op(self) -> DatabaseOp:
        token = self.consume('DB')
        op = 'open' 
        if self.check('OPEN'): op = 'open'; self.consume()
        elif self.check('QUERY'): op = 'query'; self.consume()
        elif self.check('EXEC'): op = 'exec'; self.consume()
        elif self.check('CLOSE'): op = 'close'; self.consume()
        else:
             if self.check('STRING'):
                 op = 'open'
             else:
                 raise SyntaxError(f"Unknown db operation at line {token.line}")
        args = []
        if op != 'close' and not self.check('NEWLINE'):
             args.append(self.parse_expression())
             while not self.check('NEWLINE'):
                 args.append(self.parse_expression())
        node = DatabaseOp(op, args)
        node.line = token.line
        return node
    def parse_middleware(self) -> Node:
        token = self.consume('BEFORE')
        self.consume('REQUEST')
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        return OnRequest(String('__middleware__'), body)
    def parse_when(self) -> Node:
        token = self.consume('WHEN')
        if self.check('SOMEONE'):
            self.consume('SOMEONE')
            if self.check('VISITS'):
                self.consume('VISITS')
                path = String(self.consume('STRING').value)
                self.consume('NEWLINE')
                self.consume('INDENT')
                body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    body.append(self.parse_statement())
                self.consume('DEDENT')
                node = OnRequest(path, body)
                node.line = token.line
                return node
            elif self.check('SUBMITS'):
                self.consume('SUBMITS')
                if self.check('TO'):
                    self.consume('TO')
                path = String(self.consume('STRING').value)
                self.consume('NEWLINE')
                self.consume('INDENT')
                body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    body.append(self.parse_statement())
                self.consume('DEDENT')
                node = OnRequest(path, body)
                node.line = token.line
                return node
        condition_or_value = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        if self.check('IS'):
            cases = []
            otherwise = None
            while not self.check('DEDENT') and not self.check('EOF'):
                if self.check('IS'):
                    self.consume('IS')
                    match_val = self.parse_expression()
                    self.consume('NEWLINE')
                    self.consume('INDENT')
                    case_body = []
                    while not self.check('DEDENT') and not self.check('EOF'):
                        while self.check('NEWLINE'): self.consume()
                        if self.check('DEDENT'): break
                        case_body.append(self.parse_statement())
                    self.consume('DEDENT')
                    cases.append((match_val, case_body))
                elif self.check('OTHERWISE'):
                    self.consume('OTHERWISE')
                    self.consume('NEWLINE')
                    self.consume('INDENT')
                    otherwise = []
                    while not self.check('DEDENT') and not self.check('EOF'):
                        while self.check('NEWLINE'): self.consume()
                        if self.check('DEDENT'): break
                        otherwise.append(self.parse_statement())
                    self.consume('DEDENT')
                elif self.check('NEWLINE'):
                    self.consume('NEWLINE')
                else:
                    break
            self.consume('DEDENT')
            node = When(condition_or_value, cases, otherwise)
            node.line = token.line
            return node
        else:
            body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                body.append(self.parse_statement())
            self.consume('DEDENT')
            else_body = None
            if self.check('ELSE'):
                self.consume('ELSE')
                self.consume('NEWLINE')
                self.consume('INDENT')
                else_body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    else_body.append(self.parse_statement())
                self.consume('DEDENT')
            node = If(condition_or_value, body, else_body)
            node.line = token.line
            return node
    def parse_return(self) -> Return:
        token = self.consume('RETURN')
        expr = self.parse_expression()
        self.consume('NEWLINE')
        node = Return(expr)
        node.line = token.line
        return node
    def parse_function_def(self) -> FunctionDef:
        start_token = self.consume('TO')
        name = self.consume('ID').value
        args = []
        while self.check('ID'):
            arg_name = self.consume('ID').value
            type_hint = None
            if self.check('COLON'):
                if self.peek(1).type == 'NEWLINE':
                    pass 
                else:
                    self.consume('COLON')
                    if self.check('ID'):
                        type_hint = self.consume('ID').value
                    elif self.check('STRING'): 
                        type_hint = "str"
                        self.consume()
                    else: 
                         type_hint = self.consume().value 
            default_val = None
            if self.check('ASSIGN'):
                self.consume('ASSIGN')
                default_val = self.parse_expression()
            args.append((arg_name, default_val, type_hint))
        if self.check('COLON'):
            self.consume('COLON')
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = FunctionDef(name, args, body)
        node.line = start_token.line
        return node
    def parse_class_def(self) -> ClassDef:
        start_token = self.consume('STRUCTURE')
        name = self.consume('ID').value
        parent = None
        if self.check('EXTENDS'):
            self.consume('EXTENDS')
            parent = self.consume('ID').value
        elif self.check('LPAREN'):
            self.consume('LPAREN')
            parent = self.consume('ID').value
            self.consume('RPAREN')
        self.consume('NEWLINE')
        self.consume('INDENT')
        properties = []
        methods = []
        while not self.check('DEDENT') and not self.check('EOF'):
            if self.check('HAS'):
                self.consume()
                prop_name = None
                if self.check('MAKE'):
                    prop_name = self.consume().value
                else:
                    prop_name = self.consume('ID').value
                
                default_val = None
                if self.check('ASSIGN'):
                    self.consume('ASSIGN')
                    default_val = self.parse_expression()
                
                properties.append((prop_name, default_val))
                self.consume('NEWLINE')
            elif self.check('TO'):
                methods.append(self.parse_function_def())
            elif self.check('ID'):
                prop_name = self.consume('ID').value
                default_val = None
                if self.check('ASSIGN'):
                    self.consume('ASSIGN')
                    default_val = self.parse_expression()
                properties.append((prop_name, default_val))
                self.consume('NEWLINE')
            elif self.check('NEWLINE'):
                self.consume()
            else:
                self.consume('DEDENT') 
                break
        self.consume('DEDENT')
        node = ClassDef(name, properties, methods, parent)
        node.line = start_token.line
        return node
    def parse_id_start_statement(self, passed_name_token=None) -> Node:
        if passed_name_token:
            name_token = passed_name_token
        else:
            name_token = self.consume('ID')
        name = name_token.value
        if self.check('ASSIGN'):
            self.consume('ASSIGN')
            value = self.parse_expression()
            self.consume('NEWLINE')
            node = Assign(name, value)
            node.line = name_token.line
            return node
        elif self.check('PLUSEQ'):
            self.consume('PLUSEQ')
            value = self.parse_expression()
            self.consume('NEWLINE')
            node = Assign(name, BinOp(VarAccess(name), '+', value))
            node.line = name_token.line
            return node
        elif self.check('MINUSEQ'):
            self.consume('MINUSEQ')
            value = self.parse_expression()
            self.consume('NEWLINE')
            node = Assign(name, BinOp(VarAccess(name), '-', value))
            node.line = name_token.line
            return node
        elif self.check('MULEQ'):
            self.consume('MULEQ')
            value = self.parse_expression()
            self.consume('NEWLINE')
            node = Assign(name, BinOp(VarAccess(name), '*', value))
            node.line = name_token.line
            return node
        elif self.check('DIVEQ'):
            self.consume('DIVEQ')
            value = self.parse_expression()
            self.consume('NEWLINE')
            node = Assign(name, BinOp(VarAccess(name), '/', value))
            node.line = name_token.line
            return node
        elif self.check('IS'):
            token_is = self.consume('IS')
            if self.check('ID') and self.peek().value == 'a':
                self.consume()
            if self.check('LIST'):
                self.consume('LIST')
                self.consume('NEWLINE')
                node = Assign(name, ListVal([]))
                node.line = token_is.line
                return node
            if self.check('ID') and self.peek().value in ('dictionary', 'map', 'dict'):
                self.consume()
                self.consume('NEWLINE')
                node = Assign(name, Dictionary([]))
                node.line = token_is.line
                return node
            if self.check('ID') and not self.peek().value in ('{', '['): 
                class_name = self.consume('ID').value
                args = []
                while not self.check('NEWLINE') and not self.check('EOF'):
                    args.append(self.parse_expression()) 
                self.consume('NEWLINE')
                node = Instantiation(name, class_name, args)
                node.line = token_is.line
                return node
            else:
                value = self.parse_expression()
                self.consume('NEWLINE')
                node = Assign(name, value)
                node.line = token_is.line
                return node
        elif self.check('LBRACKET'):
             self.consume('LBRACKET')
             index = self.parse_expression()
             self.consume('RBRACKET')
             self.consume('ASSIGN')
             val = self.parse_expression()
             self.consume('NEWLINE')
             # Convert simple assignment to PropertyAssign-like or specific set call?
             # interpreter.visit_IndexAccess handles get.
             # We need a node for IndexAssign. parser snippet doesn't show one.
             # But visit_PropertyAssign handles dict keys. 
             # Let's map d[k] = v to PropertyAssign(d, k, v)? 
             # No, PropertyAssign takes member name as string. Here index handles expressions.
             # I need to check if there is a node for this. 
             # If not, I'll return Call('set', [VarAccess(name), index, val])
             return Call('set', [VarAccess(name), index, val])
        elif self.check('DOT'):
            self.consume('DOT')
            member_token = self.consume()
            member = member_token.value
            if self.check('ASSIGN'):
                self.consume('ASSIGN')
                value = self.parse_expression()
                self.consume('NEWLINE')
                return PropertyAssign(name, member, value)
            
            args = []
            if self.check('LPAREN'):
                 self.consume('LPAREN')
                 if not self.check('RPAREN'):
                     args.append(self.parse_expression())
                     while self.check('COMMA'):
                         self.consume('COMMA')
                         args.append(self.parse_expression())
                 self.consume('RPAREN')
                 self.consume('NEWLINE')
                 node = MethodCall(name, member, args)
                 node.line = name_token.line
                 return node

            while not self.check('NEWLINE') and not self.check('EOF'):
                args.append(self.parse_expression())
            self.consume('NEWLINE')
            node = MethodCall(name, member, args)
            node.line = name_token.line
            return node
        elif self.check('LPAREN'):
             self.consume('LPAREN')
             args = []
             if not self.check('RPAREN'):
                 args.append(self.parse_expression())
                 while self.check('COMMA'):
                     self.consume('COMMA')
                     args.append(self.parse_expression())
             self.consume('RPAREN')
             self.consume('NEWLINE')
             node = Call(name, args)
             node.line = name_token.line
             return node
        else:
            if not self.check('NEWLINE') and not self.check('EOF') and not self.check('EQ') and not self.check('IS'):
                args = []
                while not self.check('NEWLINE') and not self.check('EOF') and not self.check('IS'): 
                     is_named_arg = False
                     if self.peek(1).type == 'ASSIGN':
                         t_type = self.peek().type
                         if t_type in ('ID', 'STRUCTURE', 'TYPE', 'FOR', 'IN', 'WHILE', 'IF', 'ELSE', 'FROM', 'TO', 'STRING', 'EXTENDS', 'WITH', 'PLACEHOLDER', 'NAME', 'VALUE', 'ACTION', 'METHOD', 'HREF', 'SRC', 'CLASS', 'STYLE'):
                             is_named_arg = True
                     if is_named_arg:
                         key_token = self.consume()
                         key = key_token.value
                         self.consume('ASSIGN')
                         val = self.parse_expression()
                         args.append(Dictionary([ (String(key), val) ]))
                     else:
                         if self.check('USING'):
                             self.consume('USING')
                         args.append(self.parse_expression())
                if self.check('NEWLINE'):
                    self.consume('NEWLINE')
                elif self.check('INDENT'):
                    pass
                else:
                    self.consume('NEWLINE')
                body = None
                if self.check('INDENT'):
                    self.consume('INDENT')
                    body = []
                    while not self.check('DEDENT') and not self.check('EOF'):
                        while self.check('NEWLINE'): self.consume()
                        if self.check('DEDENT'): break
                        body.append(self.parse_statement())
                    self.consume('DEDENT')
                node = Call(name, args, body)
                node.line = name_token.line
                return node
                node = Call(name, args, body)
                node.line = name_token.line
                return node
            if self.check('NEWLINE'):
                self.consume('NEWLINE')
            elif self.check('INDENT'):
                pass
            else:
                 self.consume('NEWLINE')
            if self.check('INDENT'):
                self.consume('INDENT')
                body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    body.append(self.parse_statement())
                self.consume('DEDENT')
                node = Call(name, [], body)
                node.line = name_token.line
                return node
            node = VarAccess(name)
            node.line = name_token.line
            return node
    def parse_print(self) -> Node:
        if self.check('PRINT'):
            token = self.consume('PRINT')
        else:
            token = self.consume('SAY')
        if self.check('PROGRESS'):
            return self.parse_progress_loop(token)
        style = None
        color = None
        if self.check('IN'):
            self.consume('IN')
            if self.peek().type in ('RED', 'GREEN', 'BLUE', 'YELLOW', 'CYAN', 'MAGENTA'):
                color = self.consume().value
        if self.check('BOLD'):
            self.consume('BOLD')
            style = 'bold'
        if self.peek().type in ('RED', 'GREEN', 'BLUE', 'YELLOW', 'CYAN', 'MAGENTA'):
            color = self.consume().value
        expr = self.parse_expression()
        self.consume('NEWLINE')
        node = Print(expression=expr, style=style, color=color)
        node.line = token.line
        return node
    def parse_progress_loop(self, start_token: Token) -> ProgressLoop:
        self.consume('PROGRESS')
        if not (self.check('FOR') or self.check('REPEAT') or self.check('LOOP')):
             raise SyntaxError(f"Expected loop after 'show progress' on line {start_token.line}")
        if self.check('FOR') or self.check('LOOP'):
            loop_node = self.parse_for()
        else:
            loop_node = self.parse_repeat()
        node = ProgressLoop(loop_node)
        node.line = start_token.line
        return node
    def parse_serve(self) -> ServeStatic:
        token = self.consume('SERVE')
        if self.check('FILES'):
            self.consume('FILES')
            if self.check('FROM'):
                self.consume('FROM')
            folder = self.parse_expression()
            url = String('/static')
            if self.check('AT'):
                self.consume('AT')
                url = self.parse_expression()
            if self.check('FOLDER'):
                self.consume('FOLDER')
            self.consume('NEWLINE')
            node = ServeStatic(folder, url)
            node.line = token.line
            return node
        self.consume('STATIC')
        folder = self.parse_expression()
        self.consume('AT')
        url = self.parse_expression()
        self.consume('NEWLINE')
        node = ServeStatic(folder, url)
        node.line = token.line
        return node
    def parse_listen(self) -> Listen:
        token = self.consume('LISTEN')
        if self.check('ON'): self.consume('ON')
        if self.check('PORT'): self.consume('PORT')
        port_num = self.parse_expression()
        self.consume('NEWLINE')
        node = Listen(port_num)
        node.line = token.line
        return node
    def parse_every(self) -> Every:
        token = self.consume('EVERY')
        interval = self.parse_expression()
        unit = 'seconds'
        if self.check('MINUTE'): 
            self.consume()
            unit = 'minutes'
        elif self.check('SECOND'):
            self.consume()
            unit = 'seconds'
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = Every(interval, unit, body)
        node.line = token.line
        return node
    def parse_after(self) -> After:
        token = self.consume('IN')
        delay = self.parse_expression()
        unit = 'seconds'
        if self.check('MINUTE'):
            self.consume()
            unit = 'minutes'
        elif self.check('SECOND'):
            self.consume()
            unit = 'seconds'
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = After(delay, unit, body)
        node.line = token.line
        return node
    def parse_define_page(self) -> Node:
        token = self.consume('DEFINE')
        if self.check('PAGE'):
            self.consume('PAGE')
        name = self.consume('ID').value
        args = []
        if self.check('USING'):
            self.consume('USING')
            args.append((self.consume('ID').value, None, None))
            while self.check('COMMA'):
                self.consume('COMMA')
                args.append((self.consume('ID').value, None, None))
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = FunctionDef(name, args, body)
        node.line = token.line
        return node
    def parse_add_to(self) -> Node:
        token = self.consume('ADD')
        item_expr = self.parse_factor_simple()
        if self.check('TO') or self.check('INTO'):
            self.consume()
        list_name = self.consume('ID').value
        self.consume('NEWLINE')
        list_access = VarAccess(list_name)
        item_list = ListVal([item_expr])
        concat = BinOp(list_access, '+', item_list)
        node = Assign(list_name, concat)
        node.line = token.line
        return node
    def parse_start_server(self) -> Node:
        token = self.consume('START')
        if self.check('SERVER'):
            self.consume('SERVER')
        port = Number(8080)
        if self.check('ON'):
            self.consume('ON')
            if self.check('PORT'):
                self.consume('PORT')
            port = self.parse_expression()
        self.consume('NEWLINE')
        node = Listen(port)
        node.line = token.line
        return node
    def parse_heading(self) -> Node:
        token = self.consume('HEADING')
        text = self.parse_expression()
        self.consume('NEWLINE')
        node = Call('h1', [text])
        node.line = token.line
        return node
    def parse_paragraph(self) -> Node:
        token = self.consume('PARAGRAPH')
        text = self.parse_expression()
        self.consume('NEWLINE')
        node = Call('p', [text])
        node.line = token.line
        return node
    def parse_assign(self) -> Assign:
        name = self.consume('ID').value
        self.consume('ASSIGN')
        value = self.parse_expression()
        self.consume('NEWLINE')
        return Assign(name, value)
    def parse_import(self) -> Node:
        token = self.consume('USE')
        
        # Check for Python Import: use python "numpy" as np
        if self.check('ID') and self.peek().value == 'python':
             self.consume('ID') # consume 'python'
             if self.check('STRING'):
                 module_name = self.consume('STRING').value
                 alias = None
                 if self.check('AS'):
                     self.consume('AS')
                     alias = self.consume('ID').value
                 self.consume('NEWLINE')
                 node = PythonImport(module_name, alias)
                 node.line = token.line
                 return node
             else:
                 raise SyntaxError(f"Expected module name string after 'use python' at line {token.line}")

        if self.check('STRING'):
            path = self.consume('STRING').value
        else:
             path = self.consume('ID').value
        if self.check('AS'):
            self.consume('AS')
            alias = self.consume('ID').value
            self.consume('NEWLINE')
            node = ImportAs(path, alias)
        else:
            self.consume('NEWLINE')
            node = Import(path)
        node.line = token.line
        return node
    def parse_if(self) -> If:
        self.consume('IF')
        condition = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        else_body = None
        if self.check('ELIF'):
            else_body = [self.parse_elif()]
        elif self.check('ELSE'):
            self.consume('ELSE')
            self.consume('NEWLINE')
            self.consume('INDENT')
            else_body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                else_body.append(self.parse_statement())
            self.consume('DEDENT')
        return If(condition, body, else_body)
    def parse_elif(self) -> If:
        token = self.consume('ELIF')
        condition = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        else_body = None
        if self.check('ELIF'):
            else_body = [self.parse_elif()]
        elif self.check('ELSE'):
            self.consume('ELSE')
            self.consume('NEWLINE')
            self.consume('INDENT')
            else_body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                else_body.append(self.parse_statement())
            self.consume('DEDENT')
        node = If(condition, body, else_body)
        node.line = token.line
        node = If(condition, body, else_body)
        node.line = token.line
        return node
    def parse_while(self) -> While:
        start_token = self.consume('WHILE')
        condition = self.parse_expression()
        self.consume('NEWLINE')
        self.consume('INDENT')
        body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            body.append(self.parse_statement())
        self.consume('DEDENT')
        node = While(condition, body)
        node.line = start_token.line
        return node
    def parse_try(self) -> Try:
        start_token = self.consume('TRY')
        self.consume('NEWLINE')
        self.consume('INDENT')
        try_body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            try_body.append(self.parse_statement())
        self.consume('DEDENT')
        self.consume('CATCH')
        catch_var = self.consume('ID').value
        self.consume('NEWLINE')
        self.consume('INDENT')
        catch_body = []
        while not self.check('DEDENT') and not self.check('EOF'):
            while self.check('NEWLINE'): self.consume()
            if self.check('DEDENT'): break
            catch_body.append(self.parse_statement())
        self.consume('DEDENT')
        always_body = []
        if self.check('ALWAYS'):
            self.consume('ALWAYS')
            self.consume('NEWLINE')
            self.consume('INDENT')
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                always_body.append(self.parse_statement())
            self.consume('DEDENT')
        if always_body:
            node = TryAlways(try_body, catch_var, catch_body, always_body)
        else:
            node = Try(try_body, catch_var, catch_body)
        node.line = start_token.line
        return node
    def parse_list(self) -> Node:
        token = self.consume('LBRACKET')
        def skip_formatted():
            while self.check('NEWLINE') or self.check('INDENT') or self.check('DEDENT'):
                self.consume()
        skip_formatted()
        if self.check('RBRACKET'):
            self.consume('RBRACKET')
            node = ListVal([])
            node.line = token.line
            return node
        if self.check('DOTDOTDOT'):
             node = self._parse_list_with_spread(token)
             skip_formatted()
             return node
        first_expr = self.parse_expression()
        skip_formatted()
        if self.check('FOR'):
            self.consume('FOR')
            var_name = self.consume('ID').value
            self.consume('IN')
            iterable = self.parse_expression()
            condition = None
            if self.check('IF'):
                self.consume('IF')
                condition = self.parse_expression()
            self.consume('RBRACKET')
            node = ListComprehension(first_expr, var_name, iterable, condition)
            node.line = token.line
            return node
        elements = [first_expr]
        while self.check('COMMA'):
            self.consume('COMMA')
            skip_formatted()
            if self.check('RBRACKET'):
                break  
            if self.check('DOTDOTDOT'):
                self.consume('DOTDOTDOT')
                spread_val = self.parse_expression()
                spread_node = Spread(spread_val)
                spread_node.line = token.line
                elements.append(spread_node)
            else:
                elements.append(self.parse_expression())
            skip_formatted()
        skip_formatted()
        self.consume('RBRACKET')
        node = ListVal(elements)
        node.line = token.line
        return node
    def _parse_list_with_spread(self, token: Token) -> ListVal:
        elements = []
        self.consume('DOTDOTDOT')
        spread_val = self.parse_expression()
        spread_node = Spread(spread_val)
        spread_node.line = token.line
        elements.append(spread_node)
        while self.check('COMMA'):
            self.consume('COMMA')
            if self.check('RBRACKET'):
                break
            if self.check('DOTDOTDOT'):
                self.consume('DOTDOTDOT')
                spread_val = self.parse_expression()
                spread_node = Spread(spread_val)
                spread_node.line = token.line
                elements.append(spread_node)
            else:
                elements.append(self.parse_expression())
        self.consume('RBRACKET')
        node = ListVal(elements)
        node.line = token.line
        return node
    def parse_dict(self) -> Dictionary:
        token = self.consume('LBRACE')
        def skip_formatted():
            while self.check('NEWLINE') or self.check('INDENT') or self.check('DEDENT'):
                self.consume()
        skip_formatted()
        pairs = []
        if not self.check('RBRACE'):
            if self.check('ID') and self.peek(1).type == 'COLON':
                key_token = self.consume('ID')
                key = String(key_token.value)
                key.line = key_token.line
            else:
                key = self.parse_expression()
            self.consume('COLON')
            skip_formatted()
            value = self.parse_expression()
            pairs.append((key, value))
            skip_formatted()
            while self.check('COMMA'):
                self.consume('COMMA')
                skip_formatted()
                if self.check('RBRACE'): break
                if self.check('ID') and self.peek(1).type == 'COLON':
                    key_token = self.consume('ID')
                    key = String(key_token.value)
                    key.line = key_token.line
                else:
                    key = self.parse_expression()
                self.consume('COLON')
                skip_formatted()
                value = self.parse_expression()
                pairs.append((key, value))
                skip_formatted()
        skip_formatted()
        self.consume('RBRACE')
        node = Dictionary(pairs)
        node.line = token.line
        return node
    def parse_app(self) -> Node:
        token = self.consume('APP')
        title = self.consume('STRING').value
        
        width = 500
        height = 400
        if self.check('SIZE'):
            self.consume('SIZE')
            width = int(self.consume('NUMBER').value)
            height = int(self.consume('NUMBER').value)
        
        self.consume('COLON')
        self.consume('NEWLINE')
        self.consume('INDENT')
        
        body = []
        while not self.check('DEDENT'):
            body.append(self.parse_ui_block())
            if self.check('NEWLINE'):
                self.consume('NEWLINE')
        
        self.consume('DEDENT')
        return App(title, width, height, body)

    def parse_ui_block(self) -> Node:
        token = self.peek()
        
        if token.type in ('COLUMN', 'ROW'):
            layout_type = self.consume().value # column or row
            self.consume('COLON')
            self.consume('NEWLINE')
            self.consume('INDENT')
            children = []
            while not self.check('DEDENT'):
               children.append(self.parse_ui_block())
               if self.check('NEWLINE'): self.consume('NEWLINE')
            self.consume('DEDENT')
            return Layout(layout_type, children)
            
        elif token.type in ('BUTTON', 'INPUT', 'HEADING', 'TEXT'):
            widget_type = self.consume().value
            label = self.consume('STRING').value
            
            var_name = None
            if self.check('AS'):
                self.consume('AS')
                var_name = self.consume('ID').value
                
            event_handler = None
            if token.type == 'BUTTON' and self.check('DO'):
                self.consume('DO')
                self.consume('COLON')
                self.consume('NEWLINE')
                self.consume('INDENT')
                event_handler = []
                while not self.check('DEDENT'):
                    event_handler.append(self.parse_statement())
                self.consume('DEDENT')
            
            return Widget(widget_type, label, var_name, event_handler)
            
        else:
            raise SyntaxError(f"Unexpected token in UI block: {token.type} at line {token.line}")

    def parse_factor_simple(self) -> Node:
        token = self.peek()
        if token.type == 'NUMBER':
            self.consume()
            val = token.value
            if '.' in val:
                node = Number(float(val))
            else:
                node = Number(int(val))
            node.line = token.line
            return node
        elif token.type == 'STRING':
            self.consume()
            val = token.value
            if '{' in val and '}' in val:
                parts = re.split(r'\{([^}]+)\}', val)
                if len(parts) == 1:
                     node = String(val)
                     node.line = token.line
                     return node
                current_node = None
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        if not part: continue 
                        expr = String(part)
                        expr.line = token.line
                    else:
                        snippet = part.strip()
                        if snippet:
                            sub_lexer = Lexer(snippet)
                            sub_tokens = sub_lexer.tokenize() 
                            sub_parser = Parser(sub_tokens)
                            try:
                                expr = sub_parser.parse_expression()
                                expr.line = token.line
                            except Exception as e:
                                raise SyntaxError(f"Invalid interpolation expression: '{snippet}' on line {token.line}")
                        else:
                            continue
                    if current_node is None:
                        current_node = expr
                    else:
                        current_node = BinOp(current_node, '+', expr)
                        current_node.line = token.line
                return current_node if current_node else String("")
            node = String(token.value)
            node.line = token.line
            return node
        elif token.type == 'YES':
            self.consume()
            node = Boolean(True)
            node.line = token.line
            return node
        elif token.type == 'NO':
            self.consume()
            node = Boolean(False)
            node.line = token.line
            return node
        elif token.type == 'LBRACKET':
            return self.parse_list()
        elif token.type == 'LBRACE':
            return self.parse_dict()
        elif token.type == 'ID':
            self.consume()
            if self.check('DOT'):
                self.consume('DOT')
                prop_token = self.consume()
                prop = prop_token.value
                node = PropertyAccess(token.value, prop)
                node.line = token.line
                return node
            node = VarAccess(token.value)
            node.line = token.line
            return node
        elif token.type == 'LPAREN':
            self.consume()
            expr = self.parse_expression()
            self.consume('RPAREN')
            return expr
        elif token.type == 'INPUT' or token.type == 'ASK':
            is_tag = False
            next_t = self.peek(1)
            if next_t.type in ('ID', 'TYPE', 'STRING', 'NAME', 'VALUE', 'CLASS', 'STYLE', 'ONCLICK', 'SRC', 'HREF', 'ACTION', 'METHOD'):
                is_tag = True
            if is_tag:
                 return self.parse_id_start_statement(passed_name_token=token)
            self.consume()
            prompt = None
            if self.check('STRING'):
                prompt = self.consume('STRING').value
            node = Input(prompt)
            node.line = token.line
            return node
        raise SyntaxError(f"Unexpected argument token {token.type} at line {token.line}")
    def parse_factor(self) -> Node:
        token = self.peek()
        if token.type == 'MINUS':
            op = self.consume()
            right = self.parse_factor()
            node = UnaryOp('-', right)
            node.line = op.line
            return node
        elif token.type == 'NOT':
             op = self.consume()
             right = self.parse_factor()
             node = UnaryOp('not', right)
             node.line = op.line
             return node
        elif token.type == 'LPAREN':
             self.consume('LPAREN')
             node = self.parse_expression()
             self.consume('RPAREN')
             return node
        elif token.type == 'DB':
            return self.parse_db_op()
        elif token.type == 'SPAWN':
            op = self.consume()
            right = self.parse_factor()
            node = Spawn(right)
            node.line = op.line
            return node
        elif token.type == 'EXECUTE':
            op = self.consume()
            right = self.parse_expression()
            node = Call('run', [right])
            node.line = op.line
            return node
        elif token.type == 'COUNT' or token.type == 'HOW':
            token = self.consume()
            if token.type == 'HOW':
                self.consume('MANY')
            if self.check('OF'):
                self.consume('OF')
            expr = self.parse_expression()
            node = Call('len', [expr])
            node.line = token.line
            return node
        elif token.type == 'AWAIT':
            op = self.consume()
            right = self.parse_factor()
            node = Await(right)
            node.line = op.line
            return node
        elif token.type == 'CONVERT':
            return self.parse_convert()
        elif token.type == 'LOAD' and self.peek(1).type == 'CSV':
             self.consume('LOAD')
             self.consume('CSV')
             path = self.parse_factor() 
             node = CsvOp('load', None, path)
             node.line = token.line
             return node
        elif token.type == 'PASTE':
             token = self.consume('PASTE')
             self.consume('FROM')
             self.consume('CLIPBOARD')
             node = ClipboardOp('paste', None)
             node.line = token.line
             return node
        elif token.type == 'READ':
             token = self.consume('READ')
             self.consume('FILE')
             path = self.parse_factor()
             node = FileRead(path)
             node.line = token.line
             return node
        elif token.type == 'DATE':
             token = self.consume('DATE')
             s = self.consume('STRING').value
             node = DateOp(s)
             node.line = token.line
             return node
        elif token.type == 'TODAY':
             token = self.consume('TODAY')
             node = DateOp('today')
             node.line = token.line
             return node
        if token.type == 'NUMBER':
            self.consume()
            val = token.value
            if '.' in val:
                node = Number(float(val))
            else:
                node = Number(int(val))
            node.line = token.line
            return node
        elif token.type == 'REGEX':
            self.consume()
            node = Regex(token.value)
            node.line = token.line
            return node
        elif token.type == 'STRING':
            return self.parse_factor_simple()
        elif token.type == 'YES':
            self.consume()
            node = Boolean(True)
            node.line = token.line
            return node
        elif token.type == 'NO':
            self.consume()
            node = Boolean(False)
            node.line = token.line
            return node
        elif token.type == 'LBRACKET':
            return self.parse_list()
        elif token.type == 'LBRACE':
            return self.parse_dict()
        elif token.type == 'ID':
            if token.value == 'a':
                if self.peek(1).type == 'LIST' and self.peek(2).type == 'OF':
                    return self._parse_natural_list()
                elif self.peek(1).type == 'UNIQUE' and self.peek(2).type == 'SET' and self.peek(3).type == 'OF':
                    return self._parse_natural_set()
            self.consume()
            instance_name = token.value
            method_name = None
            if self.check('DOT'):
                self.consume('DOT')
                method_name = self.consume().value
            
            args = []
            # Check for C-style function call: func(arg1, arg2)
            if self.check('LPAREN'):
                self.consume('LPAREN')
                if not self.check('RPAREN'):
                    args.append(self.parse_expression())
                    while self.check('COMMA'):
                        self.consume('COMMA')
                        args.append(self.parse_expression())
                self.consume('RPAREN')
                if method_name:
                    node = MethodCall(instance_name, method_name, args)
                else:
                    node = Call(instance_name, args)
                node.line = token.line
                return node

            # Fallback to command-style arguments: func arg1 arg2
            # But only if NOT a property access (method_name w/o args is property access, 
            # but if it was method call it would use parens ideally, or spaces?)
            # Existing logic supported 'func arg1 arg2'.
            # We keep it for backward compatibility e.g. 'echo 123'.
            
            force_call = False
            while True:
                next_t = self.peek()
                # If we see LPAREN now, it's ambiguous if we didn't handle it above.
                # But 'func (1)' is func called with 1 arg which is (1).
                # 'func (1, 2)' would fail in old logic too.
                # So the above block handles the explicit invocation.
                # This loop is for 'func 1 2'.
                
                # Check for keywords or invalid start tokens
                if next_t.type not in ('NUMBER', 'STRING', 'REGEX', 'ID', 'LPAREN', 'INPUT', 'ASK', 'YES', 'NO', 'LBRACKET', 'LBRACE'):
                    break
                
                # Special case: if we see LPAREN, is it part of command args?
                # e.g. 'func (1+2)' -> args=[(1+2)].
                args.append(self.parse_factor_simple())

            if method_name:
                if args:
                    node = MethodCall(instance_name, method_name, args)
                else:
                    node = PropertyAccess(instance_name, method_name)
                node.line = token.line
                return node
            
            if args:
                node = Call(instance_name, args)
                node.line = token.line
                return node

            node = VarAccess(instance_name)
            node.line = token.line
            return node
        elif token.type == 'LPAREN':
            self.consume()
            expr = self.parse_expression()
            self.consume('RPAREN')
            return expr
        elif token.type == 'INPUT' or token.type == 'ASK':
            next_t = self.peek(1)
            if next_t.type in ('ID', 'TYPE', 'STRING', 'NAME', 'VALUE', 'CLASS', 'STYLE', 'ONCLICK', 'SRC', 'HREF', 'ACTION', 'METHOD'):
                self.consume() 
                return self.parse_id_start_statement(passed_name_token=token)
            self.consume()
            prompt = None
            if self.check('STRING'):
                prompt = self.consume('STRING').value
            node = Input(prompt)
            node.line = token.line
            return node
        elif token.type == 'PROMPT':
            self.consume()
            prompt_expr = self.parse_factor() 
            node = Prompt(prompt_expr)
            node.line = token.line
            return node
        elif token.type == 'CONFIRM':
            self.consume()
            prompt_expr = self.parse_factor()
            node = Confirm(prompt_expr)
            node.line = token.line
            return node
        elif token.type == 'MAKE':
            return self.parse_make_expr()
        raise SyntaxError(f"Unexpected token {token.type} at line {token.line}")
    def parse_for(self) -> Node:
        if self.check('LOOP'):
            start_token = self.consume('LOOP')
            count_expr = self.parse_expression()
            self.consume('TIMES')
            self.consume('NEWLINE')
            self.consume('INDENT')
            body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                body.append(self.parse_statement())
            self.consume('DEDENT')
            node = For(count_expr, body)
            node.line = start_token.line
            return node
        start_token = self.consume('FOR')
        if self.check('ID') and self.peek(1).type == 'IN':
            var_name = self.consume('ID').value
            self.consume('IN')
            if self.check('RANGE'):
                self.consume('RANGE')
                start_val = self.parse_expression()
                end_val = self.parse_expression()
                self.consume('NEWLINE')
                self.consume('INDENT')
                body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    body.append(self.parse_statement())
                self.consume('DEDENT')
                iterable = Call('range', [start_val, end_val])
                node = ForIn(var_name, iterable, body)
                node.line = start_token.line
                return node
            else:
                iterable = self.parse_expression()
                self.consume('NEWLINE')
                self.consume('INDENT')
                body = []
                while not self.check('DEDENT') and not self.check('EOF'):
                    while self.check('NEWLINE'): self.consume()
                    if self.check('DEDENT'): break
                    body.append(self.parse_statement())
                self.consume('DEDENT')
                node = ForIn(var_name, iterable, body)
                node.line = start_token.line
                return node
        else:
            count_expr = self.parse_expression()
            self.consume('IN')
            self.consume('RANGE')
            self.consume('NEWLINE')
            self.consume('INDENT')
            body = []
            while not self.check('DEDENT') and not self.check('EOF'):
                while self.check('NEWLINE'): self.consume()
                if self.check('DEDENT'): break
                body.append(self.parse_statement())
            self.consume('DEDENT')
            node = For(count_expr, body)
            node.line = start_token.line
            return node
    def parse_expression_stmt(self) -> Node:
        expr = self.parse_expression()
        self.consume('NEWLINE')
        node = Print(expression=expr)
        node.line = expr.line
        return node
    def parse_expression(self) -> Node:
        if self.check('FN'):
            return self.parse_lambda()
        return self.parse_ternary()
    def parse_lambda(self) -> Lambda:
        token = self.consume('FN')
        params = []
        while self.check('ID'):
            params.append(self.consume('ID').value)
        self.consume('ARROW')
        body = self.parse_expression()
        node = Lambda(params, body)
        node.line = token.line
        return node
    def parse_ternary(self) -> Node:
        condition = self.parse_logic_or()
        if self.check('QUESTION'):
            self.consume('QUESTION')
            true_expr = self.parse_expression()
            self.consume('COLON')
            false_expr = self.parse_expression()
            node = Ternary(condition, true_expr, false_expr)
            node.line = condition.line
            return node
        return condition
    def parse_logic_or(self) -> Node:
        left = self.parse_logic_and()
        while self.check('OR'):
            op_token = self.consume()
            right = self.parse_logic_and()
            new_node = BinOp(left, op_token.value, right)
            new_node.line = op_token.line
            left = new_node
        return left
    def parse_logic_and(self) -> Node:
        left = self.parse_comparison()
        while self.check('AND'):
            op_token = self.consume()
            right = self.parse_comparison()
            new_node = BinOp(left, op_token.value, right)
            new_node.line = op_token.line
            left = new_node
        return left
    def parse_comparison(self) -> Node:
        left = self.parse_arithmetic()
        if self.peek().type in ('EQ', 'NEQ', 'GT', 'LT', 'GE', 'LE', 'IS', 'MATCHES'):
            op_token = self.consume()
            op_val = op_token.value
            if op_token.type == 'IS':
                op_val = '==' 
            right = self.parse_arithmetic()
            node = BinOp(left, op_val, right)
            node.line = op_token.line
            return node
        return left
    def parse_arithmetic(self) -> Node:
        left = self.parse_term()
        while self.peek().type in ('PLUS', 'MINUS'):
            op_token = self.consume()
            right = self.parse_term()
            new_node = BinOp(left, op_token.value, right)
            new_node.line = op_token.line
            left = new_node
        return left
    def parse_term(self) -> Node:
        left = self.parse_factor()
        while self.peek().type in ('MUL', 'DIV', 'MOD'):
            op_token = self.consume()
            right = self.parse_factor()
            new_node = BinOp(left, op_token.value, right)
            new_node.line = op_token.line
            left = new_node
        return left
    def parse_convert(self) -> Convert:
        token = self.consume('CONVERT')
        expr = self.parse_factor() 
        self.consume('TO')
        target_format = 'json'
        if self.check('JSON'):
             self.consume('JSON')
        elif self.check('ID'):
             target_format = self.consume('ID').value
        node = Convert(expr, target_format)
        node.line = token.line
        return node
    def parse_download(self) -> Download:
        token = self.consume('DOWNLOAD')
        url = self.parse_expression()
        self.consume('NEWLINE')
        node = Download(url)
        node.line = token.line
        return node
    def parse_archive(self) -> ArchiveOp:
        op = None
        token = None
        if self.check('COMPRESS'):
            token = self.consume('COMPRESS')
            op = 'compress'
            if self.check('FOLDER'): self.consume('FOLDER')
        else:
            token = self.consume('EXTRACT')
            op = 'extract'
        source = self.parse_expression()
        self.consume('TO')
        target = self.parse_expression()
        self.consume('NEWLINE')
        node = ArchiveOp(op, source, target)
        node.line = token.line
        return node
    def parse_csv_load(self) -> CsvOp:
        token = self.consume('LOAD')
        self.consume('CSV')
        path = self.parse_expression()
        self.consume('NEWLINE')
        node = CsvOp('load', None, path)
        node.line = token.line
        return node
    def parse_csv_save(self) -> CsvOp:
         token = self.consume('SAVE')
         data = self.parse_expression()
         self.consume('TO')
         self.consume('CSV')
         path = self.parse_expression()
         self.consume('NEWLINE')
         node = CsvOp('save', data, path)
         node.line = token.line
         return node
    def parse_clipboard(self) -> Node:
        if self.check('COPY'):
            token = self.consume('COPY')
            content = self.parse_expression()
            self.consume('TO')
            self.consume('CLIPBOARD')
            self.consume('NEWLINE')
            node = ClipboardOp('copy', content)
            node.line = token.line
            return node
        else:
             token = self.consume('PASTE')
             self.consume('FROM')
             self.consume('CLIPBOARD')
             self.consume('NEWLINE')
             node = ClipboardOp('paste', None)
             node.line = token.line
             return node
    def parse_automation(self) -> AutomationOp:
         if self.check('PRESS'):
             token = self.consume('PRESS')
             keys = self.parse_expression()
             self.consume('NEWLINE')
             return AutomationOp('press', [keys])
         elif self.check('TYPE'):
             token = self.consume('TYPE')
             text = self.parse_expression()
             self.consume('NEWLINE')
             return AutomationOp('type', [text])
         elif self.check('CLICK'):
             token = self.consume('CLICK')
             self.consume('AT')
             x = self.parse_expression()
             if self.check('COMMA'): self.consume('COMMA') 
             y = self.parse_expression()
             self.consume('NEWLINE')
             return AutomationOp('click', [x, y])
         elif self.check('NOTIFY'):
             token = self.consume('NOTIFY')
             title = self.parse_expression()
             msg = self.parse_expression()
             self.consume('NEWLINE')
             return AutomationOp('notify', [title, msg])
    def parse_write(self) -> FileWrite:
        token = self.consume('WRITE')
        content = self.parse_expression()
        self.consume('TO')
        self.consume('FILE')
        path = self.parse_expression()
        self.consume('NEWLINE')
        node = FileWrite(path, content, 'w')
        node.line = token.line
        return node
    def parse_append(self) -> FileWrite:
        token = self.consume('APPEND')
        content = self.parse_expression()
        self.consume('TO')
        self.consume('FILE')
        path = self.parse_expression()
        self.consume('NEWLINE')
        node = FileWrite(path, content, 'a')
        node.line = token.line
        return node
