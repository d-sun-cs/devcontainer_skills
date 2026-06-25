---
name: code-change
description: Workflow for traceable, review-friendly code writing and code modification, including optimization, bug fixes, refactors, and maintainability changes, especially when preserving original code for comparison is required. Use when the user explicitly invokes this skill for coding work, or when Codex is clearly modifying code previously written by others and should keep action-prefixed, reviewable changes.
---

# Code Change 工作流

这个 skill 用于处理写代码 / 改代码任务，不只限于"优化"。只要用户显式调用它，或任务明显是在修改别人写过的代码，就按这个工作流执行。

适用场景：
- 新增或修改实现逻辑、修 bug、做小范围重构。
- 去掉重复初始化、重复同步、重复计算、无意义热路径开销。
- 小范围整理实现结构，尽量控制对外行为变化。
- 用户要求保留原代码、写清改动理由、方便 mentor review。

## 标准流程

1. **先定边界**：明确本次写 / 改代码只解决哪个具体问题，不顺手做无关重构。
2. **先读真实上下文**：确认改动点在哪里被调用、旧代码意图是什么、是否有初始化顺序或生命周期约束。
3. **确认语义变化**：说明改动前后哪些行为保持一致，哪些行为是本次有意改变；尤其关注同步、资源属性、缓存、随机性、并发等行为。
4. **保留式修改**：别人的旧代码不物理删除，改为注释停用；新增代码和新增注释要带统一动作前缀。即使只改一行代码里的一个变量，也要先把原行注释为停用，再复制一份作为新增并修改。
5. **验证格式和最小风险**：至少跑 `git diff --check`；C/C++/CUDA 改动尽量跑仓库同款 clang-format dry-run。没有本地依赖时，如实说明。
6. **沉淀到文档**：若改动来自已有 review 文档或会继续讨论，把"状态、依据、剩余风险"同步写回对应本地文档。

## 标注规范

写代码 / 改代码统一使用动作前缀，把"做了什么"直接放进方括号，格式为 `[ACTION <主题> @<改动人>]`。方括号后面直接写理由、语义说明或风险，不再重复写 `新增:`、`停用:` 这类动作词。

固定动作前缀：
- `[ADD ...]`：本次新写的代码或说明，包括复制旧行后修改出的新行。
- `[DISABLE ...]`：原代码不物理删除，仅注释掉保留，不再参与编译。
- `[NOTE ...]`：不改原注释，在其下方新增说明。

每处改动至少写清：
- 改动点是什么。
- 如果停用原逻辑，为什么可以停用。
- 新旧为什么等价，或本次有意改变了什么行为。
- 剩余验证方式或风险。

改代码的硬规则：
- 修改别人已有代码时，不能直接在原行上就地改。
- 即使只改一行里的一个变量，也要拆成两步：先用 `[DISABLE ...]` 注释停用原行；再复制一份原行，用 `[ADD ...]` 标注后改成新逻辑。
- 如果 formatter 会把单行拆成多行，仍要保留"停用旧块 + 新增新块"的结构。
- 修改函数、方法、构造函数、类、结构体、接口声明或参数列表时，
  也算改代码；需要在声明和实现处分别标注旧形态 `[DISABLE ...]`
  和新形态 `[ADD ...]`。
- 新增完整函数、方法、构造函数、类、结构体、成员变量或接口声明时，
  要在新增实体整体前写 `[ADD ...]` 注释，不只在函数体内部标注
  关键语句。
- 新增文件时，优先在文件最开头、`#include` 之前写 `[ADD ...]`
  注释，说明这个文件新增的职责和边界。若文件已有版权、shebang
  或编译器指令，则放在这些固定头信息之后。
- 新增条件分支、循环、调用块等逻辑块时，也要在逻辑块前写
  `[ADD ...]` 注释；不能只依赖上层函数注释。
- 注释默认用中文，长句拆成多行，尽量让每行保持短而易读。

示例：

```cpp
// [DISABLE TF32ConverterPerf @sunduo.2027] kernel 属性已在初始化阶段统一设置,
// 热路径每次 compress 重复设置没有改变语义,仅增加开销。原调用保留如下:
// cudaFuncSetAttribute(k_compress, cudaFuncAttributeMaxDynamicSharedMemorySize,
//                      max_smem_bytes);

// [ADD TF32ConverterPerf @sunduo.2027] 保留 smem 上限检查,
// kernel 属性设置改为只在初始化阶段执行。
```

即使是一行里的小改动，也按同样方式拆开：

```cpp
// [DISABLE PersistPeriod @sunduo.2027] period 来源改为 task 级配置,
// 原 worker 级配置读取保留如下:
// const auto period = worker_config.persist_period();

// [ADD PersistPeriod @sunduo.2027] 使用 task_config 与新调度入口保持一致。
const auto period = task_config.persist_period();
```

```cpp
// [NOTE TF32ConverterPerf @sunduo.2027] 原注释保留; 这里补充说明新入口
// 作用在 kernel 符号上,SetEmbeddingAMPGPU 初始化时已统一设置。
```

## 空行和格式

- 动作前缀标注块、被停用代码、新增代码前后必须用空行隔开，
  方便看出本次改动区域。
- 空行必须服从 formatter。不要在 `public:`/`private:`/`protected:` 后立即插空行；不要在 `if (...) {`、`else {`、`if constexpr (...) {` 后立即插空行；不要在 `}` 前立即插空行。
- 若标注代码段后面紧跟闭括号，代码段结束由闭括号自然表达，不强塞空行。
- 遇到 `else if` 等语法位置不适合直接插空行时，优先把旧分支或
  旧调用整段 `[DISABLE ...]` 注释保留，再在新完整逻辑块前写
  `[ADD ...]`。不要为了插标注新增无必要的中间变量。

## 提交前检查

- 确认 `git diff` 中没有直接就地改写别人代码；每个旧逻辑变化都能看到对应的 `[DISABLE ...]` 旧代码和 `[ADD ...]` 新代码。
- 确认 `git diff` 中删除的非空行只包含本次主动停用的代码，不包含别人原始信息注释。
- 对 C/C++/CUDA 文件运行 `git diff --check`。
- 如果本机有 clang-format，运行 CI 同款 `clang-format --style=file --dry-run --Werror` 或至少对改动文件 dry-run。
- 若本机缺少 GPU、CUDA 或 clang-format，最终回答必须明确说明未本地验证的部分。
