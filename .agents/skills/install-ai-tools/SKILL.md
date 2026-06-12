---
name: install-ai-tools
description: 在当前环境中安装新的 AI CLI 工具（如 codex-cli、@anthropic-ai/claude-code、kiro-cli、gemini-cli 等），并保证新工具能够发现仓库内的 `.agents/skills/`。适用于 devcontainer、Linux/macOS 本地环境和 Windows 本地环境。
---

# Install AI Tools — 安装新的 AI CLI 并接入本仓库 skills

## 何时使用

- 用户说 "帮我装一下 codex / claude-code / kiro-cli / gemini-cli ..." 等任何 AI 编码助手的命令行
- 用户运行 `npm i -g <pkg>` 遇到 `EACCES` / 权限被拒
- 用户问 "怎么不用 sudo 全局安装 npm 包"
- 新装的 AI 工具启动后读不到本仓库 `.agents/skills/` 里的 skill

## 环境约束（先读再动手）

- 仓库根目录记作 `<repo-root>`
- 所有 skill 的唯一真源：`<repo-root>/.agents/skills/`
- 不把任何 tool-specific 目录当作真源
- 先确认当前环境是 Linux、macOS 还是 Windows，再选择对应命令
- 仓库存储规则详见 [skills-management](../skills-management/SKILL.md)

建议先定位仓库根目录：

```bash
git rev-parse --show-toplevel
```

PowerShell:

```powershell
git rev-parse --show-toplevel
```

## Step 0 — 一次性设置：把 npm 全局前缀挪到用户家目录

只在第一次安装 AI CLI 时做，幂等，重复执行无害。**不要使用 `sudo npm i -g`** 或管理员权限全局安装第三方 CLI，后续 update/uninstall 会越来越难维护。

### Linux / macOS

```bash
mkdir -p "$HOME/.npm-global"
npm config set prefix "$HOME/.npm-global"

LINE='export PATH="$HOME/.npm-global/bin:$PATH"'
for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$RC" ] || continue
  grep -qxF "$LINE" "$RC" || echo "$LINE" >> "$RC"
done

export PATH="$HOME/.npm-global/bin:$PATH"

npm config get prefix
```

### Windows PowerShell

```powershell
$NpmGlobal = Join-Path $HOME ".npm-global"
New-Item -ItemType Directory -Force -Path $NpmGlobal | Out-Null
npm config set prefix $NpmGlobal

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$NpmGlobal*") {
  [Environment]::SetEnvironmentVariable(
    "Path",
    "$UserPath;$NpmGlobal",
    "User"
  )
}

$env:Path = "$NpmGlobal;$env:Path"
npm config get prefix
```

完成后，当前会话以及后续新开的 shell 都可以裸跑 `npm i -g <pkg>`。

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

PowerShell:

```powershell
Get-Command <bin>
<bin> --version
```

如果命令找不到，多半是 PATH 还没重新加载。

## Step 2 — 让新工具发现 `.agents/skills/`（本仓库的特殊要求）

**核心原则：优先依赖工具原生扫描；其次使用仓库根目录 `AGENTS.md`；只有都不支持时，才在仓库内创建本地兼容层。绝不在 `$HOME` 下建任何 skill 副本。**

按以下顺序处理：

### 2.1 先确认工具的 skill 发现机制

可以从下面任一入口查清楚：

1. 工具官方文档 / `--help` 输出
2. 启动一次工具，观察 startup 日志里它扫描了哪些目录
3. 在 workspace 根跑 `<tool> --print-config` 之类的命令（不同工具命名不同）
4. 直接 `grep` 工具的 npm 包源码：`grep -r "skills" $(npm root -g)/<pkg>/`

需要回答两个问题：
- **它读不读 workspace 下的某个目录？** （workspace 模式 vs home 模式）
- **它期望的入口是什么？** （`.agents/skills/`、`.claude/skills/`、`.kiro/skills/`、`AGENTS.md`、`CLAUDE.md` ...）

