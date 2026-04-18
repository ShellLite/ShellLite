import json
import difflib
import re
import traceback
import sys
import os
import shutil
import subprocess
import urllib.request as request
from .lexer import Lexer
from .parser_gbp import GeometricBindingParser
from .interpreter import Interpreter
from .ast_nodes import *

def execute_source(source: str, interpreter: Interpreter):
    """
    -----Purpose: Tokenizes, parses, and executes a source string using a 
    -----        provided interpreter instance. Displays formatted errors.
    """
    lines = source.split('\n')
    import difflib
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        for stmt in statements:
            interpreter.visit(stmt)
    except Exception as e:
        if hasattr(e, 'line') and e.line > 0:
            print(f"\n[ShellLite Error] on line {e.line}:")
            if 0 <= e.line-1 < len(lines):
                 print(f"  > {lines[e.line-1].strip()}")
                 print(f"    {'^' * len(lines[e.line-1].strip())}")
            print(f"Message: {e}")
            if "not defined" in str(e):
                 match = re.search(r"'(.*?)'", str(e))
                 if match:
                     missing_var = match.group(1)
                     vars_list = list(interpreter.global_env.variables.keys())
                     funcs_list = list(interpreter.functions.keys())
                     candidates = vars_list + funcs_list
                     suggestions = difflib.get_close_matches(
                         missing_var, candidates, n=1, cutoff=0.6
                     )
                     if suggestions:
                         print(f"Did you mean: '{suggestions[0]}'?")
        else:
             print(f"\n[ShellLite Error]: {e}")
        if os.environ.get("SHL_DEBUG"):
            traceback.print_exc()
def run_file(filename: str):
    """
    -----Purpose: Opens a file, reads its content, and executes it.
    """
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    interpreter = Interpreter()
    execute_source(source, interpreter)

def run_repl():
    """
    -----Purpose: Starts an interactive Read-Eval-Print Loop for ShellLite.
    """
    interpreter = Interpreter()
    print("\n" + "="*40)
    print("="*40)
    print("Version: v0.05 | Made by Shrey Naithani")
    print("Commands: Type 'exit' to quit, 'help' for examples.")
    print("Note: Terminal commands (like 'shl install') must be run outside the REPL.")
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.lexers import PygmentsLexer
        from pygments.lexers.shell import BashLexer
        from prompt_toolkit.styles import Style
        style = Style.from_dict({
            'prompt': '#ansigreen bold',
        })
        session = PromptSession(lexer=PygmentsLexer(BashLexer), style=style)
        has_pt = True
    except ImportError:
        print("[Notice] Install 'prompt_toolkit' for syntax highlighting and history.")
        print("         Run: pip install prompt_toolkit")
        has_pt = False
        buffer = []
        indent_level = 0
    buffer = []
    while True:
        try:
            prompt_str = "... " if (buffer and len(buffer) > 0) else ">>> "
            if has_pt:
                line = session.prompt(prompt_str)
            else:
                line = input(prompt_str)
            if line.strip() == "exit":
                break
            if line.strip() == "help":
                 print("\nShellLite Examples:")
                 print('  say "Hello World"')
                 print('  tasks is a list            '
                       '# Initialize an empty list')
                 print('  add "Buy Milk" to tasks    '
                       '# Add items to the list')
                 print('  display(tasks)             '
                       '# View the list')
                 continue
            if line.strip().startswith("shl"):
                 print("! Hint: You are already INSIDE ShellLite.")
                 continue
            if line.strip().endswith(":") or line.strip().endswith("\\"):
                buffer.append(line)
                continue
            if buffer and (line.startswith("    ") or line.startswith("\t")):
                buffer.append(line)
                continue
            elif buffer and not line.strip():
                 source = "\n".join(buffer)
                 execute_source(source, interpreter)
                 buffer = []
                 continue
            elif buffer:
                 buffer.append(line)
                 if line.strip().startswith("else") or line.strip().startswith("elif"):
                     buffer.append(line)
                     continue
                 buffer.append(line)
                 continue
            if not buffer:
                if not line.strip(): continue
                execute_source(line, interpreter)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            buffer = []
