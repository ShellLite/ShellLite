from typing import Dict, List, Union

from ..ast_nodes import *
from .base_visitor import BaseTransformer


class Optimizer(BaseTransformer):
    def optimize(self, ast_or_map: Union[List[Node], Dict[str, List[Node]]]) -> Union[List[Node], Dict[str, List[Node]]]:
        if isinstance(ast_or_map, dict):
            return {path: [self.visit(stmt) for stmt in ast] for path, ast in ast_or_map.items()}
        return [self.visit(stmt) for stmt in ast_or_map]

    def visit_BinOp(self, node: BinOp) -> Node:
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(left, Number) and isinstance(right, Number):
            if node.op == "+":
                return Number(left.value + right.value)
            if node.op == "-":
                return Number(left.value - right.value)
            if node.op == "*":
                return Number(left.value * right.value)
            if node.op == "/" and right.value != 0:
                return Number(left.value / right.value)

        from dataclasses import replace

        return replace(node, left=left, right=right)

    def visit_UnaryOp(self, node: UnaryOp) -> Node:
        right = self.visit(node.right)
        if node.op == "-" and isinstance(right, Number):
            return Number(-right.value)
        from dataclasses import replace

        return replace(node, right=right)
