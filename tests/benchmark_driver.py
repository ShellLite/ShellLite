import os
import subprocess
import time

SHL_CMD = ["python", "shell_lite/main.py"]
def run_benchmark():
    print("Generating LLVM IR...")
    subprocess.run(SHL_CMD + ["llvm", "tests/runtime_benchmark.shl"], check=True)
    print("Compiling with Clang...")
    subprocess.run(["clang", "tests/runtime_benchmark.ll", "-o", "tests/runtime_benchmark.exe", "-O3"], check=True)
    print("\n[Running Native Executable...]")
    start = time.perf_counter()
    subprocess.run(["tests/runtime_benchmark.exe"], check=True)
    native_time = time.perf_counter() - start
    print(f"Native Time: {native_time:.4f}s")
    print("\n[Running Interpreter (GBP)...]")
    env = os.environ.copy()
    env["USE_GBP"] = "1"
    start = time.perf_counter()
    subprocess.run(SHL_CMD + ["run", "tests/runtime_benchmark.shl"], env=env, check=True)
    interp_time = time.perf_counter() - start
    print(f"Interpreter Time: {interp_time:.4f}s")
    print("\n[Running Python Equivalent...]")
    py_code = """
i = 0
sum = 0
count = 100000000
while i < count:
    sum = sum + 1
    i = i + 1
print("Done")
print(sum)
"""
    start = time.perf_counter()
    exec(py_code)
    py_time = time.perf_counter() - start
    print(f"Python Time: {py_time:.4f}s")
    print("\n" + "="*30)
    print(f"Native Speedup vs Interpreter: {interp_time/native_time:.2f}x")
    print(f"Native Speedup vs Python:      {py_time/native_time:.2f}x")
    print("="*30)
if __name__ == "__main__":
    run_benchmark()