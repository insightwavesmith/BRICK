"""PROJECT-0 S1-A: project declaration record loader (support record only).

A project is a vessel (그릇), not an axis: ``project/<id>/README.md`` is the
human charter (헌장 — why the project exists, where it is going) and
``project/<id>/project.json`` is the machine declaration extracted from that
charter (the charter's shadow; brick.md+return.yaml ≅ README.md+project.json).

This loader READS and validates the declaration record. It records facts only:

  * closed key set (exactly the 9 declared keys; any unknown key is rejected)
  * judgment vocabulary is rejected by name (``success`` / ``quality`` /
    ``movement`` and their ``_``-prefixed forms) — a project declaration holds
    direction facts, never judgment fields (TRUTH-before-QUALITY)
  * ``direction`` must be non-empty (a project must declare its direction
    before buildings accumulate)
  * ``managers`` lists human owner names only (no ``:``-prefixed machine refs;
    agents are never charter members — who worked is projected from
    AgentBinding evidence, not declared here)
  * ``charter_ref`` must point at the project's own README.md and that charter
    file must exist

Support evidence only: a loaded declaration proves the record is well-shaped
and the charter file exists. It is NOT source truth, NOT success judgment,
NOT quality judgment, and NOT Movement authority. It cannot prove a manager
string names a real human, nor that the charter text is truthful.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from brick_protocol.support.recording.capture import is_project_id_slug

PROJECT_DECLARATION_FILENAME = "project.json"
PROJECT_CHARTER_FILENAME = "README.md"
PROJECT_REF_PREFIX = "project:"

# Closed declaration key set (project-0-design-0611 §1). Closed BOTH ways:
# every key is required, and no other key is admitted.
PROJECT_DECLARATION_KEYS = (
    "project_ref",
    "label",
    "direction",
    "done_means",
    "out_of_scope",
    "managers",
    "declared_by",
    "declared_at",
    "charter_ref",
)

_REQUIRED_TEXT_KEYS = (
    "label",
    "direction",
    "done_means",
    "out_of_scope",
    "declared_by",
    "declared_at",
)

# Judgment vocabulary a declaration record must NEVER carry. These are
# rejected with their own message (clearer than the generic closed-key
# rejection) because they are the exact drift the support baseline forbids.
_FORBIDDEN_JUDGMENT_WORDS = ("success", "quality", "movement")


def _is_slug(value: str) -> bool:
    # PROJECT-0 S5-FIX: delegates to THE single slug law
    # (brick_protocol/support/recording/capture.is_project_id_slug — strict lowercase ascii
    # [-_a-z0-9], first char [a-z0-9]). The old ``.isalnum()`` form admitted
    # uppercase AND unicode ids, which propagated through buildings_root_for
    # and path admission.
    return is_project_id_slug(value)


def is_admissible_project_id(project_id: str) -> bool:
    """Public seam: the SAME id slug rule the loader enforces (single source).

    PROJECT-0 S2-A: the creation verb must refuse a non-slug id BEFORE it
    touches the filesystem (a traversal-shaped id like ``../escape`` must never
    become a mkdir), so the loader's slug predicate is exported here instead of
    being duplicated inline in the verb.
    """

    return isinstance(project_id, str) and _is_slug(project_id)


def _forbidden_judgment_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        lowered == word or lowered.startswith(f"{word}_") or lowered.endswith(f"_{word}")
        for word in _FORBIDDEN_JUDGMENT_WORDS
    )


@dataclass(frozen=True)
class ProjectDeclaration:
    """The loaded, validated facts of one project declaration record."""

    project_id: str
    project_ref: str
    label: str
    direction: str
    done_means: str
    out_of_scope: str
    managers: tuple[str, ...]
    declared_by: str
    declared_at: str
    charter_ref: str
    charter_path: Path


def _reject(project_id: str, reason: str) -> ValueError:
    return ValueError(f"project declaration rejected (project/{project_id}): {reason}")


def _require_text(project_id: str, record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _reject(
            project_id,
            f"{key} must be a non-empty string"
            + (
                " — a project must declare its direction (방향성) before buildings accumulate"
                if key == "direction"
                else ""
            ),
        )
    return value.strip()


def load_project_declaration(repo: Path | str, project_id: str) -> ProjectDeclaration:
    """Load + validate ``project/<project_id>/project.json``. Raises ValueError."""

    repo_path = Path(repo).resolve()
    if not _is_slug(project_id):
        raise _reject(
            project_id,
            "project id must be a non-empty [-_a-z0-9] slug "
            "(lowercase ascii; first char [a-z0-9])",
        )
    project_dir = repo_path / "project" / project_id
    # PROJECT-0 S5-FIX (symlink vessel escape): a vessel must be a REAL
    # directory inside <repo>/project/. A symlinked project/<id> passes every
    # record check while seam-derived landings traverse the link OUTSIDE the
    # repository (operator reproduced: project/sym-vessel -> /private/tmp/...).
    # The loader is the single validator (creation, intake, discovery and the
    # progress projection all round-trip through here), so the rejection lives
    # here once.
    if project_dir.is_symlink():
        try:
            link_target = str(project_dir.readlink())
        except OSError:
            link_target = "<unreadable link target>"
        raise _reject(
            project_id,
            f"project/{project_id} is a symlink -> {link_target} — a project "
            "vessel must be a real directory inside <repo>/project/; buildings "
            "must never land outside the repository through a link",
        )
    if project_dir.exists() and project_dir.resolve() != project_dir:
        raise _reject(
            project_id,
            f"project/{project_id} resolves to {project_dir.resolve()} — the "
            "vessel path escapes <repo>/project/ through a symlinked parent; "
            "a project vessel must be a real directory inside the repository",
        )
    declaration_path = project_dir / PROJECT_DECLARATION_FILENAME
    if not declaration_path.is_file():
        raise _reject(
            project_id,
            f"{PROJECT_DECLARATION_FILENAME} is missing — a project must declare "
            "its charter and direction before buildings accumulate",
        )
    try:
        record: Any = json.loads(declaration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _reject(project_id, f"{PROJECT_DECLARATION_FILENAME} does not parse: {exc}")
    if not isinstance(record, dict):
        raise _reject(project_id, f"{PROJECT_DECLARATION_FILENAME} must be a JSON object")

    for key in record:
        if _forbidden_judgment_key(str(key)):
            raise _reject(
                project_id,
                f"forbidden judgment key {key!r} — a project declaration records "
                "direction facts only; success/quality/movement judgment never "
                "lives in a declaration record",
            )
    unknown = sorted(set(map(str, record)) - set(PROJECT_DECLARATION_KEYS))
    if unknown:
        raise _reject(
            project_id,
            f"unknown key(s) {', '.join(unknown)} — the declaration key set is closed "
            f"({', '.join(PROJECT_DECLARATION_KEYS)})",
        )
    missing = sorted(set(PROJECT_DECLARATION_KEYS) - set(map(str, record)))
    if missing:
        raise _reject(project_id, f"missing required key(s): {', '.join(missing)}")

    project_ref = record["project_ref"]
    expected_ref = f"{PROJECT_REF_PREFIX}{project_id}"
    if project_ref != expected_ref:
        raise _reject(
            project_id,
            f"project_ref must be {expected_ref!r} (path is the first-class fact), "
            f"got {project_ref!r}",
        )

    texts = {key: _require_text(project_id, record, key) for key in _REQUIRED_TEXT_KEYS}

    declared_at = texts["declared_at"]
    try:
        datetime.fromisoformat(declared_at.replace("Z", "+00:00"))
    except ValueError:
        raise _reject(project_id, f"declared_at must be an ISO-8601 timestamp, got {declared_at!r}")

    managers = record["managers"]
    if (
        not isinstance(managers, list)
        or not managers
        or not all(isinstance(item, str) and item.strip() for item in managers)
    ):
        raise _reject(
            project_id,
            "managers must be a non-empty list of non-empty human owner names",
        )
    for item in managers:
        if ":" in item:
            raise _reject(
                project_id,
                f"managers entry {item!r} looks like a machine ref — managers are "
                "human owners only (agents change; who worked is AgentBinding "
                "evidence, never a charter field)",
            )

    charter_ref = record["charter_ref"]
    expected_charter = f"project/{project_id}/{PROJECT_CHARTER_FILENAME}"
    if charter_ref != expected_charter:
        raise _reject(
            project_id,
            f"charter_ref must be {expected_charter!r}, got {charter_ref!r}",
        )
    charter_path = repo_path / "project" / project_id / PROJECT_CHARTER_FILENAME
    if not charter_path.is_file():
        raise _reject(
            project_id,
            f"charter_ref {charter_ref!r} does not resolve — the charter README.md "
            "must exist before the declaration that shadows it",
        )

    return ProjectDeclaration(
        project_id=project_id,
        project_ref=project_ref,
        label=texts["label"],
        direction=texts["direction"],
        done_means=texts["done_means"],
        out_of_scope=texts["out_of_scope"],
        managers=tuple(item.strip() for item in managers),
        declared_by=texts["declared_by"],
        declared_at=declared_at,
        charter_ref=charter_ref,
        charter_path=charter_path,
    )


__all__ = [
    "PROJECT_CHARTER_FILENAME",
    "PROJECT_DECLARATION_FILENAME",
    "PROJECT_DECLARATION_KEYS",
    "PROJECT_REF_PREFIX",
    "ProjectDeclaration",
    "is_admissible_project_id",
    "load_project_declaration",
]
