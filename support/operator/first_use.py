"""Render the customer FIRST_USE.md support note after the local init example.

This module is support projection only. It records what the already-declared
local example build reported and points the caller at the next declared manual
steps. It does not choose Movement, judge quality, or inspect credentials.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


FIRST_USE_FILENAME = "FIRST_USE.md"
EXAMPLE_STUB_DISCLAIMER = (
    "이건 예제입니다 -- 실제 빌딩은 `brick auth login` 후 `--real-provider`."
)


def _packet_text(packet: Mapping[str, Any], key: str, default: str = "not recorded") -> str:
    value = packet.get(key)
    if value is None or value == "":
        return default
    return str(value)


def _packet_bool_text(packet: Mapping[str, Any], key: str, default: str = "not recorded") -> str:
    value = packet.get(key)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return default
    return str(value)


def _doctor_lines(doctor_packet: Mapping[str, Any]) -> list[str]:
    rows = doctor_packet.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return ["- Doctor packet recorded no rows."]
    rendered: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        target = str(row.get("target") or "unknown")
        observed = "observed" if row.get("ok") else "not observed"
        message = str(row.get("message_ko") or row.get("message") or "").strip()
        suffix = f" - {message}" if message else ""
        rendered.append(f"- {target}: {observed}{suffix}")
    return rendered or ["- Doctor packet recorded no usable rows."]


_READINESS_FIELD_KEYS = (
    "target",
    "adapter_ref",
    "ok",
    "installed",
    "authed",
    "api_key_env_present",
    "credential_validity",
    "live_provider_not_run",
)


def _structured_readiness_lines(doctor_packet: Mapping[str, Any]) -> list[str]:
    rows = doctor_packet.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return ["- not recorded"]
    rendered: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        fields = [
            f"{key}={_packet_bool_text(row, key) if isinstance(row.get(key), bool) else _packet_text(row, key)}"
            for key in _READINESS_FIELD_KEYS
            if key in row
        ]
        if fields:
            rendered.append(f"- {'; '.join(fields)}")
    return rendered or ["- not recorded"]


def _step_adapter_lines(build_packet: Mapping[str, Any]) -> list[str]:
    rows = build_packet.get("materialized_step_adapters")
    if not isinstance(rows, list) or not rows:
        return ["- not recorded"]
    rendered: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        step_ref = _packet_text(row, "step_ref")
        adapter_ref = _packet_text(row, "selected_adapter_ref")
        model_ref = _packet_text(row, "selected_model_ref")
        rendered.append(f"- `{step_ref}` -> `{adapter_ref}` (`{model_ref}`)")
    return rendered or ["- not recorded"]


def render_first_use(
    *,
    doctor_packet: Mapping[str, Any],
    build_packet: Mapping[str, Any],
) -> str:
    """Return deterministic Korean+English FIRST_USE.md text."""

    lines = [
        "# FIRST_USE",
        "",
        "## 방금 일어난 일 / What just happened",
        "",
        "Brick ran the bundled local example build and recorded support evidence.",
        "브릭이 포함된 로컬 예제 빌딩을 실행했고, 지원 증거를 기록했습니다.",
        "",
        "## 예제 스텁 고지 / Example stub notice",
        "",
        EXAMPLE_STUB_DISCLAIMER,
        "This was a local example stub. A real provider-backed build needs "
        "`brick auth login` and a `--real-provider` run.",
        "",
        "## 기록된 증거 / Recorded evidence",
        "",
        f"- building_id: `{_packet_text(build_packet, 'building_id')}`",
        f"- adapter_ref: `{_packet_text(build_packet, 'adapter_ref')}`",
        f"- chain_preset_ref: `{_packet_text(build_packet, 'chain_preset_ref')}`",
        f"- frontier_kind: `{_packet_text(build_packet, 'frontier_kind')}`",
        "- customer_visible_frontier_state: "
        f"`{_packet_text(build_packet, 'customer_visible_frontier_state')}`",
        "- customer_visible_not_ready: "
        f"`{_packet_bool_text(build_packet, 'customer_visible_not_ready')}`",
        "- frontier_message: "
        f"`{_packet_text(build_packet, 'customer_visible_frontier_message')}`",
        f"- evidence_root: `{_packet_text(build_packet, 'evidence_root')}`",
        "",
        "## Agent adapter evidence",
        "",
        *_step_adapter_lines(build_packet),
        "",
        "## Provider readiness evidence",
        "",
        *_structured_readiness_lines(doctor_packet),
        "",
        "## doctor 관찰 / Doctor observations",
        "",
        *_doctor_lines(doctor_packet),
        "",
        "## 다음 단계 / Next steps",
        "",
        "1. `cat FIRST_USE.md`",
        "2. `brick auth login`",
        "3. Run your real build with `--real-provider` after readiness is observed. "
        "With no explicit `--adapter`, Brick uses the first ready provider-backed "
        "observed-write adapter and falls back to `adapter:local` when none is ready.",
        "",
        "Proof limits: this file is support evidence only; it is not source truth, "
        "not success judgment, not quality judgment, and not Movement authority.",
        "",
    ]
    return "\n".join(lines)


def write_first_use(
    output_root: Path | str,
    *,
    doctor_packet: Mapping[str, Any],
    build_packet: Mapping[str, Any],
) -> dict[str, str]:
    """Write FIRST_USE.md under the declared output root."""

    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / FIRST_USE_FILENAME
    path.write_text(
        render_first_use(doctor_packet=doctor_packet, build_packet=build_packet),
        encoding="utf-8",
    )
    return {"path": str(path), "filename": FIRST_USE_FILENAME}
