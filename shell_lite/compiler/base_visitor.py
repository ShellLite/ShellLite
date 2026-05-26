from typing import Any

from ..ast_nodes import Node


class BaseVisitor:
    def visit(self, node: Node) -> Any:
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node) -> Any:
        for _, value in vars(node).items():
            if isinstance(value, Node):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Node):
                        self.visit(item)
        return None


class BaseTransformer:
    def visit(self, node: Node) -> Any:
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node) -> Node:
        new_vars = {}
        changed = False
        for key, value in vars(node).items():
            if isinstance(value, Node):
                new_node = self.visit(value)
                new_vars[key] = new_node
                if new_node is not value:
                    changed = True
            elif isinstance(value, list):
                new_list = []
                list_changed = False
                for item in value:
                    if isinstance(item, Node):
                        new_item = self.visit(item)
                        new_list.append(new_item)
                        if new_item is not item:
                            list_changed = True
                    else:
                        new_list.append(item)
                new_vars[key] = new_list
                if list_changed:
                    changed = True
            else:
                new_vars[key] = value

        if changed:
            from dataclasses import fields, replace

            init_fields = {f.name for f in fields(node) if f.init}
            filtered_vars = {k: v for k, v in new_vars.items() if k in init_fields}
            new_node = replace(node, **filtered_vars)
            for f in fields(node):
                if not f.init:
                    setattr(new_node, f.name, getattr(node, f.name))
            return new_node
        return node
