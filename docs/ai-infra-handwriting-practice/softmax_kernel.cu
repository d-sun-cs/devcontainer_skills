// Online Softmax CUDA kernel — skeleton with TODOs
//
// 设计:
//   输入:  X (M, N) row-major fp32
//   输出:  Y (M, N) row-major fp32
//   一个 block 处理一行, block 内 BLOCK_SIZE 个线程协作
//   假设 BLOCK_SIZE 是 32 的倍数, 且 N >= BLOCK_SIZE (避免 (-inf, 0) 全为 identity 的退化)
//   假设 BLOCK_SIZE <= 1024 (一个 block 最大线程数)

#include <cuda_runtime.h>
#include <math.h>

// online softmax 的 merge 算子: (m_a, d_a) ⊕ (m_b, d_b) → (m_ab, d_ab)
// 你已经在任务 1 推过这个公式。
__device__ __forceinline__
void merge_online(float& m, float& d, float m_other, float d_other) {
    // TODO 1: 把 (m, d) 与 (m_other, d_other) 合并, 结果写回 (m, d)
    // 注意:
    //   - 用 fmaxf 求 max
    //   - 用 __expf (fast intrinsic) 或 expf
    //   - 一般顺序: 先算 m_new, 再用它更新 d, 最后把 m_new 写回 m
    //   - 这是性能关键路径, 后面会被调用很多次
    float m_new = fmaxf(m, m_other);
    d           = d * __expf(m - m_new) + d_other * __expf(m_other - m_new);
    m           = m_new;
}

template <int BLOCK_SIZE>
__global__ void online_softmax_kernel(
    const float* __restrict__ X,   // (M, N)
    float* __restrict__ Y,         // (M, N)
    int N
) {
    static_assert(BLOCK_SIZE % 32 == 0, "BLOCK_SIZE must be a multiple of 32");
    constexpr int N_WARPS = BLOCK_SIZE / 32;

    int row = blockIdx.x;
    int tid = threadIdx.x;
    int warp_id = tid / 32;
    int lane_id = tid % 32;

    const float* x_row = X + row * N;
    float*       y_row = Y + row * N;

    // ============================================================
    // Pass 1, Step A: 线程内串行 online 递推
    // 每个线程扫自己的 strided slice: tid, tid+BLOCK_SIZE, tid+2*BLOCK_SIZE, ...
    // 结束后, 每个线程持有局部 (m, d)
    // ============================================================
    float m = -INFINITY;   // running max  (identity)
    float d = 0.0f;        // running normalizer (identity)

    for (int i = tid; i < N; i += BLOCK_SIZE) {
        float xi = x_row[i];
        // TODO 2: 把 (xi, 1) 这个"单元素状态"合并进 (m, d)
        // 提示: 直接调用 merge_online(m, d, xi, 1.0f)
        //       或者手写一遍递推也行 (推荐手写一次以巩固记忆)
        merge_online(m, d, xi, 1.0f);
    }

    // ============================================================
    // Pass 1, Step B.1: warp 内 butterfly reduce
    // 用 __shfl_xor_sync 让每个 lane 拿到对端的 (m, d), 然后 merge
    // butterfly 模式: offset = 16, 8, 4, 2, 1
    // 结束后, 同一个 warp 内的所有 32 个 lane 都持有相同的 warp 级 (m, d)
    // ============================================================
    unsigned mask = 0xffffffff;
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        // TODO 3: 用 __shfl_xor_sync 拿到对端 lane 的 m_other, d_other
        //         然后用 merge_online 合并到本地 (m, d)
        // 提示:
        //   float m_other = __shfl_xor_sync(mask, m, offset);
        //   float d_other = __shfl_xor_sync(mask, d, offset);
        //   merge_online(m, d, m_other, d_other);
        float m_other = __shfl_xor_sync(mask, m, offset);
        float d_other = __shfl_xor_sync(mask, d, offset);
        merge_online(m, d, m_other, d_other);
    }

    // ============================================================
    // Pass 1, Step B.2: 跨 warp reduce (用 shared memory)
    // 每个 warp 的 lane 0 把 warp 级 (m, d) 写到 shared memory
    // 然后让 warp 0 把 N_WARPS 个值再 reduce 一次
    // ============================================================
    __shared__ float s_m[N_WARPS];
    __shared__ float s_d[N_WARPS];

    if (lane_id == 0) {
        s_m[warp_id] = m;
        s_d[warp_id] = d;
    }
    __syncthreads();

    if (warp_id == 0) {
        // 让 warp 0 的前 N_WARPS 个 lane 装入数据, 其余装 identity
        m = (lane_id < N_WARPS) ? s_m[lane_id] : -INFINITY;
        d = (lane_id < N_WARPS) ? s_d[lane_id] : 0.0f;

        // TODO 4: 在 warp 0 内做一次 butterfly reduce (规模为 N_WARPS)
        //         注意 offset 上界不再是 16, 而是 N_WARPS / 2
        //         (例如 BLOCK_SIZE=256, N_WARPS=8, offset 取 4, 2, 1)
        // 提示: 写一个 #pragma unroll for 循环, 同上面 Step B.1
        #pragma unroll
        for (int offset = N_WARPS / 2; offset > 0; offset >>= 1) {
            float m_other = __shfl_xor_sync(mask, m, offset);
            float d_other = __shfl_xor_sync(mask, d, offset);
            merge_online(m, d, m_other, d_other);
        }
    }

    // ============================================================
    // Pass 1, Step B.3: 把 block 级全局 (m, d) 广播给所有线程
    // ============================================================
    __shared__ float s_m_global;
    __shared__ float s_d_global;
    if (tid == 0) {       // 此时 tid==0 (即 warp 0 lane 0) 持有全局结果
        s_m_global = m;
        s_d_global = d;
    }
    __syncthreads();
    float m_global = s_m_global;
    float d_global = s_d_global;

    // ============================================================
    // Pass 2: 每个线程写自己的 strided slice
    // y[i] = exp(x[i] - m_global) / d_global
    // ============================================================
    float inv_d = 1.0f / d_global;   // 用乘法替代除法 (除法在 GPU 上慢得多)
    for (int i = tid; i < N; i += BLOCK_SIZE) {
        // TODO 5: 计算 y_row[i] = exp(x_row[i] - m_global) * inv_d
        y_row[i] = __expf(x_row[i] - m_global) * inv_d;
    }
}

// ----------------------------------------------------------------
// host launcher
// ----------------------------------------------------------------
void launch_online_softmax(const float* d_X, float* d_Y, int M, int N, cudaStream_t stream = 0) {
    constexpr int BLOCK_SIZE = 256;   // 8 个 warp
    // 前置条件检查 (生产代码会用 cuda assert; 这里只是说明)
    // assert(N >= BLOCK_SIZE);
    // assert(BLOCK_SIZE <= 1024);

    online_softmax_kernel<BLOCK_SIZE><<<M, BLOCK_SIZE, 0, stream>>>(d_X, d_Y, N);
}
