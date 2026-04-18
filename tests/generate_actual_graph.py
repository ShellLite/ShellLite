import os
import subprocess
import sys
import time

import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from tests.run_jit import compile_and_run_jit
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__)))
    from run_jit import compile_and_run_jit
def run_benchmark():
    counts = [1000000, 10000000, 50000000, 100000000, 200000000]
    t_interp = []
    t_python = []
    t_llvm = []
    print("Running Massive Runtime Benchmark...")
    for n in counts:
        print(f"\n--- n = {n} ---")
        if n <= 100000:
            shl_code = f"i = 0\nwhile i < {n}:\n    i = i + 1\n"
            shl_file = f"tests/temp_{n}.shl"
            with open(shl_file, "w") as f: f.write(shl_code)
            env = os.environ.copy()
            env["USE_GBP"] = "1"
            start = time.perf_counter()
            try:
                subprocess.run(["python", "shell_lite/main.py", "run", shl_file], env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                dur = time.perf_counter() - start
            except subprocess.CalledProcessError as e:
                print(f"Interp failed: {e.stderr.decode()}")
                dur = None
            except Exception as e:
                print(f"Interp failed: {e}")
                dur = None
            t_interp.append(dur)
            if os.path.exists(shl_file): os.remove(shl_file)
            if dur is not None:
                print(f"Interpreter: {dur:.4f}s")
            else:
                 print("Interpreter: Failed")
        else:
            t_interp.append(None)
            print("Interpreter: Skipped (Too Slow)")
        start = time.perf_counter()
        i = 0
        while i < n:
            i += 1
        dur = time.perf_counter() - start
        t_python.append(dur)
        print(f"Python: {dur:.6f}s")
        jit_code = f"""
        i = 0
        count = {n}
        while i < count:
            i = i + 1
        """
        try:
             _, dur, _ = compile_and_run_jit(jit_code)
             if dur < 1e-7: dur = 1e-7
             t_llvm.append(dur)
             print(f"LLVM JIT: {dur:.8f}s")
        except Exception as e:
             print(f"JIT Failed: {e}")
             t_llvm.append(None)
    plt.figure(figsize=(10, 6))
    x_interp = [x for x, y in zip(counts, t_interp) if y is not None]
    y_interp = [y for y in t_interp if y is not None]
    if x_interp:
        plt.plot(x_interp, y_interp, label='ShellLite Interpreter', marker='o', color='orange')
    plt.plot(counts, t_python, label='Python Native', marker='s', color='green')
    plt.plot(counts, t_llvm, label='LLVM JIT', marker='^', color='purple', linestyle='-')
    plt.xlabel('Iterations')
    plt.ylabel('Time (seconds)')
    plt.title('GBP+LLVM Runtime Performance (Massive Scale)')
    plt.yscale('log')
    plt.legend()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'benchmark_final.png'))
    plt.savefig(output_path)
    print(f"Graph saved to {output_path}")
if __name__ == "__main__":
    run_benchmark()