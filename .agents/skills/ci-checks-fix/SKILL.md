---
name: "ci-checks-fix"
description: "Workflow for diagnosing and fixing MR CI Checks failures from downloaded log files. Invoke when the user reports a failed CI check (build/test/lint/pipeline gate) and provides a log file path. Reads only the key parts of logs, classifies the failure, proposes fixes, and records every change to a local doc."
---

# CI Checks 问题修复工作流

这个 skill 用于排查并修复 MR (Merge Request) 界面 Checks 选项卡里报红的 CI 问题。

适用场景：
- 用户描述某个 CI Check 失败（Build / Test / Lint / Pipeline 门禁）
- 用户给出该 Check 对应的日志文件路径（已下载到本地，通常在 `.local_workspace/logs/`）
- 需要判断"是不是代码问题、是不是我该修的、怎么修、怎么验证"

本 skill 与 `my-workflow` 叠加使用：沿用"先结论、后细节"和"对话即时说明 + 文档同步沉淀"的风格，本文件只补充 CI 排查特有的流程。

## 标准交互流程

用户每给一个 CI 问题，默认按以下顺序处理：

1. **接收**：用户描述问题现象 + 给出日志文件路径。
2. **过滤读日志**（关键约束，见下节）：不全读，先用 Grep 抓错误行，再按行号定点 Read 上下文。
3. **分类判断**：判定失败属于哪一类（见"三类失败分流"），明确"该不该你修"。
4. **给出修改**：只有判定为真实代码问题时才动代码；修改前必须核实被调用的真实接口签名/实现，不凭空写。
5. **如实记录**：把本次的判断、改动、依据、验证方式同步写入 `.local_workspace/docs` 的修复记录文档。
6. **对话里同时给出结论**：分类结果、根因、改了什么、下一步验证，必须在当前回复中说明，不能只落文档。

## 读日志的约束（省上下文）

CI 日志常常几百 KB 到几 MB，**绝不整文件读**，按以下顺序：

1. **先 Grep 抓错误**，限制 `head_limit`，常用 pattern：
   ```
   error:|Error|FAILED|\[  FAILED  \]|Failure|undefined reference|undefined symbol|
   cannot|abstract type|fatal error|ld returned|Segmentation|core dumped|
   terminate called|CHECK failed|Check failed|abort|permission|could not be found|Failed in
   ```
2. **再定点 Read**：拿到命中行号后，用 `offset` + 小 `limit`（20-40 行）读错误前后上下文，看清是哪个文件/行/符号。
3. **确认收尾状态**：找构建/测试工具的总结行（如 `blade error (ECOMPILE)`、`Exit Code`、`real ...` 耗时），确认失败发生在哪个阶段。
4. 只有定位仍不清时，才扩大读取范围；优先扩 Grep pattern 而不是盲读大段。

判断失败"阶段"很重要：拉依赖阶段失败 ≠ 编译失败 ≠ 测试运行失败，三者根因和归属完全不同。

## 三类失败分流

把每个红 Check 归到下面三类之一，决定该不该改代码：

| 类型 | 典型特征 / 例子 | 该不该你修 | 处理方式 |
|------|----------------|-----------|---------|
| **流程门禁** | MR Title Lint（正则不匹配标题）、LineChecker（`add > 限制`，提示拆 MR） | 否 | 改标题 / 忽略（若原 MR 也撞同样门禁）/ 找 mentor 确认豁免 |
| **环境/依赖** | 卡在 `Downloading dependencies` / clone / setup 阶段；报 `repo could not be found or you don't have permission`、403/404；失败模块不是你改的模块 | 否 | 非代码问题，找 owner / 平台；对照原 MR 是否同样红 |
| **真实代码失败** | 编译 `error:`（如 has no member、undefined reference、cannot instantiate abstract）、链接失败、测试断言失败 / 运行崩溃 | **是** | 这是你的目标，定位并修复 |

**关键经验**：
- 重构类 MR 最常见的真实问题是"改了被测代码/接口，漏改调用方或测试" → 表现为编译 `has no member named` / `undefined reference`。
- 同一个失败若在 mentor 的原 MR（如 `HEAD Branch: zmx/...`）上也存在，且属于门禁/依赖类，通常不是本次重构引入，不归你修。
- 判断归属时看 Job Metadata 的 `HEAD Branch` / `HEAD SHA` / `Actor`，确认这条日志到底跑的是谁的分支。

## 改代码的纪律

只有判定为"真实代码失败"才动代码，且：

- **先核实真实接口**：改测试/调用方前，必须 Read 新接口的头文件和实现，确认签名、参数顺序、语义，不靠猜。
- **保证语义等价**：替换旧 API 为新 API 时，要说清为什么等价（数据布局、恒等条件、算法是否只是搬位置没改逻辑）。
- **本机无 GPU / 无法本地复现时**，明确说明"本地验证不了，靠远程 CI 验"，不假装验证通过。
- 本机 clang 对 CUDA 头（`cuda_runtime.h not found`）等误报可忽略，但要点明这是误报、CI 用 nvcc。

## 保留式修改与标注规范（重要）

