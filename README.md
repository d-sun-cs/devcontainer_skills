# devcontainer_skills

这个仓库现在同时支持三种使用方式：

1. 作为一个可自举的开发容器仓库使用：直接用 `.devcontainer/` 构建 Linux 容器环境。
2. 作为一个普通的 skills 仓库使用：在已经有 AI agent 的 Linux、macOS、Windows 环境里直接 `git clone` 并使用仓库内的 `.agents/skills/`。
3. 作为中央 skills registry 使用：默认每个项目用 `.agents/skills.yaml` 声明自己启用哪些 skill，再从本仓库同步项目副本。

核心目标只有一个：**中央 skill 的唯一真源始终是仓库内的 `.agents/skills/`，并且具体项目只安装自己需要的 skill 副本。**

## 仓库原则

- skill 真源只有一份：`.agents/skills/`
- 默认 `.agents` 布局项目只通过 `.agents/skills.yaml` 选择启用的 skill
- 不复制 skill 到 home 目录
- 不把 tool-specific 目录当作真源
- 凭证、token、用户本地配置不进 Git（例如 `.lark-cli/`）
- devcontainer 是可选运行时，不是唯一运行时

## 目录约定

```text
devcontainer_skills/
├── .agents/skills/      # 所有 skills 的唯一真源
├── .devcontainer/       # 可选：自举 Linux 容器环境
├── registry.yaml         # 中央 skill 索引
├── scripts/skillsctl.py  # 跨平台安装 / 同步 / 回流脚本
├── templates/            # 项目 manifest 模板
└── README.md            # 仓库级说明
```

目标项目中的结构：

```text
target-project/
└── .agents/
    ├── skills.yaml       # 这个项目启用哪些 skills
    ├── skills.lock.yaml  # 上次安装的中央 commit 和 skill hash
    └── skills/           # 从中央仓库复制出来的项目副本
```

默认布局下，`.agents/skills.yaml` 是中央托管白名单。项目里的 `.agents/skills/` 可以额外放 `local-only` skill，例如飞书、本地凭证、项目私有 workflow 或临时实验 skill。只要它们不写进 `skills.yaml`，中央 `sync` 就不会覆盖它们，`promote` 也不会自动回流它们。

目标布局由 `--project` 和 `--layout` 共同决定：

```text
<project-root>/<layout>/
├── skills.yaml       # managed skill manifest
├── skills.lock.yaml  # installed source hashes
└── skills/           # installed skill copies
```

`--project` 永远指项目根目录。`--layout` 是这个根目录下的 agent 配置目录名，默认是 `.agents`。如果目标工具使用 `.codex`、`.claude`、`.kiro`、`.trae` 等目录，就显式传 `--layout .codex` / `--layout .claude` / `--layout .kiro` / `--layout .trae`。manifest 会把这个目录名原样记录为 `target_layout`，后续同步按同一目录执行。

`templates/` 只保留两类模板：

- `project-skills.yaml`：默认 `.agents` 布局项目使用。
- `custom-layout-skills.yaml`：`.codex`、`.claude`、`.kiro`、`.trae` 或其他单目录 agent layout 共用；复制后把 `target_layout` 改成实际目录名即可。

不为每个 agent 工具单独维护一份几乎相同的模板。真正的差异由 `--layout` 参数和 manifest 里的 `target_layout` 表达，这样新增工具时不用改仓库结构。

本仓库只管理你点名托管的 personal skills，不管理工具自带的系统 skills，也不管理插件缓存里的 skills。

## 快速开始

### 方式一：已有 AI agent 环境

适用于本地 TRAE Solo/IDE、Claude Code、Codex CLI、Gemini CLI、Kiro 等已经能运行的环境。

1. 克隆仓库：

```bash
git clone git@github.com:d-sun-cs/devcontainer_skills.git
cd devcontainer_skills
```

2. 让 agent 读取本仓库：

