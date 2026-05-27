import builtins
import concurrent.futures
import csv
import ctypes
import json as py_json
import mimetypes
import os
import queue
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

from shell_lite.runtime_policy import (
    get_policy,
    require_automation,
    require_clipboard,
    require_db,
    require_exec,
    require_fs_read,
    require_fs_write,
    require_net,
    require_py_import,
    require_web,
)

__executor = concurrent.futures.ThreadPoolExecutor(max_workers=32)
__locks: Dict[str, threading.Lock] = {}
__locks_guard = threading.Lock()
_original_import = builtins.__import__


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    require_py_import(name)
    return _original_import(name, globals, locals, fromlist, level)


def enable_import_guard():
    if get_policy().safe_mode:
        builtins.__import__ = _guarded_import


def disable_import_guard():
    builtins.__import__ = _original_import


def get_lock(name: str):
    if name not in __locks:
        with __locks_guard:
            if name not in __locks:
                __locks[name] = threading.Lock()
    return __locks[name]


def mixed_concat(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return str(a) + str(b)
    return a + b


def json_parse(s):
    return py_json.loads(s)


def json_stringify(obj, indent=2):
    return py_json.dumps(obj, indent=indent)


def pop(target, index=-1):
    return target.pop(index)


def clear_dict(d):
    d.clear()


def add(target, item):
    if isinstance(target, set):
        target.add(item)
    else:
        target.append(item)


def remove(target, item):
    target.remove(item)


def spawn_task(func, *args, **kwargs):
    return __executor.submit(func, *args, **kwargs)


def await_task(task):
    return task.result() if hasattr(task, "result") else task


def gather_tasks(tasks):
    return [await_task(t) for t in tasks]


def shl_parallel(funcs):
    futures = [__executor.submit(f) for f in funcs]
    for future in concurrent.futures.as_completed(futures):
        future.result()


def create_channel():
    return queue.Queue()


def channel_send(q, value):
    q.put(value)


def channel_receive(q):
    return q.get()


def shl_execute(cmd_str):
    require_exec(str(cmd_str))
    args = shlex.split(str(cmd_str))
    timeout_raw = os.environ.get("SHL_EXEC_TIMEOUT")
    timeout = float(timeout_raw) if timeout_raw else None
    res = subprocess.run(args, capture_output=True, text=True, shell=False, timeout=timeout)
    if res.returncode != 0:
        msg = res.stderr.strip() or res.stdout.strip() or "Command failed"
        raise RuntimeError(f"Command failed ({res.returncode}): {msg}")
    return res.stdout


class ShellLiteObject:
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


__html_buffer: list[str] = []


def __emit_html(s):
    __html_buffer.append(s)


def render(obj):
    if callable(obj):
        global __html_buffer
        old = __html_buffer
        __html_buffer = []
        obj()
        res = "".join(__html_buffer)
        __html_buffer = old
        return res
    return str(obj)


def __make_tag(tag_name):
    def tag_handler(*args, body=None, **kwargs):
        attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kwargs.items())
        __emit_html(f"<{tag_name}{attrs}>")
        for a in args:
            __emit_html(str(a))
        if body:
            body()
        if tag_name not in ("meta", "link", "br", "hr", "img", "input"):
            __emit_html(f"</{tag_name}>")

    return tag_handler


html = __make_tag("html")
head = __make_tag("head")
body = __make_tag("body")
div = __make_tag("div")
span = __make_tag("span")
a = __make_tag("a")
img = __make_tag("img")
ul = __make_tag("ul")
ol = __make_tag("ol")
li = __make_tag("li")
button = __make_tag("button")
input = __make_tag("input")
form = __make_tag("form")
table = __make_tag("table")
tr = __make_tag("tr")
td = __make_tag("td")
h1 = __make_tag("h1")
h2 = __make_tag("h2")
h3 = __make_tag("h3")
h4 = __make_tag("h4")
h5 = __make_tag("h5")
h6 = __make_tag("h6")
link = __make_tag("link")
meta = __make_tag("meta")
script = __make_tag("script")
footer = __make_tag("footer")
header = __make_tag("header")
nav = __make_tag("nav")
textarea = __make_tag("textarea")
label = __make_tag("label")
section = __make_tag("section")
article = __make_tag("article")
main = __make_tag("main")
aside = __make_tag("aside")
p = __make_tag("p")
strong = __make_tag("strong")
br = __make_tag("br")
hr = __make_tag("hr")
title = __make_tag("title")
style = __make_tag("style")
blockquote = __make_tag("blockquote")
pre = __make_tag("pre")
code = __make_tag("code")


