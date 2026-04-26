from typing import List
from .lexer import Lexer, Token
class Formatter:
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.indent_size = 4
    def format(self) -> str:
        lexer = Lexer(self.source_code)
        try:
            tokens = lexer.tokenize()
        except Exception:
            raise
        formatted_lines = []
        current_indent = 0
        current_line_tokens: List[Token] = []
        def flush_line():
            nonlocal current_line_tokens
            if not current_line_tokens:
                pass
            line_str = self._format_line_tokens(current_line_tokens, current_indent)
            formatted_lines.append(line_str)
            current_line_tokens.clear()
        for token in tokens:
            if token.type == 'EOF':
                if current_line_tokens:
                    flush_line()
                break
            elif token.type == 'INDENT':
                current_indent += 1
            elif token.type == 'DEDENT':
                current_indent -= 1
                if current_indent < 0: current_indent = 0
            elif token.type == 'NEWLINE':
                flush_line()
                pass
            else:
                current_line_tokens.append(token)
        return '\n'.join(formatted_lines)
    def _format_line_tokens(self, tokens: List[Token], indent_level: int) -> str:
        if not tokens:
            return ''
        line_parts = []
        line_parts.append(' ' * (indent_level * self.indent_size))
        for i, token in enumerate(tokens):
            val = token.value
            type = token.type
            if type == 'STRING':
                if '"' in val and "'" not in val:
                    val = f"'{val}'"
                else:
                    val = val.replace('"', '\\"')
                    val = f'"{val}"'
            elif type == 'REGEX':
                val = f"/{val}/"
            if i > 0:
                prev = tokens[i-1]
                need_space = True 
                if prev.type in ('LPAREN', 'LBRACKET', 'LBRACE', 'DOT', 'AT'):
                    need_space = False
                if type in ('RPAREN', 'RBRACKET', 'RBRACE', 'DOT', 'COMMA', 'COLON'):
                    need_space = False
                if type == 'LPAREN':
                    if prev.type == 'ID':
                        need_space = False
                    elif prev.type in ('RPAREN', 'RBRACKET', 'STRING'):
                         need_space = False
                    else:
                        pass
                if type == 'LBRACKET':
                    if prev.type in ('ID', 'STRING', 'RPAREN', 'RBRACKET'):
                        need_space = False
                if need_space:
                    line_parts.append(' ')
            line_parts.append(val)
        return "".join(line_parts).rstrip()
