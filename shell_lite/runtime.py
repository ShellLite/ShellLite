from typing import Any, Dict, List, Optional
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
import re
from datetime import datetime
import threading
import concurrent.futures
import tkinter as tk
from tkinter import messagebox, simpledialog
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
class Instance:
    def __init__(self, class_def: Any):
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
    def __init__(self, interpreter=None):
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
def slang_run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command Error: {result.stderr}")
        return result.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {e}")
def slang_read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read file '{path}': {e}")
def slang_write(path, content):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(content))
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to write file '{path}': {e}")
def slang_json_parse(json_str):
    try:
        return json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"Invalid JSON: {e}")
def slang_json_stringify(obj):
    try:
        if isinstance(obj, Instance):
            return json.dumps(obj.data)
        return json.dumps(obj)
    except Exception as e:
        raise RuntimeError(f"JSON stringify failed: {e}")
def slang_http_get(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"HTTP GET failed for '{url}': {e}")
def slang_http_post(url, data_dict):
    try:
        if isinstance(data_dict, Instance):
            data_dict = data_dict.data
        data = json.dumps(data_dict).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
             return response.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"HTTP POST failed for '{url}': {e}")
def slang_download(url):
    filename = url.split('/')[-1] or "downloaded_file"
    try:
        with urllib.request.urlopen(url) as response:
            with open(filename, 'wb') as f:
                shutil.copyfileobj(response, f)
        return filename
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}")
def slang_archive(op, source, target):
    try:
        if op == 'compress':
            if os.path.isfile(source):
                with zipfile.ZipFile(target, 'w') as zipf:
                    zipf.write(source, arcname=os.path.basename(source))
            elif os.path.isdir(source):
                shutil.make_archive(target.replace('.zip',''), 'zip', source)
        else:
            with zipfile.ZipFile(source, 'r') as zipf:
                zipf.extractall(target)
    except Exception as e:
        raise RuntimeError(f"Archive operation failed: {e}")
def slang_csv_load(path):
    import csv
    with open(path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]
def slang_csv_save(data, path):
    import csv
    if not isinstance(data, list): data = [data]
    if not data: return
    rows = []
    for item in data:
        if isinstance(item, Instance): rows.append(item.data)
        elif isinstance(item, dict): rows.append(item)
    if rows:
        keys = rows[0].keys()
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
def slang_clipboard_copy(text):
    try:
        import pyperclip
        pyperclip.copy(str(text))
    except ImportError:
        pass
def slang_clipboard_paste():
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        return ""
def slang_press(key):
    try:
        import keyboard
        keyboard.press_and_release(key)
    except ImportError: pass
def slang_type(text):
    try:
        import keyboard
        keyboard.write(str(text))
    except ImportError: pass
def slang_click(x, y):
    try:
        import mouse
        mouse.move(x, y, absolute=True, duration=0.2)
        mouse.click('left')
    except ImportError: pass
def slang_notify(title, msg):
    try:
        from plyer import notification
        notification.notify(title=str(title), message=str(msg))
    except ImportError: pass
def slang_date_parse(expr):
    from datetime import datetime, timedelta
    today = datetime.now()
    if expr == 'today': return today.strftime("%Y-%m-%d")
    s = expr.lower().strip()
    if s == 'tomorrow': return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if s == 'yesterday': return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if s.startswith('next '):
        day_str = s.replace('next ', '').strip()
        if day_str in days:
            target_idx = days.index(day_str); current_idx = today.weekday()
            days_ahead = target_idx - current_idx
            if days_ahead <= 0: days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return s
def slang_file_write(path, content, mode):
    with open(path, mode, encoding='utf-8') as f:
        f.write(str(content))
def slang_file_read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
import sqlite3
_slang_db_conn = None
def slang_db_open(path):
    global _slang_db_conn
    _slang_db_conn = sqlite3.connect(path, check_same_thread=False)
    _slang_db_conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
    return True
def slang_db_close():
    global _slang_db_conn
    if _slang_db_conn: _slang_db_conn.close(); _slang_db_conn = None
def slang_db_exec(sql, params=None):
    if not _slang_db_conn: raise RuntimeError("DB not open")
    if params is None: params = []
    c = _slang_db_conn.cursor(); c.execute(sql, params); _slang_db_conn.commit()
    return c.lastrowid
