from llvmlite import ir  # type: ignore


class TypeResolver:
    def __init__(self, builder, int_type):
        self.builder = builder
        self.int_type = int_type

    def coerce_types(self, left, right):
        if left.type != right.type:
            if isinstance(left.type, ir.DoubleType) and isinstance(
                right.type, ir.IntType
            ):
                right = self.builder.sitofp(right, ir.DoubleType())
            elif isinstance(right.type, ir.DoubleType) and isinstance(
                left.type, ir.IntType
            ):
                left = self.builder.sitofp(left, ir.DoubleType())
            elif isinstance(left.type, ir.PointerType):
                left = self.builder.ptrtoint(left, self.int_type)
            elif isinstance(right.type, ir.PointerType):
                right = self.builder.ptrtoint(right, self.int_type)

            if left.type != right.type:
                if left.type == ir.IntType(1):  # Boolean
                    left = self.builder.zext(left, self.int_type)
                if right.type == ir.IntType(1):
                    right = self.builder.zext(right, self.int_type)

                if isinstance(left.type, ir.IntType) and isinstance(
                    right.type, ir.IntType
                ):
                    if left.type.width < right.type.width:
                        left = self.builder.zext(left, right.type)
                    elif left.type.width > right.type.width:
                        right = self.builder.zext(right, left.type)
        return left, right
