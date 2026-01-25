import numpy as np
import soundfile as sf
import os

# ======================= Q31 CONFIG ==========================
Q = 31
Q_SCALE = (1 << Q)

def float_to_q31_array(x):
    """Convert float [-1, +1) to Q1.31 int64 array"""
    x = np.clip(x, -1.0, 1.0 - 1.0 / Q_SCALE)
    return (x * (Q_SCALE - 1)).astype(np.int64)

def write_mem_q31(path, arr):
    """Write Q1.31 array to .mem file (hex, 8 chars per line)"""
    with open(path, 'w') as f:
        for v in arr.astype(np.int32):
            f.write(f"{np.uint32(np.int32(v)):08x}\n")

# ======================= NOISE GENERATORS ==========================

def generate_sine_noise(fs, length, freq, amp):
    t = np.arange(length) / fs
    return amp * np.sin(2 * np.pi * freq * t)

def generate_double_sine_noise(fs, length, freq1, freq2, amp1, amp2):
    t = np.arange(length) / fs
    n1 = amp1 * np.sin(2 * np.pi * freq1 * t)
    n2 = amp2 * np.sin(2 * np.pi * freq2 * t)
    return n1 + n2

def generate_white_noise(length, amp):
    return amp * np.random.uniform(-1.0, 1.0, length)

def generate_gaussian_noise(length, amp):
    return amp * np.random.normal(0.0, 1.0, length)

# ======================= MAIN FUNCTION ==========================

def add_noise_to_wav(input_wav, out_dir, noise_type="sine", **kwargs):
    os.makedirs(out_dir, exist_ok=True)

    clean, fs = sf.read(input_wav)
    if clean.ndim > 1:
        clean = clean[:, 0]
    clean = clean / np.max(np.abs(clean))

    length = len(clean)
    print(f"[→] Loaded '{input_wav}' ({length:,} samples @ {fs} Hz)")
    print(f"[→] Generating {noise_type} noise...")

    # === Select noise type ===
    if noise_type == "sine":
        freq = kwargs.get("freq", 400)
        amp = kwargs.get("amp", 0.3)
        noise = generate_sine_noise(fs, length, freq, amp)

    elif noise_type == "double":
        f1 = kwargs.get("f1", 400)
        f2 = kwargs.get("f2", 1000)
        a1 = kwargs.get("a1", 0.2)
        a2 = kwargs.get("a2", 0.2)
        noise = generate_double_sine_noise(fs, length, f1, f2, a1, a2)

    elif noise_type == "white":
        amp = kwargs.get("amp", 0.2)
        noise = generate_white_noise(length, amp)

    elif noise_type == "gaussian":
        amp = kwargs.get("amp", 0.2)
        noise = generate_gaussian_noise(length, amp)

    else:
        raise ValueError("Invalid noise_type. Choose from: 'sine', 'double', 'white', 'gaussian'")

    # === Create noisy signal ===
    noisy = clean + noise
    noisy = np.clip(noisy, -1.0, 1.0)

    # === Convert to Q31 ===
    clean_q31 = float_to_q31_array(clean)
    noise_q31 = float_to_q31_array(noise)
    noisy_q31 = float_to_q31_array(noisy)

    # === Save files ===
    sf.write(os.path.join(out_dir, "clean.wav"), clean, fs)
    sf.write(os.path.join(out_dir, "noise.wav"), noise, fs)
    sf.write(os.path.join(out_dir, "noisy.wav"), noisy, fs)

    write_mem_q31(os.path.join(out_dir, "clean.mem"), clean_q31)
    write_mem_q31(os.path.join(out_dir, "noise.mem"), noise_q31)
    write_mem_q31(os.path.join(out_dir, "noisy.mem"), noisy_q31)

    print(f"[✓] Generated files saved in '{out_dir}/'")
    print("   clean.wav / clean.mem")
    print("   noise.wav / noise.mem")
    print("   noisy.wav / noisy.mem")

# ======================= INTERACTIVE MODE ==========================

if __name__ == "__main__":
    print("=== Noise Generator (Q1.31 Compatible) ===")
    input_wav = input("Enter path to clean WAV file: ").strip()
    out_dir = input("Enter output folder name (default: q31_noise_out): ").strip() or "q31_noise_out"

    print("\nSelect noise type:")
    print("1. Single frequency sine wave")
    print("2. Double frequency sine wave")
    print("3. White noise")
    print("4. Gaussian noise")
    choice = input("Enter choice (1–4): ").strip()

    if choice == "1":
        freq = float(input("Enter frequency (Hz): "))
        amp = float(input("Enter amplitude (0–1): "))
        add_noise_to_wav(input_wav, out_dir, "sine", freq=freq, amp=amp)

    elif choice == "2":
        f1 = float(input("Enter first frequency (Hz): "))
        f2 = float(input("Enter second frequency (Hz): "))
        a1 = float(input("Enter amplitude of first tone (0–1): "))
        a2 = float(input("Enter amplitude of second tone (0–1): "))
        add_noise_to_wav(input_wav, out_dir, "double", f1=f1, f2=f2, a1=a1, a2=a2)

    elif choice == "3":
        amp = float(input("Enter amplitude (0–1): "))
        add_noise_to_wav(input_wav, out_dir, "white", amp=amp)

    elif choice == "4":
        amp = float(input("Enter amplitude (0–1): "))
        add_noise_to_wav(input_wav, out_dir, "gaussian", amp=amp)

    else:
        print("❌ Invalid choice. Exiting.")
