"""
-----Purpose: A minimal Language Server Protocol (LSP) server for ShellLite.
              Speaks JSON-RPC 2.0 over stdio. Provides:
              - textDocument/publishDiagnostics (syntax errors)
              - textDocument/hover       (variable/function info)
              - textDocument/completion  (keyword completions)
              - textDocument/definition  (go-to definition)
"""
import json
import sys
from typing import Any

from .ast_nodes import Assign, ClassDef, FunctionDef, TypedAssign
from .lexer import Lexer
from .parser_gbp import GeometricBindingParser

# ---------------------------------------------------------------------------
# All ShellLite keywords for completion
# ---------------------------------------------------------------------------
_KEYWORDS = [
    "if", "elif", "else", "while", "until", "unless", "forever",
    "repeat", "times", "for", "in", "to", "give", "say", "print",
    "test", "expect", "ensure", "thing", "has", "can", "use", "import",
    "from", "as", "try", "catch", "always", "error", "spawn", "await",
    "every", "after", "stop", "skip", "yes", "no", "and", "or", "not",
    "is", "be", "more", "less", "than", "equal", "int", "str", "float",
    "bool", "list", "dict", "string", "integer", "decimal",
]


def _read_message(stream) -> dict | None:
    """Read one JSON-RPC message from the input stream."""
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.decode("utf-8").rstrip("\r\n")
        if not line:
            break
        if ":" in line:
            key, _, val = line.partition(":")
            headers[key.strip().lower()] = val.strip()

    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = stream.read(length).decode("utf-8")
    return json.loads(body)


def _write_message(stream, payload: dict):
    """Write one JSON-RPC message to the output stream."""
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header + body)
    stream.flush()


def _diagnose(source: str, uri: str) -> list[dict]:
    """Return a list of LSP Diagnostic objects for the given source."""
    diagnostics = []
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        parser.parse()
    except SyntaxError as e:
        line = max((getattr(e, "lineno", 1) or 1) - 1, 0)
        diagnostics.append({
            "range": {
                "start": {"line": line, "character": 0},
                "end":   {"line": line, "character": 9999},
            },
            "severity": 1,  # Error
            "source": "ShellLite",
            "message": str(e),
        })
    except Exception as e:
        diagnostics.append({
            "range": {
                "start": {"line": 0, "character": 0},
                "end":   {"line": 0, "character": 9999},
            },
            "severity": 1,
            "source": "ShellLite",
            "message": str(e),
        })
    return diagnostics


def _collect_symbols(source: str) -> list[dict]:
    """Parse source and collect all top-level symbols for hover/definition."""
    symbols = []
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        nodes = parser.parse()
        for node in nodes:
            if isinstance(node, FunctionDef):
                symbols.append({"kind": "function", "name": node.name, "line": node.line})
            elif isinstance(node, (Assign, TypedAssign)):
                symbols.append({"kind": "variable", "name": node.name, "line": node.line})
            elif isinstance(node, ClassDef):
                symbols.append({"kind": "class", "name": node.name, "line": node.line})
    except Exception:
        pass
    return symbols


