import numpy as np
import soundfile as sf
import os
import time

Q = 31
Q_SCALE = (1 << Q)

def float_to_q31_array(x):
    x = np.clip(x, -1.0, 1.0 - 1.0 / Q_SCALE)
    return (x * (Q_SCALE - 1)).astype(np.int64)

def q31_to_float(xq):
    return (xq.astype(np.float64) / (Q_SCALE - 1.0))

def write_mem_q31(path, arr):
    with open(path, 'w') as f:
        for v in arr.astype(np.int32):
            f.write(f"{np.uint32(np.int32(v)):08x}\n")

def lms_q31_emulator(x_q31, d_q31, taps=16, mu_shift=12):
    n = min(len(x_q31), len(d_q31))
    w = np.zeros(taps, dtype=np.int64)
    x = np.zeros(taps, dtype=np.int64)
    e_out = np.zeros(n, dtype=np.int64)

    print(f"[→] Running LMS filter on {n:,} samples...")

    start_time = time.time()
    for nidx in range(n):
        x[1:] = x[:-1]
        x[0] = x_q31[nidx]

        # Filter output
        acc = 0
        for i in range(taps):
            acc += int(w[i]) * int(x[i])
        y_q31 = (acc >> Q)
        y_q31 = np.clip(y_q31, -0x80000000, 0x7FFFFFFF)

        # Error
        e = int(d_q31[nidx]) - int(y_q31)
        e_out[nidx] = e

        # Coefficient update
        for i in range(taps):
            prod = int(e) * int(x[i])     # Q62
            prod_q31 = prod >> Q          # Q31
            delta = prod_q31 >> mu_shift  # scaled
            w[i] = int(w[i]) + int(delta)
            w[i] = np.clip(w[i], -0x80000000, 0x7FFFFFFF)

        # Print progress every 10,000 samples
        if (nidx + 1) % 10000 == 0:
            elapsed = time.time() - start_time
            print(f"   Progress: {100 * (nidx + 1) / n:.1f}% "
                  f"({nidx + 1:,}/{n:,}) | Elapsed: {elapsed:.1f}s")

    print(f"[✓] LMS filtering complete in {time.time() - start_time:.2f}s")
    return e_out

if __name__ == "__main__":
    # === CONFIG ===
    input_clean = "Original_files/clean_speech.wav"
    out_dir = "q31_out"
    taps = 16
    mu_shift = 10
    fs_noise = 400  # Hz
    noise_amp = 0.3

    os.makedirs(out_dir, exist_ok=True)

    # === READ CLEAN FILE ===
    clean, fs = sf.read(input_clean)
    if clean.ndim > 1:
        clean = clean[:, 0]
    clean = clean / np.max(np.abs(clean))

    # === ADD NOISE ===
    t = np.arange(len(clean)) / fs
    noise = noise_amp * np.sin(2 * np.pi * fs_noise * t)
    noisy = clean + noise
    noisy = np.clip(noisy, -1.0, 1.0)

    # === Convert to Q1.31 ===
    x_q31 = float_to_q31_array(noise)
    d_q31 = float_to_q31_array(noisy)

    # === Run LMS ===
    e_q31 = lms_q31_emulator(x_q31, d_q31, taps=taps, mu_shift=mu_shift)

    # === Convert back to float ===
    e_f = q31_to_float(e_q31)

    # === Save outputs ===
    sf.write(os.path.join(out_dir, "clean.wav"), clean, fs)
    sf.write(os.path.join(out_dir, "noisy.wav"), noisy, fs)
    sf.write(os.path.join(out_dir, "filtered_q31.wav"), e_f, fs)

    write_mem_q31(os.path.join(out_dir, "clean.mem"), float_to_q31_array(clean))
    write_mem_q31(os.path.join(out_dir, "noise.mem"), x_q31)
    write_mem_q31(os.path.join(out_dir, "noisy.mem"), d_q31)
    write_mem_q31(os.path.join(out_dir, "filtered_q31.mem"), e_q31)

    print("\n[✓] Q31 LMS filtering complete.")
    print(f"[→] Files saved in '{out_dir}/'")
