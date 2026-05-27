from .__shl_runtime__ import *
__SHL_MODULES = {}

def web_on_request(path, handler):
    std_web_on_request(path, handler)

def web_listen(port):
    std_web_listen(port)

def web_serve_static(url, folder):
    std_web_serve_static(url, folder)