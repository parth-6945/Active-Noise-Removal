import subprocess
import numpy as np
import matplotlib.pyplot as plt
import os

# ------------------- Utility functions -------------------

def read_mem_q31(path):
    """Read a hex mem file into numpy int32 array, handling signed Q31 correctly."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in '@#':
                continue
            val = int(line, 16)
            # Convert 32-bit unsigned hex to signed int32
            if val >= 0x80000000:
                val -= 0x100000000
            data.append(np.int32(val))
    return np.array(data, dtype=np.int32)

def snr_db(signal, noise):
    """Compute SNR in dB"""
    power_signal = np.mean(signal.astype(np.float64)**2)
    power_noise = np.mean(noise.astype(np.float64)**2)
    return 10 * np.log10(power_signal / power_noise)

# ------------------- Config -------------------

# Paths (adjust if needed)
c_exe = os.path.join(os.getcwd(), "lms_q31.exe")  # Windows: compiled executable
noise_file = os.path.join("q31_out", "noise.mem")
noisy_file = os.path.join("q31_out", "noisy.mem")
clean_file = os.path.join("q31_out", "clean.mem")
output_dir = os.path.join(os.getcwd(), "results")
os.makedirs(output_dir, exist_ok=True)

# Hyperparameters to test
taps_list = [8, 16, 32]
mu_shift_list = [8, 10, 12]

# ------------------- Check files -------------------

for f in [c_exe, noise_file, noisy_file, clean_file]:
    if not os.path.exists(f):
        raise FileNotFoundError(f"File not found: {f}")

# ------------------- Load original signals -------------------

clean = read_mem_q31(clean_file)
noisy = read_mem_q31(noisy_file)

# ------------------- Run LMS for combinations -------------------

results = []

for taps in taps_list:
    for mu_shift in mu_shift_list:
        out_file = os.path.join(output_dir, f"filtered_t{taps}_mu{mu_shift}.mem")
        print(f"\nRunning LMS: taps={taps}, mu_shift={mu_shift}")
        
        subprocess.run([c_exe, noise_file, noisy_file, out_file, str(taps), str(mu_shift)],
                       check=True, shell=True)

        # Read filtered output
        filtered = read_mem_q31(out_file)

        # True SNR calculations using clean signal
        original_snr = snr_db(clean, noisy - clean)
        filtered_snr = snr_db(clean, filtered - clean)

        results.append({
            'taps': taps,
            'mu_shift': mu_shift,
            'filtered_snr': filtered_snr,
            'original_snr': original_snr
        })

# ------------------- Find best result -------------------

best = max(results, key=lambda r: r['filtered_snr'])
print("\nBest parameters:")
print(f"  taps={best['taps']}, mu_shift={best['mu_shift']}, Filtered SNR={best['filtered_snr']:.2f} dB")

# ------------------- Generate report -------------------

report_file = os.path.join(output_dir, "report.txt")
with open(report_file, "w") as f:
    f.write("Taps\tMu_shift\tOriginal_SNR(dB)\tFiltered_SNR(dB)\n")
    for r in results:
        f.write(f"{r['taps']}\t{r['mu_shift']}\t{r['original_snr']:.2f}\t{r['filtered_snr']:.2f}\n")
    f.write(f"\nBest: taps={best['taps']}, mu_shift={best['mu_shift']}, "
            f"Filtered_SNR={best['filtered_snr']:.2f} dB\n")

print(f"Report saved to {report_file}")

# ------------------- Plot SNR vs mu_shift -------------------

plt.figure(figsize=(8,5))
for taps in taps_list:
    y = [r['filtered_snr'] for r in results if r['taps'] == taps]
    x = mu_shift_list
    plt.plot(x, y, marker='o', label=f'taps={taps}')

plt.xlabel('mu_shift')
plt.ylabel('Filtered SNR (dB)')
plt.title('Filtered SNR vs mu_shift for different taps')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "snr_plot.png"))
plt.show()

# ------------------- Plot best filtered waveform -------------------

best_file = os.path.join(output_dir, f"filtered_t{best['taps']}_mu{best['mu_shift']}.mem")
best_filtered = read_mem_q31(best_file)

plt.figure(figsize=(12,6))
plt.plot(clean, label='Clean Signal', alpha=0.8)
plt.plot(noisy, label='Noisy Signal', alpha=0.6)
plt.plot(best_filtered, label=f'Filtered Signal (taps={best["taps"]}, mu={best["mu_shift"]})', alpha=0.8)
plt.xlabel('Sample Index')
plt.ylabel('Amplitude (Q1.31)')
plt.title('Clean vs Noisy vs Best Filtered Signal')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "best_filtered_waveform.png"))
plt.show()
