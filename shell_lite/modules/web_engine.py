import os
import sys
import json
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ..ast_nodes import Listen, OnRequest, Download, String
from ..runtime import Tag, ReturnException

class WebEngine:
    """
    -----Purpose: Robust engine for handling HTTP server, routing, and file downloads.
    """
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.static_routes = {}
        self.http_routes = []
        self.middleware_routes = []

    def visit_ServeStatic(self, node):
        """
        -----Purpose: Registers a folder to serve static files over HTTP.
        """
        folder = str(self.interpreter.visit(node.folder))
        url_prefix = str(self.interpreter.visit(node.url))
        if not url_prefix.startswith('/'):
            url_prefix = '/' + url_prefix
        if not os.path.isdir(folder):
            print(f"Warning: Static folder '{folder}' does not exist.")
        self.static_routes[url_prefix] = folder
        print(f"Serving static files from '{folder}' at '{url_prefix}'")

    def visit_OnRequest(self, node: OnRequest):
        """
        -----Purpose: Registers an HTTP route handler with pattern matching.
        """
        path_str = self.interpreter.visit(node.path)
        if path_str == '__middleware__':
            self.middleware_routes.append(node.body)
            return
            
        regex_pattern = "^" + path_str + "$"
        if ':' in path_str:
            pattern = re.sub(r':(\w+)', r'(?P<\1>[^/]+)', path_str)
            regex_pattern = "^" + pattern + "$"
        compiled = re.compile(regex_pattern)
        self.http_routes.append((path_str, compiled, node.body))

    def visit_Listen(self, node: Listen):
        """
        -----Purpose: Starts the built-in HTTP server on a specified port.
        """
        if self.interpreter.safe_mode: 
            raise PermissionError("Web server is disabled in Safe Mode")

        port_val = self.interpreter.visit(node.port)
        engine_ref = self
        
        class ReusableHTTPServer(ThreadingHTTPServer):
            allow_reuse_address = True
            daemon_threads = True

        class ShellLiteHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_GET(self): self.handle_req()
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                content_type = self.headers.get('Content-Type', '')
                post_data = self.rfile.read(content_length).decode('utf-8')
                params = {}
                json_data = None
                if 'application/json' in content_type:
                    try: json_data = json.loads(post_data)
                    except: pass
                else:
                    if post_data:
                        parsed = urllib.parse.parse_qs(post_data)
                        params = {k: v[0] for k, v in parsed.items()}
                self.handle_req(params, json_data)

            def handle_req(self, post_params=None, json_data=None):
                try:
                    if post_params is None: post_params = {}
                    path = self.path
                    if '?' in path: path = path.split('?')[0]
                    
                    # Check static routes
                    for prefix, folder in engine_ref.static_routes.items():
                        if path.startswith(prefix):
                            clean_path = path[len(prefix):]
                            if clean_path.startswith('/'): clean_path = clean_path[1:]
                            if clean_path == '': clean_path = 'index.html'
                            file_path = os.path.join(folder, clean_path)
                            if os.path.exists(file_path) and os.path.isfile(file_path):
                                 self.send_response(200)
                                 ct = 'text/plain'
                                 if file_path.endswith('.css'): ct = 'text/css'
                                 elif file_path.endswith('.html'): ct = 'text/html'
                                 elif file_path.endswith('.js'): ct = 'application/javascript'
                                 self.send_header('Content-Type', ct)
                                 self.end_headers()
                                 with open(file_path, 'rb') as f: self.wfile.write(f.read())
                                 return

                    # Match dynamic routes
                    matched_body = None
                    path_params = {}
                    for pattern, regex, body in engine_ref.http_routes:
                        match = regex.match(path)
                        if match:
                            matched_body = body
                            path_params = match.groupdict()
                            break
                    
                    if matched_body:
                        # Set up environment for the request
                        req_obj = {"method": self.command, "path": path, "params": post_params, "json": json_data}
                        engine_ref.interpreter.global_env.set("request", req_obj)
                        for k, v in path_params.items(): engine_ref.interpreter.global_env.set(k, v)
                        
                        # Run middleware
                        for mw in engine_ref.middleware_routes:
                             for stmt in mw: engine_ref.interpreter.visit(stmt)
                        
                        # Run handler
                        response_body = ""
                        result = None
                        try:
                            for stmt in matched_body:
                                result = engine_ref.interpreter.visit(stmt)
                        except ReturnException as e:
                            result = e.value
                        except Exception as e:
                            raise e
                        
                        if isinstance(result, Tag): response_body = str(result)
                        elif result is not None: response_body = str(result)
                        else: response_body = "OK"
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()
                        self.wfile.write(response_body.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b'Not Found')
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode())

        server = ReusableHTTPServer(('0.0.0.0', port_val), ShellLiteHandler)
        print(f"ShellLite Server running on port {port_val}")
        try: server.serve_forever()
        except KeyboardInterrupt: server.shutdown()

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

    def visit_Download(self, node: Download):
        """
        -----Purpose: Downloads a file from a URL to the local filesystem.
        """
        if self.interpreter.safe_mode: 
            raise PermissionError("Downloads are disabled in Safe Mode")
        url = self.interpreter.visit(node.url)
        filename = url.split('/')[-1] or "downloaded_file"
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, filename)
        return filename
