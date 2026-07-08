"""Draft → launched-plan flip diff support module (anchoring-defense-0707a).

``brick draft-diff`` compares a PRESERVED draft graph-decl against the LAUNCHED
vessel plan (or any caller-specified declaration pair), splits the field-by-field
differences into a **shape-flip** aggregate (graph structure) and a
**casting-flip** aggregate (performer selection), and appends one append-only
record to ``<brick_home>/drafts/flip-ledger.jsonl``. A rolling flip-rate window
(N=10) reads this Building's records from the ledger; when the Building-scoped
sample reaches N and the flip rate is exactly zero — the operator never
overturned a single draft for that Building — it surfaces the advisory
``operator-thought-stall canary`` literal (anchoring defense §J/§L: 판단 후 수정
개념이 손실회피편향을 준다 → 비율 0 수렴 = 사고 정지 카나리아).

This is support evidence only. It is not source truth, success judgment, quality
judgment, or Movement authority. Per Rule 3 (자동발사 금지) this module reaches
NO launch seam: it never imports the launch driver, the onboard entry module, or
the walker modules, and it never emits an ``action`` key or a Movement literal.
It only READS two declaration files, WRITES an append-only evidence ledger under
``<brick_home>`` (never inside the repo), and RECORDS observations. The canary is
advice, not a verdict — it wires to no gate, no launch, and no route.

The blind pre-registration cross-check (D2) reads
``<brick_home>/drafts/preregistration/<building_id>.json`` when present and
records a field-by-field comparison plus a ``prereg-first`` ordering observation.
Honest proof limit: file mtime ordering does NOT prove the pre-registration was
not forged/backdated; the ordering is recorded evidence only, never a verdict.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "THOUGHT_STALL_CANARY",
    "DEFAULT_FLIP_WINDOW",
    "CASTING_LEAF_KEYS",
    "PROOF_LIMITS",
    "flatten_declaration",
    "classify_flip",
    "diff_declarations",
    "load_declaration_file",
    "append_flip_record",
    "read_flip_records",
    "records_for_building",
    "rolling_flip_rate",
    "thought_stall_canary_line",
    "load_preregistration",
    "compare_preregistration",
    "run_draft_diff",
]

# CANARY-LITERAL — the exact advisory literal. A drift here must flip the pin
# checker (D4 variant-RED: 카나리아 리터럴 드리프트 → rc=1). Support advice only.
THOUGHT_STALL_CANARY = "operator-thought-stall canary"
DEFAULT_FLIP_WINDOW = 10

# SHAPE-CASTING-SEPARATION — the casting leaf-key set. A flip whose flattened
# path's LEAF key is one of these tokens is a *casting* flip (performer
# selection); all other flips are *shape* flips (graph structure). Collapsing
# this separation (D1 분리집계 중화) must flip the pin checker to rc=1.
CASTING_LEAF_KEYS = frozenset(
    {
        "adapter",
        "adapter_ref",
        "model",
        "model_ref",
        "reasoning_effort",
        "reasoning_effort_ref",
        "effort",
        "adapter_timeout_seconds",
        "timeout_seconds",
        "preferred_model_ref",
        "preferred_adapter_ref",
        "selected_model_ref",
        "selected_adapter_ref",
        "casting_tier",
        "casting_tier_ref",
        "casting_lens",
        "casting_lens_ref",
    }
)

PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "file mtime ordering does not prove a pre-registration was not forged",
    "the canary is advice, not a verdict, gate, or Movement",
    "the rolling flip-rate window is scoped to the current building_id; "
    "cross-building ledger records never mask or fire another building's canary",
    "ledger-record provenance is NOT authenticated: append_flip_record trusts "
    "the recorded flipped/building_id fields; a hand-forged ledger line is not detectable here",
    "the diff compares typed scalar tokens with presence decided by key "
    "membership; a type flip (int->str) and a real value equal to a render "
    "sentinel are both detected, but semantic equivalence across types is not "
    "judged (int:1 and str:1 are recorded as a flip, never reconciled)",
)

# LEAF-KEY-EXTRACTION — a flattened path is ``a.b.c[idx]``; the *leaf key* is the
# final dotted segment with any trailing ``[idx]`` list address stripped. Casting
# classification keys ON THE LEAF ONLY, never on an ancestor token, so a
# structural sub-field under an ancestor that happens to be named like a casting
# key (e.g. ``nodes[0].model.training_corpus`` — ``model`` is a CONTAINER here,
# ``training_corpus`` is the changed leaf) is correctly a *shape* flip, not a
# casting flip (0707 attack-QA: ancestor-token collision misclassified a
# structural change as a casting flip).
_LEAF_INDEX_RE = re.compile(r"(?:\[\d+\])+$")


def _leaf_key(path: str) -> str:
    """Return the final dotted segment of a flattened path, minus trailing ``[idx]``.

    ``nodes[0].model.training_corpus`` -> ``training_corpus``;
    ``nodes[0].adapter_ref`` -> ``adapter_ref``; ``branches[2].casting.model`` ->
    ``model``; ``adapter_refs[1]`` -> ``adapter_refs``. Support evidence only.
    """

    last = str(path or "").rsplit(".", 1)[-1]
    return _LEAF_INDEX_RE.sub("", last)


# ---------------------------------------------------------------------------
# Field-by-field diff.
# ---------------------------------------------------------------------------
def flatten_declaration(value: Any, prefix: str = "") -> dict[str, str]:
    """Flatten a declaration into ``dotted.path[idx] -> str(scalar)`` leaves.

    Deterministic and order-independent for mappings (the caller compares by
    key). Lists are index-addressed so a reordered/resized fan surfaces as a
    shape flip. Support evidence only.
    """

    out: dict[str, str] = {}
    if isinstance(value, Mapping):
        for key in value:
            child = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten_declaration(value[key], child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            out.update(flatten_declaration(item, f"{prefix}[{index}]"))
    else:
        out[prefix] = "" if value is None else str(value)
    return out


# TYPED-SCALAR — the diff compares TYPED scalar tokens, never bare ``str(value)``.
# ``str(1) == str("1")`` and ``str(True) == str("True")``, so a bare-string diff
# is blind to a type flip (int->str, bool->str, null->"") — an invisible change
# an operator could use to launder a real edit past the ledger (0707 attack-QA
# P2: type-flip-invisible zero-flip). Tagging the type makes ``int:1`` and
# ``str:1`` compare unequal so the flip is recorded. ``bool`` is checked before
# ``int`` because ``bool`` is an ``int`` subclass. Support evidence only.
def _typed_scalar(value: Any) -> str:
    """Return a ``type:repr`` token for a scalar so type flips stay visible."""

    if value is None:
        return "null:"
    if isinstance(value, bool):
        return f"bool:{value}"
    if isinstance(value, int):
        return f"int:{value}"
    if isinstance(value, float):
        return f"float:{value!r}"
    return f"str:{value}"


def _flatten_typed(value: Any, prefix: str = "") -> dict[str, str]:
    """Flatten a declaration into ``dotted.path[idx] -> type:repr`` leaves.

    Mirrors :func:`flatten_declaration` but keeps the scalar TYPE in the leaf
    token (via :func:`_typed_scalar`) so :func:`diff_declarations` detects a type
    flip that a bare-string flatten would silently absorb. Support evidence only.
    """

    out: dict[str, str] = {}
    if isinstance(value, Mapping):
        for key in value:
            child = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_typed(value[key], child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            out.update(_flatten_typed(item, f"{prefix}[{index}]"))
    else:
        out[prefix] = _typed_scalar(value)
    return out


# ABSENT-MARKER — a leaf missing on one side. Presence is decided by ``path in
# map`` membership BEFORE this marker is ever read, so a real value can never
# collide with "absent" (0707 attack-QA P1: sentinel-collision zero-flip, where a
# real leaf whose value equalled the missing sentinel string was diffed as
# unchanged). This marker is cosmetic render text only, never an equality token.
_ABSENT_MARKER = "∅(absent)"


def classify_flip(path: str) -> str:
    """Return ``"casting"`` when the flattened path's LEAF key names a casting
    field, else ``"shape"``.

    Classification keys on the leaf key ONLY (``_leaf_key``), never on an
    ancestor token: a structural sub-field beneath an ancestor named like a
    casting key (``nodes[0].model.training_corpus``) is a *shape* flip, while the
    performer-selection leaf itself (``nodes[0].model``, ``nodes[0].adapter_ref``,
    ``branches[0].casting.model``) is a *casting* flip. The two aggregates are
    computed from this one classifier so the shape/casting split cannot silently
    collapse into a single bucket (D1 분리집계) and cannot silently absorb a
    structural change into the casting bucket (0707 ancestor-token-collision gap).
    """

    return "casting" if _leaf_key(path) in CASTING_LEAF_KEYS else "shape"


def diff_declarations(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Field-by-field diff → separated shape-flip and casting-flip aggregates.

    Returns a mapping carrying the two SEPARATE flip lists plus their counts and
    a ``flipped`` boolean (any flip at all). Support evidence only — no verdict.
    """

    # Compare TYPED tokens with presence decided by membership (``path in map``),
    # not by a sentinel default: this closes both the sentinel-collision (P1) and
    # the type-flip-invisible (P2) gaps — a leaf that is present on exactly one
    # side is always a flip, and a leaf whose TYPE changed (int->str, null->"")
    # is always a flip.
    flat_before = _flatten_typed(before)
    flat_after = _flatten_typed(after)
    shape_flips: list[dict[str, str]] = []
    casting_flips: list[dict[str, str]] = []
    for path in sorted(set(flat_before) | set(flat_after)):
        present_before = path in flat_before
        present_after = path in flat_after
        old = flat_before.get(path, _ABSENT_MARKER) if present_before else _ABSENT_MARKER
        new = flat_after.get(path, _ABSENT_MARKER) if present_after else _ABSENT_MARKER
        # A flip is: present on exactly one side (add/remove), or a changed typed
        # token on both sides. Two present-and-equal typed tokens are unchanged.
        if present_before and present_after and old == new:
            continue
        row = {"path": path, "before": old, "after": new}
        if classify_flip(path) == "casting":
            casting_flips.append(row)
        else:
            shape_flips.append(row)
    total = len(shape_flips) + len(casting_flips)
    return {
        "shape_flips": shape_flips,
        "casting_flips": casting_flips,
        "shape_flip_count": len(shape_flips),
        "casting_flip_count": len(casting_flips),
        "total_flip_count": total,
        "flipped": total > 0,
    }


