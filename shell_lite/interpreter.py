import concurrent.futures
import csv
import datetime
import importlib
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Set

from .ast_nodes import *
from .parser import Parser
from .compiler import runtime_lib as rt
from .runtime_policy import (
    get_policy,
    require_fs_read,
    require_exec,
    require_py_import,
    require_py_exec,
)


class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class StopException(Exception):
    pass


class SkipException(Exception):
    pass


class Environment:
    def __init__(self, parent=None, instance_data: Optional[Dict[str, Any]] = None):
        self.variables: Dict[str, Any] = {}
        self.constants: set = set()
        self.parent = parent
        self.instance_data = instance_data

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.instance_data is not None and name in self.instance_data:
            return self.instance_data[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Variable '{name}' is not defined.")

    def set(self, name: str, value: Any):
        if name in self.constants:
            raise RuntimeError(f"Cannot reassign constant '{name}'")

        if name in self.variables:
            self.variables[name] = value
            return

        if self.instance_data is not None and name in self.instance_data:
            self.instance_data[name] = value
            return

        curr = self.parent
        while curr:
            if name in curr.variables:
                if name in curr.constants:
                    raise RuntimeError(f"Cannot reassign constant '{name}'")
                curr.variables[name] = value
                return
            if curr.instance_data is not None and name in curr.instance_data:
                curr.instance_data[name] = value
                return
            curr = curr.parent

        self.variables[name] = value

    def set_const(self, name: str, value: Any):
        if name in self.variables:
            raise RuntimeError(f"Constant '{name}' already declared")
        self.variables[name] = value
        self.constants.add(name)


class PythonBridgeWrapper:
    def __init__(self, obj, name="<python_object>"):
        self._obj = obj
        self._name = name

    def __getattr__(self, key):
        if key == "_obj":
            return super()._obj
        try:
            attr = getattr(self._obj, key)

            if callable(attr):

                def wrapper(*args, **kwargs):
                    try:
                        unwrapped_args = [a._obj if isinstance(a, PythonBridgeWrapper) else a for a in args]
                        unwrapped_kwargs = {
                            k: (v._obj if isinstance(v, PythonBridgeWrapper) else v) for k, v in kwargs.items()
                        }
                        result = attr(*unwrapped_args, **unwrapped_kwargs)
                        if type(result) in (int, float, str, bool, type(None), list, dict, bytes):
                            return result
                        return PythonBridgeWrapper(result, name=f"{self._name}.{key}()")
                    except Exception as e:
                        raise RuntimeError(f"Python interop error calling '{self._name}.{key}': {e}")

                return wrapper
            if type(attr) in (int, float, str, bool, type(None), list, dict, bytes):
                return attr
            return PythonBridgeWrapper(attr, name=f"{self._name}.{key}")
        except AttributeError:
            raise AttributeError(f"Python object '{self._name}' has no member '{key}'")

    def __getitem__(self, key):
        res = self._obj[key]
        if type(res) in (int, float, str, bool, type(None), list, dict, bytes):
            return res
        return PythonBridgeWrapper(res, name=f"{self._name}[{key}]")

    def __setitem__(self, key, value):
        self._obj[key] = value

    def __len__(self):
        return len(self._obj)

    def __bool__(self):
        return bool(self._obj)

    def __add__(self, other):
        other_obj = other._obj if isinstance(other, PythonBridgeWrapper) else other
        res = self._obj + other_obj
        if type(res) in (int, float, str, bool, type(None), list, dict, bytes):
            return res
        return PythonBridgeWrapper(res)

    def __sub__(self, other):
        other_obj = other._obj if isinstance(other, PythonBridgeWrapper) else other
        res = self._obj - other_obj
        if type(res) in (int, float, str, bool, type(None), list, dict, bytes):
            return res
        return PythonBridgeWrapper(res)

    def __mul__(self, other):
        other_obj = other._obj if isinstance(other, PythonBridgeWrapper) else other
        res = self._obj * other_obj
        if type(res) in (int, float, str, bool, type(None), list, dict, bytes):
            return res
        return PythonBridgeWrapper(res)

    def __truediv__(self, other):
        other_obj = other._obj if isinstance(other, PythonBridgeWrapper) else other
        res = self._obj / other_obj
        if type(res) in (int, float, str, bool, type(None), list, dict, bytes):
            return res
        return PythonBridgeWrapper(res)


class LambdaFunction:
    def __init__(self, params: List[str], body, interpreter, name: Optional[str] = None):
        self.params = params
        self.body = body
        self.interpreter = interpreter
        self.closure_env = interpreter.current_env
        self.name = name

    def __call__(self, *args, **kwargs):
        old_env = self.interpreter.current_env
        inst = args[0] if (self.params and self.params[0] == "self" and args and isinstance(args[0], Instance)) else None
        new_env = Environment(parent=self.closure_env, instance_data=inst.data if inst else None)

        for param, arg in zip(self.params, args):
            new_env.variables[param] = arg
        self.interpreter.current_env = new_env
        try:
            result = self.interpreter.visit_block(self.body)
        except ReturnException as e:
            result = e.value
        finally:
            self.interpreter.current_env = old_env
        return result


class Instance:
    def __init__(self, class_def: ClassDef, interpreter):
        self.class_def = class_def
        self.interpreter = interpreter
        self.data: Dict[str, Any] = {}
        for prop_name, default_node in class_def.properties:
            self.data[prop_name] = interpreter.visit(default_node) if default_node else None

    def __getattr__(self, name):
        if name in self.data:
            return self.data[name]
        method = self.get_method(name)
        if method:
            return lambda *args, **kwargs: method(self, *args, **kwargs)
        raise AttributeError(f"'{self.class_def.name}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in ('class_def', 'interpreter', 'data'):
            super().__setattr__(name, value)
        else:
            self.data[name] = value

    def to_dict(self, visited=None):
        if visited is None:
            visited = set()

        obj_id = id(self)

        if obj_id in visited:
            return "<circular_instance_reference>"

        visited.add(obj_id)

        result = {
            "__class__": self.class_def.name,
        }

        for key, value in self.data.items():
            result[key] = serialize_runtime_value(value, visited)

        return result

    def get_method(self, name: str):
        for method in self.class_def.methods:
            if method.name == name:
                return LambdaFunction(["self"] + [a[0] for a in method.args], method.body, self.interpreter, name=method.name)
        return None

    def get_member(self, name: str):
        method = self.get_method(name)
        if method:
            return lambda *args, **kwargs: method(self, *args, **kwargs)
        return self.data.get(name)


class Module:
    def __init__(self, name: str, variables: Dict[str, Any]):
        self.name = name
        self.variables = variables

    def get_member(self, name: str):
        if name in self.variables:
            return self.variables[name]
        raise AttributeError(f"Module '{self.name}' has no member '{name}'")


class JITTag:
    def __init__(self, name, attrs=None):
        self.name = name
        self.attrs = attrs or {}
        self.children = []

    def add(self, child):
        self.children.append(child)

    def __str__(self):
        attr_str = "".join([f' {k}="{v}"' for k, v in self.attrs.items()])
        inner = "".join([str(c) for c in self.children])
        if self.name in ("img", "br", "hr", "input", "meta", "link"):
            return f"<{self.name}{attr_str} />"
        return f"<{self.name}{attr_str}>{inner}</{self.name}>"


def make_jit_tag_fn(name, interpreter):
    def fn(*args, **kwargs):
        attrs = dict(kwargs)
        content = []
        for arg in args:
            if isinstance(arg, dict):
                attrs.update(arg)
            elif isinstance(arg, LambdaFunction):
                t = JITTag(name, attrs)
                if interpreter.web_builder:
                    interpreter.web_builder[-1].add(t)
                interpreter.web_builder.append(t)
                try:
                    arg()
                finally:
                    interpreter.web_builder.pop()
                return t
            elif isinstance(arg, str) and "=" in arg and " " not in arg:
                k, v = arg.split("=", 1)
                attrs[k] = v
            else:
                content.append(arg)
        t = JITTag(name, attrs)
        for c in content:
            t.add(c)
        if interpreter.web_builder:
            interpreter.web_builder[-1].add(t)
        return t

    return fn


class SerializationError(Exception):
    pass


class ShellLiteJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Instance):
            return obj.to_dict()

        if isinstance(obj, LambdaFunction):
            return {
                "__type__": "LambdaFunction",
                "name": obj.name,
                "params": obj.params,
            }

        if isinstance(obj, PythonBridgeWrapper):
            return serialize_runtime_value(obj._obj)

        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()

        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def serialize_runtime_value(value, visited=None):
    if visited is None:
        visited = set()

    primitive_types = (str, int, float, bool, type(None))

    if isinstance(value, primitive_types):
        return value

    obj_id = id(value)

    if obj_id in visited:
        return "<circular_reference>"

    visited.add(obj_id)

    if isinstance(value, Instance):
        return value.to_dict(visited)

    if isinstance(value, LambdaFunction):
        return {
            "__type__": "LambdaFunction",
            "name": value.name,
            "params": value.params,
        }

    if isinstance(value, PythonBridgeWrapper):
        return serialize_runtime_value(value._obj, visited)

    if isinstance(value, dict):
        return {str(k): serialize_runtime_value(v, visited) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [serialize_runtime_value(v, visited) for v in value]

    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()

    return str(value)


def std_json_export(data, path, indent=2):
    serialized = serialize_runtime_value(data)

    with rt.open(path, "w", encoding="utf-8") as f:
        json.dump(
            serialized,
            f,
            indent=indent,
            cls=ShellLiteJSONEncoder,
            ensure_ascii=False,
        )

    return path


def validate_csv_rows(data):
    if not isinstance(data, list):
        raise SerializationError("CSV export expects a list")

    if not data:
        raise SerializationError("CSV export requires a non-empty list")

    first = data[0]

    if isinstance(first, dict):
        return "dict_rows"

    if isinstance(first, (list, tuple)):
        return "list_rows"

    raise SerializationError("CSV export requires list of dicts or list of lists")


def std_csv_export(data, path):
    mode = validate_csv_rows(data)

    with rt.open(path, "w", newline="", encoding="utf-8") as f:
        if mode == "dict_rows":
            headers = set()

            for row in data:
                headers.update(row.keys())

            headers = list(headers)

            dict_writer = csv.DictWriter(
                f,
                fieldnames=headers,
                quoting=csv.QUOTE_MINIMAL,
            )

            dict_writer.writeheader()

            for row in data:
                serialized_row = {k: serialize_runtime_value(v) for k, v in row.items()}

                dict_writer.writerow(serialized_row)

        elif mode == "list_rows":
            list_writer = csv.writer(
                f,
                quoting=csv.QUOTE_MINIMAL,
            )

            for row in data:
                list_writer.writerow([serialize_runtime_value(v) for v in row])
    return path


class Interpreter:
    def __init__(self):
        self.policy = get_policy()
        self.safe_mode = self.policy.safe_mode
        self._thread_local = threading.local()
        self.global_env = Environment()
        self.current_env = self.global_env
        self.functions: Dict[str, FunctionDef] = {}
        self.classes: Dict[str, ClassDef] = {}
        self._shared_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self._module_cache: Dict[str, Module] = {}
        self._imported_paths: Set[str] = set()
        self.builtins = {
            "str": str,
            "int": lambda x: int(float(x)) if x else 0,
            "float": float,
            "bool": bool,
            "list": list,
            "len": len,
            "save_json": std_json_export,
            "save_csv": std_csv_export,
            "serialize": serialize_runtime_value,
            "range": lambda *args: list(range(*args)),
            "abs": abs,
            "typeof": self._builtin_typeof,
            "print": print,
            "say": print,
            "ask": input,
            "sleep": time.sleep,
            "exit": sys.exit,
            "timestamp": time.time,
            "null": None,
            "true": True,
            "false": False,
            "yes": True,
            "no": False,
            "open": rt.open,
            "py_exec": self._py_exec,
            "tuple": lambda x: tuple(x),
            "getattr": getattr,
            "add": lambda target, item: target.add(item) if isinstance(target, set) else target.append(item),
            "remove": lambda target, item: target.remove(item),
            "sum": sum,
            "split": lambda x, sep=None: x.split(sep) if sep else x.split(),
            "upper": lambda x: x.upper(),
            "lower": lambda x: x.lower(),
            "sort": lambda x: sorted(x),
            "count": lambda x, y=None: x.count(y) if y is not None else len(x),
            "xor": lambda a, b: a ^ b,
            "empty": lambda x: len(x) == 0,
            "ord": ord,
            "char": chr,
            "exists": self._exists,
            "json_parse": json.loads,
            "json_stringify": lambda obj, indent=2: json.dumps(
                serialize_runtime_value(obj),
                indent=indent,
                cls=ShellLiteJSONEncoder,
                ensure_ascii=False,
            ),
            "contains": lambda obj, item: item in obj,
            "std_io_read": rt.std_io_read,
            "std_io_write": rt.std_io_write,
            "std_io_append": rt.std_io_append,
            "std_io_exists": rt.std_io_exists,
            "std_io_delete": rt.std_io_delete,
            "std_io_copy": rt.std_io_copy,
            "std_io_rename": rt.std_io_rename,
            "std_io_mkdir": rt.std_io_mkdir,
            "std_io_listdir": rt.std_io_listdir,
            "std_net_get": rt.std_net_get,
            "std_net_post": rt.std_net_post,
            "std_web_on_request": rt.std_web_on_request,
            "std_web_listen": rt.std_web_listen,
            "std_web_serve_static": rt.std_web_serve_static,
            "std_db_open": rt.std_db_open,
            "std_db_close": rt.std_db_close,
            "std_db_exec": rt.std_db_exec,
            "std_db_query": rt.std_db_query,
            "std_db_query_rows": rt.std_db_query_rows,
            "automation_click": rt.automation_click,
            "automation_type": rt.automation_type,
            "automation_press": rt.automation_press,
            "automation_notify": rt.automation_notify,
            "clipboard_copy": rt.clipboard_copy,
            "clipboard_paste": rt.clipboard_paste,
            "download": rt.download,
            "convert": rt.convert,
            "clear_dict": lambda d: d.clear(),
        }
        self.web_builder = []
        for t in [
            "div",
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "span",
            "a",
            "img",
            "button",
            "input",
            "form",
            "ul",
            "li",
            "html",
            "head",
            "body",
            "title",
            "meta",
            "link",
            "script",
            "style",
            "br",
            "hr",
            "header",
            "nav",
            "footer",
            "textarea",
            "strong",
        ]:
            self.builtins[t] = make_jit_tag_fn(t, self)
        for k, v in self.builtins.items():
            self.global_env.set(k, v)
        self._load_stdlib()

    @property
    def current_env(self):
        if not hasattr(self._thread_local, "current_env"):
            self._thread_local.current_env = self.global_env
        return self._thread_local.current_env

    @current_env.setter
    def current_env(self, value):
        self._thread_local.current_env = value

    def _builtin_typeof(self, x):
        if isinstance(x, Instance):
            return x.class_def.name
        if isinstance(x, Module):
            return "Module"
        return type(x).__name__

    def _load_stdlib(self):
        stdlib_path = os.path.join(os.path.dirname(__file__), "stdlib")
        if not os.path.exists(stdlib_path):
            return
        std_file = os.path.join(stdlib_path, "std.shl")
        if os.path.exists(std_file):
            try:
                nodes = self._load_module_nodes("std.shl", search_paths=[stdlib_path])
                self.visit_block(nodes)
            except Exception as e:
                import traceback

                print(f"Warning: Failed to load stdlib: {e}")
                if os.environ.get("SHL_DEBUG"):
                    traceback.print_exc()

    def _resolve_module_path(self, path: str, search_paths: Optional[List[str]] = None) -> str:
        if not path.endswith(".shl"):
            path += ".shl"

        if search_paths is None:
            search_paths = [os.getcwd(), os.path.join(os.path.dirname(__file__), "stdlib")]

        for p in search_paths:
            full_path = os.path.join(p, path)
            if os.path.exists(full_path):
                return os.path.abspath(full_path)

        raise FileNotFoundError(f"Module {path} not found")

    def _load_module_nodes(self, path: str, search_paths: Optional[List[str]] = None) -> List[Node]:
        abs_path = self._resolve_module_path(path, search_paths)
        stdlib_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "stdlib"))
        if abs_path.startswith(stdlib_root):
            with open(abs_path, "r", encoding="utf-8") as f:
                source = f.read()
        else:
            with rt.open(abs_path, "r", encoding="utf-8") as f:
                source = f.read()
        return Parser(source).parse()

    def visit(self, node: Node) -> Any:
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)

        try:
            return visitor(node)
        except AttributeError as e:
            if "'Number' object has no attribute 'name'" in str(e):
                print(f"DEBUG Error in {method_name} for node: {node}")
            raise
        except Exception as e:
            raise

    def generic_visit(self, node: Node):
        raise Exception(f"No visit_{type(node).__name__} method")

    def visit_block(self, body: List[Node]) -> Any:
        result = None
        for stmt in body:
            result = self.visit(stmt)
        return result

    def visit_Number(self, node: Number):
        return node.value

    def visit_String(self, node: String):
        return node.value

    def visit_Boolean(self, node: Boolean):
        return node.value

    def visit_VarAccess(self, node: VarAccess):
        val = self.current_env.get(node.name)
        if isinstance(val, LambdaFunction) and len(val.params) == 0 and getattr(val, "name", None) is not None:
            return val()
        return val

    def visit_Assign(self, node: Assign):
        val = self.visit(node.value)
        self.current_env.set(node.name, val)
        return val

    def visit_TypedAssign(self, node: TypedAssign):
        return self.visit_Assign(Assign(node.name, node.value))

    def visit_ConstAssign(self, node: ConstAssign):
        val = self.visit(node.value)
        self.current_env.set_const(node.name, val)
        return val

    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        if node.op == ".":
            member_name = node.right.name if hasattr(node.right, "name") else str(node.right)

            if hasattr(left, "get_member"):
                member = left.get_member(member_name)
            else:
                member = getattr(left, member_name)

            if isinstance(node.right, Call):
                args = [self.visit(a) for a in node.right.args]
                kwargs = {k: self.visit(v) for k, v in node.right.kwargs} if node.right.kwargs else {}
                return member(*args, **kwargs)
            return member

        right = self.visit(node.right)
        ops = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
            "%": lambda a, b: a % b,
            "**": lambda a, b: a**b,
            "&": lambda a, b: a & b,
            "|": lambda a, b: a | b,
            "^": lambda a, b: a ^ b,
            "<<": lambda a, b: a << b,
            ">>": lambda a, b: a >> b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
            "and": lambda a, b: a and b,
            "or": lambda a, b: a or b,
            "in": lambda a, b: a in b,
            "not in": lambda a, b: a not in b,
        }
        return ops[node.op](left, right)

    def visit_UnaryOp(self, node: UnaryOp):
        right = self.visit(node.right)
        return -right if node.op == "-" else (~right if node.op == "~" else not right)

    def visit_If(self, node: If):
        if self.visit(node.condition):
            return self.visit_block(node.body)
        if node.else_body:
            return self.visit_block(node.else_body)
        return None

    def visit_While(self, node: While):
        while self.visit(node.condition):
            try:
                self.visit_block(node.body)
            except StopException:
                break
            except SkipException:
                continue
        return None

    def visit_ForIn(self, node: ForIn):
        for val in self.visit(node.iterable):
            self.current_env.set(node.var_name, val)
            try:
                self.visit_block(node.body)
            except StopException:
                break
            except SkipException:
                continue
        return None

    def visit_Repeat(self, node: Repeat):
        count = self.visit(node.count)
        for _ in range(int(count)):
            try:
                self.visit_block(node.body)
            except StopException:
                break
            except SkipException:
                continue
        return None

    def visit_FunctionDef(self, node: FunctionDef):
        lf = LambdaFunction([a[0] for a in node.args], node.body, self, name=node.name)
        self.current_env.set(node.name, lf)
        return lf

    def visit_Call(self, node: Call):
        func = self.current_env.get(node.name)
        args = [self.visit(a) for a in node.args]
        if node.body:
            args.append(LambdaFunction([], node.body, self, name=None))
        kwargs = {k: self.visit(v) for k, v in node.kwargs} if node.kwargs else {}
        return func(*args, **kwargs)

    def visit_Return(self, node: Return):
        raise ReturnException(self.visit(node.value))

    def visit_Print(self, node: Print):
        val = self.visit(node.expression)
        print(val)
        return val

    def visit_ListVal(self, node: ListVal):
        return [self.visit(e) for e in node.elements]

    def visit_Dictionary(self, node: Dictionary):
        return {self.visit(k): self.visit(v) for k, v in node.pairs}

    def visit_Try(self, node: Try):
        try:
            return self.visit_block(node.try_body)
        except Exception as e:
            self.current_env.set(node.catch_var, str(e))
            return self.visit_block(node.catch_body)

    def visit_PythonImport(self, node: PythonImport):
        require_py_import(node.module_name)
        module = importlib.import_module(node.module_name)
        wrapper = PythonBridgeWrapper(module, name=node.module_name)
        self.global_env.set(node.alias or node.module_name, wrapper)
        return wrapper

    def visit_FromImport(self, node: FromImport):
        require_py_import(node.module_name)
        module = importlib.import_module(node.module_name)
        for name, alias in node.names:
            attr = getattr(module, name)
            if type(attr) not in (int, float, str, bool, type(None), list, dict):
                attr = PythonBridgeWrapper(attr, name=f"{node.module_name}.{name}")
            self.global_env.set(alias or name, attr)

    def visit_Stop(self, node: Stop):
        raise StopException()

    def visit_Skip(self, node: Skip):
        raise SkipException()

    def visit_Import(self, node: Import):
        abs_path = self._resolve_module_path(node.path)
        if abs_path in self._imported_paths:
            return None
        nodes = self._load_module_nodes(node.path)
        self._imported_paths.add(abs_path)
        return self.visit_block(nodes)

    def visit_ImportAs(self, node: ImportAs):
        abs_path = self._resolve_module_path(node.path)
        cached = self._module_cache.get(abs_path)
        if cached:
            self.current_env.set(node.alias, cached)
            return cached

        nodes = self._load_module_nodes(node.path)
        old_env = self.current_env
        module_env = Environment(parent=self.global_env)
        self.current_env = module_env
        try:
            self.visit_block(nodes)
        finally:
            self.current_env = old_env

        module_obj = Module(os.path.basename(abs_path), module_env.variables)
        self._module_cache[abs_path] = module_obj
        self.current_env.set(node.alias, module_obj)
        return module_obj

    def visit_ClassDef(self, node: ClassDef):
        self.classes[node.name] = node

        def constructor(*args, **kwargs):
            inst = Instance(node, self)
            for i, arg in enumerate(args):
                if i < len(node.properties):
                    prop_name = node.properties[i][0]
                    inst.data[prop_name] = arg

            init_method = inst.get_method("init")
            if init_method:
                init_method(inst, *args, **kwargs)
            return inst

        self.current_env.set(node.name, constructor)
        return None

    def visit_Instantiation(self, node: Instantiation):
        cls = self.classes[node.class_name]
        args = [self.visit(a) for a in node.args]
        kwargs = {k: self.visit(v) for k, v in node.kwargs} if node.kwargs else {}

        inst = Instance(cls, self)
        for i, arg in enumerate(args):
            if i < len(cls.properties):
                prop_name = cls.properties[i][0]
                inst.data[prop_name] = arg

        init_method = inst.get_method("init")
        if init_method:
            init_method(inst, *args, **kwargs)

        if node.var_name:
            self.current_env.set(node.var_name, inst)
        return inst

    def visit_PropertyAccess(self, node: PropertyAccess):
        inst = self.current_env.get(node.instance_name)
        if isinstance(inst, Instance):
            return inst.data.get(node.property_name)
        return getattr(inst, node.property_name)

    def visit_PropertyAssign(self, node: PropertyAssign):
        inst = self.current_env.get(node.instance_name)
        val = self.visit(node.value)
        if isinstance(inst, Instance):
            inst.data[node.property_name] = val
        else:
            setattr(inst, node.property_name, val)
        return val

    def visit_MethodCall(self, node: MethodCall):
        inst = self.current_env.get(node.instance_name)
        args = [self.visit(a) for a in node.args]
        if isinstance(inst, Instance):
            method = inst.get_method(node.method_name)
            return method(inst, *args)
        return getattr(inst, node.method_name)(*args)

    def visit_IndexAccess(self, node: IndexAccess):
        obj = self.visit(node.obj)

        if isinstance(node.index, Slice):
            start = self.visit(node.index.start) if node.index.start else None
            stop = self.visit(node.index.stop) if node.index.stop else None
            step = self.visit(node.index.step) if node.index.step else None

            return obj[slice(start, stop, step)]

        idx = self.visit(node.index)
        return obj[idx]

    def visit_IndexAssign(self, node: IndexAssign):
        obj = self.visit(node.obj)
        idx = self.visit(node.index)
        val = self.visit(node.value)
        obj[idx] = val
        return val

    def visit_Spawn(self, node: Spawn):
        if not isinstance(node.call, Call):
            raise Exception("Spawn requires a function call")
        func = self.current_env.get(node.call.name)
        args = [self.visit(a) for a in node.call.args]
        if node.call.body:
            args.append(LambdaFunction([], node.call.body, self, name=None))
        kwargs = {k: self.visit(v) for k, v in node.call.kwargs} if node.call.kwargs else {}

        def run_threaded():
            try:
                func(*args, **kwargs)
            except Exception as e:
                import traceback

                print(f"[Spawn Thread Error]: {e}")
                traceback.print_exc()

        return self._shared_executor.submit(run_threaded)

    def visit_Await(self, node: Await):
        f = self.visit(node.task)
        return f.result() if hasattr(f, "result") else f

    def visit_Match(self, node: Match):
        v = self.visit(node.match_expr)
        for ce, b in node.cases:
            if v == self.visit(ce):
                return self.visit_block(b)
        return self.visit_block(node.default_case) if node.default_case else None

    def visit_FileRead(self, node: FileRead):
        path = self.visit(node.path)
        with rt.open(path, "r", encoding="utf-8") as f:
            return f.read()

    def visit_FileWrite(self, node: FileWrite):
        path = self.visit(node.path)
        content = self.visit(node.content)
        with rt.open(path, node.mode, encoding="utf-8") as f:
            f.write(content)
        return None

    def visit_Execute(self, node: Execute):
        cmd = self.visit(node.code)
        require_exec(str(cmd))
        return rt.shl_execute(str(cmd))

    def visit_Throw(self, node: Throw):
        msg = self.visit(node.message)
        raise Exception(msg)

    def visit_Assertion(self, node: Assertion):
        left = self.visit(node.left)
        op = node.op
        right = self.visit(node.right) if node.right else None

        passed = False
        if op == "truthy":
            passed = bool(left)
        elif op == "==":
            passed = left == right
        elif op == "!=":
            passed = left != right
        elif op == ">":
            passed = left > right
        elif op == "<":
            passed = left < right
        elif op == ">=":
            passed = left >= right
        elif op == "<=":
            passed = left <= right

        if not passed:
            msg = f"Assertion failed: Expected {left} {op} {right if right is not None else ''}"
            raise AssertionError(msg)
        return True

    def visit_TestBlock(self, node: TestBlock):
        print(f"  [RUNNING] {node.name}...", end=" ", flush=True)
        try:
            self.visit_block(node.body)
            print("PASSED")
            return True
        except AssertionError as e:
            print(f"FAILED\n    > {e}")
            return False
        except Exception as e:
            print(f"ERROR\n    > {e}")
            return False

    def _py_exec(self, code):
        require_py_exec()
        return exec(code)

    def _exists(self, path):
        require_fs_read(path)
        return os.path.exists(path)
