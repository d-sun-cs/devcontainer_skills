import numpy as np
  
def softmax_ref(x):  # x: (M, N) float32
    m = np.max(x, axis=-1, keepdims=True)
    e = np.exp(x - m)
    d = np.sum(e, axis=-1, keepdims=True)
    return e / d