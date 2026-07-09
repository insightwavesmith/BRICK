"""Per-user LLM provider registration support.

This module owns only support-side persistence for ``~/.brick/providers.yaml``.
It records observed provider readiness and exposes read helpers for adapter
resolution. It stores no credentials, chooses no Movement, and judges no
success or quality.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.support.connection.adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_FUGU_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_GROK_LOCAL,
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_GEMINI_DEFAULT,
    MODEL_REF_GROK_DEFAULT,
    MODEL_REF_SAKANA_FUGU,
    MODEL_REF_SAKANA_FUGU_ULTRA,
)
from brick_protocol.support.connection.adapter_model_casting import (
    _validate_model_ref_for_adapter,
)


PROVIDERS_FILENAME = "providers.yaml"
PROVIDER_LADDER_ENV = "BRICK_PROVIDER_LADDER"
PROVIDER_REGISTRY_SCHEMA_VERSION = 1

CASTING_TIER_PREFIX = "casting-tier:"
CASTING_LENS_PREFIX = "casting-lens:"
CASTING_REASONING_EFFORT_DEFAULT = "effort:default"
CASTING_REASONING_EFFORT_XHIGH = "effort:xhigh"
# Policy-visible concrete model refs include model:sakana:fugu-ultra for deep tier.

CASTING_TIER_DECLARATIONS: Mapping[str, Mapping[str, Any]] = {
    "casting-tier:plan": {
        "adapter_ladder": (
            {
                "adapter_ref": ADAPTER_CLAUDE_LOCAL,
                "model_ref": "model:claude:claude-opus-4-8",
                "selected_reasoning_effort_ref": CASTING_REASONING_EFFORT_XHIGH,
            },
        ),
    },
    "casting-tier:deep": {
        "adapter_ladder": (
            {
                "adapter_ref": ADAPTER_CODEX_FUGU_LOCAL,
                "model_ref": MODEL_REF_SAKANA_FUGU_ULTRA,
                "selected_reasoning_effort_ref": CASTING_REASONING_EFFORT_XHIGH,
            },
        ),
    },
    "casting-tier:standard": {
        "adapter_ladder": (
            {
                "adapter_ref": ADAPTER_CLAUDE_LOCAL,
                "model_ref": "model:claude:claude-opus-4-8",
                "selected_reasoning_effort_ref": CASTING_REASONING_EFFORT_XHIGH,
            },
        ),
    },
    "casting-tier:light": {
        "adapter_ladder": (
            {
                "adapter_ref": ADAPTER_GEMINI_LOCAL,
                "model_ref": MODEL_REF_GEMINI_DEFAULT,
                "selected_reasoning_effort_ref": CASTING_REASONING_EFFORT_DEFAULT,
            },
        ),
    },
}

CASTING_LENS_DECLARATIONS: Mapping[str, Mapping[str, Any]] = {
    "casting-lens:plan": {},
    "casting-lens:deep-design": {},
    "casting-lens:work": {},
    "casting-lens:repair": {},
    "casting-lens:review": {},
    "casting-lens:code-attack": {},
    "casting-lens:axis-attack": {},
    "casting-lens:evidence-integrity": {},
    "casting-lens:qa": {},
    "casting-lens:closure": {},
    "casting-lens:implementation": {},
}

DEFAULT_MODEL_REF_BY_ADAPTER = {
    ADAPTER_CLAUDE_LOCAL: MODEL_REF_CLAUDE_INHERIT,
    ADAPTER_CODEX_LOCAL: MODEL_REF_CODEX_DEFAULT,
    ADAPTER_CODEX_FUGU_LOCAL: MODEL_REF_SAKANA_FUGU,
    ADAPTER_GEMINI_LOCAL: MODEL_REF_GEMINI_DEFAULT,
    ADAPTER_GROK_LOCAL: MODEL_REF_GROK_DEFAULT,
}

MODEL_REF_PROVIDER_BY_ADAPTER = {
    ADAPTER_CLAUDE_LOCAL: "claude",
    ADAPTER_CODEX_LOCAL: "codex",
    ADAPTER_CODEX_FUGU_LOCAL: "sakana",
    ADAPTER_GEMINI_LOCAL: "gemini",
    ADAPTER_GROK_LOCAL: "grok",
}

LLM_ALIAS_DECLARATIONS = {
    "claude": {
        "adapter_ref": ADAPTER_CLAUDE_LOCAL,
        "model_ref": MODEL_REF_CLAUDE_INHERIT,
        "model_aliases": {
            "sonnet": "claude-sonnet-5",
            "opus": "claude-opus-4-8",
            "haiku": "claude-haiku-4-5-20251001",
        },
    },
    "codex": {
        "adapter_ref": ADAPTER_CODEX_LOCAL,
        "model_ref": MODEL_REF_CODEX_DEFAULT,
    },
    "fugu": {
        "adapter_ref": ADAPTER_CODEX_FUGU_LOCAL,
        "model_ref": MODEL_REF_SAKANA_FUGU,
    },
    "gemini": {
        "adapter_ref": ADAPTER_GEMINI_LOCAL,
        "model_ref": MODEL_REF_GEMINI_DEFAULT,
    },
    "grok": {
        "adapter_ref": ADAPTER_GROK_LOCAL,
        "model_ref": MODEL_REF_GROK_DEFAULT,
        "model_aliases": {
            "fast": "grok-composer-2.5-fast",
        },
    },
}


def _bare_llm_alias_token(value: str) -> bool:
    parts = value.split("-")
    return bool(parts) and all(part.isalnum() and part.lower() == part for part in parts)


def llm_alias_declaration(alias: str) -> Mapping[str, str]:
    token = str(alias or "").strip()
    if not token or not _bare_llm_alias_token(token):
        raise ValueError("llm alias must be a bare token")
    declaration = LLM_ALIAS_DECLARATIONS.get(token)
    if declaration is None:
        allowed = ", ".join(sorted(LLM_ALIAS_DECLARATIONS))
        raise ValueError(f"llm alias must be one of: {allowed}")
    return declaration


def resolve_model_alias_ref(adapter_ref: str, model_ref: str) -> str:
    """Expand admitted provider model aliases to concrete model refs."""

    provider = MODEL_REF_PROVIDER_BY_ADAPTER.get(adapter_ref)
    if provider is None:
        return model_ref
    expected_prefix = f"model:{provider}:"
    if not model_ref.startswith(expected_prefix):
        _validate_model_ref_for_adapter(adapter_ref, model_ref)
        return model_ref
    model_id = model_ref.removeprefix(expected_prefix)
    if model_id in {"default", "inherit"} or model_id.startswith(f"{provider}-"):
        _validate_model_ref_for_adapter(adapter_ref, model_ref)
        return model_ref
    declaration = LLM_ALIAS_DECLARATIONS.get(provider)
    aliases = declaration.get("model_aliases") if isinstance(declaration, Mapping) else None
    if not isinstance(aliases, Mapping):
        _validate_model_ref_for_adapter(adapter_ref, model_ref)
        return model_ref
    resolved = aliases.get(model_id) if isinstance(aliases, Mapping) else None
    if isinstance(resolved, str) and resolved.strip():
        resolved_ref = f"{expected_prefix}{resolved.strip()}"
        _validate_model_ref_for_adapter(adapter_ref, resolved_ref)
        return resolved_ref
    allowed = ", ".join(sorted(aliases)) if isinstance(aliases, Mapping) else ""
    raise ValueError(
        f"selected_model_ref {provider} alias is not admitted; use "
        f"model:{provider}:<{provider}-model-id>"
        + (f" or one of aliases: {allowed}" if allowed else "")
    )


def brick_home() -> Path:
    raw = (os.environ.get("BRICK_HOME") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".brick"


def provider_registry_path(*, home: Path | str | None = None) -> Path:
    root = Path(home).expanduser() if home is not None else brick_home()
    return root / PROVIDERS_FILENAME


def provider_ladder_enabled(registry: Mapping[str, Any] | None = None) -> bool:
    if (os.environ.get(PROVIDER_LADDER_ENV) or "").strip() == "0":
        return False
    if registry is not None and registry.get("enabled") is False:
        return False
    return True


def load_provider_registry(path: Path | str | None = None) -> dict[str, Any] | None:
    registry_path = Path(path).expanduser() if path is not None else provider_registry_path()
    if not registry_path.is_file():
        return None
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - environment contract
        raise RuntimeError("provider registry requires PyYAML") from exc
    loaded = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{registry_path}: providers registry must be a mapping")
    return dict(loaded)


def save_provider_registry(registry: Mapping[str, Any], path: Path | str | None = None) -> Path:
    registry_path = Path(path).expanduser() if path is not None else provider_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - environment contract
        raise RuntimeError("provider registry requires PyYAML") from exc
    registry_path.write_text(
        yaml.safe_dump(dict(registry), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    try:
        registry_path.chmod(0o600)
    except OSError:
        pass
    return registry_path


def _providers(registry: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    rows = registry.get("providers") if isinstance(registry, Mapping) else None
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def provider_entry(registry: Mapping[str, Any] | None, adapter_ref: str) -> Mapping[str, Any] | None:
    for row in _providers(registry):
        if str(row.get("adapter_ref") or "").strip() == adapter_ref:
            return row
    return None


def provider_entry_ready(row: Mapping[str, Any] | None) -> bool:
    last_preflight = row.get("last_preflight") if isinstance(row, Mapping) else None
    if not isinstance(last_preflight, Mapping):
        return False
    return str(last_preflight.get("status") or "").strip() == "ready"


def registry_static_preference_ready(
    registry: Mapping[str, Any] | None,
    adapter_ref: str,
) -> bool:
    return provider_ladder_enabled(registry) and provider_entry_ready(
        provider_entry(registry, adapter_ref)
    )


def first_ready_registered_adapter(
    registry: Mapping[str, Any] | None,
    *,
    allowed_adapter_refs: set[str],
) -> str | None:
    if not provider_ladder_enabled(registry):
        return None
    preferred = str(registry.get("preferred_adapter_ref") or "").strip() if registry else ""
    ordered: list[str] = []
    if preferred:
        ordered.append(preferred)
    for row in _providers(registry):
        adapter_ref = str(row.get("adapter_ref") or "").strip()
        if adapter_ref and adapter_ref not in ordered:
            ordered.append(adapter_ref)
    for adapter_ref in ordered:
        if adapter_ref not in allowed_adapter_refs:
            continue
        if provider_entry_ready(provider_entry(registry, adapter_ref)):
            return adapter_ref
    return None


def model_ref_for_adapter(
    registry: Mapping[str, Any] | None,
    adapter_ref: str,
) -> str:
    default_ref = DEFAULT_MODEL_REF_BY_ADAPTER.get(adapter_ref, "model:default")
    row = provider_entry(registry, adapter_ref)
    if isinstance(row, Mapping):
        model_ref = str(row.get("model_ref") or "").strip()
        if model_ref:
            try:
                _validate_model_ref_for_adapter(adapter_ref, model_ref)
            except ValueError:
                return default_ref
            return model_ref
    return default_ref



def _required_ref_token(label: str, value: str, *, prefix: str, admitted: Mapping[str, Any]) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty")
    if not text.startswith(prefix):
        if ":" in text:
            raise ValueError(f"{label} must use {prefix}<token>")
        text = f"{prefix}{text}"
    tail = text.removeprefix(prefix)
    if not tail or any(part in tail for part in ("/", "#")):
        raise ValueError(f"{label} must be a bare {prefix}<token> ref")
    if text not in admitted:
        allowed = ", ".join(sorted(admitted))
        raise ValueError(f"{label} is not admitted: {text}; admitted refs: {allowed}")
    return text


def _optional_lens_ref(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return _required_ref_token(
        "casting_lens_ref",
        str(value),
        prefix=CASTING_LENS_PREFIX,
        admitted=CASTING_LENS_DECLARATIONS,
    )


def resolve_casting_tier(
    registry: Mapping[str, Any] | None,
    tier_ref: str,
    lens_ref: str | None = None,
) -> dict[str, str | None]:
    """Resolve one declared casting tier through the provider registry ladder.

    A tier declaration is an explicit provider-neutral interpretation delegation,
    not a support default. Therefore resolution is fail-closed: no registry, a
    disabled ladder, an unknown tier/lens token, or no ready adapter in the
    tier's declared ladder raises loudly. The returned concrete selected_* values
    are the only runtime casting data consumers should persist or execute.
    """

    tier = _required_ref_token(
        "casting_tier_ref",
        tier_ref,
        prefix=CASTING_TIER_PREFIX,
        admitted=CASTING_TIER_DECLARATIONS,
    )
    lens = _optional_lens_ref(lens_ref)
    if not isinstance(registry, Mapping):
        raise ValueError(
            "casting_tier_ref requires a providers.yaml registry; run brick onboard "
            "or declare concrete selected_* values explicitly"
        )
    if not provider_ladder_enabled(registry):
        raise ValueError(
            "casting_tier_ref requires the provider registry ladder to be enabled; "
            "BRICK_PROVIDER_LADDER=0 or enabled: false cannot execute a tier delegation"
        )

    declaration = CASTING_TIER_DECLARATIONS[tier]
    rows = declaration.get("adapter_ladder")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise ValueError(f"{tier}: adapter_ladder declaration is empty")
    checked: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"{tier}: adapter_ladder rows must be mappings")
        adapter_ref = str(row.get("adapter_ref") or "").strip()
        model_ref = str(row.get("model_ref") or "").strip()
        effort_ref = str(row.get("selected_reasoning_effort_ref") or "").strip()
        if not adapter_ref or not model_ref:
            raise ValueError(f"{tier}: adapter_ladder row missing adapter_ref/model_ref")
        _validate_model_ref_for_adapter(adapter_ref, model_ref)
        checked.append(adapter_ref)
        if not provider_entry_ready(provider_entry(registry, adapter_ref)):
            continue
        return {
            "selected_adapter_ref": adapter_ref,
            "selected_model_ref": model_ref,
            "selected_reasoning_effort_ref": effort_ref or CASTING_REASONING_EFFORT_DEFAULT,
            "casting_tier_ref": tier,
            "casting_lens_ref": lens,
        }
    checked_text = ", ".join(checked)
    raise ValueError(
        f"{tier}: no ready provider in declared tier ladder ({checked_text}); "
        "run brick onboard or declare concrete selected_* values explicitly"
    )

def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def register_ready_provider(
    adapter_ref: str,
    preflight: Mapping[str, Any],
    *,
    model_ref: str | None = None,
    reasoning_tier: str | None = "medium",
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Persist one provider row only after a ready preflight observation."""

    if not bool(preflight.get("ok")):
        return {
            "ok": False,
            "action": "skipped_not_ready",
            "adapter_ref": adapter_ref,
            "registry_path": str(Path(path).expanduser() if path is not None else provider_registry_path()),
        }
    registry = load_provider_registry(path) or {
        "version": PROVIDER_REGISTRY_SCHEMA_VERSION,
        "providers": [],
    }
    providers = list(_providers(registry))
    now = _utc_iso()
    row = {
        "adapter_ref": adapter_ref,
        "registered_at": now,
        "last_preflight": {"status": "ready", "checked_at": now},
        "model_ref": model_ref or DEFAULT_MODEL_REF_BY_ADAPTER.get(adapter_ref, "model:default"),
        "reasoning_tier": reasoning_tier,
    }
    replaced = False
    next_rows: list[Mapping[str, Any]] = []
    for existing in providers:
        if str(existing.get("adapter_ref") or "").strip() == adapter_ref:
            merged = dict(existing)
            merged.update(row)
            next_rows.append(merged)
            replaced = True
        else:
            next_rows.append(existing)
    if not replaced:
        next_rows.append(row)
    next_registry = dict(registry)
    next_registry["version"] = PROVIDER_REGISTRY_SCHEMA_VERSION
    next_registry["providers"] = next_rows
    if not str(next_registry.get("preferred_adapter_ref") or "").strip():
        next_registry["preferred_adapter_ref"] = adapter_ref
    registry_path = save_provider_registry(next_registry, path)
    return {
        "ok": True,
        "action": "registered" if not replaced else "refreshed",
        "adapter_ref": adapter_ref,
        "registry_path": str(registry_path),
        "preferred_adapter_ref": str(next_registry.get("preferred_adapter_ref") or ""),
    }