def std_web_on_request(path, handler, body=None):
    require_web()

    def wrapper():
        if body:
            return render(body)
        return render(handler)

    _web_handlers[path] = wrapper


_db_conn = None
_db_models: Dict[str, list[tuple[str, str]]] = {}
_db_path = "shell_lite.db"
_identifier_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str):
    if not _identifier_re.match(name):
        raise ValueError(f"Invalid identifier: {name}")


def _get_db():
    global _db_conn
    if _db_conn is None:
        if _db_path != ":memory:":
            require_fs_write(_db_path)
        _db_conn = sqlite3.connect(_db_path, check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def std_db_query(query: str, *args):
    require_db()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    if query.strip().upper().startswith("SELECT"):
        return [dict(row) for row in cur.fetchall()]
    conn.commit()
    return []


def std_db_open(path: str):
    require_db()
    global _db_conn, _db_path
    _db_path = path
    if _db_path != ":memory:":
        require_fs_write(_db_path)
    _db_conn = sqlite3.connect(_db_path, check_same_thread=False)
    _db_conn.row_factory = sqlite3.Row
    return _db_conn


def std_db_close():
    require_db()
    global _db_conn
    if _db_conn:
        _db_conn.close()
        _db_conn = None


def std_db_exec(query: str, params: Optional[list[Any]] = None):
    require_db()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute(query, params or [])
    conn.commit()
    return cur.rowcount


def std_db_query_rows(query: str, params: Optional[list[Any]] = None):
    require_db()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute(query, params or [])
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def std_db_model(name: str, fields: list):
    require_db()
    _validate_identifier(name)
    for k, _ in fields:
        _validate_identifier(k)
    _db_models[name] = fields


def std_db_create_table(model_name: str):
    require_db()
    _validate_identifier(model_name)
    fields = _db_models.get(model_name)
    if not fields:
        raise Exception(f"Model '{model_name}' is not defined.")
    cols = []
    for k, v in fields:
        _validate_identifier(k)
        t = "TEXT"
        if v.lower() in ("int", "integer", "bool"):
            t = "INTEGER"
        elif v.lower() in ("float", "real"):
            t = "REAL"
        cols.append(f"{k} {t}")
    std_db_query(f"CREATE TABLE IF NOT EXISTS {model_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {', '.join(cols)})")


def std_db_insert(model_name: str, record: dict):
    require_db()
    _validate_identifier(model_name)
    ks = list(record.keys())
    vs = list(record.values())
    for k in ks:
        _validate_identifier(k)
    std_db_query(f"INSERT INTO {model_name} ({', '.join(ks)}) VALUES ({', '.join(['?'] * len(ks))})", *vs)


def _build_where(conds: list):
    if not conds:
        return "", []
    for k, _, _ in conds:
        _validate_identifier(k)
    return " WHERE " + " AND ".join([f"{k} {op} ?" for k, op, v in conds]), [v for k, op, v in conds]


def std_db_find(model_name: str, conds: list, all: bool = True):
    require_db()
    _validate_identifier(model_name)
    w, v = _build_where(conds)
    res = std_db_query(f"SELECT * FROM {model_name}{w}", *v)
    return res if all else (res[0] if res else None)


def std_db_update(model_name: str, conds: list, updates: dict):
    require_db()
    _validate_identifier(model_name)
    w, v1 = _build_where(conds)
    ks = list(updates.keys())
    vs = list(updates.values())
    for k in ks:
        _validate_identifier(k)
    std_db_query(f"UPDATE {model_name} SET {', '.join([f'{k} = ?' for k in ks])}{w}", *(vs + v1))


def std_db_delete(model_name: str, conds: list):
    require_db()
    _validate_identifier(model_name)
    w, v = _build_where(conds)
    std_db_query(f"DELETE FROM {model_name}{w}", *v)


_web_handlers: Dict[str, Callable[[], Any]] = {}
_static_routes: Dict[str, str] = {}


class ShellLiteHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        for pfx, fld in _static_routes.items():
            if self.path.startswith(pfx):
                rel_path = self.path[len(pfx) :].lstrip("/")
                full_path = os.path.abspath(os.path.join(fld, rel_path))
                if not full_path.startswith(os.path.abspath(fld)):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden")
                    return

                if os.path.exists(full_path) and os.path.isfile(full_path):
                    self.send_response(200)
                    ctype, _ = mimetypes.guess_type(full_path)
                    self.send_header("Content-type", ctype or "application/octet-stream")
                    self.end_headers()
                    with open(full_path, "rb") as f:
                        self.wfile.write(f.read())
                    return

        if self.path in _web_handlers:
            try:
                res = _web_handlers[self.path]()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(str(res).encode("utf-8") if res else b"OK")
            except Exception:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, *args):
        pass


