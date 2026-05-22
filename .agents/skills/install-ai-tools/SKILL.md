---
name: install-ai-tools
description: 在本 devcontainer 中以非 root（vscode 用户）身份安装新的 AI CLI 工具（如 codex-cli、@anthropic-ai/claude-code、kiro-cli、gemini-cli 等），并保证新工具能够发现 workspace 下的 `.agents/skills/`。当用户要求安装/升级 AI 编码助手 CLI、遇到 `npm i -g` 权限问题、或新工具装完后读不到已有 skills 时触发。
---

# Install AI Tools — 安装新的 AI CLI 并接入本仓库 skills

## 何时使用

- 用户说 "帮我装一下 codex / claude-code / kiro-cli / gemini-cli ..." 等任何 AI 编码助手的命令行
- 用户运行 `npm i -g <pkg>` 遇到 `EACCES` / 权限被拒
- 用户问 "怎么不用 sudo 全局安装 npm 包"
- 新装的 AI 工具启动后读不到本仓库 `.agents/skills/` 里的 skill

## 环境约束（先读再动手）

- 容器镜像：`mcr.microsoft.com/devcontainers/base:noble`，预装 Node.js 22 / npm 10
- 当前用户：`vscode`（非 root，UID 1000）
- 默认 npm prefix 是 `/usr`（root 拥有），所以裸 `npm i -g` 一定 EACCES
- workspace 根目录：`/workspaces/devcontainer_skills`
- 所有 skill 的唯一真源：`/workspaces/devcontainer_skills/.agents/skills/`
- 已存在的工具入口：`.kiro -> .agents`（workspace 内 symlink，给 Kiro 用）
- 仓库存储规则详见 [skills-management](../skills-management/SKILL.md)

## Step 0 — 一次性设置：把 npm 全局前缀挪到用户家目录

只在第一次安装 AI CLI 时做，幂等，重复执行无害。**不要使用 `sudo npm i -g`**（postinstall 脚本以 root 跑第三方代码，且后续 update/uninstall 会持续陷在 sudo 里）。

```bash
# 1. 用户级全局目录
mkdir -p "$HOME/.npm-global"
npm config set prefix "$HOME/.npm-global"

# 2. 把 bin 永久加进 PATH（bash + zsh，幂等）
LINE='export PATH="$HOME/.npm-global/bin:$PATH"'
for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$RC" ] || continue
  grep -qxF "$LINE" "$RC" || echo "$LINE" >> "$RC"
done

# 3. 当前会话立即生效
export PATH="$HOME/.npm-global/bin:$PATH"

# 4. 验证
npm config get prefix    # 应输出 /home/vscode/.npm-global
```

完成后，本会话以及所有新开的 shell 都可以裸跑 `npm i -g <pkg>`，不需要 sudo。

## Step 1 — 安装目标 AI CLI

只列已验证可用的官方包名。其它工具按相同模式即可。

| 工具 | 安装命令 | 启动命令 |
| --- | --- | --- |
| OpenAI Codex CLI | `npm i -g @openai/codex` | `codex` |
| Anthropic Claude Code | `npm i -g @anthropic-ai/claude-code` | `claude` |
| Google Gemini CLI | `npm i -g @google/gemini-cli` | `gemini` |
| Kiro CLI | 见各发行渠道（通常非 npm，参考官方文档） | `kiro` |

安装完成后立刻验证：

```bash
which <bin> && <bin> --version
```

如果 `which` 找不到，多半是 PATH 没加载，重开终端或 `source ~/.bashrc`。

## Step 2 — 让新工具发现 `.agents/skills/`（本仓库的特殊要求）

**核心原则：优先依赖工具原生扫描；只有当原生不支持时，才在 workspace 内创建软链接。绝不在 `$HOME` 下建任何 skill symlink。**

按以下顺序处理：

### 2.1 先确认工具的 skill 发现机制

可以从下面任一入口查清楚：

1. 工具官方文档 / `--help` 输出
2. 启动一次工具，观察 startup 日志里它扫描了哪些目录
3. 在 workspace 根跑 `<tool> --print-config` 之类的命令（不同工具命名不同）
4. 直接 `grep` 工具的 npm 包源码：`grep -r "skills" $(npm root -g)/<pkg>/`

需要回答两个问题：
- **它读不读 workspace 下的某个目录？** （workspace 模式 vs home 模式）
- **它期望的目录名是什么？** （`.agents/skills/`、`.claude/skills/`、`.kiro/skills/`、`AGENTS.md`、`CLAUDE.md` ...）

### 2.2 工具已经能扫描 `.agents/skills/` → 什么都不做

