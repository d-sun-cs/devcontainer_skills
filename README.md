# devcontainer_skills

这个仓库现在同时支持两种使用方式：

1. 作为一个可自举的开发容器仓库使用：直接用 `.devcontainer/` 构建 Linux 容器环境。
2. 作为一个普通的 skills 仓库使用：在已经有 AI agent 的 Linux、macOS、Windows 环境里直接 `git clone` 并使用仓库内的 `.agents/skills/`。

核心目标只有一个：**skill 的唯一真源始终是仓库内的 `.agents/skills/`，并且这份真源可以被 Git 管理。**

## 仓库原则

- skill 真源只有一份：`.agents/skills/`
- 不复制 skill 到 home 目录
- 不把 tool-specific 目录当作真源
- 凭证、token、用户本地配置不进 Git（例如 `.lark-cli/`）
- devcontainer 是可选运行时，不是唯一运行时

## 目录约定

```text
devcontainer_skills/
├── .agents/skills/      # 所有 skills 的唯一真源
├── .devcontainer/       # 可选：自举 Linux 容器环境
├── AGENTS.md            # 给支持 manifest 的 AI agent 提供统一入口
└── README.md            # 仓库级说明
```

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
- 如果工具支持 manifest，读取仓库根目录的 `AGENTS.md`
- 只有当工具既不支持 workspace 扫描，也不支持 manifest 时，才在仓库内生成本地适配目录（例如 `.claude/`、`.kiro/`）。这些目录不是 skill 真源，也不应提交进 Git

3. 用 Git 管理更新：

```bash
git pull
git status
git add .
git commit -m "update skills"
```

### 方式二：使用 devcontainer

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
2. 工具读取 `AGENTS.md`
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
- `AGENTS.md`
- `README.md`
- 与 skill 使用规则相关的文档

### 不应提交

- `.lark-cli/`
- 各类 token、账号配置、缓存
- 本地 agent 适配目录（如 `.claude/`、`.kiro/`、`.codex/`）

## 飞书相关说明

飞书技能本体现在可以随仓库一起管理，但认证信息仍然必须留在本地：

- skill 文件：可通过 Git 管理
- `.lark-cli/`：必须继续忽略

如果你切换到 Windows 本地 TRAE 环境，是合理路径。仓库只需要保证 skill 规则和目录结构可移植，平台相关的认证、PATH、CLI 安装则在本机完成。

详细步骤见 [docs/bytedance/lark-doc-setup.md](docs/bytedance/lark-doc-setup.md)。
