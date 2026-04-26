from typing import Any, Dict, List, Callable
from .ast_nodes import *
from .lexer import Token, Lexer
from .parser import Parser
import importlib
import operator
import re
import os
import sys
import subprocess
import json
import math
import time
import random
import urllib.request
import urllib.parse
import shutil
import functools
from datetime import datetime
import threading
import concurrent.futures
import tkinter as tk
from tkinter import messagebox, simpledialog
from http.server import HTTPServer, BaseHTTPRequestHandler
import csv
import zipfile
from datetime import timedelta
import calendar
import sqlite3
try:
    import keyboard
    import mouse
    import pyperclip
    from plyer import notification
except ImportError:
    pass 
class Environment:
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
        if self.parent and name in self.parent.constants:
            raise RuntimeError(f"Cannot reassign constant '{name}'")
        self.variables[name] = value
    def set_const(self, name: str, value: Any):
        if name in self.variables:
            raise RuntimeError(f"Constant '{name}' already declared")
        self.variables[name] = value
        self.constants.add(name)
class ReturnException(Exception):
    def __init__(self, value):
        self.value = value
class StopException(Exception):
    pass
class SkipException(Exception):
    pass
class ShellLiteError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
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
    def __init__(self, class_def: ClassDef):
        self.class_def = class_def
        self.data: Dict[str, Any] = {}
class Tag:
    def __init__(self, name: str, attrs: Dict[str, Any] = None):
        self.name = name
        self.attrs = attrs or {}
        self.children: List[Any] = []
    def add(self, child):
        if isinstance(child, Tag):
             if any(c is child for c in self.children):
                 return
        self.children.append(child)
    def __str__(self):
        attr_str = ""
        for k, v in self.attrs.items():
            attr_str += f' {k}="{v}"'
        inner = ""
        for child in self.children:
            inner += str(child)
        if self.name in ('img', 'br', 'hr', 'input', 'meta', 'link'):
            return f"<{self.name}{attr_str} />"
        return f"<{self.name}{attr_str}>{inner}</{self.name}>"
class WebBuilder:
    def __init__(self, interpreter):
        self.stack: List[Tag] = []
        self.interpreter = interpreter
    def push(self, tag: Tag):
        if self.stack:
            self.stack[-1].add(tag)
        self.stack.append(tag)
    def pop(self):
        if not self.stack: return None
        return self.stack.pop()
    def add_text(self, text: str):
        if self.stack:
            self.stack[-1].add(text)
        else:
            pass
