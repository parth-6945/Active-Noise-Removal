import numpy as np

def apa_filter(d, x, mu=0.1, filter_len=32, P=4, eps=1e-6):
    """
    Affine Projection Algorithm (APA) adaptive filter
    NLMS-consistent implementation

    Parameters:
    d : ndarray
        Primary input (speech + noise)
    x : ndarray
        Reference noise
    mu : float
        Step size
    filter_len : int
        Adaptive filter length
    P : int
        Projection order (P=1 → NLMS)
    eps : float
        Regularization constant

    Returns:
    y : ndarray
        Estimated noise
    e : ndarray
        Error signal
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

        # ---------- Build input matrix X ----------
        # X shape: (filter_len, P)
        X = np.zeros((filter_len, P))
        d_vec = np.zeros(P)

        for k in range(P):
            idx = n - k
            if idx >= 0:
                X[:, k] = x_padded[idx : idx + filter_len][::-1]
                d_vec[k] = d[idx]

        # ---------- Filter output ----------
        y[n] = np.dot(w, X[:, 0])
        e[n] = d[n] - y[n]

        # ---------- APA update ----------
        # e_vec = d_vec - X^T w
        e_vec = d_vec - X.T @ w

        R = X.T @ X + eps * np.eye(P)
        w = w + mu * X @ np.linalg.solve(R, e_vec)

        w_hist[n, :] = w

    return y, e, w_hist
