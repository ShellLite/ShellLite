from llvmlite import ir  # type: ignore


class LLVMBuilderHelper:
    def __init__(self, module, builder, int_type, char_ptr, str_constants):
        self.module = module
        self.builder = builder
        self.int_type = int_type
        self.char_ptr = char_ptr
        self.str_constants = str_constants

    def alloca(self, name, typ=None):
        if typ is None:
            typ = self.int_type
        with self.builder.goto_entry_block():
            ptr = self.builder.alloca(typ, size=None, name=name)
        return ptr

    def get_string_constant(self, text):
        text += "\0"
        if text in self.str_constants:
            return self.str_constants[text]

        str_val = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(text)), bytearray(text.encode("utf8"))
        )
        str_ptr = ir.GlobalVariable(
            self.module, str_val.type, name=f".str_{len(self.str_constants)}"
        )
        str_ptr.linkage = "internal"
        str_ptr.global_constant = True
        str_ptr.initializer = str_val

        ptr = self.builder.bitcast(str_ptr, self.char_ptr)
        self.str_constants[text] = ptr
        return ptr
