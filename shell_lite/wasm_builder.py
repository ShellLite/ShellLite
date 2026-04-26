import os
import shutil
import subprocess

from .c_compiler import CCompiler


class WASMBuilder:
    def __init__(self, output_dir="dist_wasm"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def build(self, statements, base_name="output"):
        compiler = CCompiler()
        c_source = compiler.compile(statements)
        
        c_file = os.path.join(self.output_dir, f"{base_name}.c")
        with open(c_file, "w") as f:
            f.write(c_source)
        
        print(f"Generated C source: {c_file}")
        
        emcc_path = shutil.which("emcc")
        if emcc_path:
            print("Emscripten found! Compiling to WASM...")
            js_file = os.path.join(self.output_dir, f"{base_name}.js")
            try:
                subprocess.run([
                    emcc_path, c_file, 
                    "-o", js_file, 
                    "-s", "WASM=1",
                    "-O2"
                ], check=True)
                print(f"Successfully built: {js_file} and {base_name}.wasm")
                self.generate_html(base_name)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Emscripten compilation failed: {e}")
                return False
        else:
            print("TIP: Install Emscripten (emcc) to compile this C file directly to WebAssembly.")
            print(f"Command: emcc {base_name}.c -o {base_name}.html -s WASM=1")
            return False

    def generate_html(self, base_name):
        html_cont = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ShellLite WebAssembly</title>
    <style>
        body {{ font-family: sans-serif; background: #121212; color: #eee; padding: 2em; }}
        #output {{ background: #000; border: 1px solid #333; padding: 1em; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>ShellLite WASM Output</h1>
    <div id="output">Loading...</div>
    <script src="{base_name}.js"></script>
    <script>
        // Override Module.print to show in div
        var outputDiv = document.getElementById('output');
        outputDiv.innerText = '';
        Module.print = function(text) {{
            outputDiv.innerText += text + '\\n';
        }};
    </script>
</body>
</html>
"""
        html_file = os.path.join(self.output_dir, f"{base_name}.test.html")
        with open(html_file, "w") as f:
            f.write(html_cont)
        print(f"Generated test harness: {html_file}")
