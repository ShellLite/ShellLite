import sys
import os
import shutil
import urllib.request
import zipfile
import io
import subprocess
from .lexer import Lexer
from .parser import Parser
from .interpreter import Interpreter
from .ast_nodes import *
import json
def execute_source(source: str, interpreter: Interpreter):
    lines = source.split('\n')

    import difflib
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        statements = parser.parse()
        for stmt in statements:
            interpreter.visit(stmt)
    except Exception as e:
        # Check if it has a line number
        if hasattr(e, 'line') and e.line > 0:
            print(f"\n[ShellLite Error] on line {e.line}:")
            if 0 <= e.line-1 < len(lines):
                 print(f"  > {lines[e.line-1].strip()}")
                 print(f"    {'^' * len(lines[e.line-1].strip())}")
            print(f"Message: {e}")

            # "Did you mean?" for NameErrors
            if "not defined" in str(e):
                 # Extract the variable name
                 import re
                 match = re.search(r"'(.*?)'", str(e))
                 if match:
                     missing_var = match.group(1)
                     # Gather candidates (variables and functions)
                     candidates = list(interpreter.global_env.variables.keys()) + list(interpreter.functions.keys())
                     suggestions = difflib.get_close_matches(missing_var, candidates, n=1, cutoff=0.6)
                     if suggestions:
                         print(f"Did you mean: '{suggestions[0]}'?")
        else:
             print(f"\n[ShellLite Error]: {e}")
        
        # Optional: Print stack trace only if debug mode
        if os.environ.get("SHL_DEBUG"):
            import traceback
            traceback.print_exc()
def run_file(filename: str):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    import sys

    # Debug prints removed for production
    from .interpreter import Interpreter
    
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    interpreter = Interpreter()
    execute_source(source, interpreter)
