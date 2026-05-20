import concurrent.futures
import csv
import functools
import importlib
import json
import math
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from .ast_nodes import *
from .lexer import Lexer
from .parser import Parser
from .runtime import Tag, WebBuilder, ReturnException, StopException, SkipException, ShellLiteError
from .modules.gui_engine import GUIEngine
from .modules.db_engine import DBEngine
from .modules.web_engine import WebEngine

try:
    import keyboard
    import mouse
    import pyperclip
    from plyer import notification
except ImportError:
    pass

class Environment:
    """
    Represents the variable and constant binding environment at a
    specific scope level during execution.
    """
    def __init__(self, parent=None):
        self.variables: Dict[str, Any] = {}
        self.constants: set = set()
        self.parent = parent

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Variable '{name}' is not defined.")

    def set(self, name: str, value: Any):
        if name in self.constants:
            raise RuntimeError(f"Cannot reassign constant '{name}'")
        curr = self
        while curr:
            if name in curr.variables:
                if name in curr.constants:
                    raise RuntimeError(f"Cannot reassign constant '{name}'")
                curr.variables[name] = value
                return
            curr = curr.parent
        self.variables[name] = value

    def set_const(self, name: str, value: Any):
        if name in self.variables:
            raise RuntimeError(f"Constant '{name}' already declared")
        self.variables[name] = value
        self.constants.add(name)

class Namespace:
    def __init__(self, name, members):
        self._name = name
        self._members = members

    def __getattr__(self, key):
        if key in self._members: return self._members[key]
        raise AttributeError(f"Module '{self._name}' has no member '{key}'")

    def __getitem__(self, key): return self._members[key]

    def __repr__(self): return f"<Module '{self._name}'>"

class LambdaFunction:
    def __init__(self, params: List[str], body, interpreter):
        self.params = params
        self.body = body
        self.interpreter = interpreter
        self.closure_env = interpreter.current_env

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise TypeError(f"Lambda expects {len(self.params)} args, got {len(args)}")
        old_env = self.interpreter.current_env
        new_env = Environment(parent=self.closure_env)
        for param, arg in zip(self.params, args):
            new_env.set(param, arg)
        self.interpreter.current_env = new_env
        try:
            result = self.interpreter.visit(self.body)
        finally:
            self.interpreter.current_env = old_env
        return result

class Instance:
    """
    Represents an instantiated struct/class with bounded data.
    """
    def __init__(self, class_def: ClassDef):
        self.class_def = class_def
        self.data: Dict[str, Any] = {}

