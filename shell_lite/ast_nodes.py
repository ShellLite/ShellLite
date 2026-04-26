from dataclasses import dataclass, field
from typing import Any, List, Optional
@dataclass
class Node:
    line: int = field(default=0, init=False)
@dataclass
class Number(Node):
    value: int
@dataclass
class String(Node):
    value: str
@dataclass
class Regex(Node):
    pattern: str
@dataclass
class VarAccess(Node):
    name: str
@dataclass
class Assign(Node):
    name: str 
    value: Node
@dataclass
class PropertyAssign(Node):
    instance_name: str
    property_name: str
    value: Node
@dataclass
class UnaryOp(Node):
    op: str
    right: Node
@dataclass
class BinOp(Node):
    left: Node
    op: str
    right: Node
@dataclass
class Print(Node):
    expression: Node
    style: Optional[str] = None
    color: Optional[str] = None
@dataclass
class If(Node):
    condition: Node
    body: List[Node]
    else_body: Optional[List[Node]] = None
@dataclass
class While(Node):
    condition: Node
    body: List[Node]
@dataclass
class For(Node):
    count: Node
    body: List[Node]
@dataclass
class ListVal(Node):
    elements: List[Node]
@dataclass
class Dictionary(Node):
    pairs: List[tuple[Node, Node]]
@dataclass
class SetVal(Node):
    elements: List[Node]
@dataclass
class Boolean(Node):
    value: bool
@dataclass
class Input(Node):
    prompt: Optional[str] = None
@dataclass
class FunctionDef(Node):
    name: str
    args: List[tuple[str, Optional[Node], Optional[str]]] 
    body: List[Node]
    return_type: Optional[str] = None
@dataclass
class Call(Node):
    name: str
    args: List[Node]
    body: Optional[List[Node]] = None 
@dataclass
class Return(Node):
    value: Node
@dataclass
class ClassDef(Node):
    name: str
    properties: List[tuple[str, Optional[Node]]]
    methods: List[FunctionDef]
    parent: Optional[str] = None
@dataclass
class Instantiation(Node):
    var_name: str
    class_name: str
    args: List[Node]
@dataclass
class MethodCall(Node):
    instance_name: str
    method_name: str
    args: List[Node]
@dataclass
class PropertyAccess(Node):
    instance_name: str
    property_name: str
@dataclass
class Import(Node):
    path: str
@dataclass
class Try(Node):
    try_body: List[Node]
    catch_var: str
    catch_body: List[Node]
@dataclass
class Lambda(Node):
    params: List[str]
    body: Node  
@dataclass
class Ternary(Node):
    condition: Node
    true_expr: Node
    false_expr: Node
@dataclass
class ListComprehension(Node):
    expr: Node
    var_name: str
    iterable: Node
    condition: Optional[Node] = None
@dataclass
class Spread(Node):
    value: Node
@dataclass
class ConstAssign(Node):
    name: str
    value: Node
@dataclass
class ForIn(Node):
    var_name: str
    iterable: Node
    body: List[Node]
@dataclass
class IndexAccess(Node):
    obj: Node
    index: Node
@dataclass
class Stop(Node):
    pass
@dataclass
class Skip(Node):
    pass
@dataclass
class When(Node):
    value: Node
    cases: List[tuple[Node, List[Node]]]  
    otherwise: Optional[List[Node]] = None
@dataclass
class Throw(Node):
    message: Node
@dataclass
class TryAlways(Node):
    try_body: List[Node]
    catch_var: str
    catch_body: List[Node]
    always_body: List[Node]
@dataclass
class Unless(Node):
    condition: Node
    body: List[Node]
    else_body: Optional[List[Node]] = None
@dataclass
class Execute(Node):
    code: Node
@dataclass
class Repeat(Node):
    count: Node
    body: List[Node]
@dataclass
class ImportAs(Node):
    path: str
    alias: str
@dataclass
class Until(Node):
    condition: Node
    body: List[Node]
@dataclass
class Forever(Node):
    body: List[Node]
@dataclass
class Exit(Node):
    code: Optional[Node] = None
@dataclass  
class Make(Node):
    class_name: str
    args: List[Node]
@dataclass
class FileWatcher(Node):
    path: Node
    body: List[Node]
@dataclass
class Alert(Node):
    message: Node
@dataclass
class Prompt(Node):
    prompt: Node
@dataclass
class Confirm(Node):
    prompt: Node
@dataclass
class Spawn(Node):
    call: Node
@dataclass
class Await(Node):
    task: Node
@dataclass
class ProgressLoop(Node):
    loop_node: Node 
@dataclass
class Convert(Node):
    expression: Node
    target_format: str
@dataclass
class Listen(Node):
    port: Node
@dataclass
class OnRequest(Node):
    path: Node 
    body: List[Node]
@dataclass
class Every(Node):
    interval: Node
    unit: str 
    body: List[Node]
@dataclass
class After(Node):
    delay: Node
    unit: str
    body: List[Node]
@dataclass
class ServeStatic(Node):
    folder: Node
    url: Node
@dataclass
class Download(Node):
    url: Node
@dataclass
class ArchiveOp(Node):
    op: str 
    source: Node
    target: Node
@dataclass
class CsvOp(Node):
    op: str 
    data: Optional[Node]
    path: Node
@dataclass
class ClipboardOp(Node):
    op: str 
    content: Optional[Node] 
@dataclass
class AutomationOp(Node):
    action: str 
    args: List[Node]
@dataclass
class DateOp(Node):
    expr: str 
@dataclass
class FileWrite(Node):
    path: Node 
    content: Node 
    mode: str 
@dataclass
class FileRead(Node):
    path: Node
@dataclass
class DatabaseOp(Node):
    op: str
    args: List[Node]
@dataclass
class PythonImport(Node):
    module_name: str
    alias: Optional[str]

@dataclass
class App(Node):
    title: str
    width: int
    height: int
    body: List[Node]

@dataclass
class Widget(Node):
    widget_type: str  # 'button', 'input', 'heading', 'text'
    label: str
    var_name: Optional[str] = None
    event_handler: Optional[List[Node]] = None # For buttons with 'do:'

@dataclass
class Layout(Node):
    layout_type: str # 'column', 'row'
    body: List[Node]