- 优先让它直接读取 `.agents/skills/`
- 仓库规范集中在 `README.md`、`registry.yaml` 和 `scripts/skillsctl.py`
- 如果某个工具强依赖 manifest，再在本地临时生成最小 `AGENTS.md`
- 只有当工具既不支持 workspace 扫描，也不支持 manifest 时，才在仓库内生成本地适配目录（例如 `.claude/`、`.kiro/`）。这些目录不是 skill 真源，也不应提交进 Git

3. 用 Git 管理更新：

```bash
git pull
git status
git add .
git commit -m "update skills"
```

### 方式二：作为中央 registry 管理项目 skills

先进入中央仓库根目录：

```bash
cd /path/to/devcontainer_skills
```

Windows PowerShell：

```powershell
Set-Location C:\Users\Admin\Documents\PKM整理思考\devcontainer_skills
```

#### 核心概念

`skillsctl.py` 只管理写进 `<layout>/skills.yaml` 的 skills。这些 skills 叫 **managed skills**。

没有写进 `<layout>/skills.yaml`、但实际存在于 `<layout>/skills/` 的 skills 叫 **local-only skills**。它们可以是飞书、本地凭证、项目私有 workflow、临时实验 skill。`sync` 不会覆盖它们，`promote` 不会自动回流它们，`remove --clean` 也不会清理它们。

路径由两个参数决定：

```text
--project = 项目根目录
--layout  = 项目根目录下的 agent 配置目录名，默认 .agents
```

默认项目：

```text
/path/to/project/.agents/skills.yaml
/path/to/project/.agents/skills.lock.yaml
/path/to/project/.agents/skills/
```

使用 `.codex` 的工具：

```text
~/.codex/skills.yaml
~/.codex/skills.lock.yaml
~/.codex/skills/
```

实际路径中没有空格，写成：

```text
~/.codex/skills.yaml
```

#### 常用命令

列出中央仓库当前有哪些 skills：

```bash
python scripts/skillsctl.py list
```

默认输出是适合终端扫读的短表格，包含 skill 名、分类和 `registry.yaml` 里的短摘要。

只看 skill 名，方便复制到 `install`：

```bash
python scripts/skillsctl.py list --names-only
```

查看完整触发描述：

```bash
python scripts/skillsctl.py list --verbose
```

查看某个项目当前哪些是 managed、哪些是 local-only：

```bash
python scripts/skillsctl.py status --project /path/to/project
```

Windows Codex Desktop 示例：

```powershell
python .\scripts\skillsctl.py status --project C:\Users\Admin --layout .codex
```

给项目添加 managed skills：

```bash
python scripts/skillsctl.py install --project /path/to/project my-workflow leetcode-reasoning
```

Windows Codex Desktop 示例：

```powershell
python .\scripts\skillsctl.py install --project C:\Users\Admin --layout .codex my-workflow intern-daily-report
```

`install` 会做三件事：

1. 把这些 skill 写入 `<layout>/skills.yaml`
2. 从中央仓库复制到 `<layout>/skills/<name>/`
3. 写入 `<layout>/skills.lock.yaml`

同步中央仓库到项目：

```bash
python scripts/skillsctl.py sync --project /path/to/project
```

Windows Codex Desktop 示例：

```powershell
python .\scripts\skillsctl.py sync --project C:\Users\Admin --layout .codex
```

`sync` 只同步 `<layout>/skills.yaml` 里的 managed skills。它不会扫描并同步整个 `<layout>/skills/` 目录，也不会碰 local-only skills。

如果 managed skill 在项目里被改过，`sync` 会停止，避免覆盖你的本地改动。你有两个选择：

```bash
python scripts/skillsctl.py promote --project /path/to/project changed-skill
```

或者确认要丢弃本地改动：

```bash
python scripts/skillsctl.py sync --project /path/to/project --force
```

从项目取消托管某个 skill，但保留中央仓库里的源版本：

```bash
python scripts/skillsctl.py remove --project /path/to/project old-skill
```

彻底废弃某个中央 skill，同时从当前项目白名单、项目副本、中央仓库和 `registry.yaml` 删除：

```bash
python scripts/skillsctl.py remove --project /path/to/project --central old-skill
```

Windows Codex Desktop 示例：

```powershell
python .\scripts\skillsctl.py remove --project C:\Users\Admin --layout .codex --central old-skill
```

