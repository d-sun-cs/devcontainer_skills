# devcontainer_skills Agent Guide

This repository is the central skills registry.

## Skill Management Rules

- Canonical skill source: `.agents/skills/`
- Central registry index: `registry.yaml`
- Management script: `scripts/skillsctl.py`
- Default managed project: `/home/dsun/erdos-tf32-hev3-workspace`
- Default project layout: `.agents`

Always manage project skills through `scripts/skillsctl.py` from this repository root. Do not manually copy managed skill folders into a project, and do not manually edit project `.agents/skills.yaml` or `.agents/skills.lock.yaml` unless the user explicitly asks for a manual repair.

Use these commands as the normal workflow:

```bash
cd /home/dsun/devcontainer_skills

python3 scripts/skillsctl.py list --names-only
python3 scripts/skillsctl.py status --project /home/dsun/erdos-tf32-hev3-workspace
python3 scripts/skillsctl.py install --project /home/dsun/erdos-tf32-hev3-workspace <skill> [...]
python3 scripts/skillsctl.py sync --project /home/dsun/erdos-tf32-hev3-workspace
python3 scripts/skillsctl.py promote --project /home/dsun/erdos-tf32-hev3-workspace <skill>
```

Current managed skills for `/home/dsun/erdos-tf32-hev3-workspace`:

```text
my-workflow
ci-checks-fix
code-change
lark-shared
lark-doc
lark-wiki
```

Notes:

- `code-change` replaces the old `code-optimization` skill name. Do not reinstall `code-optimization` unless the user explicitly asks for that legacy name.
- Feishu/Lark document operation support is managed as the set `lark-shared`, `lark-doc`, and `lark-wiki`.
- Project-local skills such as `forgec` should stay local-only unless the user asks to promote or manage them.
- If the user changes the target project path, use that path in every `--project` argument and avoid falling back to the old `/home/dsun/erdos` path.

## Required User Verification Output

After every skill management operation, the final response must include commands the user can run to verify that the management took effect.

At minimum, include:

```bash
cd /home/dsun/devcontainer_skills

python3 scripts/skillsctl.py status --project /home/dsun/erdos-tf32-hev3-workspace
sed -n '1,160p' /home/dsun/erdos-tf32-hev3-workspace/.agents/skills.yaml
sed -n '1,260p' /home/dsun/erdos-tf32-hev3-workspace/.agents/skills.lock.yaml
```

When checking copied skill content, include a directory diff for the managed skills involved:

```bash
for s in my-workflow ci-checks-fix code-change lark-shared lark-doc lark-wiki; do
  diff -qr "/home/dsun/devcontainer_skills/.agents/skills/$s" \
           "/home/dsun/erdos-tf32-hev3-workspace/.agents/skills/$s"
done
```

No output from the `diff -qr` loop means the central copy and project copy are identical.

When a skill is promoted into the central registry, also include:

```bash
python3 scripts/skillsctl.py list --names-only
rg '<skill-name>' registry.yaml
```

The response should mention the exact management command that was run and the expected `status` result, so the user can compare quickly.