# ---------------------------------------------------------------------------
# Declaration loading (read-only).
# ---------------------------------------------------------------------------
def load_declaration_file(path: Path | str) -> Mapping[str, Any]:
    """Load a graph-decl JSON/YAML file. Raises ``ValueError`` on malformed input.

    Input malformation is the ONLY error class that must surface a non-zero CLI
    exit code; flips and the canary never fail the run.
    """

    decl_path = Path(path).expanduser()
    if not decl_path.is_file():
        raise ValueError(f"declaration file not found: {decl_path}")
    if decl_path.suffix not in {".json", ".yaml", ".yml"}:
        raise ValueError(f"declaration must be a .json/.yaml/.yml file: {decl_path}")
    text = decl_path.read_text(encoding="utf-8")
    if decl_path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - PyYAML is a hard dep
            raise ValueError("YAML declarations require PyYAML") from exc
        loaded = yaml.safe_load(text)
    else:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"declaration is not valid JSON: {decl_path}: {exc}") from exc
    if not isinstance(loaded, Mapping):
        raise ValueError(f"declaration must be a mapping object: {decl_path}")
    return loaded


# ---------------------------------------------------------------------------
# Append-only flip ledger.
# ---------------------------------------------------------------------------
def append_flip_record(ledger_path: Path | str, record: Mapping[str, Any]) -> Path:
    """Append one JSON record line to the flip ledger (append-only, never rewrites).

    The file is opened in append mode only; existing lines are never read,
    modified, or deleted here. Support evidence only.
    """

    out = Path(ledger_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(record), ensure_ascii=False, sort_keys=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return out


def read_flip_records(ledger_path: Path | str) -> list[dict[str, Any]]:
    """Read the append-only ledger into a list (read-only). Absent file → []."""

    path = Path(ledger_path).expanduser()
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue  # a corrupt line is skipped, never rewritten.
        if isinstance(loaded, Mapping):
            records.append(dict(loaded))
    return records


def records_for_building(
    records: Sequence[Mapping[str, Any]], building_id: str
) -> list[dict[str, Any]]:
    """Return only the ledger records whose ``building_id`` matches (window scope).

    The flip ledger is a single append-only file that MAY be shared across many
    Buildings. The rolling flip-rate window and the operator-thought-stall canary
    are a per-Building measure of whether *that* operator overturned *that*
    Building's drafts, so the window must read only this Building's records. The
    match is EXACT on the stripped ``building_id``: a blank/absent target scopes
    to blank/absent-id records ONLY, never to every record. Returning every
    record for a blank target (the earlier behavior) let a single ad-hoc
    (no-building) run absorb every named Building's records and drive a
    cross-building canary (0707 attack-QA P10: blank-building_id-window-absorbs-
    cross-building-records). Scoping blank->blank keeps the ad-hoc
    caller-specified-pair path working on its own records while never masking or
    firing another Building's canary. Support evidence only.
    """

    bid = str(building_id or "").strip()
    return [dict(r) for r in records if str(r.get("building_id") or "").strip() == bid]


# ---------------------------------------------------------------------------
# Rolling flip-rate window + thought-stall canary.
# ---------------------------------------------------------------------------
def rolling_flip_rate(
    records: Sequence[Mapping[str, Any]], window: int = DEFAULT_FLIP_WINDOW
) -> dict[str, Any]:
    """Compute the flip rate over the last ``window`` records.

    ``measured`` is False until the sample reaches the window (미실측 기본 태그):
    a sub-window sample is a baseline-only observation, never a conclusion.
    Support evidence only — a ratio, not a verdict.
    """

    # A non-positive window is invalid input, NOT a request for a 1-wide window.
    # Clamping ``<=0`` to 1 let a single zero-flip record satisfy ``sample >=
    # window`` and fire the canary at sample=1 (0707 attack-QA: negative-window-
    # canary-sample-one). Fall back to the declared default window instead so the
    # 미실측 기본 태그 still requires a real full window before any canary.
    try:
        window = int(window)
    except (TypeError, ValueError):
        window = DEFAULT_FLIP_WINDOW
    if window <= 0:
        window = DEFAULT_FLIP_WINDOW
    tail = list(records)[-window:]
    sample = len(tail)
    flipped = sum(1 for r in tail if bool(r.get("flipped")))
    rate = (flipped / sample) if sample else 0.0
    return {
        "window": window,
        "sample": sample,
        "flipped_count": flipped,
        "flip_rate": rate,
        "measured": sample >= window,
        "window_status": "measured" if sample >= window else "unmeasured-default",
    }


def thought_stall_canary_line(rate_info: Mapping[str, Any]) -> str | None:
    """Return the canary advisory line iff the window is full AND the rate is 0.

    Sample below the window returns None (미실측 기본 태그 — no conclusion). The
    canary is advice only: it chooses no Movement, gate, or route.
    """

    if not bool(rate_info.get("measured")):
        return None
    if float(rate_info.get("flip_rate", 0.0)) != 0.0:
        return None
    sample = rate_info.get("sample")
    window = rate_info.get("window")
    return (
        f"{THOUGHT_STALL_CANARY}: last {sample} draft(s) over window={window} "
        "show a 0.0 flip rate — the operator overturned no draft. Advisory only "
        "(support evidence; not a verdict, gate, or Movement)."
    )


# ---------------------------------------------------------------------------
# D2 — blind pre-registration cross-check.
# ---------------------------------------------------------------------------
_PREREG_FIELD_DERIVATIONS: tuple[str, ...] = (
    "width",
    "kind_family",
    "casting_tier",
    "gates",
    "write_scope",
)


def _observed_width(after: Mapping[str, Any]) -> int:
    """The widest fan block in the launched plan (1 = single-spine)."""

    widest = 1
    for node in after.get("nodes", ()) or ():
        if isinstance(node, Mapping) and "fan" in node:
            fan = node.get("fan")
            branches = fan.get("branches", ()) if isinstance(fan, Mapping) else ()
            widest = max(widest, len(list(branches or ())))
    return widest


def _observed_kind_family(after: Mapping[str, Any]) -> list[str]:
    kinds: list[str] = []
    for node in after.get("nodes", ()) or ():
        if not isinstance(node, Mapping):
            continue
        if "fan" in node:
            fan = node.get("fan")
            for branch in (fan.get("branches", ()) if isinstance(fan, Mapping) else ()):
                if isinstance(branch, Mapping) and branch.get("kind"):
                    kinds.append(str(branch.get("kind")))
        elif node.get("kind"):
            kinds.append(str(node.get("kind")))
    seen: set[str] = set()
    out: list[str] = []
    for kind in kinds:
        if kind not in seen:
            seen.add(kind)
            out.append(kind)
    return out


def _observed_casting_tier(after: Mapping[str, Any]) -> list[str]:
    flat = flatten_declaration(after)
    tiers = {
        value
        for path, value in flat.items()
        if classify_flip(path) == "casting" and value
    }
    return sorted(tiers)


def _observed_gates(after: Mapping[str, Any]) -> list[str]:
    gates = after.get("gates", ()) or ()
    return [str(g) for g in gates]


def _observed_write_scope(after: Mapping[str, Any]) -> Any:
    return after.get("write_scope")


def load_preregistration(
    prereg_dir: Path | str, building_id: str
) -> Mapping[str, Any] | None:
    """Load ``<prereg_dir>/<building_id>.json`` if it exists, else None (read-only)."""

    bid = str(building_id or "").strip()
    if not bid:
        return None
    path = Path(prereg_dir).expanduser() / f"{bid}.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def compare_preregistration(
    prereg: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Field-by-field pre-registration vs launched-plan comparison (D2).

    Only the fields the pre-registration actually declared are compared (a blind
    prereg may commit to a subset). Support evidence only — no verdict.
    """

    derivers = {
        "width": _observed_width,
        "kind_family": _observed_kind_family,
        "casting_tier": _observed_casting_tier,
        "gates": _observed_gates,
        "write_scope": _observed_write_scope,
    }
    rows: list[dict[str, Any]] = []
    for field in _PREREG_FIELD_DERIVATIONS:
        if field not in prereg:
            continue
        expected = prereg.get(field)
        observed = derivers[field](after)
        rows.append(
            {
                "field": field,
                "prereg": expected,
                "observed": observed,
                "match": _loose_equal(expected, observed),
            }
        )
    return {
        "rows": rows,
        "compared_field_count": len(rows),
        "match_count": sum(1 for r in rows if r["match"]),
        "mismatch_count": sum(1 for r in rows if not r["match"]),
    }


def _loose_equal(expected: Any, observed: Any) -> bool:
    """Order-insensitive equality for list-valued prereg fields; strict otherwise."""

    if isinstance(expected, (list, tuple)) and isinstance(observed, (list, tuple)):
        return sorted(str(x) for x in expected) == sorted(str(x) for x in observed)
    if isinstance(expected, (int, str)) and isinstance(observed, (int, str)):
        return str(expected) == str(observed)
    return expected == observed


def _prereg_first_observation(
    prereg_path: Path | None, after_path: Path
) -> dict[str, Any]:
    """Record whether the prereg file predates the launched plan by mtime.

    Honest proof limit: mtime does NOT prove the prereg was not forged/backdated;
    this is recorded ordering evidence only, never a verdict.
    """

    if prereg_path is None or not prereg_path.is_file():
        return {
            "prereg_present": False,
            "prereg_first": None,
            "proof_limit": "no pre-registration on disk; prereg-first ordering not observable",
        }
    prereg_mtime = prereg_path.stat().st_mtime
    after_mtime = after_path.stat().st_mtime if after_path.is_file() else prereg_mtime
    return {
        "prereg_present": True,
        "prereg_first": prereg_mtime <= after_mtime,
        "prereg_mtime": prereg_mtime,
        "after_mtime": after_mtime,
        "proof_limit": "mtime ordering is recorded evidence only; it does not prove the prereg was not forged/backdated",
    }


# ---------------------------------------------------------------------------
# Public orchestrator.
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_draft_diff(
    *,
    before_path: Path | str,
    after_path: Path | str,
    ledger_path: Path | str,
    prereg_dir: Path | str,
    window: int = DEFAULT_FLIP_WINDOW,
) -> dict[str, Any]:
    """Diff two declarations, append the flip record, and read the rolling window.

    Raises ``ValueError`` only on input malformation (missing/malformed files).
    Flips, the canary, and a missing pre-registration are recorded, never errors.
    """

    before = load_declaration_file(before_path)
    after = load_declaration_file(after_path)
    diff = diff_declarations(before, after)

    building_id = str(after.get("building_id") or before.get("building_id") or "").strip()
    prereg = load_preregistration(prereg_dir, building_id)
    prereg_path = (
        (Path(prereg_dir).expanduser() / f"{building_id}.json") if building_id else None
    )
    prereg_first = _prereg_first_observation(prereg_path, Path(after_path).expanduser())
    prereg_comparison = (
        compare_preregistration(prereg, after) if isinstance(prereg, Mapping) else None
    )

    record = {
        "recorded_at": _utc_now(),
        "building_id": building_id,
        "before_ref": str(Path(before_path).expanduser()),
        "after_ref": str(Path(after_path).expanduser()),
        "shape_flip_count": diff["shape_flip_count"],
        "casting_flip_count": diff["casting_flip_count"],
        "total_flip_count": diff["total_flip_count"],
        "flipped": diff["flipped"],
        "preregistration_present": bool(prereg is not None),
        "prereg_first": prereg_first.get("prereg_first"),
    }
    written_ledger = append_flip_record(ledger_path, record)

    all_records = read_flip_records(written_ledger)
    # Scope the rolling window to THIS building_id: a shared/append-only ledger
    # may carry other Buildings' records, and this Building's canary must not be
    # masked or fired by them (0707 attack-QA cross-building pollution gap).
    scoped_records = records_for_building(all_records, building_id)
    rate_info = rolling_flip_rate(scoped_records, window=window)
    rate_info["building_scoped"] = bool(building_id)
    rate_info["ledger_total_records"] = len(all_records)
    rate_info["building_records"] = len(scoped_records)
    canary = thought_stall_canary_line(rate_info)

    return {
        "command": "draft-diff",
        "building_id": building_id,
        "diff": diff,
        "flip_record": record,
        "ledger_path": str(written_ledger),
        "rolling_window": rate_info,
        "canary": canary,
        "preregistration": {
            "present": bool(prereg is not None),
            "prereg_first_observation": prereg_first,
            "comparison": prereg_comparison,
            "order_evidence": (
                "prereg-first"
                if prereg_first.get("prereg_present") and prereg_first.get("prereg_first")
                else ("prereg-late" if prereg_first.get("prereg_present") else "prereg-absent")
            ),
        },
        "proof_limits": list(PROOF_LIMITS),
    }
