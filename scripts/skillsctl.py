#!/usr/bin/env python3
"""Manage repository-backed agent skills across projects.

The central repository keeps canonical skills in `.agents/skills/`.
Target projects get explicit, project-local copies under
`<project-root>/<layout>/skills/` based on
`<project-root>/<layout>/skills.yaml`. The default layout is `.agents`.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import textwrap
from pathlib import Path


SKILL_SOURCE = Path(".agents") / "skills"
DEFAULT_LAYOUT = ".agents"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_dir() -> Path:
    return repo_root() / SKILL_SOURCE


def normalize_layout(layout: str) -> str:
    value = layout.strip().strip('"').strip("'")
    legacy = {
        "project": ".agents",
        "agents": ".agents",
    }
    value = legacy.get(value, value)
    if value in {"agent-home", "codex-home"}:
        fail("use a concrete layout directory such as .codex, .claude, or .kiro")
    if not value:
        fail("layout cannot be empty")
    if "/" in value or "\\" in value:
        fail("layout must be a single project-root directory name, such as .agents or .codex")
    if value in {".", ".."}:
        fail("layout cannot be . or ..")
    if not value.startswith("."):
        value = "." + value
    return value


def layout_paths(layout: str) -> dict[str, Path | None]:
    layout = normalize_layout(layout)
    root = Path(layout)
    return {
        "manifest": root / "skills.yaml",
        "lock": root / "skills.lock.yaml",
        "skills": root / "skills",
        "ignore": root / ".gitignore" if layout == DEFAULT_LAYOUT else None,
    }


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def run_git(args: list[str], default: str = "") -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return default


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def read_registry_metadata() -> dict[str, dict[str, str]]:
    registry = repo_root() / "registry.yaml"
    metadata: dict[str, dict[str, str]] = {}
    if not registry.exists():
        return metadata

    current: dict[str, str] | None = None
    for raw_line in registry.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if line.startswith("  - name:"):
            name = unquote(line.split(":", 1)[1])
            current = {"name": name}
            metadata[name] = current
            continue
        if current is None or not line.startswith("    ") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in {"path", "category", "status", "summary"}:
            current[key] = unquote(value)

    return metadata


def skill_description(skill_dir: Path) -> str:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return ""
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("description:"):
            return unquote(line.split(":", 1)[1]).strip()
    return ""


def wrap_for_terminal(value: str, width: int) -> list[str]:
    return textwrap.wrap(
        value,
        width=max(24, width),
        break_long_words=True,
        break_on_hyphens=False,
    ) or [""]


def read_manifest(path: Path) -> list[str]:
    if not path.exists():
        fail(f"manifest not found: {path}")

    skills: list[str] = []
    in_skills = False
    pending_map_item = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if not line.startswith(" ") and stripped.endswith(":"):
            in_skills = stripped == "skills:"
            pending_map_item = False
            continue

        if not in_skills:
            continue

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            pending_map_item = False
            if item.startswith("name:"):
                skill = unquote(item.split(":", 1)[1])
                if skill:
                    skills.append(skill)
            elif ":" not in item:
                skills.append(unquote(item))
            else:
                pending_map_item = True
        elif pending_map_item and stripped.startswith("name:"):
            skill = unquote(stripped.split(":", 1)[1])
            if skill:
                skills.append(skill)
            pending_map_item = False

    if not skills:
        fail(f"manifest has no skills: {path}")
    return unique(skills)


def read_manifest_or_empty(path: Path) -> list[str]:
    if not path.exists():
        return []
    return read_manifest(path)


def resolve_target(project: str, requested_layout: str) -> tuple[Path, str]:
    project_root = Path(project).expanduser().resolve()
    return project_root, normalize_layout(requested_layout)


def read_lock(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}

    locked: dict[str, dict[str, str]] = {}
    current: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.split("#", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith("- name:"):
            current = unquote(stripped.split(":", 1)[1])
            locked[current] = {}
        elif current and ":" in stripped:
            key, value = stripped.split(":", 1)
            locked[current][key.strip()] = unquote(value)

    return locked


def write_manifest(project_root: Path, skills: list[str], layout: str) -> None:
    layout = normalize_layout(layout)
    paths = layout_paths(layout)
    remote = run_git(["config", "--get", "remote.origin.url"], "https://github.com/d-sun-cs/devcontainer_skills")
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], "main")
    manifest = project_root / paths["manifest"]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# Managed by devcontainer_skills/scripts/skillsctl.py.",
        "# Commit this file so each project declares its enabled skills.",
        f"target_layout: {yaml_quote(layout)}",
        "source:",
        f"  repo: {yaml_quote(remote)}",
        f"  ref: {yaml_quote(branch)}",
        "skills:",
    ]
    content.extend(f"  - {skill}" for skill in unique(skills))
    manifest.write_text("\n".join(content) + "\n", encoding="utf-8")


def write_lock(project_root: Path, skills: list[str], layout: str) -> None:
    layout = normalize_layout(layout)
    paths = layout_paths(layout)
    commit = run_git(["rev-parse", "HEAD"], "unknown")
    remote = run_git(["config", "--get", "remote.origin.url"], "https://github.com/d-sun-cs/devcontainer_skills")
    lock = project_root / paths["lock"]
    lock.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# Managed by devcontainer_skills/scripts/skillsctl.py.",
        "# Records the exact source hash last installed into this project.",
        f"target_layout: {yaml_quote(layout)}",
        "source:",
        f"  repo: {yaml_quote(remote)}",
        f"  commit: {yaml_quote(commit)}",
        "skills:",
    ]
    for skill in unique(skills):
        digest = tree_hash(source_dir() / skill)
        content.extend(
            [
                f"  - name: {skill}",
                f"    source_hash: {yaml_quote(digest)}",
                f"    source_path: {yaml_quote(str(SKILL_SOURCE / skill).replace(os.sep, '/'))}",
            ]
        )
    lock.write_text("\n".join(content) + "\n", encoding="utf-8")


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def ensure_skill_exists(skill: str) -> Path:
    skill_path = source_dir() / skill
    if not skill_path.is_dir():
        fail(f"unknown skill: {skill}")
    if not (skill_path / "SKILL.md").is_file():
        fail(f"skill is missing SKILL.md: {skill}")
    return skill_path


def ensure_within(parent: Path, child: Path) -> None:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    if parent_resolved != child_resolved and parent_resolved not in child_resolved.parents:
        fail(f"refusing to operate outside {parent_resolved}: {child_resolved}")


def tree_hash(path: Path) -> str:
    if not path.exists():
        fail(f"path not found: {path}")

    digest = hashlib.sha256()
    for root, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(
            name for name in dirnames if name not in {".git", "__pycache__"}
        )
        for filename in sorted(filenames):
            if filename in {".DS_Store"} or filename.endswith(".pyc"):
                continue
            file_path = Path(root) / filename
            rel = file_path.relative_to(path).as_posix()
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            if file_path.is_symlink():
                digest.update(f"symlink:{os.readlink(file_path)}".encode("utf-8"))
            else:
                digest.update(file_path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def remove_skill_tree(path: Path) -> None:
    ensure_within(source_dir(), path)
    if path.exists():
        shutil.rmtree(path)


def ensure_project_ignore(project_root: Path, track_installed: bool, layout: str) -> None:
    if track_installed:
        return
    ignore_path = layout_paths(layout)["ignore"]
    if ignore_path is None:
        return
    ignore = project_root / ignore_path
    if ignore.exists():
        return
    ignore.parent.mkdir(parents=True, exist_ok=True)
    ignore.write_text(
        "# Installed skill copies are regenerated from the central registry.\n"
        "/skills/\n",
        encoding="utf-8",
    )


def list_skills(args: argparse.Namespace) -> None:
    root = source_dir()
    if not root.is_dir():
        fail(f"canonical skill directory not found: {root}")

    skill_dirs = sorted(
        path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")
    )
    metadata = read_registry_metadata()

    rows: list[dict[str, str]] = []
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = skill_dir.name
        description = skill_description(skill_dir)
        info = metadata.get(name, {})
        rows.append(
            {
                "name": name,
                "category": info.get("category", "-"),
                "summary": info.get("summary") or description or f"{name} skill",
                "description": description or info.get("summary", ""),
            }
        )

    if args.names_only:
        for row in rows:
            print(row["name"])
        return

    terminal_width = min(shutil.get_terminal_size((100, 20)).columns, 120)

    if args.verbose:
        for index, row in enumerate(rows):
            if index:
                print()
            print(row["name"])
            print(f"  category: {row['category']}")
            print("  summary:")
            for line in wrap_for_terminal(row["summary"], terminal_width - 4):
                print(f"    {line}")
            if row["description"] and row["description"] != row["summary"]:
                print("  description:")
                for line in wrap_for_terminal(row["description"], terminal_width - 4):
                    print(f"    {line}")
        return

    name_width = min(max([len("skill"), *(len(row["name"]) for row in rows)]), 32)
    category_width = min(max([len("category"), *(len(row["category"]) for row in rows)]), 20)
    summary_width = terminal_width - name_width - category_width - 4

    print(f"{'skill':<{name_width}}  {'category':<{category_width}}  summary")
    print(f"{'-' * name_width}  {'-' * category_width}  {'-' * max(7, summary_width)}")
    for row in rows:
        summary_lines = wrap_for_terminal(row["summary"], summary_width)
        print(f"{row['name']:<{name_width}}  {row['category']:<{category_width}}  {summary_lines[0]}")
        for line in summary_lines[1:]:
            print(f"{'':<{name_width}}  {'':<{category_width}}  {line}")


def install(args: argparse.Namespace) -> None:
    project_root, layout = resolve_target(args.project, args.layout)
    project_root.mkdir(parents=True, exist_ok=True)
    paths = layout_paths(layout)

    requested = unique(args.skills)
    for skill in requested:
        ensure_skill_exists(skill)

    manifest = project_root / paths["manifest"]
    if manifest.exists():
        skills = unique(read_manifest(manifest) + requested)
    else:
        skills = requested
    write_manifest(project_root, skills, layout)
    ensure_project_ignore(project_root, args.track_installed, layout)
    sync_project(project_root, skills, force=args.force, clean=False, layout=layout)


def sync(args: argparse.Namespace) -> None:
    project_root, layout = resolve_target(args.project, args.layout)
    paths = layout_paths(layout)
    skills = read_manifest(project_root / paths["manifest"])
    sync_project(project_root, skills, force=args.force, clean=args.clean, layout=layout)


def sync_project(project_root: Path, skills: list[str], force: bool, clean: bool, layout: str) -> None:
    paths = layout_paths(layout)
    lock = read_lock(project_root / paths["lock"])
    target_root = project_root / paths["skills"]
    target_root.mkdir(parents=True, exist_ok=True)

    for skill in skills:
        src = ensure_skill_exists(skill)
        dst = target_root / skill
        source_hash = tree_hash(src)

        if dst.exists():
            installed_hash = tree_hash(dst)
            locked_hash = lock.get(skill, {}).get("source_hash")
            if locked_hash and installed_hash != locked_hash and not force:
                fail(
                    f"{skill} has local project edits. Run promote first, or rerun sync with --force."
                )
            if not locked_hash and installed_hash != source_hash and not force:
                fail(
                    f"{skill} exists without a lock entry. Rerun with --force only if overwriting is OK."
                )
            if installed_hash == source_hash:
                print(f"up to date: {skill}")
                continue

        copy_skill(src, dst)
        print(f"synced: {skill}")

    if clean and target_root.exists():
        selected = set(skills)
        previously_managed = set(lock.keys())
        for child in sorted(path for path in target_root.iterdir() if path.is_dir()):
            if child.name in previously_managed and child.name not in selected:
                shutil.rmtree(child)
                print(f"removed managed skill: {child.name}")

    write_lock(project_root, skills, layout)


def promote(args: argparse.Namespace) -> None:
    project_root, layout = resolve_target(args.project, args.layout)
    paths = layout_paths(layout)
    skill = args.skill
    src = project_root / paths["skills"] / skill
    if not src.is_dir():
        fail(f"project skill not found: {src}")
    if not (src / "SKILL.md").is_file():
        fail(f"project skill is missing SKILL.md: {src}")

    dst = source_dir() / skill
    lock = read_lock(project_root / paths["lock"])
    locked_hash = lock.get(skill, {}).get("source_hash")
    if dst.exists() and locked_hash and tree_hash(dst) != locked_hash and not args.force:
        fail(
            f"central {skill} changed after this project installed it. Review manually or rerun with --force."
        )

    copy_skill(src, dst)
    update_registry(add={skill})
    print(f"promoted: {skill}")
    if not args.no_manage_project:
        skills = unique(read_manifest_or_empty(project_root / paths["manifest"]) + [skill])
        write_manifest(project_root, skills, layout)
        write_lock(project_root, skills, layout)
        print(f"managed in project manifest: {skill}")
    print("review, commit, and push changes from the central repository")


def remove(args: argparse.Namespace) -> None:
    project_root, layout = resolve_target(args.project, args.layout)
    paths = layout_paths(layout)
    manifest_path = project_root / paths["manifest"]
    skills = read_manifest(manifest_path)
    removed = [skill for skill in args.skills if skill in skills]
    kept = [skill for skill in skills if skill not in set(args.skills)]

    if removed:
        write_manifest(project_root, kept, layout)
        print(f"unmanaged in project: {', '.join(removed)}")
    else:
        print("no project manifest entries matched")

    sync_project(project_root, kept, force=args.force, clean=True, layout=layout)

    if args.central:
        for skill in args.skills:
            central_path = source_dir() / skill
            if central_path.exists():
                remove_skill_tree(central_path)
                print(f"removed central skill: {skill}")
            else:
                print(f"central skill not found: {skill}")
        update_registry(remove=set(args.skills))


def status(args: argparse.Namespace) -> None:
    project_root, layout = resolve_target(args.project, args.layout)
    paths = layout_paths(layout)
    manifest_skills = read_manifest_or_empty(project_root / paths["manifest"])
    managed = set(manifest_skills)
    locked = read_lock(project_root / paths["lock"])
    installed_root = project_root / paths["skills"]

    installed = set()
    if installed_root.is_dir():
        installed = {
            path.name
            for path in installed_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

    for skill in manifest_skills:
        if skill in installed:
            state = "managed"
            locked_hash = locked.get(skill, {}).get("source_hash")
            current_hash = tree_hash(installed_root / skill)
            if locked_hash and current_hash != locked_hash:
                state = "managed-modified"
        else:
            state = "managed-missing"
        print(f"{state}: {skill}")

    for skill in sorted(installed - managed):
        print(f"local-only: {skill}")


def doctor(_args: argparse.Namespace) -> None:
    root = source_dir()
    if not root.is_dir():
        fail(f"missing canonical skill directory: {root}")

    errors = 0
    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        if not (skill_dir / "SKILL.md").is_file():
            print(f"missing SKILL.md: {skill_dir.name}")
            errors += 1
    if errors:
        raise SystemExit(1)
    print(f"ok: {root}")


def skill_summary(skill: str) -> str:
    skill_file = source_dir() / skill / "SKILL.md"
    if not skill_file.exists():
        return f"{skill} skill"
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("description:"):
            return unquote(line.split(":", 1)[1]).strip()
    return f"{skill} skill"


def update_registry(remove: set[str] | None = None, add: set[str] | None = None) -> None:
    registry = repo_root() / "registry.yaml"
    if not registry.exists():
        return
    remove = remove or set()
    add = add or set()

    lines = registry.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    block: list[str] = []
    in_block = False
    drop_block = False

    def flush_block() -> None:
        nonlocal block, in_block, drop_block
        if in_block and not drop_block:
            output.extend(block)
        block = []
        in_block = False
        drop_block = False

    for line in lines:
        if line.startswith("  - name:"):
            flush_block()
            in_block = True
            block = [line]
            name = unquote(line.split(":", 1)[1])
            drop_block = name in remove
            continue
        if in_block:
            block.append(line)
        else:
            output.append(line)

    flush_block()
    existing = {
        unquote(line.split(":", 1)[1])
        for line in output
        if line.startswith("  - name:")
    }
    for skill in sorted(add - existing):
        if not (source_dir() / skill / "SKILL.md").exists():
            continue
        if output and output[-1].strip():
            output.append("")
        output.extend(
            [
                f"  - name: {yaml_quote(skill)}",
                f"    path: {yaml_quote(f'.agents/skills/{skill}')}",
                '    category: "promoted"',
                '    status: "active"',
                f"    summary: {yaml_quote(skill_summary(skill))}",
            ]
        )
    registry.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, sync, and promote skills from the central registry."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_cmd = subcommands.add_parser("list", help="List canonical skills")
    list_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="Show full descriptions in a readable block layout",
    )
    list_cmd.add_argument(
        "--names-only",
        action="store_true",
        help="Only print skill names, one per line",
    )
    list_cmd.set_defaults(func=list_skills)

    install_cmd = subcommands.add_parser(
        "install", help="Create project manifest and install selected skills"
    )
    install_cmd.add_argument("--project", required=True, help="Target project root")
    install_cmd.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help="Project-root directory for managed skills. Default: .agents. Examples: .codex, .claude, .kiro.",
    )
    install_cmd.add_argument("--force", action="store_true", help="Overwrite local skill edits")
    install_cmd.add_argument(
        "--track-installed",
        action="store_true",
        help="Do not create .agents/.gitignore; use when committing copied skills",
    )
    install_cmd.add_argument("skills", nargs="+", help="Skill names to enable")
    install_cmd.set_defaults(func=install)

    sync_cmd = subcommands.add_parser(
        "sync", help="Refresh a project from its .agents/skills.yaml"
    )
    sync_cmd.add_argument("--project", required=True, help="Target project root")
    sync_cmd.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help="Project-root directory for managed skills. Default: .agents. Examples: .codex, .claude, .kiro.",
    )
    sync_cmd.add_argument("--force", action="store_true", help="Overwrite local skill edits")
    sync_cmd.add_argument(
        "--clean",
        action="store_true",
        help="Remove previously managed skills that were removed from the manifest",
    )
    sync_cmd.set_defaults(func=sync)

    promote_cmd = subcommands.add_parser(
        "promote", help="Copy one project skill back into the central registry"
    )
    promote_cmd.add_argument("--project", required=True, help="Target project root")
    promote_cmd.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help="Project-root directory for managed skills. Default: .agents. Examples: .codex, .claude, .kiro.",
    )
    promote_cmd.add_argument("--force", action="store_true", help="Overwrite central changes")
    promote_cmd.add_argument(
        "--no-manage-project",
        action="store_true",
        help="Do not add the promoted skill to this project's manifest",
    )
    promote_cmd.add_argument("skill", help="Skill name to promote")
    promote_cmd.set_defaults(func=promote)

    remove_cmd = subcommands.add_parser(
        "remove", help="Remove managed skills from a project, optionally from the central registry"
    )
    remove_cmd.add_argument("--project", required=True, help="Target project root")
    remove_cmd.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help="Project-root directory for managed skills. Default: .agents. Examples: .codex, .claude, .kiro.",
    )
    remove_cmd.add_argument("--force", action="store_true", help="Overwrite local skill edits during cleanup")
    remove_cmd.add_argument(
        "--central",
        action="store_true",
        help="Also delete the skill from the central registry and registry.yaml",
    )
    remove_cmd.add_argument("skills", nargs="+", help="Skill names to remove")
    remove_cmd.set_defaults(func=remove)

    status_cmd = subcommands.add_parser(
        "status", help="Show managed, modified, missing, and local-only project skills"
    )
    status_cmd.add_argument("--project", required=True, help="Target project root")
    status_cmd.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help="Project-root directory for managed skills. Default: .agents. Examples: .codex, .claude, .kiro.",
    )
    status_cmd.set_defaults(func=status)

    doctor_cmd = subcommands.add_parser("doctor", help="Check central skill layout")
    doctor_cmd.set_defaults(func=doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