def std_web_listen(port: int):
    require_web()
    h = HTTPServer(("", int(port)), ShellLiteHTTPHandler)
    try:
        h.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        h.server_close()


def std_web_serve_static(url: str, folder: str):
    require_web()
    require_fs_read(folder)
    _static_routes[url] = os.path.abspath(folder)


def csv_load(p: str):
    require_fs_read(p)
    with open(p, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_save(p: str, d: list):
    require_fs_write(p)
    if not d:
        raise ValueError("csv_save requires a non-empty list")
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=d[0].keys())
        w.writeheader()
        w.writerows(d)


def compress(s: str, t: str):
    require_fs_read(s)
    require_fs_write(t)
    with zipfile.ZipFile(t, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.isfile(s):
            z.write(s, os.path.basename(s))
        else:
            for r, ds, fs in os.walk(s):
                for f in fs:
                    z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), os.path.join(s, "..")))


def extract(s: str, t: str):
    require_fs_read(s)
    require_fs_write(t)
    with zipfile.ZipFile(s, "r") as z:
        z.extractall(t)


def download(u: str, p: Optional[str] = None):
    require_net(u)
    if p is None:
        p = os.path.basename(u)
    require_fs_write(p)
    timeout_raw = os.environ.get("SHL_NET_TIMEOUT")
    timeout = float(timeout_raw) if timeout_raw else None
    with urllib.request.urlopen(u, timeout=timeout) as resp:
        data = resp.read()
    with open(p, "wb") as f:
        f.write(data)


def convert(d: Any, f: str):
    if f.lower() == "json":
        return py_json.dumps(d)
    return str(d) if f.lower() == "str" else d


def std_net_get(url: str):
    require_net(url)
    timeout_raw = os.environ.get("SHL_NET_TIMEOUT")
    timeout = float(timeout_raw) if timeout_raw else None
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def std_net_post(url: str, data):
    require_net(url)
    timeout_raw = os.environ.get("SHL_NET_TIMEOUT")
    timeout = float(timeout_raw) if timeout_raw else None
    payload = data
    if isinstance(data, dict):
        payload = py_json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


if sys.platform == "win32":

    def _setup_dpi_awareness():
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
        except Exception:
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    def _dpi_scale() -> float:
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            dpi = 96
        return max(1.0, float(dpi) / 96.0)

    def _scale_point(x, y):
        scale = _dpi_scale()
        return int(round(float(x) * scale)), int(round(float(y) * scale))

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("u", INPUT_UNION)]

    def _send_input(inputs):
        n = len(inputs)
        lp_inputs = (INPUT * n)(*inputs)
        sent = ctypes.windll.user32.SendInput(n, ctypes.pointer(lp_inputs), ctypes.sizeof(INPUT))
        if sent != n:
            raise RuntimeError("SendInput failed")

    def automation_click(x, y):
        require_automation()
        _setup_dpi_awareness()
        sx, sy = _scale_point(x, y)
        if not ctypes.windll.user32.SetCursorPos(sx, sy):
            raise RuntimeError("SetCursorPos failed")
        _send_input(
            [
                INPUT(type=0, u=INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=0x0002, time=0, dwExtraInfo=None))),
                INPUT(type=0, u=INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=0x0004, time=0, dwExtraInfo=None))),
            ]
        )

    def automation_press(key):
        require_automation()
        vk_map = {
            "enter": 0x0D,
            "tab": 0x09,
            "space": 0x20,
            "backspace": 0x08,
            "shift": 0x10,
            "ctrl": 0x11,
            "alt": 0x12,
            "esc": 0x1B,
            "up": 0x26,
            "down": 0x28,
            "left": 0x25,
            "right": 0x27,
            "delete": 0x2E,
            "home": 0x24,
            "end": 0x23,
            "pageup": 0x21,
            "pagedown": 0x22,
            "capslock": 0x14,
            "f1": 0x70,
            "f2": 0x71,
            "f3": 0x72,
            "f4": 0x73,
            "f5": 0x74,
            "f6": 0x75,
            "f7": 0x76,
            "f8": 0x77,
            "f9": 0x78,
            "f10": 0x79,
            "f11": 0x7A,
            "f12": 0x7B,
        }
        vk = vk_map.get(key.lower())
        if vk:
            _send_input(
                [
                    INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None))),
                    INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=2, time=0, dwExtraInfo=None))),
                ]
            )

    def automation_type(text):
        require_automation()
        for c in text:
            vk = ctypes.windll.user32.VkKeyScanW(ord(c)) & 0xFF
            _send_input(
                [
                    INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None))),
                    INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=2, time=0, dwExtraInfo=None))),
                ]
            )
