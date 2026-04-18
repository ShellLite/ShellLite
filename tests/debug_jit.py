
import llvmlite.binding as llvm


def debug():
    try:
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        print("LLVM Initialized.")
    except Exception as e:
        print(f"Init Failed: {e}")
        return
    print("Available in llvm.binding:")
    ops = [x for x in dir(llvm) if 'create' in x or 'jit' in x.lower() or 'engine' in x.lower()]
    print(ops)
    try:
        mod = llvm.parse_assembly('define i32 @answer() { ret i32 42 }')
        mod.verify()
        print("Module parsed.")
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        engine = None
        if hasattr(llvm, 'create_mcjit_compiler'):
            print("Attempting MCJIT...")
            try:
                engine = llvm.create_mcjit_compiler(mod, target_machine)
                print("MCJIT Created!")
            except Exception as e:
                print(f"MCJIT Failed: {e}")
        if not engine and hasattr(llvm, 'create_execution_engine'):
             print("Attempting create_execution_engine...")
             try:
                engine = llvm.create_execution_engine()
                engine.add_module(mod)
                print("ExecEngine Created!")
             except Exception as e:
                print(f"ExecEngine Failed: {e}")
        if engine:
            engine.finalize_object()
            print("Engine Finalized.")
            addr = engine.get_function_address("answer")
            print(f"Function Address: {addr}")
            import ctypes
            cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(addr)
            res = cfunc()
            print(f"Result: {res}")
    except Exception as e:
        print(f"Module/Engine Error: {e}")
if __name__ == "__main__":
    debug()