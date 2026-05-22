# Agent Skills Setup

This repository treats [`.agents/skills/`](../../.agents/skills/) as the only source of truth for reusable agent skills.

## Current setup

- Repository source folder: [`.agents/skills/`](../../.agents/skills/)
- No home-directory symlinks or duplicate skill copies are created.
- Agents are expected to scan workspace-local `.agents/skills/` directly.
- Container bootstrap lives in [`.devcontainer/devcontainer.json`](../../.devcontainer/devcontainer.json).

## Installing a skill

Prefer the Skills CLI when the skill is published in the open skills ecosystem:

```bash
npx -y skills add <owner/repo@skill>
```

Run the command from the repository root so it writes into `.agents/skills/`.

For domain-specific registries that are not packaged as ordinary agent skills, keep a small local wrapper skill in `.agents/skills/` and call the registry from that wrapper. Example:

```bash
npx -y @krxgu/kernel-skills list
npx -y @krxgu/kernel-skills show cuda.write-cuda-gemm-kernel
```

## Adding a new skill

1. Create a new folder under [`.agents/skills/`](../../.agents/skills/) with the skill name.
2. Add `SKILL.md` to that folder.
3. Keep any helper scripts or reference files one level below `SKILL.md` so they are easy for agents to load.

Example layout:

```text
.agents/skills/
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    ├── references/
    └── assets/
```

## Notes for other agents

Different agents usually have different default discovery folders. For this repository, keep `.agents/skills/` as the canonical location and avoid creating extra home-directory copies unless the user explicitly asks for a tool-specific export.

- Prefer workspace-scoped discovery when the agent supports it.
- Do not create `.claude/skills`, `.github/skills`, `~/.copilot/skills`, or similar mirrors by default.
- If a tool requires a different folder, document it as an export path rather than a second source of truth.

When you document another agent's setup, keep the same structure:

1. Where the agent expects skills to live
2. The exact discovery or export command
3. Whether the setup is automatic or manual
4. How to add a new skill in this repository