def install_globally():
    """
    -----Purpose: Installs ShellLite globally by copying the executable and 
    -----        modifying the user's PATH via PowerShell.
    """
    print("\n" + "="*50)
    print("  ShellLite Global Installer")
    print("="*50)
    is_windows = sys.platform == 'win32'
    if is_windows:
        install_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ShellLite')
        target_exe = os.path.join(install_dir, 'shl.exe')
    else:
        install_dir = os.path.expanduser('~/.local/bin')
        target_exe = os.path.join(install_dir, 'shl')

    if not os.path.exists(install_dir):
        os.makedirs(install_dir, exist_ok=True)
        
    current_path = sys.executable
    is_frozen = getattr(sys, 'frozen', False)
    try:
        if is_frozen:
            src_abs = os.path.abspath(current_path)
            dst_abs = os.path.abspath(target_exe)
            if src_abs.lower() != dst_abs.lower():
                try:
                    shutil.copy2(current_path, target_exe)
                    if not is_windows:
                        os.chmod(target_exe, 0o755)
                except Exception as copy_err:
                    print(f"Warning: Could not copy executable: {copy_err}")
                    print("This is fine if you are running the installed version.")
            else:
                print("Running from install directory, skipping copy.")
        else:
            print("Error: Installation requires the frozen shl runtime.")
            return

        if is_windows:
            ps_cmd = (
                f'$oldPath = [Environment]::GetEnvironmentVariable("Path", "User");'
                ' if ($oldPath -notlike "*ShellLite*") {{ '
                f'[Environment]::SetEnvironmentVariable("Path", '
                f'"$oldPath;{install_dir}", "User") }}'
            )
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        else:
            home = os.path.expanduser("~")
            rc_files = []
            for rc in ['.bashrc', '.zshrc', '.profile']:
                rc_path = os.path.join(home, rc)
                if os.path.exists(rc_path):
                    rc_files.append(rc_path)
            
            export_line = f'export PATH="$PATH:{install_dir}"'
            for rc in rc_files:
                with open(rc, 'r', encoding='utf-8') as f:
                    content = f.read()
                if install_dir not in content:
                    with open(rc, 'a', encoding='utf-8') as f:
                        f.write(f"\n# Added by ShellLite Installer\n{export_line}\n")

        print(f"\n[SUCCESS] ShellLite (v0.6.0) is installed!")
        print(f"Location: {install_dir}")
        print("\nIMPORTANT STEP REQUIRED:")
        print("1. Close ALL open terminal windows.")
        print("2. Open a NEW terminal.")
        print("3. Type 'shl' to verify installation.")
        print("="*50 + "\n")
        input("Press Enter to finish...")
    except Exception as e:
        print(f"Installation failed: {e}")
def init_project():
    """
    -----Purpose: Initializes a new ShellLite project by creating a 
    -----        default shell-lite.toml configuration file.
    """
    if os.path.exists("shell-lite.toml"):
        print("Error: shell-lite.toml already exists.")
        return
    content = (
        '[project]\n'
        'name = "my-shell-lite-app"\n'
        'version = "0.1.0"\n'
        'description = "A new ShellLite project"\n'
        '[dependencies]\n'
    )
    with open("shell-lite.toml", "w") as f:
        f.write(content)
    print("[SUCCESS] Created shell-lite.toml")
    print("Run 'shl install' to install dependencies listed in it.")

