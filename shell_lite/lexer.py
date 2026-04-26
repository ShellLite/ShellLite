import re
from dataclasses import dataclass
from typing import List, Optional
@dataclass
@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int = 1
class Lexer:
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tokens: List[Token] = []
        self.current_char_index = 0
        self.line_number = 1
        self.indent_stack = [0]
    def tokenize(self) -> List[Token]:
        source = self._remove_multiline_comments(self.source_code)
        lines = source.split('\n')
        for line_num, line in enumerate(lines, 1):
            self.line_number = line_num
            stripped_line = line.strip()
            if not stripped_line:
                continue
            indent_level = len(line) - len(line.lstrip())
            if stripped_line.startswith('#'):
                # self.tokens.append(Token('COMMENT', stripped_line, self.line_number, indent_level + 1))
                # self.tokens.append(Token('NEWLINE', '', self.line_number, len(line) + 1))
                continue
            if indent_level > self.indent_stack[-1]:
                self.indent_stack.append(indent_level)
                self.tokens.append(Token('INDENT', '', self.line_number, indent_level + 1))
            elif indent_level < self.indent_stack[-1]:
                while indent_level < self.indent_stack[-1]:
                    self.indent_stack.pop()
                    self.tokens.append(Token('DEDENT', '', self.line_number, indent_level + 1))
                if indent_level != self.indent_stack[-1]:
                    raise IndentationError(f"Unindent does not match any outer indentation level on line {self.line_number}")
            self.tokenize_line(stripped_line, indent_level + 1)
            self.tokens.append(Token('NEWLINE', '', self.line_number, len(line) + 1))
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token('DEDENT', '', self.line_number, 1))
        self.tokens.append(Token('EOF', '', self.line_number, 1))
        return self.tokens
    def _remove_multiline_comments(self, source: str) -> str:
        result = []
        i = 0
        while i < len(source):
            if source[i:i+2] == '/*':
                end = source.find('*/', i + 2)
                if end == -1:
                    raise SyntaxError("Unterminated multi-line comment")
                comment = source[i:end+2]
                result.append('\n' * comment.count('\n'))
                i = end + 2
            else:
                result.append(source[i])
                i += 1
        return ''.join(result)
    def tokenize_line(self, line: str, start_col: int = 1):
        pos = 0
        while pos < len(line):
            match = None
            current_col = start_col + pos
            if line[pos] == '#':
                self.tokens.append(Token('COMMENT', line[pos:], self.line_number, current_col))
                break
            if line[pos].isspace():
                pos += 1
                continue
            if line[pos].isdigit():
                match = re.match(r'^\d+(\.\d+)?', line[pos:])
                if match:
                    value = match.group(0)
                    self.tokens.append(Token('NUMBER', value, self.line_number, current_col))
                    pos += len(value)
                    continue
            if line[pos:pos+3] in ('"""', "'''"):
                 quote_char = line[pos:pos+3]
                 pass
            if line[pos] in ('"', "'"):
                quote_char = line[pos]
                end_quote = line.find(quote_char, pos + 1)
                if end_quote == -1:
                    raise SyntaxError(f"Unterminated string on line {self.line_number}")
                value = line[pos+1:end_quote]
                value = value.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\\\"", "\"").replace("\\\'", "\'")
                self.tokens.append(Token('STRING', value, self.line_number, current_col))
                pos = end_quote + 1
                continue
            if line[pos:pos+3] == '...':
                self.tokens.append(Token('DOTDOTDOT', '...', self.line_number, current_col))
                pos += 3
                continue
            two_char = line[pos:pos+2]
            two_char_tokens = {
                '=>': 'ARROW', '==': 'EQ', '!=': 'NEQ',
                '<=': 'LE', '>=': 'GE', '+=': 'PLUSEQ',
                '-=': 'MINUSEQ', '*=': 'MULEQ', '/=': 'DIVEQ',
                '%=': 'MODEQ'
            }
            if two_char in two_char_tokens:
                self.tokens.append(Token(two_char_tokens[two_char], two_char, self.line_number, current_col))
                pos += 2
                continue
            char = line[pos]
            rest_of_line = line[pos:]
            if rest_of_line.startswith('is at least '):
                self.tokens.append(Token('GE', '>=', self.line_number, current_col))
                pos += 12 
                continue
            elif rest_of_line.startswith('is exactly '):
                self.tokens.append(Token('EQ', '==', self.line_number, current_col))
                pos += 11
                continue
            elif rest_of_line.startswith('is less than '):
                self.tokens.append(Token('LT', '<', self.line_number, current_col))
                pos += 13
                continue
            elif rest_of_line.startswith('is more than '):
                self.tokens.append(Token('GT', '>', self.line_number, current_col))
                pos += 13
                continue
            if rest_of_line.startswith('the') and (len(rest_of_line) == 3 or not rest_of_line[3].isalnum()):
                 pos += 3
                 continue
            if char == '/':
                last_type = self.tokens[-1].type if self.tokens else None
                is_division = False
                if last_type in ('NUMBER', 'STRING', 'ID', 'RPAREN', 'RBRACKET'):
                     is_division = True
                if not is_division:
                    end_slash = line.find('/', pos + 1)
                    if end_slash != -1:
                        pattern = line[pos+1:end_slash]
                        flags = ""
                        k = end_slash + 1
                        while k < len(line) and line[k].isalpha():
                            flags += line[k]
                            k += 1
                        self.tokens.append(Token('REGEX', pattern, self.line_number, current_col))
                        pos = k
                        continue
            single_char_tokens = {
                '+': 'PLUS', '-': 'MINUS', '*': 'MUL', '/': 'DIV',
                '%': 'MOD', '=': 'ASSIGN', '>': 'GT', '<': 'LT',
                '?': 'QUESTION', '(': 'LPAREN', ')': 'RPAREN',
                '[': 'LBRACKET', ']': 'RBRACKET', ':': 'COLON',
                '{': 'LBRACE', '}': 'RBRACE', ',': 'COMMA', '.': 'DOT'
            }
            if char in single_char_tokens:
                self.tokens.append(Token(single_char_tokens[char], char, self.line_number, current_col))
                pos += 1
                continue
            if char.isalpha() or char == '_':
                match = re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*', line[pos:])
                if match:
                    value = match.group(0)
                    keywords = {
                        'if': 'IF', 'else': 'ELSE', 'elif': 'ELIF',
                        'for': 'FOR', 'in': 'IN', 'range': 'RANGE',
                        'loop': 'LOOP', 'times': 'TIMES',
                        'while': 'WHILE', 'until': 'UNTIL',
                        'repeat': 'REPEAT', 'forever': 'FOREVER',
                        'stop': 'STOP', 'skip': 'SKIP', 'exit': 'EXIT',
                        'each': 'EACH',
                        'check': 'CHECK',
                        'unless': 'UNLESS', 'when': 'WHEN', 'otherwise': 'OTHERWISE',
                        'then': 'THEN', 'do': 'DO',
                        'print': 'PRINT', 'say': 'SAY', 'show': 'SAY',
                        'input': 'INPUT', 'ask': 'ASK',
                        'to': 'TO', 'can': 'TO',
                        'return': 'RETURN', 'give': 'RETURN',
                        'fn': 'FN',
                        'structure': 'STRUCTURE', 'thing': 'STRUCTURE', 'class': 'STRUCTURE',
                        'has': 'HAS', 'with': 'WITH',
                        'is': 'IS', 'extends': 'EXTENDS', 'from': 'FROM',
                        'make': 'MAKE', 'new': 'MAKE',
                        'yes': 'YES', 'no': 'NO',
                        'true': 'YES', 'false': 'NO',
                        'const': 'CONST',
                        'and': 'AND', 'or': 'OR', 'not': 'NOT',
                        'try': 'TRY', 'catch': 'CATCH', 'always': 'ALWAYS', 'finally': 'ALWAYS',
                        'use': 'USE', 'as': 'AS', 'share': 'SHARE',
                        'import': 'IMPORT',
                        'execute': 'EXECUTE', 'run': 'EXECUTE',
                        'alert': 'ALERT', 'prompt': 'PROMPT', 'confirm': 'CONFIRM',
                        'spawn': 'SPAWN', 'await': 'AWAIT',
                        'matches': 'MATCHES',
                        'on': 'ON',
                        'download': 'DOWNLOAD',
                        'compress': 'COMPRESS', 'extract': 'EXTRACT', 'folder': 'FOLDER',
                        'load': 'LOAD', 'save': 'SAVE', 'csv': 'CSV',
                        'copy': 'COPY', 'paste': 'PASTE', 'clipboard': 'CLIPBOARD',
                        'press': 'PRESS', 'type': 'TYPE', 'click': 'CLICK', 'at': 'AT',
                        'notify': 'NOTIFY',
                        'date': 'ID', 'today': 'ID', 'after': 'AFTER', 'before': 'BEFORE',
                        'list': 'LIST', 'set': 'SET', 'unique': 'UNIQUE', 'of': 'OF',
                        'wait': 'WAIT',
                        'convert': 'CONVERT', 'json': 'JSON',
                        'listen': 'LISTEN', 'port': 'PORT',
                        'every': 'EVERY', 'minute': 'MINUTE', 'minutes': 'MINUTE',
                        'second': 'SECOND', 'seconds': 'SECOND',
                        'progress': 'PROGRESS',
                        'bold': 'BOLD',
                        'red': 'RED', 'green': 'GREEN', 'blue': 'BLUE', 
                        'yellow': 'YELLOW', 'cyan': 'CYAN', 'magenta': 'MAGENTA',
                        'serve': 'SERVE', 'static': 'STATIC',
                        'write': 'WRITE', 'append': 'APPEND', 'read': 'READ', 'file': 'FILE',
                        'write': 'WRITE', 'append': 'APPEND', 'read': 'READ', 'file': 'FILE',
                        'db': 'DB', 'database': 'DB',
                        'query': 'QUERY', 'open': 'OPEN', 'close': 'CLOSE', 'exec': 'EXEC',
                        'middleware': 'MIDDLEWARE', 'before': 'BEFORE',
                        'when': 'WHEN', 'someone': 'SOMEONE', 'visits': 'VISITS', 
                        'submits': 'SUBMITS', 'start': 'START', 'server': 'SERVER',
                        'files': 'FILES',
                        'define': 'DEFINE', 'page': 'PAGE', 'called': 'CALLED',
                        'using': 'USING', 'component': 'PAGE',
                        'heading': 'HEADING', 'paragraph': 'PARAGRAPH',
                        'image': 'IMAGE',
                        'add': 'ADD', 'put': 'ADD', 'into': 'INTO', 'push': 'ADD',
                        'count': 'COUNT', 'many': 'MANY', 'how': 'HOW',
                        'field': 'FIELD', 'submit': 'SUBMIT', 'named': 'NAMED',
                        'placeholder': 'PLACEHOLDER',
                        'app': 'APP', 'title': 'ID', 'size': 'SIZE',
                        'column': 'COLUMN', 'row': 'ROW',
                        'button': 'BUTTON', 'heading': 'HEADING', 
                        'sum': 'SUM', 'upper': 'UPPER', 'lower': 'LOWER',
                        'increment': 'INCREMENT', 'decrement': 'DECREMENT',
                        'multiply': 'MULTIPLY', 'divide': 'DIVIDE',
                        'subtract': 'SUBTRACT',
                        'be': 'BE', 'by': 'BY',
                        'plus': 'PLUS', 'minus': 'MINUS', 'divided': 'DIV',
                        'greater': 'GREATER', 'less': 'LESS', 'equal': 'EQUAL',
                        'define': 'DEFINE', 'function': 'FUNCTION',
                        'contains': 'CONTAINS', 'empty': 'EMPTY',
                        'remove': 'REMOVE',
                        'than': 'THAN',
                        'doing': 'DOING',
                        'make': 'MAKE', 'be': 'BE',
                        'as': 'AS', 'long': 'LONG',
                        'otherwise': 'OTHERWISE',
                        'ask': 'ASK',
                    }
                    token_type = keywords.get(value, 'ID')
                    self.tokens.append(Token(token_type, value, self.line_number, current_col))
                    pos += len(value)
                    continue
            if char in single_char_tokens:
                self.tokens.append(Token(single_char_tokens[char], char, self.line_number, current_col))
                pos += 1
                continue
            raise SyntaxError(f"Illegal character '{char}' at line {self.line_number}")
