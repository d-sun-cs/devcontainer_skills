---
name: skills-management
description: 管理本仓库中 agent skills 的存储规则。当用户要求安装新 skill、调整 skill 路径、或讨论 skill 重复加载问题时触发。
---

# Skills Management

## 存储规则

`.agents/skills/` 是唯一存储位置。不创建任何 symlink，不在 home 目录下放任何副本。

```
/workspaces/devcontainer_skills/
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

1. 所有 skill 只存在于 workspace 下的 `.agents/skills/`
2. 不创建任何 home 目录 symlink（`~/.kiro/skills` 等）
3. 不在 workspace 内创建其他入口（`.claude/skills`、`.github/skills`）
4. 依赖各 agent 自动扫描 workspace 下的 `.agents/skills/`
