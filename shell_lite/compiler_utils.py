import os

from .ast_nodes import (
    ArchiveOp,
    AutomationOp,
    Await,
    ClipboardOp,
    CreateTable,
    CsvOp,
    DatabaseOp,
    DeleteRecords,
    Download,
    FileRead,
    FileWrite,
    FindRecords,
    FromImport,
    InsertRecord,
    Listen,
    ModelDef,
    Node,
    OnRequest,
    PythonImport,
    ServeStatic,
    Spawn,
    UpdateRecords,
)


def ensure_safe(statements):
    """
    Scans AST nodes and raises PermissionError if any unsafe node is discovered while SHL_SAFE is enabled.
    """
    if os.environ.get("SHL_SAFE") != "1":
        return

    unsafe_types = (
        DatabaseOp,
        Download,
        ArchiveOp,
        CsvOp,
        ClipboardOp,
        AutomationOp,
        FileRead,
        FileWrite,
        Spawn,
        Await,
        ModelDef,
        CreateTable,
        InsertRecord,
        UpdateRecords,
        DeleteRecords,
        FindRecords,
        Listen,
        OnRequest,
        ServeStatic,
    )

    def check_node(node):
        if isinstance(node, unsafe_types):
            raise PermissionError(
                f"Operation '{type(node).__name__}' is restricted in Safe Mode."
            )

        if isinstance(node, PythonImport):
            if node.module_name != "math":
                raise PermissionError(
                    f"Importing native module '{node.module_name}' is restricted in Safe Mode."
                )

        if isinstance(node, FromImport):
            if node.module_name != "math":
                raise PermissionError(
                    f"Importing from native module '{node.module_name}' is restricted in Safe Mode."
                )
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