把项目里的 skill 回流中央仓库：

```bash
python scripts/skillsctl.py promote --project /path/to/project my-new-skill
```

如果 skill 在 `.codex` 目录里：

```bash
python scripts/skillsctl.py promote --project ~ --layout .codex my-new-skill
```

默认情况下，`promote` 会把这个 skill 加进该项目 `<layout>/skills.yaml`，让它从此成为这个项目的 managed skill。如果只想回流中央、但暂时不让当前项目托管它，可以加：

```bash
python scripts/skillsctl.py promote --project /path/to/project my-new-skill --no-manage-project
```

#### 如何决定管理或不管理

要让一个 skill 被中央仓库管理，用 `install` 或 `promote`：

```bash
python scripts/skillsctl.py install --project /path/to/project existing-central-skill
python scripts/skillsctl.py promote --project /path/to/project new-general-skill
```

要让一个 skill 保持本地专用，不要把它写进 `<layout>/skills.yaml`。可以直接把它放在：

```text
<project-root>/<layout>/skills/local-only-skill/
```

只要它不在 `<layout>/skills.yaml` 里，`status` 会显示：

```text
local-only: local-only-skill
```

要取消中央托管：

```bash
python scripts/skillsctl.py remove --project /path/to/project managed-skill
```

取消后，它不再出现在 `<layout>/skills.yaml` 中；再次 `sync --clean` 时，脚本只会清理过去由 lock 记录过的 managed 副本，不会删除其他 local-only skills。

### 方式三：使用 devcontainer

适用于你希望仓库自己提供完整容器环境时：

1. 用支持 Dev Containers 的 IDE 打开仓库
2. 选择 “Reopen in Container”
3. 容器启动后，继续使用仓库内 `.agents/skills/`

这条路径仍然成立，但它不再是本仓库的唯一使用方式。

## Windows / macOS / Linux 约束

### Git 与换行

仓库提供了 `.gitattributes`：

- `.sh`、`.md`、`.json`、`Dockerfile` 固定为 LF
- `.ps1`、`.bat`、`.cmd` 固定为 CRLF

这样做是为了避免：

- Windows 拉取后 shell 脚本被 CRLF 破坏
- 不同平台之间频繁出现无意义换行 diff

### 路径约束

文档和 skill 规则默认使用以下相对路径：

- 仓库根：`.` 或“当前仓库根目录”
- skill 真源：`.agents/skills/`

不要把 `/workspaces/devcontainer_skills`、`/home/vscode`、`C:\\Users\\...` 这种机器相关绝对路径写成规则本身。绝对路径只能出现在本地临时命令里。

### 工具适配约束

优先级固定如下：

1. 工具直接扫描 `.agents/skills/`
2. 必要时本地临时生成 manifest
3. 工具必须要求特定目录时，在仓库内创建本地适配目录

不建议默认依赖 symlink。原因很直接：

- Windows 对 symlink 有权限/开发者模式要求
- 一些 Git/IDE 环境对 symlink 处理不稳定
- 这会把跨平台问题提前引入

如果实在需要目录映射：

- macOS / Linux：优先用 symlink
- Windows：优先用目录 junction

但这些都只是本地适配层，不是仓库真源。

## Git 管理规则

### 应提交

- `.agents/skills/**`
- `registry.yaml`
- `scripts/skillsctl.py`
- `templates/**`
- `README.md`
- 与 skill 使用规则相关的文档

### 不应提交

- `.lark-cli/`
- 各类 token、账号配置、缓存
- 本地 agent 适配目录（如 `.claude/`、`.kiro/`、`.codex/`）
- 环境专用 skill（如 `lark-*`、本地凭证或账号绑定类 skill）
- 默认不提交的 `AGENTS.md`

## 项目侧提交建议

在默认 `.agents` 布局项目中，推荐提交：

- `.agents/skills.yaml`
- `.agents/skills.lock.yaml`
- `.agents/.gitignore`

默认不提交：

- `.agents/skills/`

如果某个项目需要完全离线运行，可以在安装时加 `--track-installed`，然后把 `.agents/skills/` 一起提交。