else:

    def automation_click(x, y):
        pass

    def automation_press(key):
        pass

    def automation_type(text):
        pass


def automation_notify(t, m):
    if sys.platform == "win32":
        require_automation()
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "New-BurntToastNotification -Text $args[0], $args[1]", str(t), str(m)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            msg = res.stderr.strip() or res.stdout.strip() or "Notification failed"
            raise RuntimeError(msg)


def alert(msg):
    print(f"[ALERT] {msg}")


def prompt(msg):
    return input(f"[PROMPT] {msg}")


def confirm(msg):
    return input(f"[CONFIRM] {msg} (y/n): ").lower().startswith("y")


def ui_button(l):
    print(f"[UI] Button: {l}")


def heading(l):
    print(f"[UI] Heading: {l}")


def paragraph(l):
    print(f"[UI] Paragraph: {l}")


def open(path, mode="r", encoding="utf-8", **kwargs):
    if "r" in mode and "+" in mode:
        require_fs_read(path)
        require_fs_write(path)
    elif "r" in mode and "+" not in mode and "w" not in mode and "a" not in mode:
        require_fs_read(path)
    else:
        require_fs_write(path)
    if "b" in mode:
        return builtins.open(path, mode, **kwargs)
    return builtins.open(path, mode, encoding=encoding, **kwargs)


def std_io_read(path):
    return open(path, "r", encoding="utf-8").read()


def std_io_write(path, content):
    return open(path, "w", encoding="utf-8").write(content)


def std_io_append(path, content):
    return open(path, "a", encoding="utf-8").write(content)


def std_io_exists(path):
    require_fs_read(path)
    return os.path.exists(path)


def std_io_delete(path):
    require_fs_write(path)
    return os.remove(path)


def std_io_copy(src, dest):
    require_fs_read(src)
    require_fs_write(dest)
    return shutil.copy(src, dest)


def std_io_rename(old, new):
    require_fs_write(old)
    require_fs_write(new)
    return os.rename(old, new)


def std_io_mkdir(path):
    require_fs_write(path)
    return os.makedirs(path, exist_ok=True)


def std_io_listdir(path):
    require_fs_read(path)
    return os.listdir(path)


def close(f):
    return f.close()


def read(f, n: Optional[int] = None):
    return f.read() if n is None else f.read(n)


def write(f, data):
    return f.write(data)


def clipboard_copy(text):
    require_clipboard()
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(None):
            raise RuntimeError("Failed to open clipboard")
        user32.EmptyClipboard()
        data = str(text).encode("utf-16le")
        h_global = kernel32.GlobalAlloc(0x2000, len(data) + 2)
        if not h_global:
            user32.CloseClipboard()
            raise RuntimeError("Clipboard allocation failed")
        ptr = kernel32.GlobalLock(h_global)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h_global)
        user32.SetClipboardData(13, h_global)
        user32.CloseClipboard()
        return True
    if sys.platform == "darwin":
        res = subprocess.run(["pbcopy"], input=str(text), text=True, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard copy failed")
        return True
    if shutil.which("xclip"):
        res = subprocess.run(["xclip", "-selection", "clipboard"], input=str(text), text=True, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard copy failed")
        return True
    if shutil.which("xsel"):
        res = subprocess.run(["xsel", "--clipboard", "--input"], input=str(text), text=True, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard copy failed")
        return True
    raise RuntimeError("Clipboard tool not available")


def clipboard_paste():
    require_clipboard()
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(None):
            raise RuntimeError("Failed to open clipboard")
        handle = user32.GetClipboardData(13)
        if not handle:
            user32.CloseClipboard()
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            user32.CloseClipboard()
            raise RuntimeError("Clipboard read failed")
        data = ctypes.wstring_at(ptr)
        kernel32.GlobalUnlock(handle)
        user32.CloseClipboard()
        return data
    if sys.platform == "darwin":
        res = subprocess.run(["pbpaste"], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard paste failed")
        return res.stdout
    if shutil.which("xclip"):
        res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard paste failed")
        return res.stdout
    if shutil.which("xsel"):
        res = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "Clipboard paste failed")
        return res.stdout
    raise RuntimeError("Clipboard tool not available")
