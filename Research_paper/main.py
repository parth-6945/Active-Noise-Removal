import os
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf

from dsp.utils import (
    load_wav,
    add_white_noise,
    compute_snr,
    compute_mse
)

from dsp.lms import lms_filter
from dsp.nlms import nlms_filter
from dsp.wiener import wiener_filter
from dsp.rls import rls_filter
from dsp.vss_nlms import vss_nlms_filter
from dsp.apa import apa_filter


# =========================
# PATHS
# =========================
CLEAN_PATH = "data/clean/speech.wav"
NOISY_DIR = "data/noisy"
RESULT_PLOTS = "results/plots"
RESULT_METRICS = "results/metrics"

os.makedirs(NOISY_DIR, exist_ok=True)
os.makedirs(RESULT_PLOTS, exist_ok=True)
os.makedirs(RESULT_METRICS, exist_ok=True)


# =========================
# LOAD SIGNAL
# =========================
clean_signal, fs = load_wav(CLEAN_PATH)

snr_db = 5
noisy_signal, noise_ref = add_white_noise(clean_signal, snr_db)
snr_in = compute_snr(clean_signal, noisy_signal)

print("=" * 60)
print(f"INPUT SNR : {snr_in:.2f} dB")
print("=" * 60)


# ======================================================
# HELPER: SAVE + PRINT METRICS
# ======================================================
def save_and_print_metrics(filename, title, params, snr_out, mse):
    lines = []
    lines.append("=" * 60)
    lines.append(title)
    lines.append("=" * 60)

    lines.append("\nParameters:")
    for k, v in params.items():
        lines.append(f"{k} : {v}")

    lines.append("\nMetrics:")
    lines.append(f"SNR In  : {snr_in:.2f} dB")
    lines.append(f"SNR Out : {snr_out:.2f} dB")
    lines.append(f"MSE     : {mse:.6e}\n")

    text = "\n".join(lines)
    print(text)

    with open(os.path.join(RESULT_METRICS, filename), "w") as f:
        f.write(text)


# ======================================================
# HELPER: PLOT NORMALIZED WEIGHT NORM
# ======================================================
def plot_weight_norm(w_hist, filename):
    weight_norm = np.linalg.norm(w_hist, axis=1)
    weight_norm_norm = (weight_norm - weight_norm[0]) / (
        np.max(weight_norm) - weight_norm[0] + 1e-12
    )

    plt.figure(figsize=(6, 4))
    plt.plot(weight_norm_norm, linewidth=1.5)

    # Axis labels (bigger font)
    plt.xlabel("Iteration", fontsize=14)
    plt.ylabel("Normalized $\\|\\mathbf{w}(n)\\|$", fontsize=16)

    # Tick numbers size
    plt.tick_params(axis='both', which='major', labelsize=16)

    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()


# =========================
# LMS
# =========================
mu = 0.01
filter_len = 32

y_lms, e_lms, w_hist_lms = lms_filter(
    d=noisy_signal,
    x=noise_ref,
    mu=mu,
    filter_len=filter_len
)

sf.write(f"{NOISY_DIR}/speech_lms_{snr_db}dB.wav", e_lms, fs)

snr_out_lms = compute_snr(clean_signal, e_lms)
mse_lms = compute_mse(clean_signal, e_lms)

save_and_print_metrics(
    "lms_metrics.txt",
    "LMS RESULTS",
    {"mu": mu, "filter_len": filter_len, "snr_db": snr_db},
    snr_out_lms,
    mse_lms
)

plot_weight_norm(w_hist_lms, f"{RESULT_PLOTS}/fig_lms_convergence.png")


# =========================
# NLMS
# =========================
mu_nlms = 0.0075
filter_len_nlms = 32

y_nlms, e_nlms, w_hist_nlms = nlms_filter(
    d=noisy_signal,
    x=noise_ref,
    mu=mu_nlms,
    filter_len=filter_len_nlms
)

sf.write(f"{NOISY_DIR}/speech_nlms_{snr_db}dB.wav", e_nlms, fs)

snr_out_nlms = compute_snr(clean_signal, e_nlms)
mse_nlms = compute_mse(clean_signal, e_nlms)

save_and_print_metrics(
    "nlms_metrics.txt",
    "NLMS RESULTS",
    {"mu": mu_nlms, "filter_len": filter_len_nlms, "snr_db": snr_db},
    snr_out_nlms,
    mse_nlms
)

plot_weight_norm(w_hist_nlms, f"{RESULT_PLOTS}/fig_nlms_convergence.png")


# =========================
# VSS-NLMS
# =========================
mu_max = 0.004
mu_min = 0.003
alpha = 0.98
filter_len_vss = 32

y_vss, e_vss, w_hist_vss = vss_nlms_filter(
    d=noisy_signal,
    x=noise_ref,
    filter_len=filter_len_vss,
    mu_max=mu_max,
    mu_min=mu_min,
    alpha=alpha
)