class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.current_env = self.global_env
        self.functions: Dict[str, FunctionDef] = {}
        self.classes: Dict[str, ClassDef] = {}
        self.http_routes = [] 
        self.middleware_routes = [] 
        self.static_routes = {} 
        self.web = WebBuilder(self)
        self.db_conn = None
        self.builtins = {
            'str': str, 'int': int, 'float': float, 'bool': bool,
            'list': list, 'len': len,
            'range': lambda *args: list(range(*args)),
            'typeof': lambda x: type(x).__name__,
            'run': self.builtin_run,
            'read': self.builtin_read,
            'write': self.builtin_write,
            'json_parse': self.builtin_json_parse,
            'json_stringify': self.builtin_json_stringify,
            'print': print,
            'abs': abs, 'min': min, 'max': max,
            'round': round, 'pow': pow, 'sum': sum,
            'split': lambda s, d=" ": s.split(d),
            'join': lambda lst, d="": d.join(str(x) for x in lst),
            'replace': lambda s, old, new: s.replace(old, new),
            'upper': lambda s: s.upper(),
            'lower': lambda s: s.lower(),
            'trim': lambda s: s.strip(),
            'startswith': lambda s, p: s.startswith(p),
            'endswith': lambda s, p: s.endswith(p),
            'find': lambda s, sub: s.find(sub),
            'char': chr, 'ord': ord,
            'append': lambda l, x: (l.append(x), l)[1],
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
            'map': self._builtin_map,
            'filter': self._builtin_filter,
            'reduce': self._builtin_reduce,
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
            'wait': time.sleep,
            'wait': time.sleep,
            'push': self._builtin_push,
            'remove': lambda lst, item: lst.remove(item),
            'Set': set, 
            'show': print,
            'say': print,
            'today': lambda: datetime.now().strftime("%Y-%m-%d"),
        }
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
        self.builtins['int'] = lambda x: int(float(x)) if x else 0
        self.builtins['str'] = lambda x: str(x)
        class TimeWrapper:
            def now(self):
                return str(int(time.time()))
        self.builtins['time'] = TimeWrapper()
        self._init_std_modules()
        for k, v in self.builtins.items():
            self.global_env.set(k, v)
    def _make_tag_fn(self, tag_name):
        def tag_fn(*args):
            attrs = {}
            content = []
            for arg in args:
                if isinstance(arg, dict):
                    attrs.update(arg)
                elif isinstance(arg, str):
                    if '=' in arg and not ' ' in arg and arg.split('=')[0].isalnum():
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
    def _builtin_map(self, lst, func):
        if callable(func):
            return [func(x) for x in lst]
        raise TypeError("map requires a callable")
    def _builtin_filter(self, lst, func):
        if callable(func):
            return [x for x in lst if func(x)]
        raise TypeError("filter requires a callable")
    def _builtin_reduce(self, lst, func, initial=None):
        if callable(func):
            if initial is not None:
                return functools.reduce(func, lst, initial)
            return functools.reduce(func, lst)
        raise TypeError("reduce requires a callable")
    def _builtin_push(self, lst, item):
        lst.append(item)
        return None
    def _init_std_modules(self):
        self.std_modules = {
            'math': {
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'sqrt': math.sqrt,
                'floor': math.floor,
                'ceil': math.ceil,
                'abs': abs,
                'pow': pow,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'random': random.random,
                'randint': random.randint,
                'pi': math.pi,
                'e': math.e,
            },
            'time': {
                'time': time.time,
                'sleep': time.sleep,
                'date': lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'year': lambda: datetime.now().year,
                'month': lambda: datetime.now().month,
                'day': lambda: datetime.now().day,
                'hour': lambda: datetime.now().hour,
                'minute': lambda: datetime.now().minute,
                'second': lambda: datetime.now().second,
            },
            'http': {
                'get': self._http_get,
                'post': self._http_post
            },
            'env': {
                'get': lambda k, d=None: os.environ.get(k, d),
                'set': lambda k, v: os.environ.__setitem__(k, str(v)),
                'all': lambda: dict(os.environ),
                'has': lambda k: k in os.environ,
            },
            'args': {
                'get': lambda i: sys.argv[i+1] if i+1 < len(sys.argv) else None,
                'all': lambda: sys.argv[1:],
                'count': lambda: len(sys.argv) - 1,
            },
            'path': {
                'join': os.path.join,
                'basename': os.path.basename,
                'dirname': os.path.dirname,
                'exists': os.path.exists,
                'isfile': os.path.isfile,
                'isdir': os.path.isdir,
                'abspath': os.path.abspath,
                'split': os.path.split,
                'ext': lambda p: os.path.splitext(p)[1],
            },
            'color': {
                'red': lambda s: f"\033[91m{s}\033[0m",
                'green': lambda s: f"\033[92m{s}\033[0m",
                'yellow': lambda s: f"\033[93m{s}\033[0m",
                'blue': lambda s: f"\033[94m{s}\033[0m",
                'magenta': lambda s: f"\033[95m{s}\033[0m",
                'cyan': lambda s: f"\033[96m{s}\033[0m",
                'bold': lambda s: f"\033[1m{s}\033[0m",
                'underline': lambda s: f"\033[4m{s}\033[0m",
                'reset': "\033[0m",
            },
            're': {
                'match': lambda p, s: bool(re.match(p, s)),
                'search': lambda p, s: re.search(p, s).group() if re.search(p, s) else None,
                'replace': lambda p, r, s: re.sub(p, r, s),
                'findall': lambda p, s: re.findall(p, s),
                'split': lambda p, s: re.split(p, s),
            },
        }
    def _http_get(self, url):
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    def _http_post(self, url, data):
        if isinstance(data, str):
            json_data = data.encode('utf-8')
        else:
            json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    def visit(self, node: Node) -> Any:
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
    def visit_Number(self, node: Number):
        return node.value
    def visit_String(self, node: String):
        return node.value
    def visit_Boolean(self, node: Boolean):
        return node.value
    def visit_ListVal(self, node: ListVal):
        result = []
        for e in node.elements:
            if isinstance(e, Spread):
                spread_val = self.visit(e.value)
                if not isinstance(spread_val, list):
                    raise TypeError(f"Spread operator requires a list, got {type(spread_val).__name__}")
                result.extend(spread_val)
            else:
                result.append(self.visit(e))
        return result
    def visit_Dictionary(self, node: Dictionary):
        return {self.visit(k): self.visit(v) for k, v in node.pairs}
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
             raise TypeError(f"Cannot assign property '{node.property_name}' of non-object '{node.instance_name}'")
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
    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            return left + right
        elif node.op == '-':
            return left - right
        elif node.op == '*':
            return left * right
        elif node.op == '/':
            return left / right
        elif node.op == '%':
            return left % right
        elif node.op == '==':
            return left == right
        elif node.op == '!=':
            return left != right
        elif node.op == '<':
            return left < right
        elif node.op == '>':
            return left > right
        elif node.op == '<=':
            return left <= right
        elif node.op == '>=':
            return left >= right
        elif node.op == 'and':
            return left and right
        elif node.op == 'or':
            return left or right
        elif node.op == 'matches':
            pattern = right
            if hasattr(pattern, 'search'):
                return bool(pattern.search(str(left)))
            return bool(re.search(str(pattern), str(left)))
        raise Exception(f"Unknown operator: {node.op}")
    def visit_Print(self, node: Print):
        value = self.visit(node.expression)
        if node.color or node.style:
            colors = {
                'red': '91', 'green': '92', 'yellow': '93', 'blue': '94',
                'magenta': '95', 'cyan': '96'
            }
            code_parts = []
            if node.style == 'bold':
                code_parts.append('1')
            if node.color and node.color.lower() in colors:
                code_parts.append(colors[node.color.lower()])
            if code_parts:
                ansi_code = "\033[" + ";".join(code_parts) + "m"
                print(f"{ansi_code}{value}\033[0m")
                return value
        print(value)
        return value
    def visit_If(self, node: If):
        condition = self.visit(node.condition)
        if condition:
            for stmt in node.body:
                self.visit(stmt)
        elif node.else_body:
            for stmt in node.else_body:
                self.visit(stmt)
    def visit_For(self, node: For):
        count = self.visit(node.count)
        if not isinstance(count, int):
            raise TypeError(f"Loop count must be an integer, got {type(count)}")
        for _ in range(count):
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except StopException:
                break
            except SkipException:
                continue
            except ReturnException:
                raise
    def visit_Input(self, node: Input):
        if node.prompt:
            return input(node.prompt)
        return input()
    def visit_While(self, node: While):
        while self.visit(node.condition):
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except StopException:
                break
            except SkipException:
                continue
            except ReturnException:
                raise
    def visit_Try(self, node: Try):
        try:
            for stmt in node.try_body:
                self.visit(stmt)
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'message'):
                error_msg = e.message
            self.current_env.set(node.catch_var, error_msg)
            for stmt in node.catch_body:
                self.visit(stmt)
    def visit_TryAlways(self, node: TryAlways):
        try:
            try:
                for stmt in node.try_body:
                    self.visit(stmt)
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'message'):
                    error_msg = e.message
                self.current_env.set(node.catch_var, error_msg)
                for stmt in node.catch_body:
                    self.visit(stmt)
        finally:
            for stmt in node.always_body:
                self.visit(stmt)
    def visit_UnaryOp(self, node: UnaryOp):
        val = self.visit(node.right)
        if node.op == 'not':
            return not val
        raise Exception(f"Unknown unary operator: {node.op}")
    def visit_FunctionDef(self, node: FunctionDef):
        self.functions[node.name] = node
    def visit_Return(self, node: Return):
        value = self.visit(node.value)
        raise ReturnException(value)
    def _call_function_def(self, func_def: FunctionDef, args: List[Node]):
        if len(args) > len(func_def.args):
             raise TypeError(f"Function '{func_def.name}' expects max {len(func_def.args)} arguments, got {len(args)}")
        old_env = self.current_env
        new_env = Environment(parent=self.global_env) 
        for i, (arg_name, default_node, type_hint) in enumerate(func_def.args):
            if i < len(args):
                val = self.visit(args[i])
            elif default_node is not None:
                val = self.visit(default_node)
            else:
                raise TypeError(f"Missing required argument '{arg_name}' for function '{func_def.name}'")
            if type_hint:
                self._check_type(arg_name, val, type_hint)
            new_env.set(arg_name, val)
        self.current_env = new_env
        ret_val = None
        try:
            for stmt in func_def.body:
                val = self.visit(stmt)
                ret_val = val
        except ReturnException as e:
            ret_val = e.value
        finally:
            self.current_env = old_env
        return ret_val
    def visit_Call(self, node: Call):
        if node.name in self.builtins:
             args = [self.visit(a) for a in node.args]
             result = self.builtins[node.name](*args)
             if isinstance(result, Tag):
                 if node.body:
                     self.web.push(result)
                     try:
                         for stmt in node.body:
                             res = self.visit(stmt)
                             if res is not None and (isinstance(res, str) or isinstance(res, Tag)):
                                 self.web.add_text(res)
                     finally:
                         self.web.pop()
                 return result
             return result
        try:
            func = self.current_env.get(node.name)
            if callable(func):
                args = [self.visit(a) for a in node.args]
                return func(*args)
            curr_obj = func
            if (isinstance(curr_obj, (list, dict, str)) or isinstance(curr_obj, Instance)):
                valid_chain = True
                for arg_node in node.args:
                    val = self.visit(arg_node)
                    if isinstance(val, list) and len(val) == 1:
                        idx = val[0]
                        try:
                            curr_obj = curr_obj[idx]
                        except (IndexError, KeyError) as e:
                            raise RuntimeError(f"Index/Key error: {e}")
                        except TypeError:
                             valid_chain = False; break
                    else:
                        valid_chain = False
                        break
                if valid_chain:
                    return curr_obj
                pass
        except NameError:
            pass
        except NameError:
            pass
        if node.name not in self.functions:
            raise NameError(f"Function '{node.name}' not defined (and not a variable).")
        func_def = self.functions[node.name]
        return self._call_function_def(func_def, node.args)
    def visit_ClassDef(self, node: ClassDef):
        self.classes[node.name] = node
    def visit_Instantiation(self, node: Instantiation):
        if node.class_name not in self.classes:
            raise NameError(f"Class '{node.class_name}' not defined.")
        class_def = self.classes[node.class_name]
        all_properties = self._get_class_properties(class_def)
        
        # Check args length
        # First count how many properties are required (no default)
        required_count = 0
        for name, default_val in all_properties:
            if default_val is None:
                required_count += 1
        
        if len(node.args) < required_count:
             raise TypeError(f"Structure '{node.class_name}' expects at least {required_count} args, got {len(node.args)}")
        
        instance = Instance(class_def)
        
        for i, (prop_name, default_val) in enumerate(all_properties):
            val = None
            if i < len(node.args):
                val = self.visit(node.args[i])
            elif default_val is not None:
                val = self.visit(default_val)
            else:
                # Should be caught by required_count check, but safety fallback
                raise TypeError(f"Missing argument for property '{prop_name}' in '{node.class_name}'")
            
            instance.data[prop_name] = val

        self.current_env.set(node.var_name, instance)
        return instance
    def visit_MethodCall(self, node: MethodCall):
        instance = self.current_env.get(node.instance_name)
        if isinstance(instance, dict):
            if node.method_name not in instance:
                raise AttributeError(f"Module '{node.instance_name}' has no method '{node.method_name}'")
            method = instance[node.method_name]
            if isinstance(method, FunctionDef):
                 return self._call_function_def(method, node.args)
            elif callable(method):
                args = [self.visit(a) for a in node.args]
                try:
                    return method(*args)
                except Exception as e:
                    raise RuntimeError(f"Error calling '{node.instance_name}.{node.method_name}': {e}")
            elif isinstance(method, (dict, list, str)):
                 curr_obj = method
                 valid_chain = True
                 for arg_node in node.args:
                    val = self.visit(arg_node)
                    if isinstance(val, list) and len(val) == 1:
                        idx = val[0]
                        try:
                            curr_obj = curr_obj[idx]
                        except (IndexError, KeyError) as e:
                            raise RuntimeError(f"Index/Key error: {e}")
                        except TypeError:
                             valid_chain = False; break
                    else:
                        valid_chain = False; break
                 if valid_chain:
                     return curr_obj
                 raise TypeError(f"Property '{node.method_name}' is not callable and index access failed.")
            else:
                 raise TypeError(f"Property '{node.method_name}' is not callable.")
        if hasattr(instance, node.method_name) and callable(getattr(instance, node.method_name)):
             method = getattr(instance, node.method_name)
             args = [self.visit(a) for a in node.args]
             return method(*args)
        if not isinstance(instance, Instance):
            raise TypeError(f"'{node.instance_name}' is not a structure instance (and has no native method '{node.method_name}').")
        method_node = self._find_method(instance.class_def, node.method_name)
        if not method_node:
            raise AttributeError(f"Structure '{instance.class_def.name}' has no method '{node.method_name}'")
        old_env = self.current_env
        new_env = Environment(parent=self.global_env)
        for k, v in instance.data.items():
            new_env.set(k, v)
        if len(node.args) > len(method_node.args):
             raise TypeError(f"Method '{node.method_name}' expects max {len(method_node.args)} arguments.")
        for i, (arg_name, default_node, type_hint) in enumerate(method_node.args):
             if i < len(node.args):
                 val = self.visit(node.args[i])
             elif default_node is not None:
                 val = self.visit(default_node)
             else:
                 raise TypeError(f"Missing required argument '{arg_name}' for method '{node.method_name}'")
             new_env.set(arg_name, val)
        self.current_env = new_env
        ret_val = None
        try:
            for stmt in method_node.body:
                self.visit(stmt)
        except ReturnException as e:
            ret_val = e.value
        finally:
            for k in instance.data.keys():
                if k in new_env.variables:
                    instance.data[k] = new_env.variables[k]
            self.current_env = old_env
        return ret_val
    def visit_PropertyAccess(self, node: PropertyAccess):
        instance = self.current_env.get(node.instance_name)
        
        # 1. ShellLite Instance
        if isinstance(instance, Instance):
            if node.property_name not in instance.data:
                 # Check for methods? PropertyAccess usually implies data.
                 # But in some cases we might want method reference?
                 raise AttributeError(f"Structure '{instance.class_def.name}' has no property '{node.property_name}'")
            return instance.data[node.property_name]
            
        # 2. Dictionary
        elif isinstance(instance, dict):
             if node.property_name in instance:
                 return instance[node.property_name]
             raise AttributeError(f"Dictionary has no key '{node.property_name}'")

        # 3. List
        elif isinstance(instance, list):
             if node.property_name == 'length':
                 return len(instance)
        
        # 4. String
        elif isinstance(instance, str):
             if node.property_name == 'length':
                 return len(instance)

        # 5. Python Object / Module Interop
        # If the instance has the attribute natively, return it.
        # This handles 'math.pi', 'os.name', etc.
        if hasattr(instance, node.property_name):
             return getattr(instance, node.property_name)
             
        raise TypeError(f"Object '{node.instance_name}' (type {type(instance).__name__}) has no property '{node.property_name}'")

    def visit_Import(self, node: Import):
        if node.path in self.std_modules:
            self.current_env.set(node.path, self.std_modules[node.path])
            return
        import os 
        if os.path.exists(node.path):
             target_path = node.path
        else:
             home = os.path.expanduser("~")
             global_path = os.path.join(home, ".shell_lite", "modules", node.path)
             if os.path.exists(global_path):
                 target_path = global_path
             else:
                 if not node.path.endswith('.shl'):
                     global_path_ext = global_path + ".shl"
                     if os.path.exists(global_path_ext):
                         target_path = global_path_ext
                     else:
                         raise FileNotFoundError(f"Could not find imported file: {node.path} (searched local and global modules)")
                 else:
                     raise FileNotFoundError(f"Could not find imported file: {node.path} (searched local and global modules)")
        if os.path.isdir(target_path):
             main_shl = os.path.join(target_path, "main.shl")
             pkg_shl = os.path.join(target_path, f"{os.path.basename(target_path)}.shl")
             if os.path.exists(main_shl):
                 target_path = main_shl
             elif os.path.exists(pkg_shl):
                 target_path = pkg_shl
             else:
                  raise FileNotFoundError(f"Package '{node.path}' is a folder but has no 'main.shl' or '{os.path.basename(target_path)}.shl'.")
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find imported file: {node.path}")
        from .lexer import Lexer
        from .parser import Parser
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        statements = parser.parse()
        for stmt in statements:
            self.visit(stmt)
    def _get_class_properties(self, class_def: ClassDef) -> List[tuple[str, Optional[Node]]]:
        if not hasattr(class_def, 'properties'): return []
        # Support both old string list and new tuple list for backward compat if needed, though we updated AST
        props = []
        for p in class_def.properties:
            if isinstance(p, tuple):
                props.append(p)
            else:
                props.append((p, None))
                
        if class_def.parent:
            if class_def.parent not in self.classes:
                raise NameError(f"Parent class '{class_def.parent}' not defined.")
            parent_def = self.classes[class_def.parent]
            return self._get_class_properties(parent_def) + props
        return props
    def _find_method(self, class_def: ClassDef, method_name: str) -> Optional[FunctionDef]:
        for m in class_def.methods:
            if m.name == method_name:
                return m
        if class_def.parent:
             if class_def.parent not in self.classes:
                raise NameError(f"Parent class '{class_def.parent}' not defined.")
             parent_def = self.classes[class_def.parent]
             return self._find_method(parent_def, method_name)
        return None
    def builtin_run(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Command Error: {result.stderr}")
            return result.stdout.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to run command: {e}")
    def builtin_read(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file '{path}': {e}")
    def builtin_write(self, path, content):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(str(content))
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to write file '{path}': {e}")
    def builtin_json_parse(self, json_str):
        try:
            return json.loads(json_str)
        except Exception as e:
            raise RuntimeError(f"Invalid JSON: {e}")
    def builtin_json_stringify(self, obj):
        try:
            if isinstance(obj, Instance):
                return json.dumps(obj.data)
            return json.dumps(obj)
        except Exception as e:
            raise RuntimeError(f"JSON stringify failed: {e}")
    def builtin_http_get(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"HTTP GET failed for '{url}': {e}")
    def builtin_http_post(self, url, data_dict):
        try:
            if isinstance(data_dict, Instance):
                data_dict = data_dict.data
            data = json.dumps(data_dict).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                 return response.read().decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"HTTP POST failed for '{url}': {e}")
    def visit_Lambda(self, node: Lambda):
        return LambdaFunction(node.params, node.body, self)
    def visit_Ternary(self, node: Ternary):
        condition = self.visit(node.condition)
        if condition:
            return self.visit(node.true_expr)
        else:
            return self.visit(node.false_expr)
    def visit_ListComprehension(self, node: ListComprehension):
        iterable = self.visit(node.iterable)
        if not hasattr(iterable, '__iter__'):
            raise TypeError(f"Cannot iterate over {type(iterable).__name__}")
        result = []
        old_env = self.current_env
        new_env = Environment(parent=self.current_env)
        self.current_env = new_env
        try:
            for item in iterable:
                new_env.set(node.var_name, item)
                if node.condition:
                    if not self.visit(node.condition):
                        continue
                result.append(self.visit(node.expr))
        finally:
            self.current_env = old_env
        return result
    def visit_Spread(self, node: Spread):
        return self.visit(node.value)
    def visit_Alert(self, node: Alert):
        msg = self.visit(node.message)
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo("Alert", str(msg))
        root.destroy()
    def visit_Prompt(self, node: Prompt):
        prompt = self.visit(node.prompt)
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        val = simpledialog.askstring("Input", str(prompt))
        root.destroy()
        return val if val is not None else ""
    def visit_Confirm(self, node: Confirm):
        prompt = self.visit(node.prompt)
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        val = messagebox.askyesno("Confirm", str(prompt))
        root.destroy()
        return val
    def visit_Spawn(self, node: Spawn):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.visit, node.call)
        return future
    def visit_Await(self, node: Await):
        task = self.visit(node.task)
        if isinstance(task, concurrent.futures.Future):
            return task.result()
        raise TypeError(f"Cannot await non-task object: {type(task)}")
    def visit_Regex(self, node: Regex):
        return re.compile(node.pattern)
    def visit_FileWatcher(self, node: FileWatcher):
        path = self.visit(node.path)
        if not os.path.exists(path):
            print(f"Warning: Watching non-existent file {path}")
            last_mtime = 0
        else:
            last_mtime = os.path.getmtime(path)
        try:
            while True:
                current_exists = os.path.exists(path)
                if current_exists:
                    current_mtime = os.path.getmtime(path)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        for stmt in node.body:
                            self.visit(stmt)
                time.sleep(1) 
        except StopException:
            pass 
        except ReturnException:
            raise
    def _check_type(self, arg_name, val, type_hint):
        if type_hint == 'int' and not isinstance(val, int):
            raise TypeError(f"Argument '{arg_name}' expects int, got {type(val).__name__}")
        elif type_hint == 'str' and not isinstance(val, str):
            raise TypeError(f"Argument '{arg_name}' expects str, got {type(val).__name__}")
        elif type_hint == 'bool' and not isinstance(val, bool):
             raise TypeError(f"Argument '{arg_name}' expects bool, got {type(val).__name__}")
        elif type_hint == 'float' and not isinstance(val, (float, int)):
             raise TypeError(f"Argument '{arg_name}' expects float, got {type(val).__name__}")
        elif type_hint == 'list' and not isinstance(val, list):
             raise TypeError(f"Argument '{arg_name}' expects list, got {type(val).__name__}")
    def visit_ConstAssign(self, node: ConstAssign):
        value = self.visit(node.value)
        self.current_env.set_const(node.name, value)
        return value
    def visit_ForIn(self, node: ForIn):
        iterable = self.visit(node.iterable)
        if not hasattr(iterable, '__iter__'):
            raise TypeError(f"Cannot iterate over {type(iterable).__name__}")
        old_env = self.current_env
        new_env = Environment(parent=self.current_env)
        self.current_env = new_env
        try:
            for item in iterable:
                new_env.set(node.var_name, item)
                for stmt in node.body:
                    self.visit(stmt)
        except ReturnException:
            raise
        finally:
            self.current_env = old_env
    def visit_IndexAccess(self, node: IndexAccess):
        obj = self.visit(node.obj)
        index = self.visit(node.index)
        if isinstance(obj, list):
            if not isinstance(index, int):
                raise TypeError(f"List indices must be integers, got {type(index).__name__}")
            return obj[index]
        elif isinstance(obj, dict):
            return obj[index]
        elif isinstance(obj, str):
            if not isinstance(index, int):
                raise TypeError(f"String indices must be integers, got {type(index).__name__}")
            return obj[index]
        else:
            raise TypeError(f"'{type(obj).__name__}' object is not subscriptable")
    def visit_Stop(self, node: Stop):
        raise StopException()
    def visit_Skip(self, node: Skip):
        raise SkipException()
    def visit_PythonImport(self, node: PythonImport):
        try:
            mod = importlib.import_module(node.module_name)
            name = node.alias if node.alias else node.module_name.split('.')[0]
            self.global_env.set(name, mod)
        except ImportError as e:
            raise RuntimeError(f"Could not import python module '{node.module_name}': {e}")
            
    def visit_Throw(self, node: Throw):
        message = self.visit(node.message)
        raise ShellLiteError(str(message))
    def visit_Unless(self, node: Unless):
        condition = self.visit(node.condition)
        if not condition:
            for stmt in node.body:
                self.visit(stmt)
        elif node.else_body:
            for stmt in node.else_body:
                self.visit(stmt)
    def visit_Until(self, node: Until):
        while not self.visit(node.condition):
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except StopException:
                break
            except SkipException:
                continue
            except ReturnException:
                raise
    def visit_Repeat(self, node: Repeat):
        count = self.visit(node.count)
        if not isinstance(count, int):
            raise TypeError(f"repeat count must be an integer, got {type(count).__name__}")
        for _ in range(count):
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except StopException:
                break
            except SkipException:
                continue
            except ReturnException:
                raise
    def visit_When(self, node: When):
        value = self.visit(node.value)
        for match_val, body in node.cases:
            if self.visit(match_val) == value:
                for stmt in body:
                    self.visit(stmt)
                return
        if node.otherwise:
            for stmt in node.otherwise:
                self.visit(stmt)
    def visit_Execute(self, node: Execute):
        code = self.visit(node.code)
        if not isinstance(code, str):
            raise TypeError(f"execute requires a string, got {type(code).__name__}")
        from .lexer import Lexer
        from .parser import Parser
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        statements = parser.parse()
        result = None
        for stmt in statements:
            result = self.visit(stmt)
        return result
    def visit_ImportAs(self, node: ImportAs):
        if node.path in self.std_modules:
            self.current_env.set(node.alias, self.std_modules[node.path])
            return
        old_funcs_keys = set(self.functions.keys())
        module_env = Environment(parent=self.global_env)
        old_env = self.current_env
        self.current_env = module_env
        module_env = Environment(parent=self.global_env)
        old_env = self.current_env
        self.current_env = module_env
        if os.path.exists(node.path):
             target_path = node.path
        else:
             home = os.path.expanduser("~")
             global_path = os.path.join(home, ".shell_lite", "modules", node.path)
             if os.path.exists(global_path):
                 target_path = global_path
             else:
                  if not node.path.endswith('.shl'):
                       global_path_ext = global_path + ".shl"
                       if os.path.exists(global_path_ext):
                            target_path = global_path_ext
                       else:
                            self.current_env = old_env
                            raise FileNotFoundError(f"Could not find imported file: {node.path} (searched local and global modules)")
                  else:
                       self.current_env = old_env
                       raise FileNotFoundError(f"Could not find imported file: {node.path} (searched local and global modules)")
        if os.path.isdir(target_path):
             main_shl = os.path.join(target_path, "main.shl")
             pkg_shl = os.path.join(target_path, f"{os.path.basename(target_path)}.shl")
             if os.path.exists(main_shl):
                 target_path = main_shl
             elif os.path.exists(pkg_shl):
                 target_path = pkg_shl
             else:
                  self.current_env = old_env
                  raise FileNotFoundError(f"Package '{node.path}' is a folder but has no 'main.shl' or '{os.path.basename(target_path)}.shl'.")
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                code = f.read()
            from .lexer import Lexer
            from .parser import Parser
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            statements = parser.parse()
            for stmt in statements:
                self.visit(stmt)
            module_exports = {}
            module_exports.update(module_env.variables)
            current_funcs_keys = set(self.functions.keys())
            new_funcs = current_funcs_keys - old_funcs_keys
            for fname in new_funcs:
                func_node = self.functions[fname]
                module_exports[fname] = func_node
                del self.functions[fname]
            self.current_env = old_env
            self.current_env.set(node.alias, module_exports)
        except Exception as e:
            self.current_env = old_env
            raise RuntimeError(f"Failed to import '{node.path}': {e}")
    def visit_Forever(self, node: Forever):
        while True:
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except StopException:
                break
            except SkipException:
                continue
            except ReturnException:
                raise
    def visit_Exit(self, node: Exit):
        code = 0
        if node.code:
            code = self.visit(node.code)
            sys.exit(int(code))
        sys.exit(0)

    # -------------------------------------------------------------------------
    # Project Polaris: Phase 2 (The Canvas - Native UI)
    # -------------------------------------------------------------------------
    def visit_App(self, node: App):
        # We need a root for the app
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.title(node.title)
        root.geometry(f"{node.width}x{node.height}")
        
        # Store root for potential access, though mostly we use 'master' passed down
        # Ideally we pass 'parent' to visits, but we don't have that signature.
        # So we'll use a stack or a temporary context.
        self.ui_parent_stack = [root]
        
        # Define a helpful alert function available in UI context
        def ui_alert(msg):
            messagebox.showinfo("Message", str(msg))
        self.current_env.set("alert", ui_alert)

        try:
            for child in node.body:
                self.visit(child)
        finally:
            self.ui_parent_stack.pop()
            
        root.mainloop()

    def visit_Layout(self, node: Layout):
        parent = self.ui_parent_stack[-1]
        
        # Create a frame for the layout
        frame = tk.Frame(parent)
        
        # Pack options based on layout type of THIS container relative to parent??
        # Usually Layout implies how CHILDREN are arranged.
        # But here 'column' means "I am a column" -> children stacked vertically.
        # 'row' means "I am a row" -> children stacked horizontally.
        
        # In Tkinter, pack() defaults to vertical (column).
        # side=LEFT makes it horizontal (row).
        
        # We start by adding the frame to the parent.
        # If parent is a Column, we pack(side=TOP). If Row, pack(side=LEFT).
        # But simplified: Just use pack(fill=X) or something.
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.ui_parent_stack.append((frame, node.layout_type))
        try:
            for child in node.body:
                self.visit(child)
        finally:
            self.ui_parent_stack.pop()

    def visit_Widget(self, node: Widget):
        from tkinter import messagebox
        parent_ctx = self.ui_parent_stack[-1]
        if isinstance(parent_ctx, tuple):
            parent, layout_mode = parent_ctx
        else:
            parent = parent_ctx
            layout_mode = 'column' # Default to column
            
        widget = None
        if node.widget_type == 'button':
            # Handle event
            def on_click():
                if node.event_handler:
                    try:
                        for stmt in node.event_handler:
                            self.visit(stmt)
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
                        
            widget = tk.Button(parent, text=node.label, command=on_click)
            
        elif node.widget_type == 'input':
            lbl = tk.Label(parent, text=node.label)
            pack_opts = {'side': tk.TOP, 'anchor': 'w'} if layout_mode == 'column' else {'side': tk.LEFT}
            lbl.pack(**pack_opts)
            
            widget = tk.Entry(parent)
            
            # Store accessor in Env so we can read .value
            if node.var_name:
                # We can't store the widget directly because .value access visits PropertyAccess
                # which expects dict, list, or python object.
                # Tkinter Entry has get().
                # We wrap it or just rely on 'visit_PropertyAccess' (Phase 1)
                # By default Tkinter widgets store config. 
                # Let's verify if widget.value works natively? No.
                # So we wrap it.
                class InputWrapper:
                    def __init__(self, w): self.w = w
                    @property
                    def value(self): return self.w.get()
                    @property
                    def text(self): return self.w.get()
                
                self.current_env.set(node.var_name, InputWrapper(widget))

        elif node.widget_type == 'heading':
            widget = tk.Label(parent, text=node.label, font=("Helvetica", 16, "bold"))
            
        elif node.widget_type == 'text':
            widget = tk.Label(parent, text=node.label)
            
        if widget:
            # Layout the widget
            if layout_mode == 'column':
                widget.pack(side=tk.TOP, pady=5, fill=tk.X)
            else:
                widget.pack(side=tk.LEFT, padx=5)

    def visit_Make(self, node: Make):
        if node.class_name not in self.classes:
            raise NameError(f"Thing '{node.class_name}' not defined.")
        class_def = self.classes[node.class_name]
        props = self._get_class_properties(class_def)

        # Check args length
        required_count = 0
        for name, default_val in props:
            if default_val is None:
                required_count += 1

        if len(node.args) < required_count:
             raise TypeError(f"Thing '{node.class_name}' expects at least {required_count} values, got {len(node.args)}")
        
        instance = Instance(class_def)
        
        for i, (prop_name, default_val) in enumerate(props):
            val = None
            if i < len(node.args):
                val = self.visit(node.args[i])
            elif default_val is not None:
                val = self.visit(default_val)
            else:
                raise TypeError(f"Missing argument for property '{prop_name}' in '{node.class_name}'")
            
            instance.data[prop_name] = val
            
        return instance
    def visit_Convert(self, node: Convert):
        val = self.visit(node.expression)
        if node.target_format.lower() == 'json':
             if isinstance(val, str):
                 try:
                     return json.loads(val)
                 except: 
                     return json.dumps(val) 
             else:
                 if isinstance(val, Instance):
                     return json.dumps(val.data)
                 return json.dumps(val) 
        raise ValueError(f"Unknown conversion format: {node.target_format}")
    def visit_ProgressLoop(self, node: ProgressLoop):
        loop = node.loop_node
        if isinstance(loop, Repeat):
             count = self.visit(loop.count)
             if not isinstance(count, int): count = 0
             print(f"Progress: [                    ] 0%", end='\r')
             for i in range(count):
                 percent = int((i / count) * 100)
                 bar = '=' * int(percent / 5)
                 print(f"Progress: [{bar:<20}] {percent}%", end='\r')
                 try:
                     for stmt in loop.body:
                         self.visit(stmt)
                 except: pass 
             print(f"Progress: [{'='*20}] 100%           ")
        elif isinstance(loop, For):
             count = self.visit(loop.count)
             for i in range(count):
                 percent = int((i / count) * 100)
                 bar = '=' * int(percent / 5)
                 print(f"Progress: [{bar:<20}] {percent}%", end='\r')
                 try:
                    for stmt in loop.body:
                        self.visit(stmt)
                 except: pass
             print(f"Progress: [{'='*20}] 100%           ")
        elif isinstance(loop, ForIn):
            iterable = self.visit(loop.iterable)
            total = len(iterable) if hasattr(iterable, '__len__') else 0
            i = 0
            for item in iterable:
                if total > 0:
                    percent = int((i / total) * 100)
                    bar = '=' * int(percent / 5)
                    print(f"Progress: [{bar:<20}] {percent}%", end='\r')
                self.current_env.set(loop.var_name, item)
                try:
                    for stmt in loop.body:
                        self.visit(stmt)
                except: pass
                i += 1
            if total > 0:
                print(f"Progress: [{'='*20}] 100%           ")
    def visit_DatabaseOp(self, node: DatabaseOp):
        if node.op == 'open':
            path = self.visit(node.args[0])
            self.db_conn = sqlite3.connect(path, check_same_thread=False)
            return self.db_conn
        elif node.op == 'close':
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
        elif node.op == 'exec':
            if not self.db_conn:
                raise RuntimeError("Database not open. Use 'db open \"path\"' first.")
            sql = self.visit(node.args[0])
            params = [self.visit(arg) for arg in node.args[1:]]
            cursor = self.db_conn.cursor()
            cursor.execute(sql, params)
            self.db_conn.commit()
            return cursor.lastrowid
        elif node.op == 'query':
            if not self.db_conn:
                raise RuntimeError("Database not open. Use 'db open \"path\"' first.")
            sql = self.visit(node.args[0])
            params = [self.visit(arg) for arg in node.args[1:]]
            cursor = self.db_conn.cursor()
            cursor.execute(sql, params)
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
    def visit_ServeStatic(self, node: ServeStatic):
        folder = str(self.visit(node.folder))
        url_prefix = str(self.visit(node.url))
        if not url_prefix.startswith('/'): url_prefix = '/' + url_prefix
        if not os.path.isdir(folder):
            print(f"Warning: Static folder '{folder}' does not exist.")
        self.static_routes[url_prefix] = folder
        print(f"Serving static files from '{folder}' at '{url_prefix}'")
    def visit_Every(self, node: Every):
        interval = self.visit(node.interval)
        if node.unit == 'minutes': interval *= 60
        try:
            while True:
                for stmt in node.body: self.visit(stmt)
                time.sleep(interval)
        except KeyboardInterrupt: pass
    def visit_After(self, node: After):
        delay = self.visit(node.delay)
        if node.unit == 'minutes': delay *= 60
        time.sleep(delay)
        for stmt in node.body: self.visit(stmt)
    def visit_OnRequest(self, node: OnRequest):
        path_str = self.visit(node.path)
        if path_str == '__middleware__':
            self.middleware_routes.append(node.body)
            return
        regex_pattern = "^" + path_str + "$"
        if ':' in path_str:
            regex_pattern = "^" + re.sub(r':(\w+)', r'(?P<\1>[^/]+)', path_str) + "$"
        compiled = re.compile(regex_pattern)
        self.http_routes.append((path_str, compiled, node.body))
    def visit_Listen(self, node: Listen):
        port_val = self.visit(node.port)
        interpreter_ref = self
        class ShellLiteHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass 
            def do_GET(self): 
                self.handle_req()
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                content_type = self.headers.get('Content-Type', '')
                post_data = self.rfile.read(content_length).decode('utf-8')
                params = {}
                json_data = None
                if 'application/json' in content_type:
                    try:
                        json_data = json.loads(post_data)
                    except:
                        pass
                else:
                    if post_data:
                        parsed = urllib.parse.parse_qs(post_data)
                        params = {k: v[0] for k, v in parsed.items()}
                self.handle_req(params, json_data)
            def do_HEAD(self):
                self.handle_req()
            def handle_req(self, post_params=None, json_data=None):
                try:
                    if post_params is None: post_params = {}
                    path = self.path
                    if '?' in path: path = path.split('?')[0]
                    req_obj = {
                        "method": self.command, 
                        "path": path,
                        "params": post_params,
                        "form": post_params, 
                        "json": json_data
                    }
                    interpreter_ref.global_env.set("request", req_obj)
                    interpreter_ref.global_env.set("REQUEST_METHOD", self.command) 
                    for prefix, folder in interpreter_ref.static_routes.items():
                        if path.startswith(prefix):
                            clean_path = path[len(prefix):]
                            if clean_path.startswith('/'): clean_path = clean_path[1:]
                            if clean_path == '': clean_path = 'index.html'
                            file_path = os.path.join(folder, clean_path)
                            if os.path.exists(file_path) and os.path.isfile(file_path):
                                 self.send_response(200)
                                 ct = 'application/octet-stream'
                                 if file_path.endswith('.css'): ct = 'text/css'
                                 elif file_path.endswith('.html'): ct = 'text/html'
                                 elif file_path.endswith('.js'): ct = 'application/javascript'
                                 self.send_header('Content-Type', ct)
                                 self.end_headers()
                                 if self.command != 'HEAD':
                                     with open(file_path, 'rb') as f: self.wfile.write(f.read())
                                 return
                    matched_body = None
                    path_params = {}
                    for pattern, regex, body in interpreter_ref.http_routes:
                        match = regex.match(path)
                        if match:
                            matched_body = body
                            path_params = match.groupdict()
                            break
                    if matched_body:
                        for mw in interpreter_ref.middleware_routes:
                             for stmt in mw: interpreter_ref.visit(stmt)
                        for k, v in path_params.items():
                            interpreter_ref.global_env.set(k, v)
                        for k, v in post_params.items():
                            interpreter_ref.global_env.set(k, v)
                        interpreter_ref.web.stack = []
                        response_body = ""
                        result = None
                        try:
                            for stmt in matched_body:
                                result = interpreter_ref.visit(stmt)
                        except ReturnException as re:
                            result = re.value
                        if interpreter_ref.web.stack:
                             pass
                        if isinstance(result, Tag): response_body = str(result)
                        elif result: response_body = str(result)
                        else: response_body = "OK"
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()
                        if self.command != 'HEAD':
                            self.wfile.write(response_body.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                        if self.command != 'HEAD':
                            self.wfile.write(b'Not Found')
                except Exception as e:
                    print(f"DEBUG: Server Exception: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        self.send_response(500)
                        self.end_headers()
                        if self.command != 'HEAD':
                            self.wfile.write(str(e).encode())
                    except: pass
        server = HTTPServer(('0.0.0.0', port_val), ShellLiteHandler)
        print(f"\n  ShellLite Server v0.03.4 is running!")
        print(f"  \u001b[1;36m➜\u001b[0m  Local:   \u001b[1;4;36mhttp://localhost:{port_val}/\u001b[0m\n")
        try: server.serve_forever()
        except KeyboardInterrupt: 
            print("\n  Server stopped.")
            pass
    def visit_DatabaseOp(self, node: DatabaseOp):
        if node.op == 'open':
            path = self.visit(node.args[0])
            self.db_conn = sqlite3.connect(path)
            self.db_conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
            return True
        elif node.op == 'close':
            if self.db_conn: self.db_conn.close(); self.db_conn = None
            return True
        elif node.op == 'exec':
            if not self.db_conn: raise RuntimeError("Database not open")
            sql = self.visit(node.args[0])
            params = []
            if len(node.args) > 1:
                val = self.visit(node.args[1])
                params = val if isinstance(val, list) else [val]
            c = self.db_conn.cursor(); c.execute(sql, params); self.db_conn.commit()
            return c.lastrowid
        elif node.op == 'query':
            if not self.db_conn: raise RuntimeError("Database not open")
            sql = self.visit(node.args[0])
            params = []
            if len(node.args) > 1:
                val = self.visit(node.args[1])
                params = val if isinstance(val, list) else [val]
            c = self.db_conn.cursor(); c.execute(sql, params)
            return c.fetchall()
    def visit_Download(self, node: Download):
        url = self.visit(node.url)
        filename = url.split('/')[-1] or "downloaded_file"
        print(f"Downloading {filename}...")
        try:
             with urllib.request.urlopen(url) as response:
                 with open(filename, 'wb') as f:
                     shutil.copyfileobj(response, f)
             print(f"Download complete: {filename}")
        except urllib.error.URLError as e:
             print(f"Error: Could not connect to {url}. Reason: {e}")
        except PermissionError:
             print(f"Error: Permission denied writing to {filename}.")
        except Exception as e:
             print(f"Error: Download failed: {e}")
    def visit_ArchiveOp(self, node: ArchiveOp):
        source = str(self.visit(node.source))
        target = str(self.visit(node.target))
        try:
            if node.op == 'compress':
                 print(f"Compressing '{source}' to '{target}'...")
                 if os.path.isfile(source):
                     with zipfile.ZipFile(target, 'w') as zipf:
                         zipf.write(source, arcname=os.path.basename(source))
                 elif os.path.isdir(source):
                     shutil.make_archive(target.replace('.zip',''), 'zip', source)
                 else:
                     print(f"Error: Source '{source}' does not exist.")
                     return
                 print("Compression complete.")
            else: 
                 print(f"Extracting '{source}' to '{target}'...")
                 if not os.path.exists(source):
                      print(f"Error: Archive '{source}' does not exist.")
                      return
                 with zipfile.ZipFile(source, 'r') as zipf:
                     zipf.extractall(target)
                 print("Extraction complete.")
        except zipfile.BadZipFile:
             print(f"Error: '{source}' is not a valid zip file.")
        except Exception as e:
             print(f"Error: Archive operation failed: {e}")
    def visit_CsvOp(self, node: CsvOp):
        path = self.visit(node.path)
        if node.op == 'load':
            with open(path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                return [row for row in reader]
        else: 
            data = self.visit(node.data)
            if not isinstance(data, list):
                 data = [data] 
            if not data: return 
            rows = []
            for item in data:
                 if isinstance(item, Instance):
                     rows.append(item.data)
                 elif isinstance(item, dict):
                     rows.append(item)
                 elif isinstance(item, dict):
                     rows.append(item)
                 else:
                     print("Error: Only lists of objects/dictionaries can be saved to CSV.")
                     return
            if rows:
                try:
                    keys = rows[0].keys()
                    with open(path, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(rows)
                    print(f"Saved {len(rows)} rows to '{path}'.")
                except Exception as e:
                    print(f"Error saving CSV: {e}")
    def visit_ClipboardOp(self, node: ClipboardOp):
        if 'pyperclip' not in sys.modules:
             raise RuntimeError("Install 'pyperclip' for clipboard support.")
        if node.op == 'copy':
             content = str(self.visit(node.content))
             pyperclip.copy(content)
        else:
             return pyperclip.paste()
    def visit_AutomationOp(self, node: AutomationOp):
        args = [self.visit(a) for a in node.args]
        if node.action == 'press':
             if 'keyboard' not in sys.modules: raise RuntimeError("Install 'keyboard'")
             keyboard.press_and_release(args[0])
        elif node.action == 'type':
             if 'keyboard' not in sys.modules: raise RuntimeError("Install 'keyboard'")
             keyboard.write(str(args[0]))
        elif node.action == 'click':
             if 'mouse' not in sys.modules: raise RuntimeError("Install 'mouse'")
             mouse.move(args[0], args[1], absolute=True, duration=0.2)
             mouse.click('left')
        elif node.action == 'notify':
             if 'plyer' not in sys.modules: raise RuntimeError("Install 'plyer'")
             notification.notify(title=str(args[0]), message=str(args[1]))
    def visit_DateOp(self, node: DateOp):
        if node.expr == 'today':
            return datetime.now().strftime("%Y-%m-%d")
        today = datetime.now()
        s = node.expr.lower().strip()
        if s == 'tomorrow':
            d = today + timedelta(days=1)
            return d.strftime("%Y-%m-%d")
        elif s == 'yesterday':
            d = today - timedelta(days=1)
            return d.strftime("%Y-%m-%d")
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if s.startswith('next '):
            day_str = s.replace('next ', '').strip()
            if day_str in days:
                 target_idx = days.index(day_str)
                 current_idx = today.weekday()
                 days_ahead = target_idx - current_idx
                 if days_ahead <= 0: days_ahead += 7
                 d = today + timedelta(days=days_ahead)
                 return d.strftime("%Y-%m-%d")
        return s 
    def visit_FileWrite(self, node: FileWrite):
        path = str(self.visit(node.path))
        content = str(self.visit(node.content))
        try:
            with open(path, node.mode, encoding='utf-8') as f:
                f.write(content)
            print(f"{'Appended to' if node.mode == 'a' else 'Written to'} file '{path}'")
        except Exception as e:
            raise RuntimeError(f"File operation failed: {e}")
    def visit_FileRead(self, node: FileRead):
        path = str(self.visit(node.path))
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
             raise FileNotFoundError(f"File '{path}' not found.")
             raise RuntimeError(f"Read failed: {e}")
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.interpreter <file.shl>")
        sys.exit(1)
    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        for stmt in ast:
            interpreter.visit(stmt)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