class Interpreter:
    """
    The core tree walking interpreter that executes AST nodes.
    """
    def __init__(self):
        self.safe_mode = os.environ.get("SHL_SAFE") == "1"
        self.global_env = Environment()
        self.current_env = self.global_env
        self.functions: Dict[str, FunctionDef] = {}
        self.classes: Dict[str, ClassDef] = {}
        
        self.http_routes = []
        self.middleware_routes = []
        self.static_routes = {}
        
        self.web = WebBuilder(self)
        self.gui_engine = GUIEngine(self)
        self.db_engine = DBEngine(self)
        self.web_engine = WebEngine(self)
        
        self.db_conn = None
        self._shared_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self._named_locks: Dict[str, threading.Lock] = {}
        self.models: Dict[str, 'ModelDef'] = {}

        self.builtins = {
            'str': str, 'int': lambda x: int(float(x)) if x else 0, 'float': float, 'bool': bool,
            'list': list, 'len': len,
            'range': lambda *args: list(range(*args)),
            'abs': abs,
            'typeof': lambda x: type(x).__name__,
            'run': self.builtin_run,
            'read': self.builtin_read,
            'write': self.builtin_write,
            'json_parse': self.builtin_json_parse,
            'json_stringify': self.builtin_json_stringify,
            'sum': sum,
            'even': lambda x: x % 2 == 0,
            'prime': lambda x: x > 1 and all(x % i != 0 for i in range(2, int(x**0.5) + 1)),
            'print': print,
            'add': self._builtin_smart_add,
            'ask': input,
            'split': self._builtin_split,
            'join': lambda lst, d="": d.join(str(x) for x in lst),
            'replace': lambda s, old, new: s.replace(old, new),
            'upper': self._builtin_upper,
            'lower': lambda s: s.lower(),
            'trim': lambda s: s.strip(),
            'startswith': lambda s, p: s.startswith(p),
            'endswith': lambda s, p: s.endswith(p),
            'sum_range': self._builtin_sum_range,
            'range_list': self._builtin_range_list,
            'find': lambda s, sub: s.find(sub),
            'char': chr, 'ord': ord,
            'append': self._builtin_smart_add,
            'push': self._builtin_push,
            'count': len,
            'remove': lambda l, x: l.remove(x),
            'pop': lambda l, idx=-1: l.pop(idx),
            'get': lambda l, idx: l[idx],
            'set': lambda l, idx, val: l.__setitem__(idx, val) or l,
            'sort': lambda l: sorted(l),
            'reverse': lambda l: list(reversed(l)),
            'slice': lambda l, start, end=None: l[start:end],
            'contains': lambda l, x: x in l,
            'index': lambda l, x: l.index(x) if x in l else -1,
            'exists': os.path.exists,
            'delete': os.remove,
            'copy': shutil.copy,
            'rename': os.rename,
            'mkdir': lambda p: os.makedirs(p, exist_ok=True),
            'listdir': os.listdir,
            'http_get': self.builtin_http_get,
            'http_post': self.builtin_http_post,
            'random': random.random,
            'randint': random.randint,
            'sleep': time.sleep,
            'now': lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'timestamp': time.time,
            'unique': lambda l: list(dict.fromkeys(l)),
            'first': lambda l: l[0] if l else None,
            'last': lambda l: l[-1] if l else None,
            'empty': lambda x: len(x) == 0 if hasattr(x, '__len__') else x is None,
            'keys': lambda d: list(d.keys()),
            'values': lambda d: list(d.values()),
            'items': lambda d: list(d.items()),
            'Set': set,
            'show': print,
            'say': print,
            'today': lambda: datetime.now().strftime("%Y-%m-%d"),
            'wait': time.sleep,
            'null': None,
            'None': None,
        }

        self.math_members = {
            'abs': abs, 'min': min, 'max': max,
            'round': round, 'pow': pow, 'sum': sum,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'floor': math.floor, 'ceil': math.ceil, 'sqrt': math.sqrt,
            'log': math.log, 'log10': math.log10, 'exp': math.exp,
            'pi': math.pi, 'e': math.e,
            'lerp': lambda a, b, t: a + (b - a) * t,
            'clamp': lambda v, lo, hi: max(lo, min(v, hi))
        }
        
        self._init_std_modules()

        tags = [
            'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'span', 'a', 'img', 'button', 'input', 'form',
            'ul', 'li', 'ol', 'table', 'tr', 'td', 'th',
            'html', 'head', 'body', 'title', 'meta', 'link',
            'script', 'style', 'br', 'hr',
            'header', 'footer', 'section', 'article', 'nav', 'aside', 'main',
            'strong', 'em', 'code', 'pre', 'blockquote', 'iframe', 'canvas', 'svg',
            'css', 'textarea', 'label'
        ]
        for t in tags:
            self.builtins[t] = self._make_tag_fn(t)
            
        self.builtins['env'] = lambda name: os.environ.get(str(name), None)
        
        class TimeWrapper:
            def now(self):
                return str(int(time.time()))
        self.builtins['time'] = TimeWrapper()

        for k, v in self.builtins.items():
            self.global_env.set(k, v)

    def _make_tag_fn(self, tag_name):
        def tag_fn(*args, **kwargs):
            attrs = {}
            attrs.update(kwargs)
            content = []
            for arg in args:
                if isinstance(arg, dict):
                    attrs.update(arg)
                elif isinstance(arg, str):
                    if '=' in arg and ' ' not in arg and arg.split('=')[0].isalnum():
                        k, v = arg.split('=', 1)
                        attrs[k] = v
                    else:
                        content.append(arg)
                else:
                    content.append(str(arg))
            t = Tag(tag_name, attrs)
            for c in content:
                t.add(c)
            return t
        return tag_fn

    def _builtin_push(self, lst, item):
        lst.append(item)
        return None

    def _builtin_split(self, s, delimiter=None):
        if delimiter == "":
            return list(str(s))
        return str(s).split(delimiter)

    def _builtin_sum_range(self, start, end, condition=None):
        """
        Builtin helper to sum a range with optional filtering.
        """
        total = 0
        s = int(start)
        e = int(end)
        for i in range(s, e + 1):
             include = True
             if condition == 'even' and i % 2 != 0: include = False
             elif condition == 'odd' and i % 2 == 0: include = False
             elif condition == 'prime':
                 if i < 2: include = False
                 else:
                     for k in range(2, int(i ** 0.5) + 1):
                         if i % k == 0:
                             include = False
                             break
             if include:
                 total += i
        return total

    def _builtin_range_list(self, start, end, condition=None):
        """
        Builtin helper to generate a list from a range with optional filtering.
        """
        res = []
        s = int(start)
        e = int(end)
        for i in range(s, e + 1):
             include = True
             if condition == 'even' and i % 2 != 0: include = False
             elif condition == 'odd' and i % 2 == 0: include = False
             elif condition == 'prime':
                 if i < 2: include = False
                 else:
                     for k in range(2, int(i ** 0.5) + 1):
                         if i % k == 0:
                             include = False
                             break
             if include:
                 res.append(i)
        return res

    def _builtin_smart_add(self, target, val):
        if isinstance(target, list):
            target.append(val)
            return target
        elif isinstance(target, (int, float, str)):
            return target + val
        else:
            raise TypeError(f"Cannot add to {type(target).__name__}")

    def _builtin_upper(self, s, only=None):
        """
        Builtin helper to convert string to uppercase.
        """
        if isinstance(s, list):
            return [self._builtin_upper(x, only=only) for x in s]
        
        s_str = str(s)
        if only == 'letters':
            return re.sub(r'[^a-zA-Z\s]', '', s_str).upper()
        return s_str.upper()

    def _init_std_modules(self):
        self.std_modules = {
            'math': Namespace('math', self.math_members),
            'time': Namespace('time', {
                'time': time.time,
                'sleep': time.sleep,
                'date': lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'year': lambda: datetime.now().year,
                'month': lambda: datetime.now().month,
                'day': lambda: datetime.now().day,
            }),
            'env': Namespace('env', {
                'get': lambda k, d=None: os.environ.get(k, d),
                'set': lambda k, v: os.environ.__setitem__(k, str(v)),
                'all': lambda: dict(os.environ),
                'os': os.name,
                'platform': sys.platform,
            }),
            'path': Namespace('path', {
                'join': os.path.join,
                'basename': os.path.basename,
                'exists': os.path.exists,
                'isdir': os.path.isdir,
                'abspath': os.path.abspath,
            }),
            'color': Namespace('color', {
                'red': lambda s: f"\033[91m{s}\033[0m",
                'green': lambda s: f"\033[92m{s}\033[0m",
                'blue': lambda s: f"\033[94m{s}\033[0m",
                'bold': lambda s: f"\033[1m{s}\033[0m",
                'reset': "\033[0m",
            }),
            're': Namespace('re', {
                'match': lambda p, s: bool(re.match(p, s)),
                'search': lambda p, s: re.search(p, s).group() if re.search(p, s) else None,
                'replace': lambda p, r, s: re.sub(p, r, s),
            }),
        }

    def visit(self, node: Node) -> Any:
        if node is None:
            return None
        try:
            method_name = f'visit_{type(node).__name__}'
            visitor = getattr(self, method_name, self.generic_visit)
            return visitor(node)
        except ReturnException:
            raise
        except Exception as e:
            if not hasattr(e, 'line') and hasattr(node, 'line'):
                e.line = node.line
            raise e

    def generic_visit(self, node: Node):
        raise Exception(f'No visit_{type(node).__name__} method')

    def visit_statement_list(self, statements: List[Node]):
        """
        Executes a list of statements in order.
        """
        results = []
        for stmt in statements:
            results.append(self.visit(stmt))
        return results[-1] if results else None

    def visit_Number(self, node: Number):
        return node.value

    def visit_String(self, node: String):
        return node.value

    def visit_Boolean(self, node: Boolean):
        return node.value

    def visit_ListVal(self, node: ListVal):
        return [self.visit(e) for e in node.elements]

    def visit_Dictionary(self, node: Dictionary):
        return {self.visit(k): self.visit(v) for k, v in node.pairs}

    def visit_VarAccess(self, node: VarAccess):
        try:
            return self.current_env.get(node.name)
        except NameError:
            if node.name in self.builtins:
                val = self.builtins[node.name]
                if node.name in ('random', 'time_now', 'date_str'):
                    return val()
                return val
            if node.name in self.functions:
                return self.visit_Call(Call(node.name, []))
            raise

    def visit_Assign(self, node: Assign):
        value = self.visit(node.value)
        self.current_env.set(node.name, value)
        return value

    def visit_ConstAssign(self, node: ConstAssign):
        value = self.visit(node.value)
        self.current_env.set_const(node.name, value)
        return value

    _TYPE_MAP = {
        'int': int, 'integer': int,
        'float': float, 'decimal': float, 'number': float,
        'str': str, 'string': str, 'text': str,
        'bool': bool, 'boolean': bool,
        'list': list, 'array': list,
        'dict': dict, 'map': dict,
    }

    def visit_TypedAssign(self, node: TypedAssign):
        value = self.visit(node.value)
        expected = self._TYPE_MAP.get(node.type_hint)
        if expected is not None and not isinstance(value, expected):
            try:
                value = expected(value)
            except (ValueError, TypeError):
                raise TypeError(
                    f"Type error: '{node.name}' declared as '{node.type_hint}' "
                    f"but got {type(value).__name__} ({value!r})"
                )
        self.current_env.set(node.name, value)
        return value

    def visit_PropertyAssign(self, node: PropertyAssign):
        instance = self.current_env.get(node.instance_name)
        val = self.visit(node.value)
        if isinstance(instance, Instance):
            instance.data[node.property_name] = val
            return val
        elif isinstance(instance, dict):
            instance[node.property_name] = val
            return val
        else:
            raise TypeError(
                f"Cannot assign property '{node.property_name}' "
                f"of non-object '{node.instance_name}'"
            )

    def visit_IndexAccess(self, node: IndexAccess):
        obj = self.visit(node.obj)
        index = self.visit(node.index)
        try:
            return obj[index]
        except (IndexError, KeyError, TypeError) as e:
            raise RuntimeError(f"Index access error: {e}")

    def visit_IndexAssign(self, node: IndexAssign):
        obj = self.visit(node.obj)
        index = self.visit(node.index)
        value = self.visit(node.value)
        try:
            obj[index] = value
            return value
        except (IndexError, KeyError, TypeError) as e:
            raise RuntimeError(f"Index assignment error: {e}")

    def visit_BinOp(self, node: BinOp):
        if node.op == '.':
            left = self.visit(node.left)
            if isinstance(node.right, VarAccess):
                attr = node.right.name
                if hasattr(left, attr): return getattr(left, attr)
                if hasattr(left, 'get'): return left.get(attr)
                if isinstance(left, Instance) and attr in left.data:
                    return left.data[attr]
                raise AttributeError(f"Member '{attr}' not found on {left}")
            elif isinstance(node.right, Call):
                func = None
                attr = node.right.name
                if isinstance(left, str) and attr == 'trim': attr = 'strip'
                if hasattr(left, attr):
                    func = getattr(left, attr)
                elif hasattr(left, 'get'):
                    func = left.get(attr)
                
                if not func and isinstance(left, Instance):
                    method_node = self._find_method(left.class_def, attr)
                    if method_node:
                        args = [self.visit(a) for a in node.right.args]
                        old_env = self.current_env
                        new_env = Environment(parent=self.global_env)
                        new_env.set('self', left)
                        for k, v in left.data.items(): new_env.set(k, v)
                        for i, (arg_name, default_node, type_hint) in enumerate(method_node.args):
                            if i < len(args): val = args[i]
                            elif default_node is not None: val = self.visit(default_node)
                            else: raise TypeError(f"Missing arg '{arg_name}' for method '{attr}'")
                            new_env.set(arg_name, val)
                        self.current_env = new_env
                        ret_val = None
                        try:
                            for stmt in method_node.body: self.visit(stmt)
                        except ReturnException as e: ret_val = e.value
                        finally:
                            for k in left.data.keys():
                                if k in new_env.variables: left.data[k] = new_env.variables[k]
                            self.current_env = old_env
                        return ret_val

                if not func: raise AttributeError(f"Method '{attr}' not found")
                args = [self.visit(a) for a in node.right.args]
                kwargs = {}
                if getattr(node.right, 'kwargs', None):
                    for k, v in node.right.kwargs: kwargs[k] = self.visit(v)
                return func(*args, **kwargs)
            raise SyntaxError(f"Invalid member access: {node.right}")

        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            if node.op == '+':
                if isinstance(left, (str, list)) or isinstance(right, (str, list)):
                    if isinstance(left, list) and isinstance(right, list): return left + right
                    return str(left) + str(right)
                return left + right
            elif node.op == '-': return left - right
            elif node.op == '*': return left * right
            elif node.op == '/': return left / right
            elif node.op == '%': return left % right
            elif node.op == '==': return left == right
            elif node.op == '!=': return left != right
            elif node.op == '<': return left < right
            elif node.op == '>': return left > right
            elif node.op == '<=': return left <= right
            elif node.op == '>=': return left >= right
            elif node.op == 'in': return left in right
            elif node.op == 'not in': return left not in right
            elif node.op == 'and': return left and right
            elif node.op == 'or': return left or right
            elif node.op == 'matches': return bool(re.search(str(right), str(left)))
            else: raise Exception(f"Unknown operator: {node.op}")
        except TypeError as e: raise e

    def visit_UnaryOp(self, node: UnaryOp):
        val = self.visit(node.right)
        if node.op == 'not': return not val
        elif node.op == '-': return -val
        raise Exception(f"Unknown unary operator: {node.op}")

    def visit_Print(self, node: Print):
        value = self.visit(node.expression)
        if node.color or node.style:
            colors = {'red': '91', 'green': '92', 'yellow': '93', 'blue': '94', 'magenta': '95', 'cyan': '96'}
            code_parts = []
            if node.style == 'bold': code_parts.append('1')
            if node.color and node.color.lower() in colors: code_parts.append(colors[node.color.lower()])
            if code_parts:
                ansi_code = "\033[" + ";".join(code_parts) + "m"
                print(f"{ansi_code}{value}\033[0m", flush=True)
                return value
        print(value, flush=True)
        return value

    def visit_If(self, node: If):
        if self.visit(node.condition):
            for stmt in node.body: self.visit(stmt)
        elif node.else_body:
            for stmt in node.else_body: self.visit(stmt)

    def visit_Unless(self, node: Unless):
        if not self.visit(node.condition):
            for stmt in node.body: self.visit(stmt)
        elif node.else_body:
            for stmt in node.else_body: self.visit(stmt)

    def visit_Match(self, node):
        match_val = self.visit(node.match_expr)
        for case_expr, case_body in node.cases:
            if match_val == self.visit(case_expr):
                for stmt in case_body: self.visit(stmt)
                return
        if node.default_case:
            for stmt in node.default_case: self.visit(stmt)

    def visit_For(self, node: For):
        count = self.visit(node.count)
        if not isinstance(count, int): raise TypeError(f"Loop count must be int, got {type(count)}")
        for _ in range(count):
            try:
                for stmt in node.body: self.visit(stmt)
            except StopException: break
            except SkipException: continue

    def visit_ForIn(self, node: ForIn):
        iterable = self.visit(node.iterable)
        if not hasattr(iterable, '__iter__'): raise TypeError(f"Cannot iterate over {type(iterable).__name__}")
        for item in iterable:
            self.current_env.set(node.var_name, item)
            try:
                for stmt in node.body: self.visit(stmt)
            except StopException: break
            except SkipException: continue

    def visit_While(self, node: While):
        while self.visit(node.condition):
            try:
                for stmt in node.body: self.visit(stmt)
            except StopException: break
            except SkipException: continue

    def visit_Until(self, node: Until):
        while not self.visit(node.condition):
            try:
                for stmt in node.body: self.visit(stmt)
            except StopException: break
            except SkipException: continue

    def visit_Repeat(self, node: Repeat):
        count = self.visit(node.count)
        if not isinstance(count, int): raise TypeError(f"repeat count must be int, got {type(count)}")
        old_env = self.current_env
        self.current_env = Environment(parent=self.current_env)
        try:
            for i in range(count):
                self.current_env.set('index', i)
                try:
                    for stmt in node.body: self.visit(stmt)
                except StopException: break
                except SkipException: continue
        finally: self.current_env = old_env

    def visit_Forever(self, node: Forever):
        while True:
            try:
                for stmt in node.body: self.visit(stmt)
            except StopException: break
            except SkipException: continue

    def visit_Stop(self, node: Stop): raise StopException()
    def visit_Skip(self, node: Skip): raise SkipException()

    def visit_Try(self, node: Try):
        try:
            for stmt in node.try_body: self.visit(stmt)
        except Exception as e:
            self.current_env.set(node.catch_var, str(getattr(e, 'message', e)))
            for stmt in node.catch_body: self.visit(stmt)

    def visit_TryAlways(self, node: TryAlways):
        try:
            try:
                for stmt in node.try_body: self.visit(stmt)
            except Exception as e:
                self.current_env.set(node.catch_var, str(getattr(e, 'message', e)))
                for stmt in node.catch_body: self.visit(stmt)
        finally:
            for stmt in node.always_body: self.visit(stmt)

    def visit_Throw(self, node: Throw):
        raise ShellLiteError(str(self.visit(node.message)))

    def visit_FunctionDef(self, node: FunctionDef):
        self.functions[node.name] = node

    def visit_Return(self, node: Return):
        raise ReturnException(self.visit(node.value))

    def _call_function_def(self, func_def: FunctionDef, args: List[Node]):
        if len(args) > len(func_def.args): raise TypeError(f"Func '{func_def.name}' expects max {len(func_def.args)} args")
        old_env = self.current_env
        new_env = Environment(parent=self.global_env)
        for i, (name, default, hint) in enumerate(func_def.args):
            if i < len(args): val = self.visit(args[i])
            elif default is not None: val = self.visit(default)
            else: raise TypeError(f"Missing required arg '{name}' for func '{func_def.name}'")
            if hint: self._check_type(name, val, hint)
            new_env.set(name, val)
        self.current_env = new_env
        try:
            ret_val = None
            for stmt in func_def.body: ret_val = self.visit(stmt)
            return ret_val
        except ReturnException as e: return e.value
        finally: self.current_env = old_env

    def visit_Call(self, node: Call):
        kwargs = {k: self.visit(v) for k, v in (node.kwargs or [])}
        if node.name in self.builtins:
             args = [self.visit(a) for a in node.args]
             result = self.builtins[node.name](*args, **kwargs)
             if isinstance(result, Tag) and node.body:
                 self.web.push(result)
                 try:
                     for stmt in node.body:
                         res = self.visit(stmt)
                         if isinstance(res, (str, Tag)): self.web.add_text(res)
                 finally: self.web.pop()
             return result
        try:
            func = self.current_env.get(node.name)
            if callable(func): return func(*[self.visit(a) for a in node.args], **kwargs)
        except NameError: pass
        if node.name in self.classes:
            return self.visit_Instantiation(Instantiation(None, node.name, node.args, node.kwargs))
        if node.name in self.functions:
            return self._call_function_def(self.functions[node.name], node.args)
        raise NameError(f"Function '{node.name}' not defined.")

    def visit_ClassDef(self, node: ClassDef):
        self.classes[node.name] = node

    def visit_Instantiation(self, node: Instantiation):
        if node.class_name not in self.classes: raise NameError(f"Class '{node.class_name}' not defined.")
        class_def = self.classes[node.class_name]
        props = self._get_class_properties(class_def)
        req_count = sum(1 for p in props if p[1] is None)
        if len(node.args) < req_count: raise TypeError(f"'{node.class_name}' expects at least {req_count} args")
        instance = Instance(class_def)
        for i, (name, default) in enumerate(props):
            if i < len(node.args): val = self.visit(node.args[i])
            elif default is not None: val = self.visit(default)
            else: raise TypeError(f"Missing arg for property '{name}'")
            instance.data[name] = val
        if node.var_name: self.current_env.set(node.var_name, instance)
        return instance

    def visit_MethodCall(self, node: MethodCall):
        instance = self.current_env.get(node.instance_name)
        if isinstance(instance, dict):
            method = instance.get(node.method_name)
            if isinstance(method, FunctionDef): return self._call_function_def(method, node.args)
            if callable(method): return method(*[self.visit(a) for a in node.args])
        if hasattr(instance, node.method_name) and callable(getattr(instance, node.method_name)):
             return getattr(instance, node.method_name)(*[self.visit(a) for a in node.args])
        if isinstance(instance, Instance):
            method_node = self._find_method(instance.class_def, node.method_name)
            if method_node:
                old_env = self.current_env
                new_env = Environment(parent=self.global_env)
                new_env.set('self', instance)
                for k, v in instance.data.items(): new_env.set(k, v)
                args = [self.visit(a) for a in node.args]
                for i, (name, default, hint) in enumerate(method_node.args):
                    if i < len(args): val = args[i]
                    elif default is not None: val = self.visit(default)
                    else: raise TypeError(f"Missing required arg '{name}'")
                    new_env.set(name, val)
                self.current_env = new_env
                try:
                    for stmt in method_node.body: self.visit(stmt)
                    return None
                except ReturnException as e: return e.value
                finally:
                    for k in instance.data:
                        if k in new_env.variables: instance.data[k] = new_env.variables[k]
                    self.current_env = old_env
        raise AttributeError(f"Method '{node.method_name}' not found.")

    def visit_PropertyAccess(self, node: PropertyAccess):
        instance = self.current_env.get(node.instance_name)
        if isinstance(instance, Instance):
            if node.property_name in instance.data: return instance.data[node.property_name]
        elif isinstance(instance, dict):
            if node.property_name in instance: return instance[node.property_name]
        elif isinstance(instance, (list, str)) and node.property_name == 'length':
            return len(instance)
        if hasattr(instance, node.property_name): return getattr(instance, node.property_name)
        raise AttributeError(f"'{node.instance_name}' has no property '{node.property_name}'")

    def visit_Import(self, node: Import):
        if node.path in self.std_modules:
            self.current_env.set(node.path, self.std_modules[node.path])
            return
        target_path = node.path if os.path.exists(node.path) else os.path.join(os.path.expanduser("~"), ".shell_lite", "modules", node.path)
        if not os.path.exists(target_path) and not target_path.endswith('.shl'): target_path += ".shl"
        if os.path.isdir(target_path):
             for f in ["main.shl", f"{os.path.basename(target_path)}.shl"]:
                 if os.path.exists(os.path.join(target_path, f)):
                     target_path = os.path.join(target_path, f)
                     break
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                for stmt in Parser(Lexer(f.read()).tokenize()).parse(): self.visit(stmt)
            return
        try:
            mod = importlib.import_module(node.path)
            self.current_env.set(node.path, Namespace(node.path, {k: getattr(mod, k) for k in dir(mod) if not k.startswith('_')}))
            return
        except ImportError: pass
        raise FileNotFoundError(f"Could not find module '{node.path}'")

    def visit_ImportAs(self, node: ImportAs):
        if node.path in self.std_modules:
            self.current_env.set(node.alias, self.std_modules[node.path])
            return
        old_funcs = set(self.functions.keys())
        module_env = Environment(parent=self.global_env)
        old_env = self.current_env
        self.current_env = module_env
        try:
            self.visit_Import(Import(node.path))
            exports = dict(module_env.variables)
            for f in (set(self.functions.keys()) - old_funcs):
                exports[f] = self.functions[f]
                del self.functions[f]
            self.current_env = old_env
            self.current_env.set(node.alias, exports)
        except Exception as e:
            self.current_env = old_env
            raise RuntimeError(f"Failed to import '{node.path}': {e}")

    def visit_PythonImport(self, node: PythonImport):
        if node.module_name in self.std_modules:
            self.current_env.set(node.alias or node.module_name, self.std_modules[node.module_name])
        else:
            self.current_env.set(node.alias or node.module_name, importlib.import_module(node.module_name))

    def visit_FromImport(self, node: FromImport):
        mod = importlib.import_module(node.module_name)
        for name, alias in node.names:
            self.global_env.set(alias or name, getattr(mod, name))

    def _get_class_properties(self, class_def: ClassDef) -> List[tuple[str, Optional[Node]]]:
        props = [(p[0], p[1]) if isinstance(p, tuple) else (p, None) for p in class_def.properties]
        if class_def.parent:
            return self._get_class_properties(self.classes[class_def.parent]) + props
        return props

    def _find_method(self, class_def: ClassDef, method_name: str) -> Optional[FunctionDef]:
        for m in class_def.methods:
            if m.name == method_name: return m
        if class_def.parent: return self._find_method(self.classes[class_def.parent], method_name)
        return None

    def builtin_run(self, cmd):
        if self.safe_mode: raise PermissionError("System execution disabled")
        return subprocess.check_output(cmd, shell=True).decode()

    def builtin_read(self, path):
        if self.safe_mode: raise PermissionError("File reading disabled")
        with open(path, 'r') as f: return f.read()

    def builtin_write(self, path, content):
        if self.safe_mode: raise PermissionError("File writing disabled")
        with open(path, 'w') as f: f.write(content)

    def builtin_json_parse(self, s):
        try: return json.loads(s)
        except Exception as e: raise RuntimeError(f"Invalid JSON: {e}")

    def builtin_json_stringify(self, obj):
        try: return json.dumps(obj.data if isinstance(obj, Instance) else obj)
        except Exception as e: raise RuntimeError(f"JSON stringify failed: {e}")

    def builtin_http_get(self, url, headers=None):
        return self.web_engine._http_get(url) # Fallback to engine's helper if needed

    def builtin_http_post(self, url, data, headers=None):
        return self.web_engine._http_post(url, data)

    def visit_ListComprehension(self, node: ListComprehension):
        iterable = self.visit(node.iterable)
        result = []
        old_env = self.current_env
        self.current_env = Environment(parent=self.current_env)
        try:
            for item in iterable:
                self.current_env.set(node.var_name, item)
                if not node.condition or self.visit(node.condition):
                    result.append(self.visit(node.expr))
        finally: self.current_env = old_env
        return result

    def visit_Spawn(self, node: Spawn): return self._shared_executor.submit(self.visit, node.call)
    def visit_Await(self, node: Await):
        task = self.visit(node.task)
        return task.result() if isinstance(task, concurrent.futures.Future) else task

    def _check_type(self, name, val, hint):
        types = {'int': int, 'str': str, 'bool': bool, 'float': (float, int), 'list': list}
        if hint in types and not isinstance(val, types[hint]):
            raise TypeError(f"Arg '{name}' expects {hint}, got {type(val).__name__}")

    def visit_Execute(self, node: Execute):
        code = self.visit(node.code)
        res = None
        for stmt in Parser(Lexer(code).tokenize()).parse(): res = self.visit(stmt)
        self.current_env.set('__exec_result__', res)
        return res

    def visit_Exit(self, node: Exit): sys.exit(int(self.visit(node.code) if node.code else 0))

    def visit_Convert(self, node: Convert):
        val = self.visit(node.expression)
        if node.target_format.lower() == 'json':
             return json.loads(val) if isinstance(val, str) else json.dumps(val.data if isinstance(val, Instance) else val)
        raise ValueError(f"Unknown format: {node.target_format}")

    def visit_Parallel(self, node: Parallel): return [self._shared_executor.submit(self.visit, s) for s in node.body]
    def visit_Gather(self, node: Gather):
        tasks = self.visit(node.tasks)
        return [f.result() if isinstance(f, concurrent.futures.Future) else f for f in (tasks if isinstance(tasks, list) else [tasks])]

    def visit_Lock(self, node: Lock):
        if node.name not in self._named_locks: self._named_locks[node.name] = threading.Lock()
        with self._named_locks[node.name]: return self.visit_statement_list(node.body)

    def visit_Channel(self, node: Channel): return queue.Queue()
    def visit_Send(self, node: Send):
        q = self.visit(node.channel)
        val = self.visit(node.value)
        if isinstance(q, queue.Queue): q.put(val)
        return val
    def visit_Receive(self, node: Receive):
        q = self.visit(node.channel)
        return q.get() if isinstance(q, queue.Queue) else None

    def visit_Every(self, node: Every):
        interval = self.visit(node.interval) * (60 if node.unit == 'minutes' else 1)
        while True:
            for stmt in node.body: self.visit(stmt)
            time.sleep(interval)

    def visit_After(self, node: After):
        time.sleep(self.visit(node.delay) * (60 if node.unit == 'minutes' else 1))
        for stmt in node.body: self.visit(stmt)

    def visit_ArchiveOp(self, node: ArchiveOp):
        if self.safe_mode: raise PermissionError("Archive operations disabled")
        src, tgt = str(self.visit(node.source)), str(self.visit(node.target))
        if node.op == 'compress':
            if os.path.isfile(src):
                with zipfile.ZipFile(tgt, 'w') as z: z.write(src, arcname=os.path.basename(src))
            else: shutil.make_archive(tgt.replace('.zip', ''), 'zip', src)
        else:
            with zipfile.ZipFile(src, 'r') as z: z.extractall(tgt)

    def visit_CsvOp(self, node: CsvOp):
        path = self.visit(node.path)
        if node.op == 'load':
            with open(path, 'r', newline='') as f: return [row for row in csv.DictReader(f)]
        else:
            data = self.visit(node.data)
            rows = [item.data if isinstance(item, Instance) else item for item in (data if isinstance(data, list) else [data])]
            if rows:
                with open(path, 'w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=rows[0].keys())
                    w.writeheader()
                    w.writerows(rows)

    def visit_ClipboardOp(self, node: ClipboardOp):
        if node.op == 'copy': pyperclip.copy(str(self.visit(node.content)))
        else: return pyperclip.paste()

    def visit_AutomationOp(self, node: AutomationOp):
        if self.safe_mode: raise PermissionError("Automation disabled")
        args = [self.visit(a) for a in node.args]
        if node.action == 'press': keyboard.press_and_release(args[0])
        elif node.action == 'type': keyboard.write(str(args[0]))
        elif node.action == 'click':
             mouse.move(args[0], args[1], absolute=True, duration=0.2)
             mouse.click('left')
        elif node.action == 'notify': notification.notify(title=str(args[0]), message=str(args[1]))

    def visit_FileWrite(self, node: FileWrite):
        if self.safe_mode: raise PermissionError("File writing disabled")
        with open(str(self.visit(node.path)), node.mode, encoding='utf-8') as f: f.write(str(self.visit(node.content)))

    def visit_FileRead(self, node: FileRead):
        if self.safe_mode: raise PermissionError("File reading disabled")
        with open(str(self.visit(node.path)), 'r', encoding='utf-8') as f: return f.read()

    def visit_TestBlock(self, node: TestBlock):
        try:
            for stmt in node.body: self.visit(stmt)
            print(f"\033[92m[PASS]\033[0m {node.name}")
        except AssertionError as e: print(f"\033[91m[FAIL]\033[0m {node.name}: {e}")
        except Exception as e: print(f"\033[91m[ERROR]\033[0m {node.name}: {e}")

    def visit_Assertion(self, node: Assertion):
        l, r = self.visit(node.left), self.visit(node.right) if node.right else None
        if node.right is None:
            if not l: raise AssertionError(f"Expected truthy, got {l}")
        elif node.op == '==' and l != r: raise AssertionError(f"Expected {r}, got {l}")
        elif node.op == '!=' and l == r: raise AssertionError(f"Expected not {r}, got {l}")

    def visit_MaxNode(self, node: MaxNode):
        l = self.visit(node.left)
        return max(l, self.visit(node.right)) if node.right else (max(l) if isinstance(l, (list, tuple)) else l)

    def visit_MinNode(self, node: MinNode):
        l = self.visit(node.left)
        return min(l, self.visit(node.right)) if node.right else min(l)

    def visit_ClampNode(self, node: ClampNode):
        return max(self.visit(node.min_val), min(self.visit(node.value), self.visit(node.max_val)))

    def visit_LerpNode(self, node: LerpNode):
        a, b, t = self.visit(node.start), self.visit(node.end), self.visit(node.alpha)
        return a + (b - a) * t

    # GUI Engine Delegation
    def visit_App(self, node): return self.gui_engine.visit_App(node)
    def visit_Layout(self, node): return self.gui_engine.visit_Layout(node)
    def visit_Widget(self, node): return self.gui_engine.visit_Widget(node)
    def visit_Alert(self, node): return self.gui_engine.visit_Alert(node)
    def visit_Prompt(self, node): return self.gui_engine.visit_Prompt(node)
    def visit_Confirm(self, node): return self.gui_engine.visit_Confirm(node)

    # DB Engine Delegation
    def visit_DatabaseOp(self, node): return self.db_engine.visit_DatabaseOp(node)
    def visit_ModelDef(self, node): return self.db_engine.visit_ModelDef(node)
    def visit_CreateTable(self, node): return self.db_engine.visit_CreateTable(node)
    def visit_InsertRecord(self, node): return self.db_engine.visit_InsertRecord(node)
    def visit_FindRecords(self, node): return self.db_engine.visit_FindRecords(node)
    def visit_UpdateRecords(self, node): return self.db_engine.visit_UpdateRecords(node)
    def visit_DeleteRecords(self, node): return self.db_engine.visit_DeleteRecords(node)

    # Web Engine Delegation
    def visit_Listen(self, node): return self.web_engine.visit_Listen(node)
    def visit_Download(self, node): return self.web_engine.visit_Download(node)
    def visit_OnRequest(self, node): return self.web_engine.visit_OnRequest(node)
    def visit_ServeStatic(self, node): return self.web_engine.visit_ServeStatic(node)