sf.write(f"{NOISY_DIR}/speech_vss_nlms_{snr_db}dB.wav", e_vss, fs)

snr_out_vss = compute_snr(clean_signal, e_vss)
mse_vss = compute_mse(clean_signal, e_vss)

save_and_print_metrics(
    "vss_nlms_metrics.txt",
    "VSS-NLMS RESULTS",
    {
        "filter_len": filter_len_vss,
        "mu_max": mu_max,
        "mu_min": mu_min,
        "alpha": alpha,
        "snr_db": snr_db,
    },
    snr_out_vss,
    mse_vss
)

plot_weight_norm(w_hist_vss, f"{RESULT_PLOTS}/fig_vss_nlms_convergence.png")


# =========================
# APA
# =========================
filter_len_apa = 16
mu_apa = 0.0005
P = 4

y_apa, e_apa, w_hist_apa = apa_filter(
    d=noisy_signal,
    x=noise_ref,
    mu=mu_apa,
    filter_len=filter_len_apa,
    P=P
)

sf.write(f"{NOISY_DIR}/speech_apa_{snr_db}dB.wav", e_apa, fs)

snr_out_apa = compute_snr(clean_signal, e_apa)
mse_apa = compute_mse(clean_signal, e_apa)

save_and_print_metrics(
    "apa_metrics.txt",
    "APA RESULTS",
    {"filter_len": filter_len_apa, "mu": mu_apa, "P": P, "snr_db": snr_db},
    snr_out_apa,
    mse_apa
)

plot_weight_norm(w_hist_apa, f"{RESULT_PLOTS}/fig_apa_convergence.png")


# =========================
# RLS
# =========================
filter_len_rls = 32
lam = 0.99999
delta = 500.0

y_rls, e_rls, w_hist_rls = rls_filter(
    d=noisy_signal,
    x=noise_ref,
    filter_len=filter_len_rls,
    lam=lam,
    delta=delta
)

sf.write(f"{NOISY_DIR}/speech_rls_{snr_db}dB.wav", e_rls, fs)

snr_out_rls = compute_snr(clean_signal, e_rls)
mse_rls = compute_mse(clean_signal, e_rls)

save_and_print_metrics(
    "rls_metrics.txt",
    "RLS RESULTS",
    {"filter_len": filter_len_rls, "lambda": lam, "delta": delta, "snr_db": snr_db},
    snr_out_rls,
    mse_rls
)

plot_weight_norm(w_hist_rls, f"{RESULT_PLOTS}/fig_rls_convergence.png")


# =========================
# WIENER (NON-ADAPTIVE)
# =========================
filter_len_wiener = 32

y_w, e_w, w_opt = wiener_filter(
    d=noisy_signal,
    x=noise_ref,
    filter_len=filter_len_wiener
)

sf.write(f"{NOISY_DIR}/speech_wiener_{snr_db}dB.wav", e_w, fs)

snr_out_w = compute_snr(clean_signal, e_w)
mse_w = compute_mse(clean_signal, e_w)

print("=" * 60)
print("WIENER FILTER RESULTS")
print("=" * 60)
print(f"filter_len : {filter_len_wiener}")
print(f"SNR Out    : {snr_out_w:.2f} dB")
print(f"MSE        : {mse_w:.6e}")
print("Convergence: Closed-form (non-adaptive)\n")

with open(f"{RESULT_METRICS}/wiener_metrics.txt", "w") as f:
    f.write("WIENER FILTER RESULTS\n")
    f.write(f"filter_len : {filter_len_wiener}\n")
    f.write(f"SNR Out    : {snr_out_w:.2f} dB\n")
    f.write(f"MSE        : {mse_w:.6e}\n")


# =========================
# BAR CHART: OUTPUT SNR
# =========================
algorithms = ["LMS", "NLMS", "VSS-NLMS", "APA", "RLS", "Wiener"]
snr_values = [
    snr_out_lms,
    snr_out_nlms,
    snr_out_vss,
    snr_out_apa,
    snr_out_rls,
    snr_out_w
]

plt.figure(figsize=(7, 4))
plt.bar(algorithms, snr_values)
plt.xlabel("Algorithm")
plt.ylabel("Output SNR (dB)")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(f"{RESULT_PLOTS}/fig_snr_comparison.png", dpi=300)
plt.close()


# =========================
# BAR CHART: MSE (LOG SCALE)
# =========================
mse_values = [
    mse_lms,
    mse_nlms,
    mse_vss,
    mse_apa,
    mse_rls,
    mse_w
]

plt.figure(figsize=(7, 4))
plt.bar(algorithms, mse_values)
plt.yscale("log")
plt.xlabel("Algorithm")
plt.ylabel("Mean Squared Error (log scale)")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(f"{RESULT_PLOTS}/fig_mse_comparison.png", dpi=300)
plt.close()

print("ALL ALGORITHMS COMPLETED SUCCESSFULLY")
