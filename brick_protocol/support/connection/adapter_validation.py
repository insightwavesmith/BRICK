"""Secret/text/JSON cleaning + payload guard (universal base layer).

Extracted VERBATIM from ``brick_protocol/support/connection/agent_adapter.py`` (E2 split,
extraction 2/7). PURE relocation -- no logic/name/signature change. The
``agent_adapter`` facade re-exports every symbol here (public AND
underscore-private) so late-bound ``agent_adapter.<sym>`` access never breaks.

This module imports siblings DIRECTLY and NEVER ``from
support.connection.agent_adapter import ...`` at top level (cycle). The
external ``brick_protocol.*`` import strings are kept byte-identical to the
prior agent_adapter-local imports to preserve import identity.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from brick_protocol.agent.return_fact import ALWAYS_SECRET_KEYS as _ALWAYS_SECRET_KEYS
from brick_protocol.agent.return_fact import TOP_LEVEL_VERDICT_KEYS as _TOP_LEVEL_VERDICT_KEYS
from brick_protocol.support.connection.secret_text import (
    RAW_SECRET_PATTERNS as _RAW_SECRET_PATTERNS,
)

_RAW_SESSION_PATTERNS = (
    re.compile(r"\bsess[_-][A-Za-z0-9_-]{12,}\b"),  # sess_ and sess- (OpenAI)
    re.compile(r"\bprovider-session-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bresume-token-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bchatcmpl-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bya29\.[A-Za-z0-9._-]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),
    re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b"),  # Crockford base32 ULID session id
)
_SOURCE_FACT_BODY_LIMIT = 12000


def _validate_returned_payload(label: str, value: Any, *, depth: int = 0) -> tuple[str, ...]:
    """Walk a returned payload. Two distinct lines (Smith 0623 LOCK):

    KEEP (egress / integrity raise): a secret/session-bearing key name
    (``_ALWAYS_SECRET_KEYS``) or raw credential/session text STILL hard-raises at
    any depth -- credential egress is a real stop the worktree does not soften.

    MOVE+RECORD (no halt): a TOP-LEVEL verdict key (depth==0, in
    ``_TOP_LEVEL_VERDICT_KEYS``) is NOT halted. It is quarantined -- this walker
    REPORTS its raw key name so the caller can STRIP it from the structured return
    and record an ``ignored_forbidden_return_key`` fact. Brick comparison + the Link
    gate compute the real verdict from the structured return, so a smuggled
    top-level verdict key is inert evidence, not an authority assertion.

    Returns the raw top-level verdict key names observed at depth 0 (empty tuple
    otherwise)."""

    ignored_top_level_keys: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = _normalize(raw_key)
            # KEEP: secret/session-bearing key names stay a recursive hard raise. A
            # nested key can still structure credential material even when it is not
            # an authority assertion.
            if key in _ALWAYS_SECRET_KEYS:
                raise ValueError(f"{label} contains forbidden return key {raw_key!r}")
            if depth == 0 and key in _TOP_LEVEL_VERDICT_KEYS:
                # MOVE+RECORD: quarantine, do not halt; the caller strips + records.
                ignored_top_level_keys.append(str(raw_key))
                continue
            _validate_returned_payload(f"{label}.{raw_key}", child, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_returned_payload(f"{label}[{index}]", child, depth=depth + 1)
    elif isinstance(value, str):
        _reject_secret_text(label, value)
    return tuple(ignored_top_level_keys)


def _safe_excerpt(value: str, *, limit: int = 600) -> str:
    text = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _reject_secret_text(label: str, value: str) -> None:
    if any(pattern.search(value) for pattern in _RAW_SECRET_PATTERNS):
        raise ValueError(f"{label} contains raw credential-looking text")
    if any(pattern.search(value) for pattern in _RAW_SESSION_PATTERNS):
        raise ValueError(f"{label} contains raw provider session-looking text")


def _reject_forbidden_text(label: str, value: str) -> None:
    if value:
        _reject_secret_text(label, value)


def _clean_optional_text(label: str, value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    return value.strip()


def _clean_source_fact_bodies(value: Any) -> Mapping[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("source_fact_bodies must be a mapping")
    cleaned: dict[str, str] = {}
    for raw_ref, raw_body in value.items():
        ref = _clean_optional_text("source_fact_bodies ref", raw_ref)
        body = _clean_optional_text(f"source_fact_bodies.{ref}", raw_body)
        if not ref:
            raise ValueError("source_fact_bodies refs must not be blank")
        _reject_forbidden_text("source_fact_bodies ref", ref)
        cleaned[ref] = safe_source_fact_body(body)
    return cleaned


def _clean_link_handoff_refs(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("link_handoff_refs must be a mapping")
    cleaned = _clean_json_value("link_handoff_refs", value)
    if not isinstance(cleaned, Mapping):
        raise TypeError("link_handoff_refs must clean to a mapping")
    return cleaned


def _clean_agent_instruction_packet(
    value: Any,
    *,
    agent_object_ref: str,
) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("agent_instruction_packet must be a mapping")
    if not value:
        return {}
    cleaned = _clean_instruction_json_value("agent_instruction_packet", value)
    if not isinstance(cleaned, Mapping):
        raise TypeError("agent_instruction_packet must clean to a mapping")
    if cleaned.get("kind") != "agent-instruction-packet":
        raise ValueError("agent_instruction_packet.kind must be agent-instruction-packet")
    if cleaned.get("agent_object_ref") != agent_object_ref:
        raise ValueError(
            "agent_instruction_packet.agent_object_ref must match AgentAdapterRequest.agent_object_ref"
        )
    return cleaned


def _clean_json_value(label: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = _clean_optional_text(f"{label} key", raw_key)
            if not key:
                raise ValueError(f"{label} keys must not be blank")
            _reject_secret_text(f"{label} key", key)
            cleaned[key] = _clean_json_value(f"{label}.{key}", child)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(f"{label}[{index}]", item) for index, item in enumerate(value)]
    if isinstance(value, str):
        text = _clean_optional_text(label, value)
        _reject_secret_text(label, text)
        return text
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"{label} must be JSON-compatible")


def _clean_instruction_json_value(label: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = _clean_optional_text(f"{label} key", raw_key)
            if not key:
                raise ValueError(f"{label} keys must not be blank")
            _reject_secret_text(f"{label} key", key)
            cleaned[key] = _clean_instruction_json_value(f"{label}.{key}", child)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [
            _clean_instruction_json_value(f"{label}[{index}]", item)
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        return safe_source_fact_body(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"{label} must be JSON-compatible")


def safe_source_fact_body(value: str, *, limit: int = _SOURCE_FACT_BODY_LIMIT) -> str:
    """Redact/truncate source bodies before carrying them as work-packet support."""

    body = _clean_optional_text("source_fact_body", value)
    for pattern in _RAW_SECRET_PATTERNS:
        body = pattern.sub("[REDACTED_RAW_CREDENTIAL]", body)
    for pattern in _RAW_SESSION_PATTERNS:
        body = pattern.sub("[REDACTED_PROVIDER_SESSION_REF]", body)
    if len(body) > limit:
        body = body[:limit] + "\n[TRUNCATED_SOURCE_FACT_BODY]"
    return body


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")