def slang_db_query(sql, params=None):
    if not _slang_db_conn: raise RuntimeError("DB not open")
    if params is None: params = []
    c = _slang_db_conn.cursor(); c.execute(sql, params)
    return c.fetchall()
def slang_json_stringify(val):
    if isinstance(val, (Instance, dict)): 
        d = val.data if isinstance(val, Instance) else val
        return json.dumps(d)
    if isinstance(val, list):
         return json.dumps([v.data if isinstance(v, Instance) else v for v in val])
    return json.dumps(val)
def slang_color_print(val, color=None, style=None):
    colors = {'red': '91', 'green': '92', 'yellow': '93', 'blue': '94', 'magenta': '95', 'cyan': '96'}
    parts = []
    if style == 'bold': parts.append('1')
    if color and color.lower() in colors: parts.append(colors[color.lower()])
    if parts:
        print(f"\033[{';'.join(parts)}m{val}\033[0m")
    else:
        print(val)
def slang_alert(msg):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showinfo("Alert", str(msg))
    root.destroy()
def slang_prompt(prompt):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    val = simpledialog.askstring("Input", str(prompt))
    root.destroy()
    return val if val is not None else ""
def slang_confirm(prompt):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    val = messagebox.askyesno("Confirm", str(prompt))
    root.destroy()
    return val
def get_std_modules():
    return {
        'math': {
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'sqrt': math.sqrt, 'floor': math.floor, 'ceil': math.ceil,
            'abs': abs, 'pow': pow, 'log': math.log, 'log10': math.log10,
            'exp': math.exp, 'random': random.random, 'randint': random.randint,
            'pi': math.pi, 'e': math.e,
        },
        'time': {
            'time': time.time, 'sleep': time.sleep,
            'date': lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'year': lambda: datetime.now().year,
            'month': lambda: datetime.now().month,
            'day': lambda: datetime.now().day,
            'hour': lambda: datetime.now().hour,
            'minute': lambda: datetime.now().minute,
            'second': lambda: datetime.now().second,
        },
        'http': {
            'get': slang_http_get,
            'post': slang_http_post
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
            'join': os.path.join, 'basename': os.path.basename,
            'dirname': os.path.dirname, 'exists': os.path.exists,
            'isfile': os.path.isfile, 'isdir': os.path.isdir,
            'abspath': os.path.abspath, 'split': os.path.split,
            'ext': lambda p: os.path.splitext(p)[1],
            'getcwd': os.getcwd,
        },
        're': {
            'match': lambda p, s: bool(re.match(p, s)),
            'search': lambda p, s: re.search(p, s).group() if re.search(p, s) else None,
            'replace': lambda p, r, s: re.sub(p, r, s),
            'findall': lambda p, s: re.findall(p, s),
            'split': lambda p, s: re.split(p, s),
        },
    }
def slang_map(lst, func):
    if callable(func):
        return [func(x) for x in lst]
    raise TypeError("map requires a callable")
def slang_filter(lst, func):
    if callable(func):
        return [x for x in lst if func(x)]
    raise TypeError("filter requires a callable")
def slang_reduce(lst, func, initial=None):
    if callable(func):
        if initial is not None:
            return functools.reduce(func, lst, initial)
        return functools.reduce(func, lst)
    raise TypeError("reduce requires a callable")
def slang_push(lst, item):
    lst.append(item)
    return None
def get_builtins():
    return {
        'str': str, 'int': int, 'float': float, 'bool': bool,
        'list': list, 'len': len,
        'range': lambda *args: list(range(*args)),
        'typeof': lambda x: type(x).__name__,
        'run': slang_run,
        'read': slang_read,
        'write': slang_write,
        'json_parse': slang_json_parse,
        'json_stringify': slang_json_stringify,
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
        'push': slang_push,
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
        'map': slang_map,
        'filter': slang_filter,
        'reduce': slang_reduce,
        'exists': os.path.exists,
        'delete': os.remove,
        'copy': shutil.copy,
        'rename': os.rename,
        'mkdir': lambda p: os.makedirs(p, exist_ok=True),
        'listdir': os.listdir,
        'http_get': slang_http_get,
        'http_post': slang_http_post,
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
        'alert': slang_alert,
        'prompt': slang_prompt,
        'confirm': slang_confirm,
        'Set': set,
        'show': print,
        'say': print,
    }
