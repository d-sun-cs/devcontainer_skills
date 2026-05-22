# Online Safe Softmax — CUDA C++ 实现笔记

## 1. Softmax 数学定义

$$
y_i = \frac{e^{x_i}}{\sum_{j} e^{x_j}}
$$

输入 `(M, N)`，沿最后一维归约，输出形状不变。每行的输出之和为 1。

## 2. Safe Softmax：为什么要减 max

fp32 中 `exp(x)` 在 `x ≈ 88.72` 就 overflow 到 inf。减去行最大值 `m` 后：

$$
y_i = \frac{e^{x_i - m}}{\sum_{j} e^{x_j - m}}, \quad m = \max_j x_j
$$

- 所有指数 `x_i - m ≤ 0`，所以 `exp(x_i - m) ∈ (0, 1]`，永远不溢出
- 数学上等价：分子分母同乘 `e^{-m}`，值不变

## 3. 标准 3-pass vs Online 2-pass

### 标准 safe softmax（3 次遍历）

| Pass | 操作 | 读写 |
|------|------|------|
| 1 | `m = max(x[i])` | 读 N |
| 2 | `d = sum(exp(x[i] - m))` | 读 N |
| 3 | `y[i] = exp(x[i] - m) / d` | 读 N + 写 N |

总 memory traffic ≈ 4N。

### Online softmax（2 次遍历）

将 pass 1 和 pass 2 合并：**一边扫描一边同时维护 max 和 sum**。

核心递推——遇到新元素 `x_i` 时更新状态 `(m, d)`：

```
m_new = max(m, x_i)
d     = d * exp(m - m_new) + exp(x_i - m_new)
m     = m_new
```

直觉：当 max 变大时，之前累积的 `d` 是以旧 max 为基准的，乘上 `exp(m_old - m_new)` 就把基准统一到新 max。

| Pass | 操作 | 读写 |
|------|------|------|
| 1 | online 递推得到全局 `(m, d)` | 读 N |
| 2 | `y[i] = exp(x[i] - m) / d` | 读 N + 写 N |

总 memory traffic ≈ 3N。

## 4. Merge 算子与结合律

将递推一般化为两个子集的合并：

```
m_ab = max(m_a, m_b)
d_ab = d_a * exp(m_a - m_ab) + d_b * exp(m_b - m_ab)
```

关键性质：
- **结合律**：`(A ⊕ B) ⊕ C = A ⊕ (B ⊕ C)` → 允许树形并行 reduce（log2(N) 步）
- **交换律**：`A ⊕ B = B ⊕ A` → 允许 butterfly 模式（`__shfl_xor_sync`）双向交换
- **单位元**：`(-∞, 0)` → merge 任何状态不改变结果

## 5. CUDA Kernel 结构

设计：一个 block 处理一行，BLOCK_SIZE 个线程协作。

```
gridDim.x  = M（行数）
blockDim.x = BLOCK_SIZE（如 256，必须是 2 的幂）
N_WARPS    = BLOCK_SIZE / 32
```

### Pass 1, Step A：线程内串行递推

每个线程用 block-stride loop 扫自己的 slice：

```cpp
float m = -INFINITY, d = 0.0f;
for (int i = tid; i < N; i += BLOCK_SIZE) {
    merge_online(m, d, x_row[i], 1.0f);
}
// 结束后每个线程持有局部 (m, d)
```

### Pass 1, Step B.1：warp 内 butterfly reduce

```cpp
for (int offset = 16; offset > 0; offset >>= 1) {
    float m_other = __shfl_xor_sync(0xffffffff, m, offset);
    float d_other = __shfl_xor_sync(0xffffffff, d, offset);
    merge_online(m, d, m_other, d_other);
}
// 结束后 warp 内 32 个 lane 都持有相同的 warp 级 (m, d)
```

### Pass 1, Step B.2：跨 warp reduce（shared memory）

```cpp
__shared__ float s_m[N_WARPS], s_d[N_WARPS];
if (lane_id == 0) { s_m[warp_id] = m; s_d[warp_id] = d; }
__syncthreads();

if (warp_id == 0) {
    m = (lane_id < N_WARPS) ? s_m[lane_id] : -INFINITY;
    d = (lane_id < N_WARPS) ? s_d[lane_id] : 0.0f;
    for (int offset = N_WARPS / 2; offset > 0; offset >>= 1) {
        float m_other = __shfl_xor_sync(0xffffffff, m, offset);
        float d_other = __shfl_xor_sync(0xffffffff, d, offset);
        merge_online(m, d, m_other, d_other);
    }
}
```

### Pass 1, Step B.3：广播全局 (m, d)

```cpp
__shared__ float s_m_global, s_d_global;
if (tid == 0) { s_m_global = m; s_d_global = d; }
__syncthreads();
float m_global = s_m_global, d_global = s_d_global;
```

### Pass 2：写回结果

```cpp
float inv_d = 1.0f / d_global;  // 乘法替代除法，GPU 上更快
for (int i = tid; i < N; i += BLOCK_SIZE) {
    y_row[i] = __expf(x_row[i] - m_global) * inv_d;
}
```

## 6. `__shfl_xor_sync` 要点

```cpp
float val_from_partner = __shfl_xor_sync(mask, my_val, offset);
```

- 配对规则：当前 lane 与 `lane_id XOR offset` 互换值
- **双向**：A 拿到 B 的值，B 同时拿到 A 的值
- XOR 是自逆的（`a ^ b ^ b = a`），所以配对永远是对称的一对一映射
- 无进位时 XOR 等于加法；有进位时"折回"——这让 butterfly 自动把 lane 分成 `2*offset` 大小的组，组内前半后半互换
- butterfly reduce 要求参与者数量是 2 的幂；非 2 的幂时多余 lane 填 identity 值

## 7. 数值精度

- 输入可以是 bf16/fp16，但**累加器 (m, d) 必须用 fp32**
  - bf16 只有 7 位尾数（~2-3 位十进制精度），累加千级元素误差爆炸
  - 套路：load bf16 → compute fp32 → store bf16
- `__expf` 是 fast intrinsic，精度约 2 ULP，softmax 可接受
- online 路径比 3-pass 精度略差（每步 rescale 引入舍入），但相对误差在 1e-6 量级，实践中可接受

## 8. 设计决策备忘

| 决策 | 原因 |
|------|------|
| BLOCK_SIZE = 256 | occupancy 甜区；太大则单 block 资源占用高，并发 block 少 |
| BLOCK_SIZE 必须是 2 的幂 | butterfly reduce 要求 |
| `1.0f / d_global` 预计算 | GPU 除法吞吐量远低于乘法（A100 约 1:4） |
| `__syncthreads()` 在 shared memory 读写之间 | 防止 warp 间 race condition |
| shared memory 用量极小 | `(2*N_WARPS + 2) * 4` bytes，BLOCK_SIZE=256 时仅 72 bytes |

## 9. 常见 Bug Checklist

- [ ] 忘记减 max → exp overflow 出 inf/nan
- [ ] 累加器用 fp16/bf16 → 精度崩溃
- [ ] reduce 后忘记广播 → 只有 thread 0 有正确 (m, d)，其他线程用旧值
- [ ] `__syncthreads()` 缺失 → shared memory race
- [ ] pass 2 忘乘 `inv_d` → 输出未归一化，行和 ≠ 1
- [ ] boundary mask 缺失 → N 不是 BLOCK_SIZE 倍数时越界读
- [ ] merge 时先写 m 再用旧 m 算 d → 顺序错误导致 d 计算基准错误
