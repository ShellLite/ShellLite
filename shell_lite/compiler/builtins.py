from typing import Dict, Optional


class BuiltinMapping:
    def __init__(
        self,
        name: str,
        min_args: int = 0,
        max_args: Optional[int] = None,
        py_name: Optional[str] = None,
        is_dsl: bool = False,
        handler: Optional[str] = None,
    ):
        self.name = name
        self.min_args = min_args
        self.max_args = max_args
        self.py_name = py_name or name
        self.is_dsl = is_dsl
        self.handler = handler


BUILTINS: Dict[str, BuiltinMapping] = {
    # Core IO
    "print": BuiltinMapping("print", 0, None, "print"),
    "say": BuiltinMapping("say", 0, None, "print"),
    "ask": BuiltinMapping("ask", 0, 1, "shl_ask"),
    # Type Conversion
    "str": BuiltinMapping("str", 1, 1, "str"),
    "int": BuiltinMapping("int", 1, 1, "int"),
    "float": BuiltinMapping("float", 1, 1, "float"),
    "bool": BuiltinMapping("bool", 1, 1, "bool"),
    "typeof": BuiltinMapping("typeof", 1, 1, "type"),
    # Math
    "abs": BuiltinMapping("abs", 1, 1, "abs"),
    "range": BuiltinMapping("range", 1, 3, "range"),
    "max": BuiltinMapping("max", 1, None, "max"),
    "min": BuiltinMapping("min", 1, None, "min"),
    "ord": BuiltinMapping("ord", 1, 1, "ord"),
    "char": BuiltinMapping("char", 1, 1, "chr"),
    # Collections / Strings
    "len": BuiltinMapping("len", 1, 1, "len"),
    "upper": BuiltinMapping("upper", 1, 1, "str.upper"),
    "lower": BuiltinMapping("lower", 1, 1, "str.lower"),
    "sort": BuiltinMapping("sort", 1, 1, "sorted"),
    "count": BuiltinMapping("count", 1, 2, "shl_count"),
    "split": BuiltinMapping("split", 1, 2, "shl_split"),
    "add": BuiltinMapping("add", 2, 2),
    "remove": BuiltinMapping("remove", 2, 2),
    "pop": BuiltinMapping("pop", 1, 2),
    "contains": BuiltinMapping("contains", 2, 2, "shl_contains"),
    "empty": BuiltinMapping("empty", 1, 1, "shl_empty"),
    "xor": BuiltinMapping("xor", 2, 2, "shl_xor"),
    # JSON
    "json_parse": BuiltinMapping("json_parse", 1, 1, "py_json.loads"),
    "json_stringify": BuiltinMapping("json_stringify", 1, 2, "py_json.dumps"),
    # System
    "shl_execute": BuiltinMapping("shl_execute", 1, 1, "shl_execute"),
    "shl_parallel": BuiltinMapping("shl_parallel", 1, 1, "shl_parallel"),
    # IO Standard Lib (Lowered names)
    "std_io_read": BuiltinMapping("std_io_read", 1, 1),
    "std_io_write": BuiltinMapping("std_io_write", 2, 2),
    "std_io_append": BuiltinMapping("std_io_append", 2, 2),
    "std_io_exists": BuiltinMapping("std_io_exists", 1, 1),
    "exists": BuiltinMapping("exists", 1, 1, "std_io_exists"),
    "std_io_delete": BuiltinMapping("std_io_delete", 1, 1),
    "std_io_copy": BuiltinMapping("std_io_copy", 2, 2),
    "std_io_rename": BuiltinMapping("std_io_rename", 2, 2),
    "std_io_mkdir": BuiltinMapping("std_io_mkdir", 1, 1),
    "std_io_listdir": BuiltinMapping("std_io_listdir", 1, 1),
    # Web Standard Lib
    "std_web_on_request": BuiltinMapping("std_web_on_request", 1, None),
    "std_web_listen": BuiltinMapping("std_web_listen", 1, 1),
    "std_web_serve_static": BuiltinMapping("std_web_serve_static", 2, 2),
    # Dict helpers
    "clear_dict": BuiltinMapping("clear_dict", 1, 1, "dict.clear"),
    # Standard Lib - DB
    "std_db_open": BuiltinMapping("std_db_open", 1, 1),
    "std_db_close": BuiltinMapping("std_db_close", 0, 0),
    "std_db_query": BuiltinMapping("std_db_query", 1, None),
    "std_db_exec": BuiltinMapping("std_db_exec", 1, None),
    "std_db_query_rows": BuiltinMapping("std_db_query_rows", 1, None),
    # Standard Lib - Automation
    "automation_click": BuiltinMapping("automation_click", 2, 2),
    "automation_type": BuiltinMapping("automation_type", 1, 1),
    "automation_press": BuiltinMapping("automation_press", 1, 1),
    "automation_notify": BuiltinMapping("automation_notify", 2, 2),
    # Standard Lib - Clipboard
    "clipboard_copy": BuiltinMapping("clipboard_copy", 1, 1),
    "clipboard_paste": BuiltinMapping("clipboard_paste", 0, 0),
}

# Add HTML elements as builtins (all variadic)
HTML_ELEMENTS = [
    "html",
    "head",
    "body",
    "div",
    "span",
    "a",
    "img",
    "ul",
    "ol",
    "li",
    "button",
    "input",
    "form",
    "table",
    "tr",
    "td",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "link",
    "meta",
    "script",
    "textarea",
    "header",
    "footer",
    "nav",
    "main",
    "p",
    "label",
    "section",
    "article",
    "aside",
    "strong",
    "br",
    "hr",
    "title",
    "style",
    "blockquote",
    "pre",
    "code",
]

for el in HTML_ELEMENTS:
    BUILTINS[el] = BuiltinMapping(el, 0, None)

# Web specific DSL
BUILTINS["redirect"] = BuiltinMapping("redirect", 1, 1)
BUILTINS["render"] = BuiltinMapping("render", 1, 1)
