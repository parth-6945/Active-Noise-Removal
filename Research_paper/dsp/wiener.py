import numpy as np
from scipy.linalg import toeplitz

def wiener_filter(d, x, filter_len=32):
    """
    Wiener filter for noise cancellation.

    Parameters:
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise input
    filter_len : int
        Length of FIR Wiener filter

    Returns:
    y : ndarray
        Estimated noise
    e : ndarray
        Error signal (cleaned speech estimate)
    w_opt : ndarray
        Optimal Wiener filter coefficients
    """

    # Estimate autocorrelation of reference noise
    r_xx = np.correlate(x, x, mode='full')
    mid = len(r_xx) // 2
    r_xx = r_xx[mid:mid + filter_len]

    # Toeplitz autocorrelation matrix
    R_xx = toeplitz(r_xx)

    # Cross-correlation between reference noise and primary input
    r_xd = np.correlate(d, x, mode='full')
    r_xd = r_xd[mid:mid + filter_len]

    # Solve Wiener-Hopf equations
    w_opt = np.linalg.solve(R_xx, r_xd)

    # Apply filter
    x_padded = np.concatenate([np.zeros(filter_len - 1), x])
    y = np.zeros(len(d))

    for n in range(len(d)):
        x_vec = x_padded[n:n + filter_len][::-1]
        y[n] = np.dot(w_opt, x_vec)

    # Error signal
    e = d - y

    return y, e, w_opt
