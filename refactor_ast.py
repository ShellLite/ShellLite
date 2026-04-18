import re


def rewrite_ast_nodes(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        src = f.read()
        
    lines = src.split('\n')
    out_lines = []
    
    # We will parse line by line to keep formatting mostly intact
    # We find `@dataclass` followed by `class ...:`
    
    i = 0
    in_class = False
    current_class = ""
    class_fields = []
    
    out_lines.append("\"\"\"")
    out_lines.append("NASA Standard Abstract Syntax Tree (AST) node definitions.")
    out_lines.append("This module defines the tree structures used during parsing.")
    out_lines.append("\"\"\"")
    
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('@dataclass'):
            # It's a dataclass
            out_lines.append(line)
            i += 1
            class_line = lines[i]
            out_lines.append(class_line)
            
            # Extract class name
            m = re.match(r'class\s+(\w+)\s*\(Node\):', class_line)
            if not m:
                m = re.match(r'class\s+(\w+):', class_line)
            current_class = m.group(1) if m else "Unknown"
            
            # Gather fields until next @dataclass or EOF
            j = i + 1
            class_fields = []
            class_body_lines = []
            
            while j < len(lines) and not lines[j].startswith('@dataclass'):
                body_line = lines[j]
                stripped = body_line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('pass') and ':' in stripped:
                    if '=' not in stripped: # only simple fields or defaults we can parse
                        var_name, type_hint = [x.strip() for x in stripped.split(':', 1)]
                        class_fields.append((var_name, type_hint))
                    else:
                        var_name, rest = [x.strip() for x in stripped.split(':', 1)]
                        type_hint = rest.split('=', 1)[0].strip()
                        class_fields.append((var_name, type_hint))
                class_body_lines.append(body_line)
                j += 1
                
            # Create docstring
            docstring = f'    \"\"\"\n    AST Node representing {current_class}.\n\n    Attributes:\n'
            if not class_fields:
                docstring += '        None\n'
            for v, t in class_fields:
                docstring += f'        {v} ({t}): The {v} property.\n'
            docstring += '    \"\"\"'
            
            out_lines.append(docstring)
            for bl in class_body_lines:
                out_lines.append(bl)
                
            # Create post init if needed, unless it's Node
            if class_fields and current_class != 'Node':
                post_init = []
                post_init.append('    def __post_init__(self) -> None:')
                post_init.append('        \"\"\"Validate invariants after initialization.\"\"\"')
                valid_checks = 0
                for v, t in class_fields:
                    if t == 'int':
                        post_init.append(f'        assert isinstance(self.{v}, int), f"{current_class}.{v} must be int"')
                        valid_checks += 1
                    elif t == 'str':
                        post_init.append(f'        assert isinstance(self.{v}, str), f"{current_class}.{v} must be str"')
                        valid_checks += 1
                    elif t == 'bool':
                        post_init.append(f'        assert isinstance(self.{v}, bool), f"{current_class}.{v} must be bool"')
                        valid_checks += 1
                    elif t == 'Node':
                        post_init.append(f'        assert isinstance(self.{v}, Node), f"{current_class}.{v} must be a Node instance"')
                        valid_checks += 1
                    elif t == 'List[Node]':
                        post_init.append(f'        assert isinstance(self.{v}, list), f"{current_class}.{v} must be a list"')
                        post_init.append(f'        for item in self.{v}:')
                        post_init.append(f'            assert isinstance(item, Node), f"Elements of {current_class}.{v} must be Node instances"')
                        valid_checks += 1
                        
                if valid_checks > 0:
                    out_lines.extend(post_init)
                    
            i = j - 1
            
        else:
            if not in_class:
                out_lines.append(line)
        i += 1
                
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
        
if __name__ == '__main__':
    rewrite_ast_nodes('shell_lite/ast_nodes.py')
    print("Done rewriting ast_nodes.py")
