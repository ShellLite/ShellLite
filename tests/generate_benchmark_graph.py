import os

import matplotlib.pyplot as plt


def generate_benchmark_graph():
    labels = ['Interpreted Mode', 'LLVM JIT (Compiled)']
    times = [28.5, 0.001]
    colors = ['#ffaa00', '#00aa44']
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, times, color=colors, width=0.5)
    plt.yscale('log')
    plt.ylabel('Time (Seconds) - Log Scale', fontsize=12)
    plt.title('Runtime Performance: Interpreted vs LLVM', fontsize=14, fontweight='bold')
    plt.ylim(0.0001, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.3, which='both')
    for bar, time_val in zip(bars, times):
        height = bar.get_height()
        if time_val < 0.01:
            label = f"< {time_val}s"
        else:
            label = f"{time_val}s"
        plt.text(bar.get_x() + bar.get_width()/2., height * 1.2,
                 label,
                 ha='center', va='bottom', fontsize=11, fontweight='bold')
    output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "benchmark_final.png")
    output_file = os.path.abspath(output_file)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Graph generated at: {output_file}")
if __name__ == "__main__":
    generate_benchmark_graph()