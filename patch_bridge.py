import os

file_path = r"c:\Users\shrey\OneDrive\Desktop\oka\shell-lite\shell_lite\interpreter.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_index = -1
end_index = -1

for i, line in enumerate(lines):
    if line.strip().startswith("def visit_Import(self, node: Import):"):
        start_index = i
    if line.strip().startswith("def _get_class_properties(self, class_def: ClassDef)"):
        end_index = i
        break

if start_index != -1 and end_index != -1:
    print(f"Found visit_Import at {start_index} and _get_class_properties at {end_index}")
    
    new_method = """    def visit_Import(self, node: Import):
        if node.path in self.std_modules:
            self.current_env.set(node.path, self.std_modules[node.path])
            return
        
        # 1. Check File System (ShellLite modules)
        import os 
        import importlib
        target_path = None
        
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

        # 2. If found on FS, load as ShellLite
        if target_path:
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
            return

        # 3. BRIDGE: Try importing as a raw Python module
        try:
            py_module = importlib.import_module(node.path)
            self.current_env.set(node.path, py_module)
            return
        except ImportError:
            pass # Fall through to error
            
        raise FileNotFoundError(f"Could not find module '{node.path}'. Searched:\\n - ShellLite Local/Global\\n - Python Site-Packages (The Bridge)")
"""
    # Insert new method
    # We replace from start_index to end_index (exclusive of end_index)
    # But new_method needs a trailing newline
    
    lines[start_index:end_index] = [new_method + "\n"]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("PATCH APPLIED SUCCESSFULLY")

else:
    print("FAILED TO FIND METHOD BOUNDARIES")
