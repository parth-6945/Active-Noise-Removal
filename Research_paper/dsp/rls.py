import numpy as np

def rls_filter(d, x, filter_len=32, lam=0.995, delta=100.0, eps=1e-6):
    """
    Numerically stable RLS adaptive filter for noise cancellation.

    Parameters
    ----------
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise input
    filter_len : int
        Filter length
    lam : float
        Forgetting factor (0.995–0.999 recommended)
    delta : float
        Initial diagonal loading (100–1000 recommended)
    eps : float
        Numerical stability constant

    Returns
    -------
    y : ndarray
        Estimated noise
    e : ndarray
        Error signal (cleaned speech)
    w_hist : ndarray
        Weight history
    """

    N = len(d)

    # Normalize reference noise (CRITICAL)
    x = x / (np.std(x) + eps)

    # Initialize
    w = np.zeros(filter_len)
    P = (1.0 / delta) * np.eye(filter_len)

    y = np.zeros(N)
    e = np.zeros(N)
    w_hist = np.zeros((N, filter_len))

    # Zero-pad reference
    x_padded = np.concatenate([np.zeros(filter_len - 1), x])

    for n in range(N):
        x_vec = x_padded[n:n + filter_len][::-1]

        # Output
        y[n] = np.dot(w, x_vec)
        e[n] = d[n] - y[n]

        # Gain vector
        Px = P @ x_vec
        denom = lam + np.dot(x_vec, Px)
        denom = max(denom, eps)  # prevent blow-up

        k = Px / denom

        # Weight update
        w = w + k * e[n]

        # Joseph-stabilized P update
        P = (P - np.outer(k, Px)) / lam

        # Enforce symmetry (VERY important)
        P = 0.5 * (P + P.T)

        w_hist[n] = w

    return y, e, w_hist