class LSPServer:
    """Minimal LSP server for ShellLite."""

    def __init__(self):
        self._documents: dict[str, str] = {}  # uri -> text
        self._running = True

    def _notify(self, method: str, params: Any):
        _write_message(sys.stdout.buffer, {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        })

    def _respond(self, req_id: Any, result: Any):
        _write_message(sys.stdout.buffer, {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        })

    def _error_response(self, req_id: Any, code: int, message: str):
        _write_message(sys.stdout.buffer, {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        })

    def _publish_diagnostics(self, uri: str):
        source = self._documents.get(uri, "")
        diags = _diagnose(source, uri)
        self._notify("textDocument/publishDiagnostics", {
            "uri": uri,
            "diagnostics": diags,
        })

    def _handle_initialize(self, req_id, _params):
        self._respond(req_id, {
            "capabilities": {
                "textDocumentSync": 1,          # Full sync
                "hoverProvider": True,
                "completionProvider": {"triggerCharacters": [" "]},
                "definitionProvider": True,
            },
            "serverInfo": {"name": "ShellLite LSP", "version": "0.6.0"},
        })

    def _handle_open(self, params):
        doc = params["textDocument"]
        uri = doc["uri"]
        self._documents[uri] = doc.get("text", "")
        self._publish_diagnostics(uri)

    def _handle_change(self, params):
        uri = params["textDocument"]["uri"]
        changes = params.get("contentChanges", [])
        if changes:
            self._documents[uri] = changes[-1]["text"]
        self._publish_diagnostics(uri)

    def _handle_close(self, params):
        uri = params["textDocument"]["uri"]
        self._documents.pop(uri, None)

    def _handle_hover(self, req_id, params):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        line_no = pos["line"]
        char_no = pos["character"]
        source = self._documents.get(uri, "")
        try:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
        except Exception:
            self._respond(req_id, None)
            return

        # Find token under cursor
        word = None
        for tok in tokens:
            if tok.line - 1 == line_no:
                col = tok.column - 1
                if col <= char_no <= col + len(tok.value):
                    word = tok.value
                    break

        if not word:
            self._respond(req_id, None)
            return

        symbols = _collect_symbols(source)
        for sym in symbols:
            if sym["name"] == word:
                kind = sym["kind"]
                hover_md = f"**{kind}** `{word}`\n\n*Defined on line {sym['line']}*"
                self._respond(req_id, {
                    "contents": {"kind": "markdown", "value": hover_md}
                })
                return

        if word in _KEYWORDS:
            self._respond(req_id, {
                "contents": {"kind": "markdown", "value": f"**keyword** `{word}`"}
            })
            return

        self._respond(req_id, None)

    def _handle_completion(self, req_id, params):
        uri = params["textDocument"]["uri"]
        source = self._documents.get(uri, "")
        symbols = _collect_symbols(source)
        items = []
        seen = set()

        for sym in symbols:
            if sym["name"] not in seen:
                seen.add(sym["name"])
                kind = 3 if sym["kind"] == "function" else (7 if sym["kind"] == "class" else 6)
                items.append({"label": sym["name"], "kind": kind})

        for kw in _KEYWORDS:
            if kw not in seen:
                items.append({"label": kw, "kind": 14})  # keyword kind

        self._respond(req_id, {"isIncomplete": False, "items": items})

    def _handle_definition(self, req_id, params):
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        line_no = pos["line"]
        char_no = pos["character"]
        source = self._documents.get(uri, "")

        try:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
        except Exception:
            self._respond(req_id, None)
            return

        word = None
        for tok in tokens:
            if tok.line - 1 == line_no:
                col = tok.column - 1
                if col <= char_no <= col + len(tok.value):
                    word = tok.value
                    break

        if not word:
            self._respond(req_id, None)
            return

        symbols = _collect_symbols(source)
        for sym in symbols:
            if sym["name"] == word:
                def_line = max(sym["line"] - 1, 0)
                self._respond(req_id, {
                    "uri": uri,
                    "range": {
                        "start": {"line": def_line, "character": 0},
                        "end":   {"line": def_line, "character": 0},
                    },
                })
                return

        self._respond(req_id, None)

    def run(self):
        """Main stdio loop."""
        stdin = sys.stdin.buffer
        while self._running:
            try:
                msg = _read_message(stdin)
            except Exception:
                break
            if msg is None:
                break

            method = msg.get("method", "")
            req_id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                self._handle_initialize(req_id, params)
            elif method == "initialized":
                pass
            elif method == "shutdown":
                self._respond(req_id, None)
            elif method == "exit":
                self._running = False
            elif method == "textDocument/didOpen":
                self._handle_open(params)
            elif method == "textDocument/didChange":
                self._handle_change(params)
            elif method == "textDocument/didClose":
                self._handle_close(params)
            elif method == "textDocument/hover":
                self._handle_hover(req_id, params)
            elif method == "textDocument/completion":
                self._handle_completion(req_id, params)
            elif method == "textDocument/definition":
                self._handle_definition(req_id, params)
            elif req_id is not None:
                self._error_response(req_id, -32601, f"Method not found: {method}")


def run_lsp():
    server = LSPServer()
    server.run()
