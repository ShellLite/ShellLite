import sys
import traceback

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("\n--- Checking llvmlite ---")
try:
    import llvmlite
    print(f"llvmlite version: {getattr(llvmlite, '__version__', 'unknown')}")
    print(f"llvmlite file: {getattr(llvmlite, '__file__', 'unknown')}")
    import llvmlite.binding as llvm
    print("llvmlite.binding imported successfully")
    try:
        llvm.initialize()
        print("llvm.initialize() successful")
        llvm.initialize_native_target()
        print("llvm.initialize_native_target() successful")
        llvm.initialize_native_asmprinter()
        print("llvm.initialize_native_asmprinter() successful")
    except Exception as e:
        print(f"LLVM Initialization failed: {e}")
        traceback.print_exc()
except ImportError as e:
    print(f"llvmlite import failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()