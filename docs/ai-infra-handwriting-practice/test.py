import numpy as np
from taskA import softmax_ref
from taskB import online_softmax_row

np.random.seed(0)
x = np.random.randn(4, 1000).astype(np.float32) * 10
ref = softmax_ref(x)
out = np.stack([online_softmax_row(row) for row in x])
print("max abs err:", np.abs(ref - out).max())   # 期望 < 1e-6

# 行和应该都接近 1
print("row sums (ref):", ref.sum(axis=-1))
print("row sums (online):", out.sum(axis=-1))

# 极值测试：故意制造一个超大值，验证数值稳定
x_extreme = np.array([[1.0, 2.0, 1000.0, 3.0]], dtype=np.float32)
print("extreme:", softmax_ref(x_extreme))   # 期望接近 [0, 0, 1, 0]