### 2.2 工具已经能扫描 `.agents/skills/` → 什么都不做

直接列一个 skill 让它复述名字 / 描述，验证可见即可。例如：

```bash
# 在工具的对话里
> 列出当前可用的 skills，并告诉我 leetcode-reasoning 是做什么的
```

### 2.3 工具支持 manifest → 让它读取 `AGENTS.md`

如果工具默认读取仓库根目录的 manifest 文件，优先使用仓库里的 `AGENTS.md`，不要再复制一份技能目录。

### 2.4 工具只认某个特定目录 → 在仓库内建本地兼容层

**兼容层方向永远是 “工具期望路径 → `.agents/skills/`”**，反过来会让真源依赖错误位置。

Linux / macOS：

```bash
cd <repo-root>
ln -s .agents .kiro

mkdir -p .claude
ln -s ../.agents/skills .claude/skills
```

Windows PowerShell：

```powershell
Set-Location <repo-root>
New-Item -ItemType Junction -Path .kiro -Target .agents

New-Item -ItemType Directory -Force -Path .claude | Out-Null
New-Item -ItemType Junction -Path .claude\skills -Target ..\.agents\skills
```

已知映射：

| 工具 | 期望路径 | 处理方式 |
| --- | --- | --- |
| Kiro | `.kiro/skills/` | 优先直读 `.agents/skills/`；不行再建 `.kiro` 兼容层 |
| Claude Code | `.claude/skills/` 或 manifest | 优先读取 `AGENTS.md`；不行再建 `.claude/skills` 兼容层 |
| Codex CLI | manifest 为主 | 优先读取 `AGENTS.md` |
| 其它 | 装完现场确认 | — |

## Step 3 — 验证清单

每装完一个新工具，跑一遍这三条：

```bash
# 1. 工具本身可用
which <bin> && <bin> --version

# 2. 仓库内真源存在
test -d .agents/skills

# 3. 真源唯一：除了 .agents/skills/ 外不应有第二份被提交的真目录
find . -maxdepth 3 -name 'skills' -type d
```

如果第 3 步出现额外的真实目录而不是兼容层，说明某个工具自己写了一份副本。应立刻删除副本，回到 `.agents/skills/` 单一真源。

## 常见陷阱

1. **用 sudo 装 npm 全局包**：会把 `~/.npm` 的部分缓存改成 root，下次非 sudo 操作就 EACCES。如已发生，跑 `sudo chown -R $(id -u):$(id -g) "$HOME/.npm" "$HOME/.npm-global"` 修回。
2. **在 `~/.kiro/skills`、`~/.claude/skills` 建副本或 symlink**：违反本仓库存储规则；一律改成仓库内兼容层。
3. **复制而非兼容映射**：`cp -r .agents/skills .claude/skills` 会产生第二份真源，后续一定漂移。
4. **只写 Linux 路径说明**：`/workspaces/devcontainer_skills`、`/home/vscode` 之类路径不能写成跨平台规则。
5. **Windows 默认依赖 symlink**：很多本地环境没有开启对应权限，优先用 junction 或 manifest。
6. **工具说 "skill 没找到"**：先确认它能否读 `.agents/skills/` 或 `AGENTS.md`，再决定是否创建兼容层。

## 给 agent 的执行模板

收到 "帮我装 X" 后，按这个顺序：

1. 判断当前 OS 和 shell
2. 跑 `npm config get prefix`；若为系统目录 → 先做 Step 0
3. 确认仓库根目录和 `.agents/skills/` 存在
4. 执行 Step 1 安装命令并验证 `--version`
5. 不带任何参数启动一次工具（或读其文档），定位 skill 发现路径
6. 按 2.2 / 2.3 / 2.4 处理
7. 跑 Step 3 验证清单
8. 把新增的工具映射补回本 SKILL.md，方便下次复用