def install_all_dependencies():
    """
    -----Purpose: Reads shell-lite.toml and installs all project dependencies.
    """
    if not os.path.exists("shell-lite.toml"):
        msg = "Error: No shell-lite.toml found. Run 'shl init' first."
        print(msg)
        return
    print("Reading shell-lite.toml...")
    deps = {}
    in_deps = False
    with open("shell-lite.toml", 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line == "[dependencies]":
                in_deps = True
                continue
            elif line.startswith("["):
                in_deps = False
                continue
            if in_deps and '=' in line:
                parts = line.split('=', 1)
                key = parts[0].strip().strip('"').strip("'")
                val = parts[1].strip().strip('"').strip("'")
                deps[key] = val
    if not deps:
        print("No dependencies found.")
        return
    print(f"Found {len(deps)} dependencies.")
    for repo, branch in deps.items():
        install_package(repo, branch=branch)

def install_package(package_name: str, branch: str = "main"):
    """
    -----Purpose: Downloads and extracts a specific GitHub repository into 
    -----        the local ShellLite modules directory.
    """
    if '/' not in package_name:
        msg = f"Error: Package '{package_name}' must be in format 'user/repo'"
        print(msg)
        return
    user, repo = package_name.split('/')
    print(f"Fetching '{package_name}' ({branch}) from GitHub...")
    home = os.path.expanduser("~")
    modules_dir = os.path.join(home, ".shell_lite", "modules")
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
    target_dir = os.path.join(modules_dir, repo)
    
    base_url = f"https://github.com/{user}/{repo}/archive/refs/heads"
    zip_url = f"{base_url}/{branch}.zip"
    try:
        import tempfile
        import urllib.request as request
        import zipfile
        import io
        import shutil
        print(f"Downloading {zip_url}...")
        try:
            with request.urlopen(zip_url) as response:
                zip_data = response.read()
        except urllib.error.HTTPError as e:
            if branch == "main" and e.code == 404:
                print("Branch 'main' not found, trying 'master'...")
                zip_url = f"{base_url}/master.zip"
                with request.urlopen(zip_url) as response:
                    zip_data = response.read()
            else:
                 raise e
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            z.extractall(modules_dir)
            root_name = z.namelist()[0].split('/')[0]
        
        extracted_path = os.path.join(modules_dir, root_name)
        if os.path.exists(target_dir):
             shutil.rmtree(target_dir)
        os.rename(extracted_path, target_dir)
        print(f"[SUCCESS] Installed '{package_name}' to {target_dir}")
    except Exception as e:
        print(f"Installation failed for {package_name}: {e}")

def compile_file(filename: str, target: str = 'llvm'):
    """
    -----Purpose: Transpiles a ShellLite script to JS, Python, or LLVM.
    """
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    print(f"Compiling {filename} to {target.upper()}...")
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        if target.lower() == 'js':
            from .js_compiler import JSCompiler
            compiler = JSCompiler()
            code = compiler.compile(statements)
            ext = '.js'
        elif target.lower() == 'llvm':
            try:
                from .llvm_backend.builder import build_llvm
                build_llvm(filename)
                return
            except ImportError:
                print("Error: 'llvmlite' is required for LLVM compilation.")
                return
        else:
            from .compiler import Compiler
            compiler = Compiler()
            code = compiler.compile(statements)
            ext = '.py'
        output_file = filename.replace('.shl', ext)
        if output_file == filename:
            output_file += ext
        with open(output_file, 'w') as f:
            f.write(code)
        print(f"[SUCCESS] Transpiled to {output_file}")
        if target.lower() == 'python':
            try:
                import PyInstaller.__main__
                print("Building Executable with PyInstaller...")
                PyInstaller.__main__.run([
                    output_file,
                    '--onefile',
                    '--name', 
                    os.path.splitext(os.path.basename(filename))[0],
                    '--log-level', 'WARN'
                ])
                exe_name = os.path.splitext(os.path.basename(filename))[0]
                print(f"[SUCCESS] Built {exe_name}.exe")
            except ImportError:
                 pass
    except Exception as e:
        print(f"Compilation Failed: {e}")

def lint_file(filename: str):
    """
    -----Purpose: Validates the syntax of a ShellLite file and outputs JSON
    -----        errors compatible with IDE extensions.
    """
    if not os.path.exists(filename):
        msg = f"File {filename} not found"
        print(json.dumps([{"line": 0, "message": msg}]))
        return
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        parser.parse()
        print(json.dumps([]))
    except Exception as e:
        line = getattr(e, 'line', 1)
        print(json.dumps([{
            "line": line,
            "message": str(e)
        }]))
def resolve_cursor(filename: str, line: int, col: int):
    """
    -----Purpose: Resolves the definition of an identifier at a given 
    -----        cursor position for IDE 'Go to Definition' features.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        nodes = parser.parse()
        target_token = None
        for t in tokens:
            if t.line == line:
                if t.column <= col <= t.column + len(t.value):
                    target_token = t
                    break
        if not target_token or target_token.type != 'ID':
             print(json.dumps({"found": False}))
             return
        word = target_token.value
        def find_def(n_list, name):
            for node in n_list:
                if isinstance(node, FunctionDef) and node.name == name:
                    return node, "Function"
                if isinstance(node, ClassDef) and node.name == name:
                    return node, "Class"
                if isinstance(node, Assign) and node.name == name:
                    return node, "Variable"
                if isinstance(node, If):
                     res = find_def(node.body, name)
                     if res: return res
            return None, None
        found_node = None
        found_type = None
        queue = nodes[:]
        while queue:
            n = queue.pop(0)
            if isinstance(n, FunctionDef):
                if n.name == word:
                    found_node = n
                    found_type = "Function"
                    break
                queue.extend(n.body)
            elif isinstance(n, ClassDef):
                if n.name == word:
                    found_node = n
                    found_type = "Class"
                    break
                queue.extend(n.methods)
            elif isinstance(n, Assign) and n.name == word:
                found_node = n
                found_type = "Variable"
                break
            elif isinstance(n, If): queue.extend(n.body)
            elif isinstance(n, While): queue.extend(n.body)
            elif isinstance(n, For): queue.extend(n.body)
        if found_node:
            print(json.dumps({
                "found": True,
                "file": filename,
                "line": found_node.line,
                "hover": f"**{found_type}** `{word}`"
            }))
        else:
             print(json.dumps({"found": False}))
    except Exception:
        print(json.dumps({"found": False}))

def format_file(filename: str):
    """
    -----Purpose: Standardizes the indentation and style of a ShellLite 
    -----        file using the built-in formatter.
    """
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        from .formatter import Formatter
        formatter = Formatter(source)
        formatted_code = formatter.format()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(formatted_code)
        print(f"[SUCCESS] Formatted {filename}")
    except Exception as e:
        print(f"Formatting failed: {e}")
def self_install_check():
    """
    -----Purpose: Checks if ShellLite is in the system PATH and offers to 
    -----        install it globally if not.
    """
    if not shutil.which("shl"):
        print("\nShellLite is not installed globally.")
        msg = (
            "Would you like to install it so 'shl' "
            "works everywhere? (y/n): "
        )
        choice = input(msg).lower()
        if choice == 'y':
            install_globally()

def show_help():
    """
    -----Purpose: Displays CLI usage information and available commands.
    """
    print("""
ShellLite - The English-Like Programming Language
Usage:
  shl <filename.shl>    Run a ShellLite script
  shl                   Start the interactive REPL
  shl help              Show this help message
  shl compile <file>    Compile a script (Options: --target js)
  shl fmt <file>        Format a script
  shl check <file>      Lint a file (JSON output)
  shl resolve <file> <line> <col>  Resolve symbol (JSON output)
  shl install           Install ShellLite globally to your system PATH
For documentation, visit: https://github.com/Shrey-N/ShellDesk
""")
def main():
    """
    -----Purpose: Main CLI dispatcher for ShellLite. Handles all system 
    -----        arguments and routes to appropriate functions.
    """
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "compile" or cmd == "build":
            if len(sys.argv) > 2:
                filename = sys.argv[2]
                target = 'llvm'
                if '--target' in sys.argv:
                    try:
                        idx = sys.argv.index('--target')
                        target = sys.argv[idx+1]
                    except IndexError:
                        msg = (
                            "Error: --target requires an "
                            "argument (js/python/llvm)"
                        )
                        print(msg)
                        return
                compile_file(filename, target)
            else:
                print("Usage: shl compile <filename> [--target js]")
        elif cmd == "llvm":
             if len(sys.argv) > 2:
                 try:
                     import llvmlite
                     from .llvm_backend.builder import build_llvm
                     build_llvm(sys.argv[2])
                 except ImportError:
                     msg = (
                         "Error: 'llvmlite' is required for LLVM backend. "
                         "Run: pip install llvmlite"
                     )
                     print(msg)
             else:
                 print("Usage: shl llvm <filename>")
        elif cmd == "help" or cmd == "--help" or cmd == "-h":
            show_help()
        elif cmd == "--version" or cmd == "-v":
             print("ShellLite v0.5.3.3")
        elif cmd == "get":
            if len(sys.argv) > 2:
                package_name = sys.argv[2]
                install_package(package_name)
            else:
                print("Usage: shl get <user/repo>")
        elif cmd == "init":
            init_project()
        elif cmd == "install":
            if len(sys.argv) > 2:
                package_name = sys.argv[2]
                install_package(package_name)
            else:
                install_all_dependencies()
        elif cmd == "setup-path":
             install_globally()
        elif cmd == "fmt" or cmd == "format":
            if len(sys.argv) > 2:
                filename = sys.argv[2]
                format_file(filename)
            else:
                print("Usage: shl fmt <filename>")
        elif cmd == "check":
            if len(sys.argv) > 2:
                filename = sys.argv[2]
                lint_file(filename)
        elif cmd == "test":
            from .test_runner import TestRunner
            target_dir = '.'
            if len(sys.argv) > 2:
                target_dir = sys.argv[2]
            runner = TestRunner(target_dir)
            runner.discover_and_run()
        elif cmd == "resolve":
            if len(sys.argv) > 4:
                filename = sys.argv[2]
                line = int(sys.argv[3])
                col = int(sys.argv[4])
                resolve_cursor(filename, line, col)
        elif cmd == "run":
            if len(sys.argv) > 2:
                run_file(sys.argv[2])
            else:
                print("Usage: shl run <filename>")
        else:
            run_file(sys.argv[1])
    else:
        self_install_check()
        run_repl()
if __name__ == "__main__":
    main()
