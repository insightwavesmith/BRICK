"""Local Agent projection writer for COO-SYNC-0 and later projection slices.

This support surface writes already-rendered Agent resource projections to local
Codex and Claude app files. It does not call providers, execute hooks or tools,
choose Movement, create GateFacts, or own Agent meaning.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from brick_protocol.support.connection.agent_resources import (
    list_agent_object_refs,
    render_claude_projection_seed,
    render_codex_projection_seed,
)


_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROOF_LIMITS = (
    "support local projection evidence only",
    "agent/ remains the Agent resource source",
    "local app files are projection files only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_NOT_PROVEN = (
    "Codex app reload behavior",
    "Claude app reload behavior",
    "provider quality",
    "provider session behavior",
    "MCP projection behavior",
    "native tool or hook execution",
    "future Building correctness",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT


def _home_path(home: str | Path | None, default: Path) -> Path:
    return Path(home).expanduser().resolve() if home is not None else default.expanduser().resolve()


def _codex_home(codex_home: str | Path | None) -> Path:
    return _home_path(codex_home, Path("~/.codex"))


def _claude_home(claude_home: str | Path | None) -> Path:
    return _home_path(claude_home, Path("~/.claude"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _admitted_projection_roles(repo_root: str | Path | None = None) -> tuple[str, ...]:
    repo = _repo_root(repo_root)
    return tuple(ref.removeprefix("agent-object:") for ref in list_agent_object_refs(repo))


def _normalize_role(role: str, repo_root: str | Path | None = None) -> str:
    if not isinstance(role, str) or not role:
        raise ValueError("projection role must be an admitted Agent projection role")
    clean = role.removeprefix("agent-object:") if role.startswith("agent-object:") else role
    if clean not in _admitted_projection_roles(repo_root):
        raise ValueError("projection role must be an admitted Agent projection role")
    return clean


def _codex_target(role: str) -> Path:
    return Path("skills") / f"brick-protocol-{role}" / "SKILL.md"


def _claude_target(role: str) -> Path:
    return Path("agents") / f"brick-protocol-{role}.md"


def _codex_frontmatter(role: str) -> str:
    description = (
        "Use when operating Brick Protocol as the synced COO projection generated from Agent resources."
        if role == "coo"
        else f"Use when acting as the Brick Protocol {role.upper()} projection generated from Agent resources."
    )
    return f"---\nname: brick-protocol-{role}\ndescription: {description}\n---\n"


def _claude_frontmatter(role: str) -> str:
    role_label = role.upper() if role != "coo" else "COO"
    return (
        "---\n"
        f"name: brick-protocol-{role}\n"
        f"description: Brick Protocol {role_label} projection generated from Agent resources.\n"
        "---\n"
    )


def _require_rendered_seed(seed: dict[str, Any], *, target: str, role: str) -> str:
    expected_ref = f"agent-object:{role}"
    if seed.get("agent_object_ref") != expected_ref:
        raise ValueError(f"{target}: seed must come from {expected_ref}")
    if seed.get("projection_status") != "rendered":
        raise ValueError(f"{target}: Agent projection seed must be rendered")
    body = seed.get("rendered_instruction_text")
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"{target}: rendered_instruction_text must be non-empty")
    return body


def _with_frontmatter(body: str, frontmatter: str) -> str:
    return f"{frontmatter}\n{body.lstrip()}"


def _record(*, role: str, kind: str, target: str, path: Path, body: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "target": target,
        "path": str(path),
        "agent_object_ref": f"agent-object:{role}",
        "projection_status": "projection only; source remains agent/",
        "body": body,
        "sha256": _sha256(body),
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_codex_coo_skill(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    """Render the local Codex COO skill projection record without writing."""

    return render_codex_agent_skill("coo", repo_root=repo_root, codex_home=codex_home)


def render_claude_coo_agent(
    repo_root: str | Path | None = None,
    claude_home: str | Path | None = None,
) -> dict[str, Any]:
    """Render the local Claude COO agent projection record without writing."""

    return render_claude_agent_projection("coo", repo_root=repo_root, claude_home=claude_home)


def render_codex_agent_skill(
    role: str,
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    """Render one local Codex Agent skill projection record without writing."""

    clean_role = _normalize_role(role, repo_root)
    repo = _repo_root(repo_root)
    target_path = _codex_home(codex_home) / _codex_target(clean_role)
    seed = render_codex_projection_seed(clean_role, repo_root=repo)
    body = _with_frontmatter(
        _require_rendered_seed(seed, target="codex", role=clean_role),
        _codex_frontmatter(clean_role),
    )
    return _record(
        role=clean_role,
        kind=f"{clean_role}-sync-codex-skill-projection",
        target=f"codex:~/.codex/{_codex_target(clean_role).as_posix()}",
        path=target_path,
        body=body,
    )


def render_claude_agent_projection(
    role: str,
    repo_root: str | Path | None = None,
    claude_home: str | Path | None = None,
) -> dict[str, Any]:
    """Render one local Claude Agent projection record without writing."""

    clean_role = _normalize_role(role, repo_root)
    repo = _repo_root(repo_root)
    target_path = _claude_home(claude_home) / _claude_target(clean_role)
    seed = render_claude_projection_seed(clean_role, repo_root=repo)
    body = _with_frontmatter(
        _require_rendered_seed(seed, target="claude", role=clean_role),
        _claude_frontmatter(clean_role),
    )
    return _record(
        role=clean_role,
        kind=f"{clean_role}-sync-claude-agent-projection",
        target=f"claude:~/.claude/{_claude_target(clean_role).as_posix()}",
        path=target_path,
        body=body,
    )


def plan_coo_sync(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
    claude_home: str | Path | None = None,
) -> dict[str, Any]:
    """Return intended COO projection writes without touching the filesystem."""

    return plan_agent_projection_sync(
        repo_root=repo_root,
        codex_home=codex_home,
        claude_home=claude_home,
        roles=("coo",),
    )


def plan_agent_projection_sync(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
    claude_home: str | Path | None = None,
    *,
    roles: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Return intended Agent projection writes without touching the filesystem."""

    clean_roles = (
        _admitted_projection_roles(repo_root)
        if roles is None
        else tuple(_normalize_role(role, repo_root) for role in roles)
    )
    return {
        "kind": "agent-projection-sync-plan",
        "roles": list(clean_roles),
        "writes": [
            record
            for role in clean_roles
            for record in (
                render_codex_agent_skill(role, repo_root=repo_root, codex_home=codex_home),
                render_claude_agent_projection(role, repo_root=repo_root, claude_home=claude_home),
            )
        ],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def _write_record(record: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(record["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(record["body"]), encoding="utf-8")
    return {
        "kind": "agent-sync-written-projection",
        "target": record["target"],
        "path": record["path"],
        "agent_object_ref": record["agent_object_ref"],
        "projection_status": record["projection_status"],
        "sha256": record["sha256"],
        "proof_limits": list(record["proof_limits"]),
        "not_proven": list(record["not_proven"]),
    }


def write_coo_sync(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
    claude_home: str | Path | None = None,
) -> dict[str, Any]:
    """Write only the exact COO Codex and Claude projection targets."""

    result = write_agent_projection_sync(
        repo_root=repo_root,
        codex_home=codex_home,
        claude_home=claude_home,
        roles=("coo",),
    )
    return {**result, "kind": "coo-sync-write-evidence"}


def write_agent_projection_sync(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
    claude_home: str | Path | None = None,
    *,
    roles: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Write exact local Agent projection targets for admitted roles."""

    plan = plan_agent_projection_sync(
        repo_root=repo_root,
        codex_home=codex_home,
        claude_home=claude_home,
        roles=roles,
    )
    return {
        "kind": "agent-projection-sync-write-evidence",
        "roles": list(plan["roles"]),
        "written": [_write_record(record) for record in plan["writes"]],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def observe_agent_projection_freshness(
    repo_root: str | Path | None = None,
    codex_home: str | Path | None = None,
    claude_home: str | Path | None = None,
    *,
    roles: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Observe whether local projection files match rendered Agent resources.

    This is a read-only projection freshness observation. It does not write local
    app files, reload apps, call providers, or judge provider behavior.
    """

    plan = plan_agent_projection_sync(
        repo_root=repo_root,
        codex_home=codex_home,
        claude_home=claude_home,
        roles=roles,
    )
    observations: list[dict[str, Any]] = []
    for record in plan["writes"]:
        path = Path(str(record["path"]))
        existing_body = path.read_text(encoding="utf-8") if path.is_file() else ""
        observed_sha256 = _sha256(existing_body) if existing_body else ""
        expected_sha256 = str(record["sha256"])
        observations.append(
            {
                "target": record["target"],
                "path": str(path),
                "agent_object_ref": record["agent_object_ref"],
                "exists": path.is_file(),
                "expected_sha256": expected_sha256,
                "observed_sha256": observed_sha256,
                "matches_rendered_agent_resource": bool(existing_body)
                and observed_sha256 == expected_sha256,
                "field_presence": {
                    "first_line_contract_candidate": "first_line_contract_candidate" in existing_body,
                    "honest_report_questions": "honest_report_questions" in existing_body,
                    "transition_concern_evidence": "transition_concern_evidence" in existing_body,
                },
                "proof_limits": list(_PROOF_LIMITS),
                "not_proven": list(_NOT_PROVEN),
            }
        )
    return {
        "kind": "agent-projection-freshness-observation",
        "roles": list(plan["roles"]),
        "observations": observations,
        "all_present": all(item["exists"] for item in observations),
        "all_match_rendered_agent_resource": all(
            item["matches_rendered_agent_resource"] for item in observations
        ),
        "proof_limits": [
            *_PROOF_LIMITS,
            "freshness observation only",
            "not app reload proof",
        ],
        "not_proven": list(_NOT_PROVEN),
    }


def render_agent_projection_sync_context(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render the read-only Agent projection sync contract.

    This is a support context only. It may describe sync-out and sync-in
    observation, but it must not write local app files or modify agent/.
    """

    repo = _repo_root(repo_root)
    roles = list(_admitted_projection_roles(repo))
    return {
        "kind": "agent-projection-sync-context",
        "schema_version": "agent-projection-sync-0",
        "source": "agent/",
        "sync_out": {
            "direction": "agent/ -> provider-native projection files",
            "planner_ref": "support/connection/coo_sync.py::plan_agent_projection_sync",
            "writer_ref": "support/connection/coo_sync.py::write_agent_projection_sync",
            "roles": roles,
            "targets": [
                "codex:~/.codex/skills/brick-protocol-<role>/SKILL.md",
                "claude:~/.claude/agents/brick-protocol-<role>.md",
            ],
        },
        "sync_in_observation": {
            "direction": "provider-native projection files -> drift observation",
            "observer_ref": "support/connection/coo_sync.py::observe_agent_projection_freshness",
            "automatic_agent_resource_write": False,
            "candidate_import_requires_building": True,
        },
        "forbidden_authority": [
            "provider projection as source truth",
            "automatic local-file to agent/ overwrite",
            "provider-specific Agent identity",
            "credential or session body storage",
            "native hook execution",
            "Movement choice",
            "success judgment",
            "quality judgment",
        ],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


__all__ = [
    "render_codex_coo_skill",
    "render_claude_coo_agent",
    "render_codex_agent_skill",
    "render_claude_agent_projection",
    "plan_coo_sync",
    "write_coo_sync",
    "plan_agent_projection_sync",
    "write_agent_projection_sync",
    "observe_agent_projection_freshness",
    "render_agent_projection_sync_context",
]