def run_repl():
    interpreter = Interpreter()
    print("\n" + "="*40)
    print("  ShellLite REPL - English Syntax")
    print("="*40)
    print("Version: v0.04.6.8 | Made by Shrey Naithani")
    print("Commands: Type 'exit' to quit, 'help' for examples.")
    print("Note: Terminal commands (like 'shl install') must be run in CMD/PowerShell, not here.")

    # Try importing prompt_toolkit for a better experience
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.lexers import PygmentsLexer
        from pygments.lexers.shell import BashLexer 
        from prompt_toolkit.styles import Style
        # Ideally we'd have a ShellLite lexer, but Bash or Python is decent for now.
        
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
                # Use prompt_toolkit
                line = session.prompt(prompt_str)
            else:
                # Fallback
                line = input(prompt_str)

            if line.strip() == "exit":
                break
                
            if line.strip() == "help":
                 print("\nShellLite Examples:")
                 print('  say "Hello World"')
                 print('  tasks is a list            # Initialize an empty list')
                 print('  add "Buy Milk" to tasks    # Add items to the list')
                 print('  display(tasks)             # View the list')
                 continue
            
            if line.strip().startswith("shl"):
                 print("! Hint: You are already INSIDE ShellLite.")
                 continue

            # Multi-line handling logic
            # If line ends with ':' or '\', or we are inside a block (indent > 0)
            # ShellLite uses indentation.
            
            # Heuristic: if line ends with ':', expect more.
            # If line is empty and we have buffer, execute.
            
            if line.strip().endswith(":") or line.strip().endswith("\\"):
                buffer.append(line)
                continue
            
            # If line starts with indent (standard 4 spaces or tab), keep adding to buffer
            if buffer and (line.startswith("    ") or line.startswith("\t")):
                buffer.append(line)
                continue
            elif buffer and not line.strip():
                 # Empty line triggers execution of buffer
                 source = "\n".join(buffer)
                 execute_source(source, interpreter)
                 buffer = []
                 continue
            elif buffer:
                 # Non-empty, non-indented line. 
                 # This means we left the block? Or it's a new separate command?
                 # If we were in a block, usually we need an empty line to signal end in a REPL.
                 # But let's assume this ends the block and starts new.
                 buffer.append(line)
                 # Actually, if it's not indented, it might be the end of the block.
                 # Let's try to execute the buffer, then execute this line.
                 # But wait, what if it's 'else:'? That is not indented but part of block.
                 if line.strip().startswith("else") or line.strip().startswith("elif"):
                     buffer.append(line)
                     continue
                 
                 # Execute accumulated buffer first
                 # This mimics Python REPL slightly but Python waits for empty line.
                 # Let's force empty line for execution to be safe for now.
                 buffer.append(line)
                 continue

            # Single line execution if no buffer
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
    print("\n" + "="*50)
    print("  ShellLite Global Installer")
    print("="*50)
    install_dir = os.path.join(os.environ['LOCALAPPDATA'], 'ShellLite')
    if not os.path.exists(install_dir):
        os.makedirs(install_dir)
    target_exe = os.path.join(install_dir, 'shl.exe')
    current_path = sys.executable
    is_frozen = getattr(sys, 'frozen', False)
    try:
        if is_frozen:
            if os.path.abspath(current_path).lower() != os.path.abspath(target_exe).lower():
                try:
                    shutil.copy2(current_path, target_exe)
                except Exception as copy_err:
                    print(f"Warning: Could not copy executable: {copy_err}")
                    print("This is fine if you are running the installed version.")
            else:
                print("Running from install directory, skipping copy.")
        else:
            print("Error: Installation requires the shl.exe file.")
            return

        # Update PATH user variable
        ps_cmd = f'$oldPath = [Environment]::GetEnvironmentVariable("Path", "User"); if ($oldPath -notlike "*ShellLite*") {{ [Environment]::SetEnvironmentVariable("Path", "$oldPath;{install_dir}", "User") }}'
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        
        print(f"\n[SUCCESS] ShellLite (v0.04.6.8) is installed!")
        print(f"Location: {install_dir}")
        print("\nIMPORTANT STEP REQUIRED:")
        print("1. Close ALL open terminal windows (CMD, PowerShell, VS Code).")
        print("2. Open a NEW terminal.")
        print("3. Type 'shl' to verify installation.")
        print("="*50 + "\n")
        
        # Optional: Try using setx for immediate effect in future sessions (though usually requires restart of shell)
        # subprocess.run(f'setx PATH "%PATH%;{install_dir}"', shell=True, capture_output=True)
        
        input("Press Enter to finish...")
    except Exception as e:
        print(f"Installation failed: {e}")
    except Exception as e:
        print(f"Installation failed: {e}")

def init_project():
    if os.path.exists("shell-lite.toml"):
        print("Error: shell-lite.toml already exists.")
        return
    
    content = """[project]
name = "my-shell-lite-app"
version = "0.1.0"
description = "A new ShellLite project"

[dependencies]
# Format: "user/repo" = "branch" (default: main)
# Example: "shrey-n/stdlib" = "main"
"""
    with open("shell-lite.toml", "w") as f:
        f.write(content)
    print("[SUCCESS] Created shell-lite.toml")
    print("Run 'shl install' to install dependencies listed in it.")

