"""Per-user report sink registration support.

This module owns only support-side persistence for ``~/.brick/sinks.yaml``. It
records observed sink credential presence and reachability checks. It stores no
credential values, chooses no Movement, and judges no success or quality.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SINKS_FILENAME = "sinks.yaml"
SINK_REGISTRY_SCHEMA_VERSION = 1

SINK_REF_SLACK = "report-sink:slack"
SINK_REF_DASHBOARD = "report-sink:dashboard"


def brick_home() -> Path:
    raw = (os.environ.get("BRICK_HOME") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".brick"


def sink_registry_path(*, home: Path | str | None = None) -> Path:
    root = Path(home).expanduser() if home is not None else brick_home()
    return root / SINKS_FILENAME


def load_sink_registry(path: Path | str | None = None) -> dict[str, Any] | None:
    registry_path = Path(path).expanduser() if path is not None else sink_registry_path()
    if not registry_path.is_file():
        return None
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - environment contract
        raise RuntimeError("sink registry requires PyYAML") from exc
    loaded = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{registry_path}: sinks registry must be a mapping")
    return dict(loaded)


def save_sink_registry(registry: Mapping[str, Any], path: Path | str | None = None) -> Path:
    registry_path = Path(path).expanduser() if path is not None else sink_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - environment contract
        raise RuntimeError("sink registry requires PyYAML") from exc
    registry_path.write_text(
        yaml.safe_dump(dict(registry), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    try:
        registry_path.chmod(0o600)
    except OSError:
        pass
    return registry_path


def _sinks(registry: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    rows = registry.get("sinks") if isinstance(registry, Mapping) else None
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_sink_reachability(
    sink_ref: str,
    *,
    credentials_present: bool,
    reachability_status: str,
    detail: Mapping[str, Any] | None = None,
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Persist one sink row with cached reachability evidence.

    ``detail`` must be credential-free. Callers pass only status classes,
    response codes, or error kinds.
    """

    registry = load_sink_registry(path) or {
        "version": SINK_REGISTRY_SCHEMA_VERSION,
        "enabled": True,
        "sinks": [],
    }
    rows = list(_sinks(registry))
    now = _utc_iso()
    check: dict[str, Any] = {
        "status": reachability_status,
        "checked_at": now,
    }
    if detail:
        for key, value in detail.items():
            if value is not None:
                check[str(key)] = value
    next_row = {
        "sink_ref": sink_ref,
        "registered_at": now,
        "enabled": True,
        "credentials_present": bool(credentials_present),
        "last_reachability_check": check,
    }
    replaced = False
    next_rows: list[Mapping[str, Any]] = []
    for row in rows:
        if str(row.get("sink_ref") or "").strip() == sink_ref:
            merged = dict(row)
            merged.update(next_row)
            if row.get("registered_at"):
                merged["registered_at"] = row["registered_at"]
            next_rows.append(merged)
            replaced = True
        else:
            next_rows.append(row)
    if not replaced:
        next_rows.append(next_row)
    next_registry = dict(registry)
    next_registry["version"] = SINK_REGISTRY_SCHEMA_VERSION
    next_registry.setdefault("enabled", True)
    next_registry["sinks"] = next_rows
    registry_path = save_sink_registry(next_registry, path)
    return {
        "ok": True,
        "action": "recorded" if not replaced else "refreshed",
        "sink_ref": sink_ref,
        "registry_path": str(registry_path),
        "reachability_status": reachability_status,
    }
