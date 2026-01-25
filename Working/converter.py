import numpy as np
import soundfile as sf
import json
import os

# ======================= Q31 CONFIG ==========================
Q = 31
Q_SCALE = (1 << Q)
MAX_Q31 = 0x7FFFFFFF
MIN_Q31 = -0x80000000

# ======================= CONVERSIONS ==========================

def float_to_q31_array(x):
    """Convert float [-1, +1) to Q1.31 int64 array"""
    x = np.clip(x, -1.0, 1.0 - 1.0 / Q_SCALE)
    return (x * (Q_SCALE - 1)).astype(np.int64)

def q31_to_float(xq):
    """Convert Q1.31 int array back to float"""
    return xq.astype(np.float64) / (Q_SCALE - 1.0)

def write_mem_q31(path, arr):
    """Write Q1.31 array to .mem file (hex, 8 chars per line)"""
    with open(path, 'w') as f:
        for v in arr.astype(np.int32):
            f.write(f"{np.uint32(np.int32(v)):08x}\n")

def read_mem_q31(path):
    """Read .mem file and return Q1.31 int array"""
    with open(path, 'r') as f:
        lines = f.read().strip().splitlines()
    vals = [np.int32(np.uint32(int(line, 16))) for line in lines]
    return np.array(vals, dtype=np.int64)

# ======================= MAIN FUNCTIONS ==========================

def wav_to_mem(wav_path, mem_path):
    """Convert .wav → .mem and store fs metadata"""
    data, fs = sf.read(wav_path)
    if data.ndim > 1:
        data = data[:, 0]  # Use first channel
    data = data / np.max(np.abs(data))  # Normalize
    q31 = float_to_q31_array(data)

    write_mem_q31(mem_path, q31)

    # Save sampling rate metadata
    meta_path = os.path.splitext(mem_path)[0] + ".json"
    with open(meta_path, "w") as f:
        json.dump({"fs": fs}, f)

    print(f"[✓] Converted '{wav_path}' → '{mem_path}'")
    print(f"[→] Sampling rate saved in '{meta_path}' (fs = {fs} Hz)")

def mem_to_wav(mem_path, wav_path):
    """Convert .mem → .wav using stored metadata"""
    q31 = read_mem_q31(mem_path)

    # Read sampling rate metadata
    meta_path = os.path.splitext(mem_path)[0] + ".json"
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            fs = json.load(f).get("fs", 16000)
    else:
        fs = 44100  # default fallback
        print(f"[!] No metadata found. Using default fs = {fs} Hz")

    data = q31_to_float(q31)
    sf.write(wav_path, data, fs)

    print(f"[✓] Converted '{mem_path}' → '{wav_path}' (fs = {fs} Hz)")

# ======================= INTERACTIVE MODE ==========================

if __name__ == "__main__":
    print("=== Q1.31 WAV ↔ MEM Converter ===")
    print("1. WAV → MEM")
    print("2. MEM → WAV")
    choice = input("Select mode (1 or 2): ").strip()

    if choice == "1":
        wav_path = input("Enter path of input WAV file: ").strip()
        mem_path = input("Enter desired output MEM file path: ").strip()
        wav_to_mem(wav_path, mem_path)

    elif choice == "2":
        mem_path = input("Enter path of input MEM file: ").strip()
        wav_path = input("Enter desired output WAV file path: ").strip()
        mem_to_wav(mem_path, wav_path)

    else:
        print("Invalid selection. Exiting.")
