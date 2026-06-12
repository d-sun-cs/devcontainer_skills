# Repository Skills Index

This repository keeps all reusable skills in `.agents/skills/`.

## Rules

1. The single source of truth is `.agents/skills/`
2. Do not copy skills into home-directory tool folders
3. Prefer reading the target `SKILL.md` directly from this repository
4. Local tool adapters such as `.claude/` or `.kiro/` are optional compatibility layers, not the canonical source

## Skills

- `.agents/skills/ai-infra-handwriting/SKILL.md`
  CUDA / Triton / Python AI infra handwriting exercises.

- `.agents/skills/find-skills/SKILL.md`
  Find and install external skills from the open skills ecosystem.

- `.agents/skills/install-ai-tools/SKILL.md`
  Install AI CLIs and connect them to this repository across different environments.

- `.agents/skills/intern-daily-report/SKILL.md`
  Turn scattered work notes into a structured daily report and optionally publish to Lark.

- `.agents/skills/lark-doc/SKILL.md`
  Read, create, update, and manipulate Lark docs and related content.

- `.agents/skills/lark-shared/SKILL.md`
  Shared rules for lark-cli auth, identity switching, and permission handling.

- `.agents/skills/leetcode-reasoning/SKILL.md`
  Derive algorithm solutions rigorously instead of applying templates mechanically.

- `.agents/skills/skills-management/SKILL.md`
  Repository-level rules for storing and exposing skills.

## Notes

- Lark credentials and tokens are local-only and should stay outside Git-managed content.
- If an agent cannot scan `.agents/skills/` directly, it should read this file first.