直接列一个 skill 让它复述名字 / 描述，验证可见即可。例如：

```bash
# 在工具的对话里
> 列出当前可用的 skills，并告诉我 leetcode-reasoning 是做什么的
```

### 2.3 工具只认某个特定目录 → 在 workspace 内建软链接

**链接方向永远是 "工具期望路径 → `.agents/skills/`"**，反过来会让真源指向错误位置。

```bash
cd /workspaces/devcontainer_skills

# 通用模板：<tool-dir> 是工具期望的目录名
# 如果工具想要 .<tool>/skills（一个父目录，里面放 skills 子目录）：
ln -s .agents .<tool>            # e.g. ln -s .agents .kiro

# 如果工具直接想要 .<tool>/skills 这个具体路径：
mkdir -p .<tool>
ln -s ../.agents/skills .<tool>/skills
```

已知映射（验证过的，逐渐补充）：

| 工具 | 期望路径 | 处理方式 |
| --- | --- | --- |
| Kiro | `.kiro/skills/` | `ln -s .agents .kiro`（已存在） |
| Claude Code | `.claude/skills/`（如不再原生支持 workspace skills 则需 manifest） | `mkdir -p .claude && ln -s ../.agents/skills .claude/skills` |
| 其它 | 装完现场确认 | — |

### 2.4 工具用 manifest 文件而非目录扫描

某些工具（如 Codex CLI 默认用 `AGENTS.md`）只读一个根目录的 manifest 文件，不做目录扫描。这种情况下：

- **不要**为每个 skill 建独立 symlink
- 在 workspace 根创建 / 追加该 manifest，把 `.agents/skills/` 作为 "external skill index" 引用进去
- manifest 的内容尽量简短：列出 skill 名 + 触发条件 + 文件路径，由工具按需读 SKILL.md

示例 `AGENTS.md` 片段：

```markdown
## Repository skills

Skill 真源在 `.agents/skills/`，按需读取对应 `SKILL.md`：

- `.agents/skills/leetcode-reasoning/SKILL.md` — 算法题逻辑推导
- `.agents/skills/ai-infra-handwriting/SKILL.md` — AI infra 手撕代码
- ...
```

## Step 3 — 验证清单

每装完一个新工具，跑一遍这三条：

```bash
# 1. 工具本身可用
which <bin> && <bin> --version

# 2. workspace 内入口存在且指向 .agents/skills/
ls -la /workspaces/devcontainer_skills/.<tool>* 2>/dev/null

# 3. 真源唯一：除了 .agents/skills/ 外不应有第二份真目录
find /workspaces/devcontainer_skills -maxdepth 3 -name 'skills' -type d
# 期望只看到一行：./.agents/skills
```

如果第 3 步出现非软链接的额外 `skills/` 目录，说明某个工具自己写了一份副本——立刻删除并改用软链接，避免后续 skill 更新只改了真源、副本不同步。

## 常见陷阱

1. **用 sudo 装 npm 全局包**：会把 `~/.npm` 的部分缓存改成 root，下次非 sudo 操作就 EACCES。如已发生，跑 `sudo chown -R $(id -u):$(id -g) "$HOME/.npm" "$HOME/.npm-global"` 修回。
2. **在 `~/.kiro/skills`、`~/.claude/skills` 建 symlink**：违反本仓库存储规则；容器重建后家目录可能不持久，且和 workspace 解耦。一律改成 workspace 内的 symlink。
3. **复制而非 symlink**：跑 `cp -r .agents/skills .claude/skills` 会产生第二份真源，skill 改一处就漂移。**永远用 `ln -s`**。
4. **proxy 没生效**：本容器 `devcontainer.json` 里设了 `http://host.docker.internal:7890`，但 npm 不读 VS Code 的 http.proxy。如果安装卡住，手动 `npm config set proxy http://host.docker.internal:7890 && npm config set https-proxy http://host.docker.internal:7890`。
5. **工具说 "skill 没找到"**：先确认它扫的不是 `~/.config/<tool>/skills` 之类的 home 路径。如是，回到 Step 2.3，让它读 workspace。

## 给 agent 的执行模板

收到 "帮我装 X" 后，按这个顺序：

1. 跑 `npm config get prefix`；若为 `/usr` 或类似系统目录 → 先做 Step 0
2. 执行 Step 1 安装命令并验证 `--version`
3. 不带任何参数启动一次工具（或读其文档），定位 skill 发现路径
4. 按 2.2 / 2.3 / 2.4 三选一处理
5. 跑 Step 3 验证清单
6. 把 "已知映射" 表里新增的工具补回本 SKILL.md，方便下次复用
