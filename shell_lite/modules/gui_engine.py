import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import List, Any
from ..ast_nodes import App, Layout, Widget, Node

_HAS_TK = True
try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog
except ImportError:
    _HAS_TK = False

class GUIEngine:
    """
    -----Purpose: Robust engine for handling Tkinter-based GUI rendering.
    """
    def __init__(self, interpreter):
        self.interpreter = interpreter

    def visit_App(self, node: App):
        """
        -----Purpose: Initializes and runs a Tkinter-based GUI application.
        """
        if not _HAS_TK:
            print("[App] GUI apps require tkinter. Install python3-tk on Linux (sudo apt install python3-tk).")
            return
        root = tk.Tk()
        root.title(node.title)
        root.geometry(f"{node.width}x{node.height}")
        self.interpreter.ui_parent_stack = [root]
        
        # Inject alert as a GUI-aware function
        def ui_alert(msg):
            messagebox.showinfo("Message", str(msg))
        self.interpreter.current_env.set("alert", ui_alert)
        
        try:
            for child in node.body:
                self.interpreter.visit(child)
            root.mainloop()
        finally:
            self.interpreter.ui_parent_stack = []

    def visit_Layout(self, node: Layout):
        """
        -----Purpose: Handles nested layout frames (column/row).
        """
        if not self.interpreter.ui_parent_stack:
            return
        parent = self.interpreter.ui_parent_stack[-1]
        frame = tk.Frame(parent)
        
        # Pack strategy based on layout type
        if node.type == 'column':
            frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        else:
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
        self.interpreter.ui_parent_stack.append(frame)
        for child in node.children:
            self.interpreter.visit(child)
        self.interpreter.ui_parent_stack.pop()

    def visit_Widget(self, node: Widget):
        """
        -----Purpose: Renders individual GUI components (button, label, input).
        """
        if not self.interpreter.ui_parent_stack:
            return
        parent = self.interpreter.ui_parent_stack[-1]
        
        if node.type == 'button':
            def handler():
                if node.handler:
                    for stmt in node.handler:
                        self.interpreter.visit(stmt)
            btn = tk.Button(parent, text=node.label, command=handler)
            btn.pack(pady=5, padx=10, fill=tk.X)
        elif node.type == 'heading':
            lbl = tk.Label(parent, text=node.label, font=("Helvetica", 16, "bold"))
            lbl.pack(pady=10, padx=10, anchor='w')
        elif node.type == 'paragraph':
            lbl = tk.Label(parent, text=node.label, wraplength=400, justify=tk.LEFT)
            lbl.pack(pady=5, padx=10, anchor='w')
        elif node.type == 'image':
            # Placeholder for image support
            lbl = tk.Label(parent, text=f"[Image: {node.label}]", bg="gray")
            lbl.pack(pady=5)
        elif node.type == 'input':
            var = tk.StringVar()
            if node.label:
                lbl = tk.Label(parent, text=node.label)
                lbl.pack(anchor='w', padx=10)
            entry = tk.Entry(parent, textvariable=var)
            entry.pack(pady=5, padx=10, fill=tk.X)
            if node.var_name:
                self.interpreter.current_env.set(node.var_name, var)

    def visit_Alert(self, node):
        msg = self.interpreter.visit(node.message)
        if _HAS_TK and self.interpreter.ui_parent_stack:
            messagebox.showinfo("Alert", str(msg))
        else:
            print(f"ALERT: {msg}")

    def visit_Prompt(self, node):
        msg = self.interpreter.visit(node.message)
        if _HAS_TK and self.interpreter.ui_parent_stack:
            return simpledialog.askstring("Prompt", str(msg))
        return input(f"{msg}: ")

    def visit_Confirm(self, node):
        msg = self.interpreter.visit(node.message)
        if _HAS_TK and self.interpreter.ui_parent_stack:
            return messagebox.askyesno("Confirm", str(msg))
        res = input(f"{msg} (y/n): ").lower()
        return res.startswith('y')
