---
name: skills-management
description: 管理本仓库中 agent skills 的存储规则。当用户要求安装新 skill、调整 skill 路径、或讨论 skill 重复加载问题时触发。
---

# Skills Management

## 存储规则

`.agents/skills/` 是唯一真源目录。仓库需要同时适配 devcontainer、Linux/macOS 本地环境、Windows 本地环境，以及已经预装 AI agent 的工作区。

默认规则：

1. 所有 skill 只存在于仓库内的 `.agents/skills/`
2. 不在 home 目录放任何 skill 副本
3. 不把 `.claude/skills`、`.kiro/skills`、`.codex/skills` 之类的工具目录当成真源
4. 优先让 agent 直接扫描 `.agents/skills/`
5. 默认**不提交**仓库根目录 `AGENTS.md`，因为部分环境会把它当成项目规则在每轮自动加载
6. 只有当工具既不能扫描 `.agents/skills/`，又强依赖 manifest 时，才在本地临时生成 `AGENTS.md` 或其他兼容入口
7. 只有当工具既不能扫描 `.agents/skills/`，也不能读取 manifest 时，才在仓库内创建本地适配层

```
<repo-root>/
└── .agents/skills/        ← 所有 skill 在此，npx skills add 直接写入
    ├── find-skills/
    ├── ai-infra-handwriting/
    ├── leetcode-reasoning/
    └── skills-management/
```

## 安装新 Skill

```bash
npx -y skills add <owner/repo>
# 直接写入 .agents/skills/，无需额外操作
```

如果合适的能力来自其他合理渠道（例如 npm 上的专用 skill registry、GitHub 仓库中的 playbook、课程/论文配套资料），不要把整套外部资料硬塞进多个入口。优先在 `.agents/skills/` 下创建一个小的 wrapper skill，记录来源、命令和触发规则。

## 规则

1. skill 真源只有 `.agents/skills/`
2. 不创建任何 home 目录 symlink 或副本（`~/.kiro/skills`、`~/.claude/skills` 等）
3. 不默认创建 workspace 内的其他入口；如需创建，仅作为本地兼容层
4. 兼容层必须指向 `.agents/skills/`，不能反向让真源依赖工具目录
5. 任何兼容层都不应提交到 Git，避免第二份真源长期漂移

## 兼容层策略

### 优先级

按以下顺序选择：

1. 直接扫描 `.agents/skills/`
2. 必要时在本地临时生成 manifest
3. 创建本地兼容层

### 关于 `AGENTS.md`

本仓库的默认策略是：**不把 `AGENTS.md` 作为常驻提交文件。**

原因：

1. 一些环境会自动读取仓库根目录 `AGENTS.md`，导致每轮都被动加载
2. `AGENTS.md` 很容易和真正的仓库规范重复，形成双份规则
3. 仓库规范应集中维护在 `skills-management/SKILL.md`

如果某个外部工具明确要求 `AGENTS.md`：

- 在本地临时生成一个极简 manifest
- 内容只保留指向 `.agents/skills/` 的入口说明
- 不把这个文件提交到 Git
- 用完后删除，或放进仓库本地的 `.git/info/exclude`

### Linux / macOS

优先使用仓库内 symlink：

```bash
cd <repo-root>
ln -s .agents .kiro
```

### Windows

优先使用目录 junction，而不是默认使用 symlink。junction 通常不要求额外权限，更适合本地 IDE 环境：

```powershell
Set-Location <repo-root>
New-Item -ItemType Junction -Path .kiro -Target .agents
```

如果工具要求的是具体的 `skills` 目录：

```powershell
Set-Location <repo-root>
New-Item -ItemType Directory -Force -Path .claude | Out-Null
New-Item -ItemType Junction -Path .claude\skills -Target ..\.agents\skills
```

## Git 管理规则

- 应提交：通用 skill、仓库说明文档、跨平台公共规则
- 不应提交：账号配置、token、本地缓存、本地兼容层目录、环境专用 skill、默认 `AGENTS.md`

### 环境专用内容

以下内容默认视为本地环境专用，不纳入仓库真源：

- `lark-doc`
- `lark-shared`
- `intern-daily-report`
- `docs/bytedance/`

这类规则优先写入仓库本地的 `.git/info/exclude`，而不是提交到仓库根目录 `.gitignore`。

## 判断标准

当用户说“这个仓库要跨平台、能在已有 agent 环境里直接用、还能用 Git 管理 skills”时，最终应满足以下条件：

1. 仓库中只有一份被 Git 管理的 skill 真源
2. 不要求用户必须先进入 devcontainer
3. Windows / macOS / Linux 都有明确接入路径
4. 任何工具特定适配都不会污染真源
5. 默认不会因为仓库根目录存在 `AGENTS.md` 而在当前环境被动加载额外规则
