"""
Lexical Analysis module for ShellLite. Tokenizes source code.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Token:
    """
    Represents a lexical token

    Attributes:
        type (str): The classification of the token
        value (str): The literal string value from the source code.
        line (int): The line number where the token appears.
        column (int): The starting column of the token.
    """
    type: str
    value: str
    line: int
    column: int = 1

    def __post_init__(self) -> None:
        assert isinstance(self.type, str), f"Token type must be str, got {type(self.type)}"
        assert isinstance(self.value, str), f"Token value must be str, got {type(self.value)}"
        assert isinstance(self.line, int) and self.line > 0, "Token line must be a positive integer"
        assert isinstance(self.column, int) and self.column > 0, "Token column must be a positive integer"


class Lexer:
    """
    Tokenizes source code strings into discrete Token objects.
    Produces a list of Tokens from source code while managing 
    indentation levels and bracket depth.
    """

    KEYWORDS: Dict[str, str] = {
        'if': 'IF', 'else': 'ELSE', 'elif': 'ELIF',
        'for': 'FOR', 'in': 'IN', 'range': 'RANGE',
        'loop': 'LOOP', 'times': 'TIMES',
        'while': 'WHILE', 'until': 'UNTIL',
        'repeat': 'REPEAT', 'forever': 'FOREVER',
        'stop': 'STOP', 'skip': 'SKIP', 'exit': 'EXIT',
        'each': 'EACH', 'check': 'CHECK', 'unless': 'UNLESS',
        'when': 'WHEN', 'otherwise': 'OTHERWISE', 'then': 'THEN', 'do': 'DO',
        'begin': 'BEGIN', 'end': 'END', 'print': 'PRINT', 'say': 'SAY',
        'show': 'SAY', 'input': 'INPUT', 'ask': 'ASK', 'to': 'TO',
        'can': 'TO', 'return': 'RETURN', 'give': 'RETURN', 'fn': 'FN',
        'structure': 'STRUCTURE', 'thing': 'STRUCTURE', 'class': 'STRUCTURE',
        'has': 'HAS', 'with': 'WITH', 'is': 'IS', 'extends': 'EXTENDS',
        'from': 'FROM', 'make': 'MAKE', 'new': 'MAKE', 'the': 'NOISE',
        'let': 'NOISE', 'please': 'NOISE', 'yes': 'YES', 'no': 'NO',
        'true': 'YES', 'false': 'NO', 'const': 'CONST', 'and': 'AND',
        'or': 'OR', 'not': 'NOT', 'try': 'TRY', 'catch': 'CATCH',
        'always': 'ALWAYS', 'finally': 'ALWAYS', 'error': 'ERROR',
        'use': 'USE', 'as': 'AS', 'share': 'SHARE', 'import': 'IMPORT',
        'execute': 'EXECUTE', 'run': 'EXECUTE', 'alert': 'ALERT',
        'prompt': 'PROMPT', 'confirm': 'CONFIRM', 'spawn': 'SPAWN',
        'await': 'AWAIT', 'matches': 'MATCHES', 'on': 'ON',
        'download': 'DOWNLOAD', 'compress': 'COMPRESS', 'extract': 'EXTRACT',
        'folder': 'FOLDER', 'load': 'LOAD', 'save': 'SAVE', 'csv': 'CSV',
        'copy': 'COPY', 'paste': 'PASTE', 'clipboard': 'CLIPBOARD',
        'press': 'PRESS', 'type': 'TYPE', 'click': 'CLICK', 'at': 'AT',
        'notify': 'NOTIFY', 'after': 'AFTER', 'before': 'BEFORE',
        'list': 'LIST', 'set': 'SET', 'unique': 'UNIQUE', 'of': 'OF',
        'wait': 'WAIT', 'convert': 'CONVERT', 'json': 'JSON', 'http': 'HTTP',
        'listen': 'LISTEN', 'port': 'PORT', 'every': 'EVERY',
        'minute': 'MINUTE', 'minutes': 'MINUTE', 'second': 'SECOND',
        'seconds': 'SECOND', 'progress': 'PROGRESS', 'bold': 'BOLD',
        'red': 'RED', 'green': 'GREEN', 'blue': 'BLUE', 'yellow': 'YELLOW',
        'cyan': 'CYAN', 'magenta': 'MAGENTA', 'serve': 'SERVE',
        'static': 'STATIC', 'write': 'WRITE', 'append': 'APPEND',
        'read': 'READ', 'file': 'FILE', 'db': 'DB', 'database': 'DB',
        'query': 'QUERY', 'open': 'OPEN', 'close': 'CLOSE', 'exec': 'EXEC',
        'middleware': 'MIDDLEWARE', 'someone': 'SOMEONE', 'visits': 'VISITS',
        'submits': 'SUBMITS', 'start': 'START', 'server': 'SERVER',
        'files': 'FILES', 'define': 'DEFINE', 'page': 'PAGE',
        'called': 'CALLED', 'using': 'USING', 'component': 'PAGE',
        'heading': 'HEADING', 'paragraph': 'PARAGRAPH', 'image': 'IMAGE',
        'add': 'ADD', 'put': 'ADD', 'into': 'INTO', 'push': 'ADD',
        'many': 'MANY', 'how': 'HOW', 'field': 'FIELD', 'submit': 'SUBMIT',
        'named': 'NAMED', 'placeholder': 'PLACEHOLDER', 'app': 'APP',
        'size': 'SIZE', 'button': 'BUTTON', 'upper': 'UPPER',
        'lower': 'LOWER', 'increment': 'INCREMENT', 'decrement': 'DECREMENT',
        'multiply': 'MULTIPLY', 'divide': 'DIVIDE', 'subtract': 'SUBTRACT',
        'be': 'BE', 'by': 'BY', 'plus': 'PLUS', 'minus': 'MINUS',
        'divided': 'DIV', 'greater': 'GREATER', 'less': 'LESS',
        'equal': 'EQUAL', 'function': 'FUNCTION', 'contains': 'CONTAINS',
        'empty': 'EMPTY', 'than': 'THAN', 'doing': 'DOING', 'long': 'LONG',
        'test': 'TEST', 'expect': 'EXPECT', 'ensure': 'ENSURE',
        'parallel': 'PARALLEL', 'gather': 'GATHER', 'lock': 'LOCK',
        'channel': 'CHANNEL', 'send': 'SEND', 'receive': 'RECEIVE',
        'model': 'MODEL', 'create': 'CREATE', 'table': 'TABLE',
        'insert': 'INSERT', 'find': 'FIND', 'update': 'UPDATE',
        'delete': 'DELETE', 'where': 'WHERE', 'count': 'COUNT',
        'maximum': 'MAX', 'minimum': 'MIN', 'clamped': 'CLAMPED',
        'between': 'BETWEEN', 'lerp': 'LERP',
    }

    TOKEN_SPECS = [
        ('COMMENT', re.compile(r'#.*')),
        ('NUMBER', re.compile(r'\d+(\.\d+)?')),
        ('STRING', re.compile(r'\"([^\\\"]|\\.)*\"|\'([^\\\']|\\.)*\'')),
        ('DOTDOTDOT', re.compile(r'\.\.\.')),
        # Multi-word operators (longest first to avoid partial matches)
        ('GE', re.compile(r'is\s+at\s+least\b')),
        ('EQ', re.compile(r'is\s+exactly\b')),
        ('LT', re.compile(r'is\s+less\s+than\b')),
        ('GT', re.compile(r'is\s+more\s+than\b')),
        ('NOTIN', re.compile(r'(?:is\s+not\s+in|not\s+in)\b')),
        ('NEQ', re.compile(r'is\s+not\b')),
        ('IN', re.compile(r'is\s+in\b')),
        # Two-character operators
        ('ARROW', re.compile(r'=>')),
        ('EQ', re.compile(r'==')),
        ('NEQ', re.compile(r'!=')),
        ('LE', re.compile(r'<=')),
        ('GE', re.compile(r'>=')),
        ('PLUSEQ', re.compile(r'\+=')),
        ('MINUSEQ', re.compile(r'-=')),
        ('MULEQ', re.compile(r'\*=')),
        ('DIVEQ', re.compile(r'/=')),
        ('MODEQ', re.compile(r'%=')),
        # Identifiers
        ('ID', re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')),
        # Single-character operators
        ('PLUS', re.compile(r'\+')),
        ('MINUS', re.compile(r'-')),
        ('MUL', re.compile(r'\*')),
        ('DIV', re.compile(r'/')),
        ('MOD', re.compile(r'%')),
        ('ASSIGN', re.compile(r'=')),
        ('GT', re.compile(r'>')),
        ('LT', re.compile(r'<')),
        ('QUESTION', re.compile(r'\?')),
        ('LPAREN', re.compile(r'\(')),
        ('RPAREN', re.compile(r'\)')),
        ('LBRACKET', re.compile(r'\[')),
        ('RBRACKET', re.compile(r'\]')),
        ('LBRACE', re.compile(r'\{')),
        ('RBRACE', re.compile(r'\}')),
        ('COLON', re.compile(r':')),
        ('COMMA', re.compile(r',')),
        ('DOT', re.compile(r'\.')),
    ]

    def __init__(self, source_code: str) -> None:
        """
        Initialize the lexer with source code and reset state.
        """
        assert isinstance(source_code, str), "source_code must be a string"
        self.source_code: str = source_code
        self.tokens: List[Token] = []
        self.line_number: int = 1
        self.indent_stack: List[int] = [0]
        self.bracket_depth: int = 0

    def tokenize_line_only(self) -> List[Token]:
        """Tokenize a single line without handling INDENT/DEDENT/NEWLINE."""
        self.tokens = []
        stripped_line = self.source_code.strip()
        if not stripped_line or stripped_line.startswith('#'):
            return []
        
        start_pos = len(self.source_code) - len(self.source_code.lstrip())
        self.tokenize_line(self.source_code, start_pos)
        return self.tokens

    def tokenize(self) -> List[Token]:
        """
        Main entry point for tokenization. Processes each line and 
        manages indentation levels.
        """
        source = self._remove_multiline_comments(self.source_code)
        lines = source.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            self.line_number = line_num
            stripped_line = line.strip()
            
            if not stripped_line:
                continue
                
            if stripped_line.startswith('#'):
                continue

            indent_level = len(line) - len(line.lstrip())
            
            # Indentation/Dedentation logic (only when not inside brackets)
            if self.bracket_depth == 0:
                if indent_level > self.indent_stack[-1]:
                    self.indent_stack.append(indent_level)
                    self.tokens.append(Token('INDENT', '', self.line_number, indent_level + 1))
                elif indent_level < self.indent_stack[-1]:
                    while indent_level < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        self.tokens.append(Token('DEDENT', '', self.line_number, indent_level + 1))
                    if indent_level != self.indent_stack[-1]:
                        raise IndentationError(
                            f"Unindent does not match any outer indentation level on line {self.line_number}"
                        )

            self.tokenize_line(line, indent_level)
            
            # Newlines are only meaningful outside brackets
            if self.bracket_depth == 0:
                self.tokens.append(Token('NEWLINE', '', self.line_number, len(line) + 1))

        # Emit any remaining dedents at the end of the file
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token('DEDENT', '', self.line_number, 1))
            
        self.tokens.append(Token('EOF', '', self.line_number, 1))
        self.tokens = self._convert_begin_end(self.tokens)
        return self.tokens

    def tokenize_line(self, line: str, start_pos: int):
        """
        Processes a single line of code into discrete tokens.
        """
        pos = start_pos
        while pos < len(line):
            if line[pos].isspace():
                pos += 1
                continue

            # Context-sensitive handling for Regex literals
            if line[pos] == '/':
                if self._is_regex_start():
                    regex_token = self._match_regex(line, pos)
                    if regex_token:
                        self.tokens.append(regex_token)
                        pos += len(regex_token.value) + 2 # +2 for slashes
                        # Consume optional regex flags
                        while pos < len(line) and line[pos].isalpha():
                            pos += 1
                        continue

            # Regex-based pattern matching
            matched = False
            for token_type, pattern in self.TOKEN_SPECS:
                match = pattern.match(line, pos)
                if match:
                    value = match.group(0)
                    col = pos + 1
                    
                    if token_type == 'ID':
                        token_type = self.KEYWORDS.get(value, 'ID')
                    elif token_type == 'STRING':
                        value = self._process_string_literal(value)
                    
                    # Normalize multi-word operator values
                    normalization_map = {
                        'GE': '>=', 'EQ': '==', 'LT': '<', 'GT': '>',
                        'NEQ': '!=', 'NOTIN': 'not in', 'IN': 'in'
                    }
                    if token_type in normalization_map and ' ' in value:
                        value = normalization_map[token_type]
                    
                    self.tokens.append(Token(token_type, value, self.line_number, col))
                    
                    # Track bracket depth for indentation management
                    if token_type in ('LPAREN', 'LBRACKET', 'LBRACE'):
                        self.bracket_depth += 1
                    elif token_type in ('RPAREN', 'RBRACKET', 'RBRACE'):
                        self.bracket_depth = max(0, self.bracket_depth - 1)
                        
                    pos += len(match.group(0))
                    matched = True
                    break
            
            if not matched:
                raise SyntaxError(
                    f"Illegal character '{line[pos]}' at line {self.line_number}, column {pos + 1}"
                )

    def _is_regex_start(self) -> bool:
        """
        Heuristic to determine if '/' starts a regex or is a division operator.
        """
        if not self.tokens:
            return True
        last_token = self.tokens[-1]
        return last_token.type not in ('NUMBER', 'STRING', 'ID', 'RPAREN', 'RBRACKET')

    def _match_regex(self, line: str, pos: int) -> Optional[Token]:
        """
        Attempts to match a regex literal /.../.
        """
        end_slash = line.find('/', pos + 1)
        if end_slash != -1:
            pattern = line[pos + 1:end_slash]
            return Token('REGEX', pattern, self.line_number, pos + 1)
        return None

    def _process_string_literal(self, value: str) -> str:
        """
        Removes quotes and processes escape sequences in a string literal.
        """
        content = value[1:-1]
        escapes = {
            '\\n': '\n', '\\t': '\t', '\\r': '\r',
            '\\"': '"', "\\'": "'", '\\\\': '\\'
        }
        for esc, rel in escapes.items():
            content = content.replace(esc, rel)
        return content

    def _remove_multiline_comments(self, source: str) -> str:
        """
        Strips multiline /* ... */ comments from the source code.
        """
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

    def _convert_begin_end(self, tokens: List[Token]) -> List[Token]:
        """
        Converts BEGIN/END keywords to INDENT/DEDENT for parser consistency.
        """
        result = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == 'BEGIN':
                if result and result[-1].type == 'NEWLINE':
                    result.pop()
                result.append(Token('INDENT', '', token.line, token.column))
            elif token.type == 'END':
                result.append(Token('DEDENT', '', token.line, token.column))
                if i + 1 < len(tokens) and tokens[i + 1].type == 'NEWLINE':
                    i += 1
            else:
                result.append(token)
            i += 1
        return result
