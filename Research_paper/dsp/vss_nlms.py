import numpy as np

def vss_nlms_filter(d, x, mu_max=0.8, mu_min=0.01, filter_len=32, alpha=0.95, eps=1e-6):
    """
    Variable Step-Size NLMS adaptive filter for noise cancellation,
    based on your NLMS implementation.

    Parameters:
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise input
    mu_max : float
        Maximum step size
    mu_min : float
        Minimum step size
    filter_len : int
        Length of adaptive filter
    alpha : float
        Smoothing factor for step size adaptation
    eps : float
        Small constant to avoid division by zero

    Returns:
    y : ndarray
        Estimated noise
    e : ndarray
        Error signal (cleaned speech estimate)
    w_hist : ndarray
        Weight history
    """

    N = len(d)
    w = np.zeros(filter_len)
    y = np.zeros(N)
    e = np.zeros(N)
    w_hist = np.zeros((N, filter_len))

    # Zero-pad reference signal
    x_padded = np.concatenate([np.zeros(filter_len - 1), x])

    # Initialize smoothed error power
    power_e = 0.0

    for n in range(N):
        x_vec = x_padded[n:n + filter_len][::-1]

        # Filter output
        y[n] = np.dot(w, x_vec)
        e[n] = d[n] - y[n]

        # Update smoothed error power
        power_e = alpha * power_e + (1 - alpha) * (e[n] ** 2)

        # Compute variable step size
        mu = np.clip(power_e / (np.dot(x_vec, x_vec) + eps), mu_min, mu_max)

        # Weight update
        w = w + (mu / (np.dot(x_vec, x_vec) + eps)) * e[n] * x_vec
        w_hist[n, :] = w

    return y, e, w_hist
