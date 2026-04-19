from .ast_nodes import (
    Node, DatabaseOp, Download, ArchiveOp, CsvOp, ClipboardOp, AutomationOp,
    FileRead, FileWrite, Execute, FileWatcher, Spawn, Await,
    ModelDef, CreateTable, InsertRecord, UpdateRecords, DeleteRecords, FindRecords,
    Listen, OnRequest, ServeStatic, PythonImport, FromImport
)

def ensure_safe(statements):
    """
    -----Purpose: Scans an AST for restricted operations when Safe Mode is active.
    -----        Raises PermissionError if an unsafe node is discovered.
    """
    if os.environ.get("SHL_SAFE") != "1":
        return

    unsafe_types = (
        DatabaseOp, Download, ArchiveOp, CsvOp, ClipboardOp, AutomationOp,
        FileRead, FileWrite, Execute, FileWatcher, Spawn, Await,
        ModelDef, CreateTable, InsertRecord, UpdateRecords, DeleteRecords, FindRecords,
        Listen, OnRequest, ServeStatic
    )

    def check_node(node):
        if isinstance(node, unsafe_types):
            raise PermissionError(f"Operation '{type(node).__name__}' is restricted in Safe Mode.")
        
        if isinstance(node, PythonImport):
            if node.module_name != 'math':
                raise PermissionError(f"Importing native module '{node.module_name}' is restricted in Safe Mode.")
        
        if isinstance(node, FromImport):
             if node.module_name != 'math':
                raise PermissionError(f"Importing from native module '{node.module_name}' is restricted in Safe Mode.")
        for attr in vars(node):
            val = getattr(node, attr)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, Node):
                        check_node(item)
            elif isinstance(val, Node):
                check_node(val)

    for stmt in statements:
        check_node(stmt)