这是本工作流的明确偏好：**修复时尽量不直接删除原有代码和注释，改为注释保留**，方便日后对照"原来是什么、为什么改"。

具体规则：

- **统一动作标签**：每个 `[CI-FIX ...]` 标注块用一个动作词说明本处改动类型，固定三种：
  - `新增`：本次新写的代码或注释。
  - `停用`：原代码不物理删除，仅注释掉保留（"停用"准确表达"代码还在、只是不参与编译"，避免用"删除"误导）。
  - `补充`：对别人原有注释的补充/不同说明——不改原注释，在其下方新增 `补充` 注释表达自己的观点。
- **不直接删旧代码**：被替换/不再需要的旧代码（旧 API 调用、随之失效的脚手架变量、对应的 free/cleanup）用 `停用` 注释保留，不要物理删除。
- **不丢失原有信息注释**：旧代码上原本承载额外信息的注释要一并保留。
- **绝不修改或删除别人原有的注释**：原作者写的注释一字不动地保留下来（连同被注释的旧代码一起保留）。如果想表达不同/补充的说明，用 `[CI-FIX ...] 补充:` 在其下方**新增**自己的注释，而不是改写或删掉原注释。校验方式：`git diff` 中删除行（`-`）应只有代码、不应包含任何原始注释行。
- **新增代码也要配注释**：所有新增的代码（新 include、新实例化、新 API 调用等）都要搭配 `[CI-FIX ...] 新增:` 说明注释，讲清这行新增是为解决哪个 Check、做什么、参数含义、与旧代码的对应关系。宁可注释偏多——可追溯优先，后续若要清理可统一检索 `[CI-FIX` 前缀批量删除。
- **每处改动加标注块**，至少包含：
  - 标签前缀：`[CI-FIX <Check 名称> @<改动人，如 sunduo.2027>] <动作词:新增/停用/补充>`
  - 为解决什么问题（哪个 CI Check、什么报错）
  - 为什么这么改 / 新旧为何等价
  - 紧跟其后用注释保留被停用的原始代码
- 标注块统一格式示例：

  ```cpp
  // [CI-FIX EmbeddingModuleTest @sunduo.2027] 停用: 重构(MR<编号>)删除了 X::SwapOut,
  // 逻辑迁入 IConverter。编译报错 "has no member named 'SwapOut'"。
  // 因 <等价性原因>,改用 converter.compress。原调用注释停用如下:
  // amp.SwapOut(meta, 1, d_hvi, d_swap_out, 0);
  // [CI-FIX EmbeddingModuleTest @sunduo.2027] 新增: 用新接口替代,等价于旧 SwapOut。
  newApi.compress(...);
  ```

- **取舍**：注释保留旧脚手架后，原本"删变量避免 unused 报错"的顾虑自然消除（被注释的变量不参与编译）；保持可追溯性优先于代码简洁。
- 这是本工作流相对通用"少写注释"准则的**有意例外**——CI 修复场景重在可追溯、可回看，故采用保留式修改。

## 修复记录文档（必做）

每处理完一个 CI 问题，把改动如实记录到 `.local_workspace/docs` 下的修复记录文档，方便用户回看"到底改了什么"。

- 文档命名建议：按 MR 维度建一份，如 `CI_FIX_LOG_MR<编号>.md`（例：`CI_FIX_LOG_MR34249.md`）。
- **同一个 MR 复用同一份文档**，每个新 Check 问题在文档里追加一节，不要每次新建零散文档。
- 每节按以下结构记录（先结论后细节）：

  ```
  ## <Check 名称> — <日期>
  - 分类：流程门禁 / 环境依赖 / 真实代码失败
  - 该不该我修：是 / 否（原因）
  - 日志：<本地日志路径> + 关键错误行号
  - 根因：<一句话>
  - 改动：<文件 + 具体改了什么>（无改动则写"无，已说明归属"）
  - 等价性/依据：<为什么这么改是对的>
  - 验证方式：<靠哪个 CI Check 转绿 / 本地能否验>
  - 状态：已修待验 / 已验证通过 / 搁置（非代码）
  ```

- 文档顶部维护一个"分流总账"小表，汇总该 MR 所有 Check 的分类与状态，便于一眼看全貌。
- 文档持久化不替代对话输出：对话里即时给结论，文档里同步沉淀。

## 默认回答模板（CI 场景）

如无更强约束，优先接近下面结构：

1. **分类结论**：这是哪一类失败、该不该你修。
2. **根因**：失败在哪个阶段、哪个文件/符号、为什么。
3. **修改方案**（若需改）：改什么、为什么等价、怎么验证。
4. **下一步**：push 验证哪个 Check / 找谁 / 搁置。
5. **已同步到文档的内容摘要**。

其中第 1、2 项必须先在对话里给出，不能只落文档。

## 与同步/提交工作流的衔接

- 本机写代码，靠远程 CI 验证（本机常无 GPU）。
- 改完默认**先不自动 commit/push**，除非用户明确要求；push 前可提示用户是否需要先 rebase 对齐 mentor 最新分支，避免修了过时代码。
- 验证分支与目标分支的约束遵循 `DEV_WORKFLOW.md`：不直接改 master，改动只在个人分支。
