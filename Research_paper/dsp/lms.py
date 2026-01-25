import numpy as np

def lms_filter(d, x, mu=0.005, filter_len=32):
    """
    LMS adaptive filter for noise cancellation.

    Parameters:
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise input
    mu : float
        Step size
    filter_len : int
        Length of adaptive filter

    Returns:
    y : ndarray
        Estimated noise
    e : ndarray
        Error signal (cleaned speech estimate)
    w_hist : ndarray
        Weight history (for convergence plots)
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

        w = w + mu * e[n] * x_vec
        w_hist[n, :] = w

    return y, e, w_hist
