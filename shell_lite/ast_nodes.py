from dataclasses import dataclass, field
from typing import List, Optional, Any, Union


@dataclass
class Node:
    """
    Base class for all AST nodes.
    """
    line: int = field(default=0, init=False)
    col: int = field(default=0, init=False)
    end_line: int = field(default=0, init=False)
    end_col: int = field(default=0, init=False)

@dataclass
class Number(Node):
    value: Union[int, float]

@dataclass
class String(Node):
    value: str

@dataclass
class Slice(Node):
    start: Optional[Node] = None
    stop: Optional[Node] = None
    step: Optional[Node] = None

@dataclass
class VarAccess(Node):
    name: str

@dataclass
class Assign(Node):
    name: str
    value: Node

@dataclass
class TypedAssign(Node):
    name: str
    type_hint: str
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
class ForIn(Node):
    var_name: str
    iterable: Node
    body: List[Node]

@dataclass
class ListVal(Node):
    elements: List[Node]

@dataclass
class Dictionary(Node):
    pairs: List[tuple[Node, Node]]

@dataclass
class Boolean(Node):
    value: bool

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
    kwargs: Optional[List[tuple[str, Node]]] = None
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
    kwargs: Optional[List[tuple[str, Node]]] = None

@dataclass
class MethodCall(Node):
    instance_name: str
    method_name: str
    args: List[Node]
    kwargs: Optional[List[tuple[str, Node]]] = None

@dataclass
class PropertyAccess(Node):
    instance_name: str
    property_name: str

@dataclass
class Import(Node):
    path: str

@dataclass
class ImportAs(Node):
    path: str
    alias: str

@dataclass
class Try(Node):
    try_body: List[Node]
    catch_var: str
    catch_body: List[Node]

@dataclass
class TryAlways(Node):
    try_body: List[Node]
    catch_var: str
    catch_body: List[Node]
    always_body: List[Node]

@dataclass
class Match(Node):
    match_expr: Node
    cases: List[tuple[Node, List[Node]]]
    default_case: Optional[List[Node]] = None

@dataclass
class ListComprehension(Node):
    expr: Node
    var_name: str
    iterable: Node
    condition: Optional[Node] = None

@dataclass
class ConstAssign(Node):
    name: str
    value: Node

@dataclass
class IndexAccess(Node):
    obj: Node
    index: Node

@dataclass
class IndexAssign(Node):
    obj: Node
    index: Node
    value: Node

@dataclass
class Stop(Node):
    pass

@dataclass
class Skip(Node):
    pass

@dataclass
class Throw(Node):
    message: Node

@dataclass
class PythonImport(Node):
    module_name: str
    alias: Optional[str]

@dataclass
class FromImport(Node):
    module_name: str
    names: List[tuple[str, Optional[str]]]


@dataclass
class For(Node):
    count: Node
    body: List[Node]


@dataclass
class Unless(Node):
    condition: Node
    body: List[Node]


@dataclass
class Repeat(Node):
    count: Node
    body: List[Node]


@dataclass
class Forever(Node):
    body: List[Node]


@dataclass
class Until(Node):
    condition: Node
    body: List[Node]


@dataclass
class Convert(Node):
    expression: Node
    target_format: str


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
    path: Node
    data: Optional[Node] = None


@dataclass
class ClipboardOp(Node):
    op: str
    content: Optional[Node] = None


@dataclass
class AutomationOp(Node):
    action: str
    args: List[Node]


@dataclass
class FileWrite(Node):
    path: Node
    content: Node
    mode: str = 'w'


@dataclass
class FileRead(Node):
    path: Node


@dataclass
class DatabaseOp(Node):
    op: str
    args: List[Node]


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
class Exit(Node):
    code: Optional[Node] = None


@dataclass
class Spawn(Node):
    call: Node


@dataclass
class Await(Node):
    task: Node


@dataclass
class Parallel(Node):
    body: List[Node]


@dataclass
class Gather(Node):
    tasks: Node


@dataclass
class Lock(Node):
    name: str
    body: List[Node]


@dataclass
class Channel(Node):
    pass


@dataclass
class Send(Node):
    channel: Node
    value: Node


@dataclass
class Receive(Node):
    channel: Node


@dataclass
class Assertion(Node):
    left: Node
    op: str
    right: Optional[Node] = None


@dataclass
class TestBlock(Node):
    name: str
    body: List[Node]


@dataclass
class Layout(Node):
    kind: str
    body: List[Node]


@dataclass
class Widget(Node):
    kind: str
    label: str
    var_name: Optional[str] = None
    handler: Optional[List[Node]] = None


@dataclass
class OnRequest(Node):
    path: Node
    body: List[Node]


@dataclass
class Listen(Node):
    port: Node


@dataclass
class MaxNode(Node):
    left: Node
    right: Optional[Node] = None


@dataclass
class MinNode(Node):
    left: Node
    right: Optional[Node] = None


@dataclass
class ClampNode(Node):
    val: Node
    min_val: Node
    max_val: Node


@dataclass
class LerpNode(Node):
    a: Node
    b: Node
    t: Node