def install_all_dependencies():
    if not os.path.exists("shell-lite.toml"):
        print("Error: No shell-lite.toml found. Run 'shl init' first.")
        return
        
    print("Reading shell-lite.toml...")
    deps = {}
    in_deps = False
    with open("shell-lite.toml", 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            
            if line == "[dependencies]":
                in_deps = True
                continue
            elif line.startswith("["):
                in_deps = False
                continue
                
            if in_deps and '=' in line:
                # Parse "key" = "value"
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
    if '/' not in package_name:
        print(f"Error: Package '{package_name}' must be in format 'user/repo'")
        return
    
    user, repo = package_name.split('/')
    print(f"Fetching '{package_name}' ({branch}) from GitHub...")
    
    home = os.path.expanduser("~")
    modules_dir = os.path.join(home, ".shell_lite", "modules")
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
        
    target_dir = os.path.join(modules_dir, repo)
    
    # We always overwrite for now, or maybe warn?
    # Let's remove if exists to ensure fresh install
    if os.path.exists(target_dir):
        # check if it's the same? simple way: remove and reinstall
        pass 
        
    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
    
    try:
        # Check if cache/temp dir exists
        import tempfile
        
        print(f"Downloading {zip_url}...")
        try:
            with urllib.request.urlopen(zip_url) as response:
                zip_data = response.read()
        except urllib.error.HTTPError as e:
            if branch == "main" and e.code == 404:
                # Try master fallback if explicit branch wasn't really explicit (default)
                # But here we passed 'main' as default.
                print("Branch 'main' not found, trying 'master'...")
                zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/master.zip"
                with urllib.request.urlopen(zip_url) as response:
                    zip_data = response.read()
            else:
                 raise e

        # Extract to temp first? No, extract to modules_dir then rename
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            z.extractall(modules_dir)
            
        # GitHub zips extract to "repo-branch"
        # We need to find what it extracted to.
        # It usually is repo-branch.
        # Let's handle the rename safely
        
        # We don't know exact folder name if branch has slashes or generic.
        # But usually 'repo-branch'.
        
        # Heuristic: List dirs in modules_dir, find the new one?
        # A bit racy if running parallel, but we aren't.
        # Better: get the first member of zip
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            root_name = z.namelist()[0].split('/')[0]
        
        extracted_path = os.path.join(modules_dir, root_name)
        
        if os.path.exists(target_dir):
             shutil.rmtree(target_dir) # Remove old version
             
        os.rename(extracted_path, target_dir)
        print(f"[SUCCESS] Installed '{package_name}' to {target_dir}")
        
    except Exception as e:
        print(f"Installation failed for {package_name}: {e}")

def compile_file(filename: str, target: str = 'python'):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return
    print(f"Compiling {filename} to {target.upper()}...")
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    try:
        from .parser import Parser
        from .lexer import Lexer
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        statements = parser.parse()
        if target.lower() == 'js':
            from .js_compiler import JSCompiler
            compiler = JSCompiler()
            code = compiler.compile(statements)
            ext = '.js'
        else:
            from .compiler import Compiler
            compiler = Compiler()
            code = compiler.compile(statements)
            ext = '.py'
        output_file = filename.replace('.shl', ext)
        if output_file == filename: output_file += ext
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
                    '--name', os.path.splitext(os.path.basename(filename))[0],
                    '--log-level', 'WARN'
                ])
                print(f"[SUCCESS] Built {os.path.splitext(os.path.basename(filename))[0]}.exe")
            except ImportError:
                 pass 
    except Exception as e:
        print(f"Compilation Failed: {e}")
def lint_file(filename: str):
    if not os.path.exists(filename):
        print(json.dumps([{"line": 0, "message": f"File {filename} not found"}]))
        return
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        parser.parse()
        print(json.dumps([]))
    except Exception as e:
        line = getattr(e, 'line', 1)
        print(json.dumps([{
            "line": line, 
            "message": str(e)
        }]))
def resolve_cursor(filename: str, line: int, col: int):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
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
    if not shutil.which("shl"):
        print("\nShellLite is not installed globally.")
        choice = input("Would you like to install it so 'shl' works everywhere? (y/n): ").lower()
        if choice == 'y':
            install_globally()
def show_help():
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
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "compile" or cmd == "build":
            if len(sys.argv) > 2:
                filename = sys.argv[2]
                target = 'python'
                if '--target' in sys.argv:
                    try:
                        idx = sys.argv.index('--target')
                        target = sys.argv[idx+1]
                    except IndexError:
                        print("Error: --target requires an argument (js/python)")
                        return
                compile_file(filename, target)
            else:
                print("Usage: shl compile <filename> [--target js]")
        elif cmd == "help" or cmd == "--help" or cmd == "-h":
            show_help()
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
                # Install specific package
                package_name = sys.argv[2]
                install_package(package_name)
                # TODO: Add to shell-lite.toml if it exists
            else:
                # Install dependencies from shell-lite.toml
                install_all_dependencies()
        elif cmd == "setup-path": # Renamed from 'install' to avoid confusion, but kept 'install' as verify
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
