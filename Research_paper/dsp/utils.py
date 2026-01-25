import numpy as np
import soundfile as sf

def load_wav(path):
    """
    Load a WAV file and normalize it.
    """
    signal, fs = sf.read(path)
    if signal.ndim > 1:
        signal = signal[:, 0]  # take mono if stereo
    signal = signal / np.max(np.abs(signal))
    return signal, fs


def add_white_noise(signal, snr_db):
    """
    Add white Gaussian noise to a signal at a given SNR (dB).
    Returns noisy signal and noise reference.
    """
    signal_power = np.mean(signal ** 2)
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear

    noise = np.sqrt(noise_power) * np.random.randn(len(signal))
    noisy_signal = signal + noise

    return noisy_signal, noise


def compute_snr(clean, processed):
    """
    Compute SNR in dB.
    """
    noise = clean - processed
    return 10 * np.log10(np.sum(clean ** 2) / np.sum(noise ** 2))


def compute_mse(clean, processed):
    """
    Compute Mean Squared Error.
    """
    return np.mean((clean - processed) ** 2)

def compute_ise(error_signal):
    """
    Instantaneous Squared Error (ISE)
    """
    return error_signal ** 2


def smooth_curve(signal, window):
    """
    Moving-average smoothing (for visualization / convergence detection only)
    """
    window = int(window)
    if window <= 1:
        return signal
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode="valid")


def compute_steady_state_mse(ise, fraction=0.1):
    """
    Steady-state MSE computed over the last `fraction` of samples
    """
    N = len(ise)
    start = int((1 - fraction) * N)
    return np.mean(ise[start:])


def find_convergence_iteration(ise_smooth, steady_state_mse, tol=0.10, window_frac=0.02):
    """
    Efficiently finds the first iteration where smoothed ISE
    enters and stays within ±tol of steady-state MSE using a short stability window.
    """
    N = len(ise_smooth)
    window_len = max(1, int(N * window_frac))  # e.g., 2% of signal length

    lower = steady_state_mse * (1 - tol)
    upper = steady_state_mse * (1 + tol)

    for i in range(N - window_len):
        window = ise_smooth[i:i + window_len]
        if np.all((window >= lower) & (window <= upper)):
            return i

    return None



def compute_convergence_metrics(
    error_signal,
    fs,
    smooth_window=5000,
    tol=0.10,
    steady_fraction=0.1
):
    """
    High-level helper: computes convergence iteration and time
    """
    ise = compute_ise(error_signal)
    ise_smooth = smooth_curve(ise, smooth_window)
    steady_mse = compute_steady_state_mse(ise, steady_fraction)

    conv_iter = find_convergence_iteration(
        ise_smooth,
        steady_mse,
        tol
    )

    if conv_iter is not None:
        conv_time_ms = (conv_iter / fs) * 1000
    else:
        conv_time_ms = None

    return {
        "steady_state_mse": steady_mse,
        "convergence_iteration": conv_iter,
        "convergence_time_ms": conv_time_ms,
        "ise": ise,
        "ise_smooth": ise_smooth
    }
