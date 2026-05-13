# Agent Skills Setup

This repository treats [`skills/`](../../skills/) as the source of truth for reusable agent skills.

## What is configured here

GitHub Copilot in VS Code does not expose a public setting for pointing to an arbitrary skills root. The supported way to make a custom skills repository visible is to place or link skills under Copilot's default personal skills location:

`~/.copilot/skills/<skill-name>/SKILL.md`

For this workspace, the dev container now creates a symlink from that default location to the repository's [`skills/`](../../skills/) folder when the container is created.

## Current setup

- Repository source folder: [`skills/`](../../skills/)
- Copilot target folder inside the container: `~/.copilot/skills`
- Container bootstrap: [`.devcontainer/devcontainer.json`](../../.devcontainer/devcontainer.json)

The container bootstrap runs a `postCreateCommand` that links:

`~/.copilot/skills -> /workspaces/devcontainer_skills/skills`

## Reproduce manually

If you need to recreate the setup outside Dev Containers, run:

```bash
mkdir -p "$HOME/.copilot"
ln -sfn /workspaces/devcontainer_skills/skills "$HOME/.copilot/skills"
```

If `~/.copilot/skills` already exists and is not a symlink, remove or rename it first, then run the command again.

## Adding a new skill

1. Create a new folder under [`skills/`](../../skills/) with the skill name.
2. Add `SKILL.md` to that folder.
3. Keep any helper scripts or reference files one level below `SKILL.md` so they are easy for agents to load.

Example layout:

```text
skills/
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    ├── references/
    └── assets/
```

## Notes for other agents

Different agents usually have different default discovery folders. The same pattern can be reused by linking this repository's `skills/` folder into each tool's expected location.

- Claude Code: link to `~/.claude/skills`
- Agent frameworks that follow the same convention: link to their documented personal skills path
- If a tool supports workspace-scoped discovery instead of personal skills, use its documented workspace folder rather than adding a custom settings path

When you document another agent's setup, keep the same structure:

1. Where the agent expects skills to live
2. The exact link or copy command
3. Whether the setup is automatic or manual
4. How to add a new skill in this repository