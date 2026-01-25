import numpy as np

def nlms_filter(d, x, mu=0.8, filter_len=32, eps=1e-6):
    """
    NLMS adaptive filter for noise cancellation.

    Parameters:
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise input
    mu : float
        Step size (0 < mu <= 2 typically)
    filter_len : int
        Length of adaptive filter
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

    for n in range(N):
        x_vec = x_padded[n:n + filter_len][::-1]
        y[n] = np.dot(w, x_vec)
        e[n] = d[n] - y[n]

        norm_factor = np.dot(x_vec, x_vec) + eps
        w = w + (mu / norm_factor) * e[n] * x_vec
        w_hist[n, :] = w

    return y, e, w_hist
