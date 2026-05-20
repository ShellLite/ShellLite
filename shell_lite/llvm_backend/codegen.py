
import logging
from typing import Any, Optional

from llvmlite import ir

from ..ast_nodes import *
from ..lexer import Lexer
from ..parser import Parser
from .errors import CompilerError, UnsupportedNodeError

logger = logging.getLogger("shelllite.llvm")


class LLVMCompiler:
    def __init__(self, base_path=None, filename="main"):
        """Initialize the LLVM module and declare external C runtime functions."""
        self.base_path = base_path
        self.imported_files = set()
        self.current_class = None
        self.current_method = None
        self.module = ir.Module(name="shell_lite_module")
        import llvmlite.binding as llvm_binding
        llvm_binding.initialize_native_target()
        llvm_binding.initialize_native_asmprinter()
        
        default_triple = llvm_binding.get_default_triple()
        self.module.triple = default_triple
        
        target = llvm_binding.Target.from_triple(default_triple)
        target_machine = target.create_target_machine()
        self.module.data_layout = str(target_machine.target_data)
        self.int_type = ir.IntType(64)  # 64-bit integer for pointer-width compatibility
        self.char_ptr = ir.IntType(8).as_pointer()
        vptr = ir.IntType(8).as_pointer()
        
        prnt_ty = ir.FunctionType(ir.IntType(32), [vptr], var_arg=True)
        self.printf = ir.Function(self.module, prnt_ty, name="printf")
        
        m_ty = ir.FunctionType(vptr, [ir.IntType(64)])
        self.malloc = ir.Function(self.module, m_ty, name="malloc")
        
        
        dict_get_ty = ir.FunctionType(vptr, [vptr, vptr])
        self.dict_get = ir.Function(self.module, dict_get_ty, name="dict_get")
        
        dict_set_ty = ir.FunctionType(ir.VoidType(), [vptr, vptr, vptr])
        self.dict_set = ir.Function(self.module, dict_set_ty, name="dict_set")

        
        dict_get_ty = ir.FunctionType(vptr, [vptr, vptr])
        self.dict_get = ir.Function(self.module, dict_get_ty, name="dict_get")
        
        dict_set_ty = ir.FunctionType(ir.VoidType(), [vptr, vptr, vptr])
        self.dict_set = ir.Function(self.module, dict_set_ty, name="dict_set")

        f_ty = ir.FunctionType(ir.VoidType(), [vptr])
        self.free = ir.Function(self.module, f_ty, name="free")
        
        slen_ty = ir.FunctionType(self.int_type, [vptr])
        self.strlen = ir.Function(self.module, slen_ty, name="strlen")
        
        scpy_ty = ir.FunctionType(vptr, [vptr, vptr])
        self.strcpy = ir.Function(self.module, scpy_ty, name="strcpy")
        
        scat_ty = ir.FunctionType(vptr, [vptr, vptr])
        self.strcat = ir.Function(self.module, scat_ty, name="strcat")
        
        fop_ty = ir.FunctionType(vptr, [vptr, vptr])
        self.fopen = ir.Function(self.module, fop_ty, name="fopen")
        
        fcl_ty = ir.FunctionType(self.int_type, [vptr])
        self.fclose = ir.Function(self.module, fcl_ty, name="fclose")
        
        fwr_ty = ir.FunctionType(
            self.int_type, [vptr, self.int_type, self.int_type, vptr]
        )
        self.fwrite = ir.Function(self.module, fwr_ty, name="fwrite")
        
        frd_ty = ir.FunctionType(
            self.int_type, [vptr, self.int_type, self.int_type, vptr]
        )
        self.fread = ir.Function(self.module, frd_ty, name="fread")
        
        fgt_ty = ir.FunctionType(vptr, [vptr, self.int_type, vptr])
        self.fgets = ir.Function(self.module, fgt_ty, name="fgets")
        
        fsk_ty = ir.FunctionType(self.int_type, [vptr, self.int_type, self.int_type])
        self.fseek = ir.Function(self.module, fsk_ty, name="fseek")
        
        ftl_ty = ir.FunctionType(self.int_type, [vptr])
        self.ftell = ir.Function(self.module, ftl_ty, name="ftell")
        
        rwd_ty = ir.FunctionType(ir.VoidType(), [vptr])
        self.rewind = ir.Function(self.module, rwd_ty, name="rewind")
        
        gst_ty = ir.FunctionType(vptr, [])
        self.get_stdin = ir.Function(
            self.module, gst_ty, name="getchar"
        )
        
        # realloc: i8* realloc(i8*, i32)
        real_ty = ir.FunctionType(vptr, [vptr, self.int_type])
        self.realloc = ir.Function(self.module, real_ty, name="realloc")
        
        sys_ty = ir.FunctionType(self.int_type, [vptr])
        self.system = ir.Function(self.module, sys_ty, name="system")
        
        self.filename = filename.replace(".", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
        init_func_name = f"__init_{self.filename}"
        
        func_type = ir.FunctionType(self.int_type, [], var_arg=False)
        self.main_func = ir.Function(self.module, func_type, name=init_func_name)
        block = self.main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        
        self.str_constants = {}
        self.struct_registry = {}
        self.classes = {}
        self.scanned_files = set()
        
        fmt_ptr = self.bh.get_string_constant(f"DEBUG: Init {init_func_name}")
        
        try:
            puts_func = self.module.get_global("puts")
        except KeyError:
            puts_ty = ir.FunctionType(ir.IntType(32), [self.char_ptr])
            puts_func = ir.Function(self.module, puts_ty, name="puts")
        self.builder.call(puts_func, [fmt_ptr])
        self.scopes = [{}]
        self.loop_stack = []
    def _get_scope(self):
        return self.scopes[-1]
    
    def _resolve_path(self, path):
        import os
        path = path.strip('"\'')
        if not path.endswith('.shl'):
            path += '.shl'
        if self.base_path and not os.path.isabs(path):
            resolved_path = os.path.join(self.base_path, path)
        else:
            resolved_path = path
        return resolved_path
    def compile(self, statements, is_entry_point=False):
        """Visit all statements and generate the final LLVM IR module."""
        self._scan_declarations(statements)

        for stmt in statements:
            self.visit(stmt)
        self.builder.ret(ir.Constant(self.int_type, 0))
        
        if is_entry_point:
            main_func_type = ir.FunctionType(self.int_type, [])
            real_main = ir.Function(self.module, main_func_type, name="main")
            block = real_main.append_basic_block('entry')
            builder = ir.IRBuilder(block)
            builder.call(self.main_func, [])
            builder.ret(ir.Constant(self.int_type, 0))
            
        return self.module

    def _scan_declarations(self, statements):
        for stmt in statements:
            if isinstance(stmt, FunctionDef):
                self._declare_function(stmt)
            elif isinstance(stmt, ClassDef):
                self.classes[stmt.name] = stmt
                # Register struct layout
                prop_map = {p[0] if isinstance(p, tuple) else p: i for i, p in enumerate(stmt.properties)}
                self.struct_registry[stmt.name] = {'properties': prop_map, 'size': len(stmt.properties)}
                # Declare methods
                old_class = self.current_class
                self.current_class = stmt
                for method in stmt.methods:
                    self._declare_function(method)
                self.current_class = old_class
            elif isinstance(stmt, Assign):
                if stmt.name not in self.module.globals:
                    g_var = ir.GlobalVariable(self.module, self.int_type, name=stmt.name)
                    g_var.linkage = 'common'
                    g_var.initializer = ir.Constant(self.int_type, 0)
            elif isinstance(stmt, Import):
                if stmt.path.strip('"\'') == "time":
                     scope = self.scopes[0]
                     if "time" not in scope:
                         # Use global variable for module stubs to ensure cross-function visibility
                         ptr = ir.GlobalVariable(self.module, self.char_ptr, name="time_mod_ptr")
                         ptr.linkage = 'common'
                         ptr.initializer = ir.Constant(self.char_ptr, None)
                         ptr.sl_type = "time"
                         scope["time"] = ptr
                     continue
                
                # Recursive scan for imports
                import os
                resolved_path = self._resolve_path(stmt.path)
                
                if os.path.exists(resolved_path) and resolved_path not in self.scanned_files:
                    self.scanned_files.add(resolved_path)
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                        lexer = Lexer(code)
                        tokens = lexer.tokenize()
                        parser = Parser(tokens)
                        imported_stmts = parser.parse()
                        self._scan_declarations(imported_stmts)
                    except Exception as e:
                        logger.warning("Scan failed for %s: %s", resolved_path, e)

    def _declare_function(self, node: FunctionDef):
        func_name = node.name
        if self.current_class:
            func_name = f"{self.current_class.name}_{node.name}"
            
        if func_name in self.module.globals:
            return self.module.globals[func_name]
            
        func_args = node.args
        if self.current_class:
            func_args = [('self', None, self.current_class.name)] + list(node.args)

        arg_types = [self.int_type] * len(func_args)
        if self.current_class:
            arg_types[0] = self.char_ptr

        fnty = ir.FunctionType(self.int_type, arg_types)
        return ir.Function(self.module, fnty, name=func_name)
    def visit(self, node: ASTNode) -> Optional[ir.Value]:
        """Dispatch to the appropriate visitor method for the given AST node."""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    def visit_ForIn(self, node: ForIn) -> Optional[ir.Value]:
        """Generate LLVM loop for iterating over a range."""
        if not (isinstance(node.iterable, Call) and node.iterable.name == 'range'):
            raise UnsupportedNodeError(
                f"ForIn on non-range iterable '{type(node.iterable).__name__}' is not supported"
            )

        cond_bb = self.builder.append_basic_block(name="for.cond")
        body_bb = self.builder.append_basic_block(name="for.body")
        after_bb = self.builder.append_basic_block(name="for.after")
        
        scope = self._get_scope()
        ptr = self.builder.alloca(self.int_type, name=node.var_name)
        scope[node.var_name] = ptr
        
        if len(node.iterable.args) == 2:
            start_val = self.visit(node.iterable.args[0])
            end_val = self.visit(node.iterable.args[1])
        else:
            start_val = ir.Constant(self.int_type, 0)
            end_val = self.visit(node.iterable.args[0])
        
        self.builder.store(start_val, ptr)
        self.builder.branch(cond_bb)
        
        self.builder.position_at_end(cond_bb)
        curr_val = self.builder.load(ptr)
        cond = self.builder.icmp_signed('<', curr_val, end_val, name="forcond")
        self.builder.cbranch(cond, body_bb, after_bb)
        
        self.builder.position_at_end(body_bb)
        self.loop_stack.append((cond_bb, after_bb))
        for stmt in node.body:
            self.visit(stmt)
        self.loop_stack.pop()
        
        if not self.builder.block.is_terminated:
            new_val = self.builder.add(curr_val, ir.Constant(self.int_type, 1))
            self.builder.store(new_val, ptr)
            self.builder.branch(cond_bb)
            
        self.builder.position_at_end(after_bb)
        return None



    def generic_visit(self, node):
        raise UnsupportedNodeError(
            f"LLVM backend does not support '{type(node).__name__}'"
        )
    def visit_Number(self, node: Number) -> Optional[ir.Value]:
        """Generate an integer or float constant."""
        if isinstance(node.value, float):
            return ir.Constant(ir.DoubleType(), node.value)
        return ir.Constant(self.int_type, int(node.value))

    def visit_Boolean(self, node: Boolean) -> Optional[ir.Value]:
        return ir.Constant(ir.IntType(1), 1 if node.value else 0)

    def visit_String(self, node: String) -> Optional[ir.Value]:
        return self.bh.get_string_constant(node.value)
    def visit_BinOp(self, node: BinOp) -> Optional[ir.Value]:
        left = self.visit(node.left)
        op = node.op
        
        if op == '.':
             if isinstance(node.right, Call):
                 method_name = node.right.name
                 sl_type = getattr(left, 'sl_type', None)
                 if sl_type == "time" and method_name == "time":
                      return ir.Constant(ir.DoubleType(), 0.0)
                 if sl_type and sl_type in self.classes:
                     target_func_name = f"{sl_type}_{method_name}"
                     if target_func_name in self.module.globals:
                         func = self.module.globals[target_func_name]
                         call_left = left
                         if call_left.type != self.char_ptr:
                             call_left = self.builder.inttoptr(call_left, self.char_ptr)
                         args = [call_left] + [self.visit(a) for a in node.right.args]
                         final_args = []
                         for i, arg in enumerate(args):
                             if i > 0 and arg.type != self.int_type:
                                 if isinstance(arg.type, ir.PointerType):
                                     arg = self.builder.ptrtoint(arg, self.int_type)
                                 else:
                                     arg = self.builder.zext(arg, self.int_type)
                             final_args.append(arg)
                         return self.builder.call(func, final_args, name="methcall")
                     else:
                         raise CompilerError(f"Method {target_func_name} not found in module")
                 else:
                      raise CompilerError(f"Could not resolve method {method_name} on {left.type} (no sl_type)")
             elif isinstance(node.right, VarAccess):
                 prop_name = node.right.name
                 sl_type = getattr(left, 'sl_type', None)
                 if sl_type and sl_type in self.classes:
                     cls = self.classes[sl_type]
                     prop_idx = -1
                     for i, (name, _) in enumerate(cls.properties):
                         if name == prop_name:
                             prop_idx = i
                             break
                     if prop_idx != -1:
                         ptr_i32 = self.builder.bitcast(left, self.int_type.as_pointer())
                         ptr = self.builder.gep(ptr_i32, [ir.Constant(self.int_type, prop_idx)], name=f"prop_{prop_name}")
                         val = self.builder.load(ptr, name=prop_name)
                         if val.type != self.int_type:
                             val = self.builder.zext(val, self.int_type)
                         return val
                 raise CompilerError(f"Could not resolve property {prop_name} on {left.type}")

        right = self.visit(node.right)
        
        # Coerce types via TypeResolver
        from .type_resolver import TypeResolver
        tr = TypeResolver(self.builder, self.int_type)
        left, right = tr.coerce_types(left, right)

        if op == '+':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fadd(left, right, name="faddtmp")
            is_str_op = False
            if left.type == self.char_ptr or right.type == self.char_ptr:
                is_str_op = True
            if is_str_op:
                if left.type == self.int_type:
                    left = self.builder.inttoptr(left, self.char_ptr, name="cast_l")
                if right.type == self.int_type:
                    right = self.builder.inttoptr(right, self.char_ptr, name="cast_r")
            if is_str_op:
                 len1 = self.builder.call(self.strlen, [left], name="len1")
                 len2 = self.builder.call(self.strlen, [right], name="len2")
                 t_len = self.builder.add(len1, len2, name="total_len")
                 a_len = self.builder.add(
                     t_len, ir.Constant(self.int_type, 1), name="alloc_len"
                 )
                 n_str = self.builder.call(self.malloc, [a_len], name="new_str")
                 self.builder.call(self.strcpy, [n_str, left])
                 self.builder.call(self.strcat, [n_str, right])
                 return n_str
            return self.builder.add(left, right, name="addtmp")
        elif op == '-':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fsub(left, right, name="fsubtmp")
            return self.builder.sub(left, right, name="subtmp")
        elif op == '*':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fmul(left, right, name="fmultmp")
            return self.builder.mul(left, right, name="multmp")
        elif op == '/':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fdiv(left, right, name="fdivtmp")
            return self.builder.sdiv(left, right, name="divtmp")
        elif op == '==' or op == 'is':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('==', left, right, name="feqtmp")
            return self.builder.icmp_signed('==', left, right, name="eqtmp")
        elif op == '!=' or op == 'is not':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('!=', left, right, name="fnetmp")
            return self.builder.icmp_signed('!=', left, right, name="netmp")
        elif op == '<':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('<', left, right, name="flttmp")
            return self.builder.icmp_signed('<', left, right, name="lttmp")
        elif op == '<=':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('<=', left, right, name="fletmp")
            return self.builder.icmp_signed('<=', left, right, name="letmp")
        elif op == '>':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('>', left, right, name="fgttmp")
            return self.builder.icmp_signed('>', left, right, name="gttmp")
        elif op == '>=':
            if isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('>=', left, right, name="fgetmp")
            return self.builder.icmp_signed('>=', left, right, name="getmp")
        elif op == '%':
            # Handle potential division by zero if divisor is 0 (e.g. 2^64 truncated to 64-bit 0)
            if isinstance(right, ir.Constant) and right.constant == 0:
                return left
            return self.builder.srem(left, right, name="modtmp")
        elif op == 'and':
            return self.builder.and_(left, right, name="andtmp")
        elif op == 'or':
            return self.builder.or_(left, right, name="ortmp")
        elif op == 'xor':
            return self.builder.xor(left, right, name="xortmp")
        else:
            raise CompilerError(f"Unknown operator: {op}")
    def visit_If(self, node: If) -> Optional[ir.Value]:
        cond_val = self.visit(node.condition)
        if cond_val.type != ir.IntType(1):
             cond_val = self.builder.icmp_signed(
                 '!=', cond_val, ir.Constant(self.int_type, 0), name="ifcond"
             )
        then_bb = self.builder.append_basic_block(name="then")
        else_bb = self.builder.append_basic_block(name="else")
        merge_bb = self.builder.append_basic_block(name="ifcont")
        self.builder.cbranch(cond_val, then_bb, else_bb)
        self.builder.position_at_end(then_bb)
        for stmt in node.body:
            self.visit(stmt)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_bb)
        self.builder.position_at_end(else_bb)
        if node.else_body:
            for stmt in node.else_body:
                self.visit(stmt)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_bb)
        self.builder.position_at_end(merge_bb)
    def visit_While(self, node: While) -> Optional[ir.Value]:
        cond_bb = self.builder.append_basic_block(name="loop.cond")
        body_bb = self.builder.append_basic_block(name="loop.body")
        after_bb = self.builder.append_basic_block(name="loop.after")
        self.loop_stack.append((cond_bb, after_bb))
        self.builder.branch(cond_bb)
        self.builder.position_at_end(cond_bb)
        cond_val = self.visit(node.condition)
        if cond_val.type != ir.IntType(1):
             cond_val = self.builder.icmp_signed(
                 '!=', cond_val, ir.Constant(self.int_type, 0), name="loopcond"
             )
        self.builder.cbranch(cond_val, body_bb, after_bb)
        self.builder.position_at_end(body_bb)
        for stmt in node.body:
            self.visit(stmt)
        self.builder.branch(cond_bb)
        self.builder.position_at_end(after_bb)
        self.loop_stack.pop()
    def visit_Repeat(self, node: Repeat) -> Optional[ir.Value]:
        count_val = self.visit(node.count)
        import random
        uid = random.randint(0, 10000)
        i_ptr = self.bh.alloca(f"_loop_i_{uid}")
        self.builder.store(ir.Constant(self.int_type, 0), i_ptr)
        cond_bb = self.builder.append_basic_block(name="repeat.cond")
        body_bb = self.builder.append_basic_block(name="repeat.body")
        after_bb = self.builder.append_basic_block(name="repeat.after")
        self.loop_stack.append((cond_bb, after_bb))
        self.builder.branch(cond_bb)
        self.builder.position_at_end(cond_bb)
        curr_i = self.builder.load(i_ptr, name="i_load")
        cmp = self.builder.icmp_signed('<', curr_i, count_val, name="loopcheck")
        self.builder.cbranch(cmp, body_bb, after_bb)
        self.builder.position_at_end(body_bb)
        for stmt in node.body:
            self.visit(stmt)
        curr_i_Body = self.builder.load(i_ptr)
        next_i = self.builder.add(curr_i_Body, ir.Constant(self.int_type, 1), name="inc_i")
        self.builder.store(next_i, i_ptr)
        self.builder.branch(cond_bb)
        self.builder.position_at_end(after_bb)
        self.loop_stack.pop()
    def visit_ClassDef(self, node: ClassDef) -> Optional[ir.Value]:
        # Passing scan_declarations already registered this, but we re-set context for bodies
        old_class = self.current_class
        self.current_class = node
        try:
            for method in node.methods:
                self.visit(method)
        finally:
            self.current_class = old_class
        return None

    def visit_Instantiation(self, node: Instantiation) -> Optional[ir.Value]:
        if node.class_name not in self.struct_registry:
            raise Exception(f"Unknown structure: {node.class_name}")
        
        struct_info = self.struct_registry[node.class_name]
        size = struct_info['size']
        total_bytes = ir.Constant(self.int_type, (size or 1) * 4)
        name = node.var_name if node.var_name else f"new_{node.class_name}"
        ptr = self.builder.call(self.malloc, [total_bytes], name=name)
        
        if node.var_name:
            scope = self._get_scope()
            scope[node.var_name] = ptr
        # Attach type info to the pointer object for property resolution
        ptr.sl_type = node.class_name
        return ptr

    def visit_PropertyAccess(self, node: PropertyAccess) -> Optional[ir.Value]:
        scope = self._get_scope()
        if node.instance_name not in scope:
            if node.instance_name == 'self':
                instance_ptr = self.builder.load(scope['self'])
            raise Exception(f"Instance '{node.instance_name}' not defined")
        
        instance_ptr = self.builder.load(scope[node.instance_name])
        class_name = getattr(scope[node.instance_name], 'sl_type', None)
        
        if not class_name:
             # Heuristic fallback
             for name, info in self.struct_registry.items():
                 if node.property_name in info['properties']:
                     class_name = name
                     break
        
        if not class_name:
            raise Exception(f"Could not resolve property '{node.property_name}'")
            
        prop_idx = self.struct_registry[class_name]['properties'][node.property_name]
        offset = ir.Constant(self.int_type, prop_idx)
        ptr = self.builder.gep(instance_ptr, [offset], name="propptr")
        ptr = self.builder.bitcast(ptr, self.int_type.as_pointer())
        return self.builder.load(ptr, name="propval")

    def visit_PropertyAssign(self, node: PropertyAssign) -> Optional[ir.Value]:
        value = self.visit(node.value)
        scope = self._get_scope()
        if node.instance_name not in scope:
            raise Exception(f"Instance '{node.instance_name}' not defined")
            
        instance_ptr = self.builder.load(scope[node.instance_name])
        class_name = getattr(scope[node.instance_name], 'sl_type', None)
        if not class_name:
             for name, info in self.struct_registry.items():
                 if node.property_name in info['properties']:
                     class_name = name
                     break
        
        prop_idx = self.struct_registry[class_name]['properties'][node.property_name]
        offset = ir.Constant(self.int_type, prop_idx)
        ptr = self.builder.gep(instance_ptr, [offset], name="propptr")
        ptr = self.builder.bitcast(ptr, self.int_type.as_pointer())
        self.builder.store(value, ptr)
        return value

    def visit_FunctionDef(self, node: FunctionDef) -> Optional[ir.Value]:
        func = self._declare_function(node)
        func.linkage = 'weak'
        
        func_args = node.args
        if self.current_class:
            func_args = [('self', None, self.current_class.name)] + list(node.args)

        block = func.append_basic_block(name="entry")
        old_builder = self.builder
        self.builder = ir.IRBuilder(block)
        
        self.scopes.append({})
        for i, (arg_name, default, type_hint) in enumerate(func_args):
            arg_ptr = self.builder.alloca(func.args[i].type, name=arg_name)
            self.builder.store(func.args[i], arg_ptr)
            self._get_scope()[arg_name] = arg_ptr
            if arg_name == 'self' and self.current_class:
                arg_ptr.sl_type = self.current_class.name
                
        for stmt in node.body:
            self.visit(stmt)
            
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(self.int_type, 0))
            
        self.scopes.pop()
        self.builder = old_builder
    def visit_Return(self, node: Return) -> Optional[ir.Value]:
        val = self.visit(node.value)
        if val.type == self.char_ptr:
             val = self.builder.ptrtoint(val, self.int_type)
        elif val.type == ir.IntType(1):
             val = self.builder.zext(val, self.int_type)
        self.builder.ret(val)
    def visit_Call(self, node: Call) -> Optional[ir.Value]:
        # Handle built in funcs
        if node.name == 'xor':
            return self.builder.xor(self.visit(node.args[0]), self.visit(node.args[1]), name="xortmp")
        elif node.name == 'abs':
            val = self.visit(node.args[0])
            if isinstance(val.type, ir.DoubleType):
                cond = self.builder.fcmp_ordered('<', val, ir.Constant(ir.DoubleType(), 0.0), name="abs_cond")
                neg_val = self.builder.fsub(ir.Constant(ir.DoubleType(), 0.0), val, name="abs_neg")
                return self.builder.select(cond, neg_val, val, name="abs_res")
            else:
                if val.type != self.int_type:
                    val = self.builder.zext(val, self.int_type)
                cond = self.builder.icmp_signed('<', val, ir.Constant(self.int_type, 0), name="abs_cond")
                neg_val = self.builder.sub(ir.Constant(self.int_type, 0), val, name="abs_neg")
                return self.builder.select(cond, neg_val, val, name="abs_res")
        elif node.name == 'int' or node.name == 'float' or node.name == 'str':
            return self.visit(node.args[0])
        elif node.name == 'char':
             val = self.visit(node.args[0])
             if val.type != self.int_type:
                 if isinstance(val.type, ir.PointerType):
                     val = self.builder.ptrtoint(val, self.int_type)
                 else:
                     val = self.builder.zext(val, self.int_type)
             buf = self.builder.call(self.malloc, [ir.Constant(self.int_type, 2)], name="char_buf")
             val_i8 = self.builder.trunc(val, ir.IntType(8))
             self.builder.store(val_i8, buf)
             null_ptr = self.builder.gep(buf, [ir.Constant(self.int_type, 1)])
             self.builder.store(ir.Constant(ir.IntType(8), 0), null_ptr)
             return buf
        elif node.name == 'len':
            arg_val = self.visit(node.args[0])
            if arg_val.type == self.char_ptr:
                return self.builder.call(self.strlen, [arg_val], name="len_res")
            else:
                return ir.Constant(self.int_type, 0)

        elif node.name == 'print' or node.name == 'say' or node.name == 'show':
            val = self.visit(node.args[0])
            if val.type == self.int_type:
                 fmt = self.bh.get_string_constant("%d\n")
            else:
                 fmt = self.bh.get_string_constant("%s\n")
            return self.builder.call(self.printf, [fmt, val])
        elif node.name == 'range':
            size = self.visit(node.args[0])
            # Use 8 bytes for 64-bit pointers/ints
            total_bytes = self.builder.mul(size, ir.Constant(self.int_type, 8))
            buffer = self.builder.call(self.malloc, [total_bytes], name="range_buf")
            return buffer

        elif node.name == 'add':
            if len(node.args) >= 2:
                 val = self.visit(node.args[0])
                 obj = self.visit(node.args[1])
                 logger.info("Mapping 'add' to list operation")
                 return ir.Constant(self.int_type, 0)
        
        if node.name in self.module.globals:
            func = self.module.globals[node.name]
        elif node.name in self.classes:
            return self.visit_Instantiation(Instantiation(var_name=None, class_name=node.name, args=node.args))
        elif node.name == 'read':
             if len(node.args) > 0:
                 return self.visit_FileRead(FileRead(node.args[0]))
             else:
                 return ir.Constant(self.int_type, 0)
        else:
             raise Exception(f"Function {node.name} not found")
        
        args = []
        for i, a in enumerate(node.args):
            val = self.visit(a)
            target_type = func.args[i].type
            if val.type != target_type:
                 if val.type == self.int_type and target_type == self.char_ptr:
                      val = self.builder.inttoptr(val, self.char_ptr)
                 elif val.type == self.char_ptr and target_type == self.int_type:
                      val = self.builder.ptrtoint(val, self.int_type)
            args.append(val)
        return self.builder.call(func, args, name="calltmp")
    def visit_IndexAccess(self, node: IndexAccess) -> Optional[ir.Value]:
        obj_ptr = self.visit(node.obj)
        if isinstance(obj_ptr, ir.Constant) and obj_ptr.type == self.char_ptr and obj_ptr.constant is None:
             return self.builder.call(self.dict_get, [obj_ptr, self.visit(node.index)]) 
        
        if obj_ptr.type == self.int_type:
             obj_ptr = self.builder.inttoptr(obj_ptr, self.char_ptr)
             
        index_val = self.visit(node.index)
        if index_val.type != self.int_type:
             if isinstance(index_val.type, ir.PointerType):
                 index_val = self.builder.ptrtoint(index_val, self.int_type)
             elif index_val.type.width > 32:
                 index_val = self.builder.trunc(index_val, self.int_type)
             elif index_val.type.width < 32:
                 index_val = self.builder.zext(index_val, self.int_type)

        ptr_i32 = self.builder.bitcast(obj_ptr, self.int_type.as_pointer())
        ptr = self.builder.gep(ptr_i32, [index_val], name="idxptr")
        return self.builder.load(ptr, name="idxval")

    def visit_IndexAssign(self, node: IndexAssign) -> Optional[ir.Value]:
        obj_ptr = self.visit(node.obj)
        if isinstance(obj_ptr, ir.Constant) and obj_ptr.type == self.char_ptr and obj_ptr.constant is None:
             self.builder.call(self.dict_set, [obj_ptr, self.visit(node.index), self.visit(node.value)]) 
             return self.visit(node.value)
        
        if obj_ptr.type == self.int_type:
             obj_ptr = self.builder.inttoptr(obj_ptr, self.char_ptr)
             
        index_val = self.visit(node.index)
        if index_val.type != self.int_type:
             if isinstance(index_val.type, ir.PointerType):
                 index_val = self.builder.ptrtoint(index_val, self.int_type)
             elif index_val.type.width > 32:
                 index_val = self.builder.trunc(index_val, self.int_type)
             elif index_val.type.width < 32:
                 index_val = self.builder.zext(index_val, self.int_type)
                 
        value = self.visit(node.value)
        if value.type != self.int_type:
             if isinstance(value.type, ir.IntType) and value.type.width < 32:
                 value = self.builder.zext(value, self.int_type)
             elif isinstance(value.type, ir.PointerType):
                 value = self.builder.ptrtoint(value, self.int_type)
             elif isinstance(value.type, ir.IntType) and value.type.width > 32:
                 value = self.builder.trunc(value, self.int_type)
             elif isinstance(value.type, ir.DoubleType):
                 value = self.builder.fptosi(value, self.int_type)

        ptr_i32 = self.builder.bitcast(obj_ptr, self.int_type.as_pointer())
        ptr = self.builder.gep(ptr_i32, [index_val], name="idxptr")
        self.builder.store(value, ptr)
        return value

    def visit_ListVal(self, node: ListVal) -> Optional[ir.Value]:
        size = len(node.elements)
        # Allocate at least 128 elements (1024 bytes) for empty/small lists to allow some growth
        capacity = max(size, 128)
        total_bytes = ir.Constant(self.int_type, capacity * 8)
        buffer = self.builder.call(self.malloc, [total_bytes], name="list_buf")
        for i, elem in enumerate(node.elements):
            val = self.visit(elem)
            if val.type != self.int_type:
                 if isinstance(val.type, ir.PointerType):
                     val = self.builder.ptrtoint(val, self.int_type)
                 elif val.type.width < 32:
                     val = self.builder.zext(val, self.int_type)
                 elif val.type.width > 32:
                     val = self.builder.trunc(val, self.int_type)
                     
            ptr = self.builder.gep(buffer, [ir.Constant(self.int_type, i)])
            ptr = self.builder.bitcast(ptr, self.int_type.as_pointer())
            self.builder.store(val, ptr)
        return buffer

    def visit_Dictionary(self, node: Dictionary) -> Optional[ir.Value]:
        return ir.Constant(self.char_ptr, None)
    def visit_Assign(self, node: Assign) -> Optional[ir.Value]:
        value = self.visit(node.value)
        scope = self._get_scope()

        # Global variable detection
        if len(self.scopes) == 1:
            if node.name not in self.module.globals:
                ptr = ir.GlobalVariable(self.module, value.type, name=node.name)
                ptr.linkage = 'common'
                ptr.initializer = ir.Constant(value.type, None)
                self.builder.store(value, ptr)
                return value
            else:
                ptr = self.module.globals[node.name]
                if ptr.linkage == 'external':
                     ptr.linkage = 'common'
                     ptr.initializer = ir.Constant(ptr.type.pointee, None)
        else:
            if node.name not in scope:
                ptr = self.bh.alloca(node.name, typ=value.type)
                scope[node.name] = ptr
            else:
                ptr = scope[node.name]
            
        if value.type != ptr.type.pointee:
             if value.type == ir.IntType(1) and ptr.type.pointee == self.int_type:
                 value = self.builder.zext(value, self.int_type)
             elif isinstance(value.type, ir.PointerType) and ptr.type.pointee == self.int_type:
                  value = self.builder.ptrtoint(value, self.int_type)
             elif value.type == self.int_type and isinstance(ptr.type.pointee, ir.PointerType):
                  value = self.builder.inttoptr(value, ptr.type.pointee)
             elif isinstance(value.type, ir.DoubleType) and ptr.type.pointee == self.int_type:
                  value = self.builder.fptosi(value, self.int_type)
             elif value.type == self.int_type and isinstance(ptr.type.pointee, ir.DoubleType):
                  value = self.builder.sitofp(value, ir.DoubleType())
        self.builder.store(value, ptr)
        return value
    def visit_MethodCall(self, node: MethodCall) -> Optional[ir.Value]:
        scope = self._get_scope()
        instance_ptr = None
        class_name = None
        
        # Determine instance and its type
        if node.instance_name in scope:
            instance_ptr = self.builder.load(scope[node.instance_name])
            class_name = getattr(scope[node.instance_name], 'sl_type', None)
        elif node.instance_name == 'self' and 'self' in scope:
            instance_ptr = self.builder.load(scope['self'])
            class_name = getattr(scope['self'], 'sl_type', None)

        full_method_name = f"{class_name}_{node.method_name}" if class_name else node.method_name
        
        if full_method_name in self.module.globals:
            func = self.module.globals[full_method_name]
        elif node.method_name in self.module.globals:
            func = self.module.globals[node.method_name]
        else:
            # Handle special list methods
            if node.method_name in ('push', 'append', 'pop', 'len'):
                 logger.info(f"List method {node.method_name} call detected")
                 return ir.Constant(self.int_type, 0)
            raise Exception(f"Method '{full_method_name}' not found")

        args = [instance_ptr] + [self.visit(a) for a in node.args]
        return self.builder.call(func, args, name="methcall")

    def visit_Import(self, node: Import) -> Optional[ir.Value]:
        if node.path.strip('"\'') == "time":
            return
            
        import os
        resolved_path = self._resolve_path(node.path)
        base = os.path.basename(resolved_path)
        mod_name = base.replace(".", "_")
        
        func_name = f"__init_{mod_name}"
        if func_name in self.module.globals:
             init_func = self.module.get_global(func_name)
        else:
             init_func_type = ir.FunctionType(self.int_type, [])
             init_func = ir.Function(self.module, init_func_type, name=func_name)
        self.builder.call(init_func, [])
        import os
        resolved_path = self._resolve_path(node.path)

        if node.path.strip('"\'') == "time":
             # Define virtual time module
             scope = self.scopes[0]
             if "time" not in scope:
                 if "time_mod_ptr" in self.module.globals:
                     ptr = self.module.get_global("time_mod_ptr")
                 else:
                     ptr = ir.GlobalVariable(self.module, self.char_ptr, name="time_mod_ptr")
                     ptr.linkage = 'internal'
                     ptr.initializer = ir.Constant(self.char_ptr, None)
                 ptr.sl_type = "time"
                 scope["time"] = ptr
             return

        if not os.path.exists(resolved_path):
             raise CompilerError(f"Could not find import at '{resolved_path}'")
             return
             
        if resolved_path in self.imported_files:
            return
        self.imported_files.add(resolved_path)

        with open(resolved_path, 'r', encoding='utf-8') as f:
            source = f.read()
            
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        statements = parser.parse()

        self._scan_declarations(statements)

    def visit_Execute(self, node: Execute) -> Optional[ir.Value]:
        cmd = self.visit(node.code)
        self.builder.call(self.system, [cmd])
        return ir.Constant(self.int_type, 0)
    def visit_Stop(self, node: Stop) -> Optional[ir.Value]:
        if not self.loop_stack:
            logger.error("stop used outside of loop")
            raise CompilerError("stop used outside of loop")
            return
        after_bb = self.loop_stack[-1][1]
        self.builder.branch(after_bb)
        dead_bb = self.builder.append_basic_block(name="dead")
        self.builder.position_at_end(dead_bb)
    def visit_Skip(self, node: Skip) -> Optional[ir.Value]:
        if not self.loop_stack:
            logger.error("skip used outside of loop")
            raise CompilerError("skip used outside of loop")
            return
        cond_bb = self.loop_stack[-1][0]
        self.builder.branch(cond_bb)
        dead_bb = self.builder.append_basic_block(name="dead")
        self.builder.position_at_end(dead_bb)

    def visit_FileWrite(self, node: FileWrite) -> Optional[ir.Value]:
        path = self.visit(node.path)
        content = self.visit(node.content)
        if content.type == self.int_type:
             content = self.builder.inttoptr(content, self.char_ptr)
        mode = self.bh.get_string_constant("w")
        fp = self.builder.call(self.fopen, [path, mode], name="fp")
        length = self.builder.call(self.strlen, [content])
        self.builder.call(
            self.fwrite, [content, ir.Constant(self.int_type, 1), length, fp]
        )
        self.builder.call(self.fclose, [fp])
        return ir.Constant(self.int_type, 0)
    def visit_FileRead(self, node: FileRead) -> Optional[ir.Value]:
        path = self.visit(node.path)
        mode = self.bh.get_string_constant("rb")
        fp = self.builder.call(self.fopen, [path, mode], name="fp")
        self.builder.call(
            self.fseek,
            [fp, ir.Constant(self.int_type, 0), ir.Constant(self.int_type, 2)]
        )
        size = self.builder.call(self.ftell, [fp], name="fsize")
        self.builder.call(self.rewind, [fp])
        a_size = self.builder.add(size, ir.Constant(self.int_type, 1))
        buffer = self.builder.call(self.malloc, [a_size], name="fbuf")
        self.builder.call(
            self.fread, [buffer, ir.Constant(self.int_type, 1), size, fp]
        )
        null_term_ptr = self.builder.gep(buffer, [size])
        self.builder.store(ir.Constant(ir.IntType(8), 0), null_term_ptr)
        self.builder.call(self.fclose, [fp])
        return buffer
    def visit_VarAccess(self, node: VarAccess) -> Optional[ir.Value]:
        for scope in reversed(self.scopes):
            if node.name in scope:
                ptr = scope[node.name]
                val = self.builder.load(ptr, name=node.name)
                if hasattr(ptr, 'sl_type'):
                     val.sl_type = ptr.sl_type
                return val
        
        if self.current_class and any(p[0] == node.name for p in self.current_class.properties):
            scope = self._get_scope()
            if 'self' in scope:
                self_ptr = self.builder.load(scope['self'], name="self_ptr")
                # Property lookup logic (same as visit_PropertyAccess)
                prop_idx = -1
                for i, (name, _) in enumerate(self.current_class.properties):
                    if name == node.name:
                        prop_idx = i
                        break
                if prop_idx != -1:
                    self_ptr_i32 = self.builder.bitcast(self_ptr, self.int_type.as_pointer())
                    ptr = self.builder.gep(self_ptr_i32, [ir.Constant(self.int_type, prop_idx)], name=f"prop_{node.name}")
                    val = self.builder.load(ptr, name=node.name)
                    if val.type != self.int_type:
                         if val.type.width < 32:
                             val = self.builder.zext(val, self.int_type)
                         elif val.type.width > 32:
                             val = self.builder.trunc(val, self.int_type)
                    return val
            
        if node.name in self.module.globals:
            return self.builder.load(self.module.globals[node.name], name=node.name)
        elif node.name == 'null' or node.name == 'None' or node.name == 'nil':
            return ir.Constant(self.char_ptr, None)
        elif node.name == 'yes':
            return ir.Constant(ir.IntType(1), 1)
        elif node.name == 'no':
            return ir.Constant(ir.IntType(1), 0)
        else:
            msg = f"Variable '{node.name}' not defined"
            raise Exception(msg)

    def visit_UnaryOp(self, node: UnaryOp) -> Optional[ir.Value]:
        right = self.visit(node.right)
        if node.op == 'not':
            if right.type == ir.IntType(1):
                 return self.builder.not_(right, name="nottmp")
            if right.type != self.int_type:
                 right = self.builder.zext(right, self.int_type)
            return self.builder.xor(right, ir.Constant(self.int_type, 1), name="nottmp")
        elif node.op == '-':
            return self.builder.neg(right, name="negtmp")
        return right
    

    def visit_Try(self, node: Try) -> Optional[ir.Value]:
        for stmt in node.try_body:
            self.visit(stmt)

    def visit_TryAlways(self, node: TryAlways) -> Optional[ir.Value]:
        for stmt in node.try_body:
            self.visit(stmt)
        for stmt in node.always_body:
            self.visit(stmt)
    def visit_Print(self, node: Print) -> Optional[ir.Value]:
        value = self.visit(node.expression)
        if value.type == self.char_ptr:
            fmt_str = self.bh.get_string_constant("%s\n")
            self.builder.call(self.printf, [fmt_str, value])
        else:
            fmt_str = self.bh.get_string_constant("%d\n")
            self.builder.call(self.printf, [fmt_str, value])
        return ir.Constant(ir.IntType(1), 1)