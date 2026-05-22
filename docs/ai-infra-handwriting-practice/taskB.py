import numpy as np

def online_softmax_row(x_row):  # x_row: (N,) float32
    m = -np.inf   # running max
    d = 0.0       # running normalizer
    # pass 1: 用 online 递推同时更新 m 和 d
    for i in range(len(x_row)):
        m_new = max(m, x_row[i])
        # TODO: 用上面给的递推公式更新 d
        d = d * np.exp(m - m_new) + np.exp(x_row[i] - m_new)
        m = m_new
    # pass 2: 写出 y
    y = np.empty_like(x_row)
    for i in range(len(x_row)):
        y[i] = np.exp(x_row[i]- m) / d
    return y