import numpy as np
from dsp.apa import apa_filter
from dsp.utils import load_wav, add_white_noise, compute_snr, compute_mse

# -------------------------------
# Load signals (same as main.py)
# -------------------------------
clean_signal, fs = load_wav("data/clean/speech.wav")
snr_db = 5
noisy_signal, noise_ref = add_white_noise(clean_signal, snr_db)

# Truncate
N = min(len(clean_signal), len(noisy_signal), len(noise_ref))
clean_signal = clean_signal[:N]
noisy_signal = noisy_signal[:N]
noise_ref = noise_ref[:N]

snr_in = compute_snr(clean_signal, noisy_signal)
print(f"SNR In : {snr_in:.2f} dB\n")

# Limit length for APA sweep (speed!)
fs_test = fs
max_seconds = 2
max_samples = int(fs_test * max_seconds)

clean_signal = clean_signal[:max_samples]
noisy_signal = noisy_signal[:max_samples]
noise_ref = noise_ref[:max_samples]

# -------------------------------
# APA sweep parameters
# -------------------------------
filter_len = 32

mu_values = [0.01, 0.03, 0.05, 0.1, 0.2]
P_values = [1, 2, 4, 8]
eps = 1e-6

results = []

for P in P_values:
    for mu in mu_values:
        try:
            y, e, _ = apa_filter(
                d=noisy_signal,
                x=noise_ref,
                mu=mu,
                filter_len=filter_len,
                P=P,
                eps=eps
            )

            snr_out = compute_snr(clean_signal, e)
            mse = compute_mse(clean_signal, e)

            results.append((P, mu, snr_out, mse))

            print(
                f"P={P}, mu={mu:5.3f} | "
                f"SNR Out={snr_out:6.2f} dB | "
                f"MSE={mse:.6f}"
            )

        except Exception as ex:
            print(f"P={P}, mu={mu} FAILED: {ex}")

# -------------------------------
# Best configs
# -------------------------------
results.sort(key=lambda x: x[2], reverse=True)

print("\n==== TOP APA CONFIGS ====")
for P, mu, snr_out, mse in results[:5]:
    print(
        f"P={P}, mu={mu:.3f} | "
        f"SNR Out={snr_out:.2f} dB | "
        f"MSE={mse:.6f}"
    )
