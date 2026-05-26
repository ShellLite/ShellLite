from typing import Dict, Optional, Any
from enum import Enum, auto

class SymbolType(Enum):
    VARIABLE = auto()
    FUNCTION = auto()
    CLASS = auto()
    MODEL = auto()
    CONSTANT = auto()

class Symbol:
    def __init__(self, name: str, symbol_type: SymbolType, type_info: Any = None, metadata: Dict[str, Any] = None, is_property: bool = False, is_global: bool = False):
        self.name = name
        self.symbol_type = symbol_type
        self.type_info = type_info
        self.metadata = metadata or {}
        self.is_property = is_property
        self.is_global = is_global

class SymbolTable:
    def __init__(self, parent: Optional['SymbolTable'] = None):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, name: str, symbol: Symbol):
        self.symbols[name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def is_local(self, name: str) -> bool:
        return name in self.symbols
