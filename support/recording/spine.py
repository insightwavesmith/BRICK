"""U5.5 Evidence Spine — shared pure functions + the disk writer.

This module owns the SHARED, recording-layer logic for the U5.5 spine:

  * the spine Truth event_type set (the §2 projection of the recording
    contract);
  * ``canonical_json`` / ``content_hash`` — the deterministic serialization +
    integrity hash basis (the declaration_packets.py separators form);
  * ``render_event_md`` — a DETERMINISTIC pure rendering of an event BODY to
    markdown (md == render(json));
  * the PURE derivation helpers (``_derive_index_from_events``,
    ``_index_entry_view``, ``render_spine_md`` and their pure dependencies) that
    re-derive the ordered index from ``events/`` on disk — the SINGLE SOURCE the
    structural checker (``check_evidence_spine.py``) imports, so the writer and
    the checker agree BY CONSTRUCTION;
  * ``append_spine_events`` — the slice-1B disk WRITER: an HONEST APPEND-ONLY
    pen — append-only, atomic (temp + ``os.replace``), ``.json`` canonical +
    ``.md`` derived, disk-stateful sequence/run-segment seeding, and the DERIVED
    ``spine.{json,jsonl,md}`` index rebuilt purely from ``events/``. It does NO
    repair: NO stale-``.tmp`` cleanup, NO orphan ``.md`` completion, NO index
    refresh on an empty call. It refuses (raises) on any unclean spine with ZERO
    writes; DETECTING the anomaly is the checker's job and FIXING it is a SEPARATE
    explicit repair slice.

Dependency direction (correct): checker -> recording. The checker imports the
pure helpers from HERE; recording NEVER imports checkers.

Axis rule: this is support mechanics. It RECORDS / RENDERS facts; it judges
NOTHING (no success / quality / fault verdict), launches nothing, chooses no
Movement. The per-event ``.json`` is the canonical body; ``content_hash`` /
``prev_hash`` / ``md_hash`` live in the spine INDEX (spine.json), NOT inside the
event body (the body would be self-referential otherwise). The writer is a
ONE-SHOT read-back-then-append at assembly: it reads the on-disk ``events/``
once and exits; nothing is held between invocations (no daemon / scheduler /
queue / resident runtime).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

# Reuse the GENERIC graph-ready envelope helper (do NOT invent one). The spine
# wraps each event with this, local_id=evidence/spine/events/... — identical in
# shape to capture, so the whole spine is one knowledge-graph-ingestable stream.
# FORBIDDEN_CAPTURE_KEYS is also single-sourced from here (the writer applies the
# no-success/quality-key rule the graph envelope does NOT enforce, design §6).
from brick_protocol.support.recording.capture import (
    FORBIDDEN_CAPTURE_KEYS,
    graph_ready_json_object as graph_ready_json_object,
)

# The Agent-return forbidden-key set is single-sourced from its owning module.
from brick_protocol.agent.return_fact import RETURNED_FORBIDDEN_KEYS


# ---------------------------------------------------------------------------
# The spine Truth event_type set (the §2 projection of the recording contract).
#
# This is a 1:1 PROJECTION (not a hand-pick): the Builder declaration-provenance
# rows + the 10-type CAPTURE_EVENT_TYPES validator family + the Link claim
# families + the Agent->Link seam step outputs + frontier/disposition + the
# mechanical attempt delta. The per-event file is events/<seq>-<type>.{json,md}
# where <type> is one of these short PascalCase names (the filename type segment
# matches ``^[0-9]+-[A-Za-z]+\.(json|md)$``).
#
# Layer-2 QualityEvaluation is NOT in this set: it is a separate APPEND surface
# under quality/<seq>-quality.{json,md}, human-authored, not a Truth event.
# ---------------------------------------------------------------------------
SPINE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        # Builder rows (the declared plan, before run) — all 4 declaration packets.
        "TaskSource",
        "BrickInput",
        "AgentBinding",
        "PresetExpansion",
        "LinkLaunchPolicy",
        # Engine run events (1:1 with the 10-type CAPTURE_EVENT_TYPES validator
        # set + the claim families + the Agent->Link seam step outputs).
        "BuildingOpened",
        "SupportNote",
        "AgentReceipt",
        "AgentReturn",
        "TransitionConcern",
        "RouteRequest",
        "BrickCompared",
        "LinkSufficiency",
        "LinkGateCheck",
        "LinkPolicyAction",
        "LinkTransfer",
        "LinkCarry",
        "Movement",
        # Terminal / disposition.
        "Frontier",
        "ResumeDisposition",
        # Mechanical retrospective (Layer 1, no verdict).
        "AttemptDelta",
    }
)

# The axis_scope vocabulary (non-empty subset of these). "Support residue" is
# the existing non-axis lifecycle literal (capture.CAPTURE_AXIS_ATTRIBUTIONS),
# NOT a new meaning axis.
SPINE_AXIS_SCOPE_LITERALS: frozenset[str] = frozenset(
    {"Brick", "Agent", "Link", "Support residue"}
)

SPINE_SCHEMA_VERSION = "spine-v1"

# Genesis sentinel for the first event's prev_hash (there is no prior event).
GENESIS_PREV_HASH = "0" * 64

# events/<seq>-<type>.{json,md}: zero-padded (or bare) integer seq, then a spine
# event_type, then .json|.md. Never .tmp (a .tmp is a torn write; the collectors
# residue-filter it and it is never a valid event file).
EVENT_FILENAME_RE = re.compile(r"^(?P<seq>[0-9]+)-(?P<type>[A-Za-z]+)\.(?P<ext>json|md)$")

# The union forbidden-key set (normalized) used to scan event bodies. Reuses the
# two single-source frozensets; this module only UNIONS + normalizes them.
_FORBIDDEN_KEYS_NORMALIZED = frozenset(
    {
        key.strip().lower().replace("-", "_").replace(" ", "_")
        for key in (set(FORBIDDEN_CAPTURE_KEYS) | set(RETURNED_FORBIDDEN_KEYS))
    }
)

# The header field keys read (for display only) by render_event_md. These are
# read from the body when present; the rendering stays deterministic and total
# even when a key is absent.
_HEADER_EVENT_TYPE_KEY = "event_type"
_HEADER_SEQUENCE_KEY = "sequence_index"
_HEADER_AXIS_SCOPE_KEY = "axis_scope"


def canonical_json(body: Mapping[str, Any] | Any) -> str:
    """Canonical sorted-key JSON for a hash/render basis.

    Sorted keys + the compact ``separators=(",", ":")`` form (the same form as
    declaration_packets.py:_plan_snapshot and capture.py:_json_line). Pure and
    deterministic: the same body always yields the same string. ``ensure_ascii``
    is False so non-ASCII text round-trips as itself. Accepts any JSON value
    (object, list, scalar) so it can also serialize a single field value inside
    render_event_md.
    """

    return json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_hash(body: Mapping[str, Any]) -> str:
    """sha256 hex digest over canonical_json(body).

    This is the integrity basis recorded in the spine INDEX (spine.json) as the
    per-event content_hash. It is taken over the exact canonical string so it is
    deterministic and re-derivable by re-reading the on-disk event body. It does
    NOT live inside the event body itself (that would be self-referential).
    """

    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def render_event_md(body: Mapping[str, Any]) -> str:
    """Deterministic PURE rendering of an event BODY to markdown.

    A header line, then every body key in SORTED order as ``- {key}:
    {canonical_json(value)}``. Pure function of the body: no time, no
    randomness, no disk. This is the shared contract the slice-1B writer uses to
    derive the ``.md`` from the canonical ``.json`` and that the checker uses to
    verify ``md == render_event_md(json-body)``. Because the ``.md`` is a pure
    function of the ``.json`` body, it can carry no independent / contaminating
    content.

    The header reads event_type / sequence_index / axis_scope from the body when
    present (rendered via canonical_json so the line is deterministic for any
    value type) and falls back to a stable ``-`` placeholder when a key is
    absent, so the function is total over any JSON-object body.
    """

    if not isinstance(body, Mapping):
        raise TypeError("render_event_md requires a JSON object body mapping")

    event_type = _header_token(body, _HEADER_EVENT_TYPE_KEY)
    sequence_index = _header_token(body, _HEADER_SEQUENCE_KEY)
    axis_scope = _header_token(body, _HEADER_AXIS_SCOPE_KEY)

    lines = [f"# {event_type} · seq {sequence_index} · {axis_scope}"]
    for key in sorted(body):
        lines.append(f"- {key}: {canonical_json(body[key])}")
    return "\n".join(lines) + "\n"


def _header_token(body: Mapping[str, Any], key: str) -> str:
    """A deterministic header token for one body key.

    A plain string value is shown verbatim (the common case for event_type);
    any other value (or absence) is rendered via canonical_json / a stable
    placeholder so the header is total and deterministic.
    """

    if key not in body:
        return "-"
    value = body[key]
    if isinstance(value, str):
        return value
    return canonical_json(value)


# ---------------------------------------------------------------------------
# PURE derivation helpers (moved from check_evidence_spine.py in slice-1B).
#
# These are pure, recording-layer logic that re-derive the ordered index from
# ``events/`` on disk. The structural checker IMPORTS them so writer and checker
# agree by construction. Behaviour is byte-identical to the slice-1A checker's
# private copies (verified by re-running the slice-1A FIRE cases + --all).
# ---------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_key(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _forbidden_keys_in_body(value: Any) -> set[str]:
    """Every forbidden KEY occurring anywhere in a JSON value (ITERATIVE).

    KEY-only by design (a forbidden literal as a VALUE — e.g. `complete` as a
    legal frontier_kind value — is allowed; the rule is forbidden = KEYS). The
    writer-discipline limit (a verdict hiding in a permitted key's prose) is the
    writer's job, documented in the design; this is the key guard.

    Implemented as an explicit-stack DFS (NOT recursion) so a deeply nested body
    (a ~2000+ deep nested dict/list) cannot raise RecursionError — this scanner is
    called by BOTH the checker and the writer, so an unbounded-depth crash would
    fail-open. Semantics are IDENTICAL to the prior recursive form: only dict KEYS
    are matched (normalized) against _FORBIDDEN_KEYS_NORMALIZED; we descend into
    dict VALUES and list/tuple ITEMS; the result is the SET of matching keys.
    Set-union is order-independent, so the DFS order does not change the result.
    (``tuple`` is folded in with ``list``: json.loads never yields a tuple, but a
    PRE-serialization in-memory body handed to the writer's preflight could carry
    one — canonical_json would later flatten it to a list, so the scanner must see
    inside it too, else a forbidden key in a tuple value would slip the preflight.)

    CYCLE-SAFE: an in-memory body could contain a reference cycle (a list/tuple/dict
    reachable from itself). Each container's id() is recorded once and never re-
    expanded, so a cyclic body TERMINATES (then the writer's canonical_json raises
    "Circular reference detected" downstream) instead of looping forever — a list
    cycle hung even the prior list-only form, so this also closes that pre-existing
    case. All nodes are alive for the scan's duration, so id() reuse is impossible;
    skipping an already-seen container never drops a key (set semantics make a second
    visit redundant), so the result is unchanged for every finite-shaped body. This
    assumes ORDINARY JSON-shaped containers — exactly what json.loads (always a plain
    ``dict``/``list``, never a subclass) and the projector produce; a deliberately
    self-mutating container subclass (different keys per ``items()`` call) is a
    malicious construction, which the U5.5 threat model puts OUT OF SCOPE.
    """

    found: set[str] = set()
    seen_ids: set[int] = set()
    stack: list[Any] = [value]
    while stack:
        node = stack.pop()
        if isinstance(node, (dict, list, tuple)):
            node_id = id(node)
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
        if isinstance(node, dict):
            for key, child in node.items():
                if _normalize_key(str(key)) in _FORBIDDEN_KEYS_NORMALIZED:
                    found.add(str(key))
                stack.append(child)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)
    return found


def _load_json(path: Path, violations: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        violations.append(f"{path}: JSON parse failed: {exc}")
        return None


def _read_text(path: Path, violations: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        violations.append(f"{path}: read failed: {exc}")
        return None


def _event_body_violations(
    label: str,
    seq_text: str,
    type_segment: str,
    body: Any,
) -> list[str]:
    out: list[str] = []
    if not isinstance(body, dict):
        out.append(f"{label}: event body must be a JSON object")
        return out
    # admitted event type (the filename type segment must be a real spine type).
    if type_segment not in SPINE_EVENT_TYPES:
        out.append(
            f"{label}: event type segment {type_segment!r} is not an admitted "
            "spine event_type"
        )
    # IDENTITY (codex P1#2): the body's own event_type MUST match the filename type
    # segment — else 0001-TaskSource.json could declare event_type "Movement" and
    # pass (render_event_md renders body.event_type), a mislabeled-axis false-green.
    body_type = body.get("event_type")
    if body_type != type_segment:
        out.append(
            f"{label}: body event_type {body_type!r} != filename type segment "
            f"{type_segment!r} (event identity mismatch)"
        )
    # axis_scope: non-empty subset of the literals.
    axis_scope = body.get("axis_scope")
    if not isinstance(axis_scope, list) or not axis_scope:
        out.append(f"{label}: axis_scope must be a non-empty list")
    else:
        bad = [a for a in axis_scope if a not in SPINE_AXIS_SCOPE_LITERALS]
        if bad:
            out.append(
                f"{label}: axis_scope outside {sorted(SPINE_AXIS_SCOPE_LITERALS)!r}: {bad!r}"
            )
    # no forbidden success/quality/fault KEY anywhere in the body.
    forbidden = _forbidden_keys_in_body(body)
    if forbidden:
        out.append(
            f"{label}: event body carries forbidden success/quality/fault key(s): "
            f"{sorted(forbidden)!r}"
        )
    return out


def _collect_event_files(events_dir: Path, violations: list[str]) -> dict[str, dict[str, Path]]:
    """Group present event files by (seq-type) stem -> {ext: path}.

    A ``.tmp`` is torn-write residue (a crash between the temp write and os.replace).
    Under the narrowed slice-1B contract the writer is an HONEST APPEND-ONLY pen that
    NEVER cleans residue — so a surviving ``.tmp`` is an ANOMALY the checker DETECTS
    (RED) and a SEPARATE explicit repair slice cleans. (The path checkers still
    residue-filter ``.tmp`` at the path-admission layer — "is this path allowed"; this
    STRUCTURAL checker answers "is the spine clean" and flags it. Different questions.)
    """

    grouped: dict[str, dict[str, Path]] = {}
    for path in sorted(events_dir.iterdir()):
        if not path.is_file():
            violations.append(
                f"{path}: only event files are allowed directly under events/"
            )
            continue
        name = path.name
        if name.endswith(".tmp"):
            violations.append(
                f"{path}: a stale .tmp (torn write) is a spine anomaly — the "
                "append-only writer does not clean it; run the explicit repair slice"
            )
            continue
        match = EVENT_FILENAME_RE.match(name)
        if match is None:
            violations.append(
                f"{path}: event file name must match <seq>-<type>.(json|md)"
            )
            continue
        stem = f"{match.group('seq')}-{match.group('type')}"
        grouped.setdefault(stem, {})[match.group("ext")] = path
    return grouped


def _derive_index_from_events(
    events_dir: Path,
    violations: list[str],
) -> list[dict[str, Any]] | None:
    """Re-derive the ordered spine index PURELY from events/ (the source of truth).

    Returns an ordered list of per-event index entries
    ``{sequence_index, run_segment, event_type, event_ref, content_hash,
    md_hash, prev_hash}`` sorted by sequence_index, with the prev_hash chain
    computed over content_hash. Returns None if events/ cannot yield a coherent
    set (pairing / parse / monotonicity failures already recorded as RED).
    """

    grouped = _collect_event_files(events_dir, violations)
    entries: list[dict[str, Any]] = []
    ok = True
    for stem in sorted(grouped):
        pair = grouped[stem]
        json_path = pair.get("json")
        md_path = pair.get("md")
        if json_path is None:
            violations.append(f"{events_dir}/{stem}.md: event .md has no paired .json")
            ok = False
            continue
        if md_path is None:
            violations.append(f"{json_path}: event .json has no paired .md")
            ok = False
            continue
        body = _load_json(json_path, violations)
        if body is None:
            ok = False
            continue
        # BYTE-CANONICAL (codex pass-3 P1): the on-disk .json MUST be exactly
        # canonical_json(body) — sorted keys, compact separators, no trailing
        # newline, no NaN/Infinity, no duplicate keys. Proves the design's "event
        # body = canonical sorted-key JSON" at the byte level: a pretty / unsorted
        # file, a duplicate-key file (re-emit collapses it), or a NaN
        # (canonical_json(allow_nan=False) raises) all diverge from the raw text.
        raw_json_text = _read_text(json_path, violations)
        try:
            canonical = canonical_json(body) if isinstance(body, dict) else None
        except ValueError as exc:
            # NaN/Infinity: the body is unprocessable (render_event_md / content_hash
            # would also raise) — record + SKIP this event, do not crash.
            violations.append(f"{json_path}: event .json body is not canonical JSON ({exc})")
            ok = False
            continue
        if canonical is not None and raw_json_text is not None and raw_json_text != canonical:
            violations.append(
                f"{json_path}: event .json is not byte-canonical (must equal "
                "canonical_json(body): sorted keys, compact separators, no trailing "
                "newline, no duplicate keys / NaN)"
            )
            ok = False
        seq_text, _, type_segment = stem.partition("-")
        body_violations = _event_body_violations(str(json_path), seq_text, type_segment, body)
        if body_violations:
            violations.extend(body_violations)
            ok = False
        md_text = _read_text(md_path, violations)
        if md_text is None:
            ok = False
            continue
        # md == render(json): the bidirectional pair contract (a hand-edited .md
        # or a .json edit both break this).
        expected_md = render_event_md(body) if isinstance(body, dict) else None
        if expected_md is None or md_text != expected_md:
            violations.append(
                f"{md_path}: event .md does not equal render_event_md(.json body)"
            )
            ok = False
        seq_value = body.get("sequence_index") if isinstance(body, dict) else None
        run_segment = body.get("run_segment") if isinstance(body, dict) else None
        if not isinstance(seq_value, int) or isinstance(seq_value, bool):
            violations.append(f"{json_path}: sequence_index must be an integer")
            ok = False
        if not isinstance(run_segment, int) or isinstance(run_segment, bool):
            violations.append(f"{json_path}: run_segment must be an integer")
            ok = False
        # the filename seq must match the body sequence_index (no dangling label).
        if isinstance(seq_value, int) and not isinstance(seq_value, bool):
            if str(seq_value) != str(int(seq_text)):
                violations.append(
                    f"{json_path}: filename seq {seq_text!r} != body sequence_index {seq_value!r}"
                )
                ok = False
        entries.append(
            {
                "sequence_index": seq_value,
                "run_segment": run_segment,
                "event_type": type_segment,
                "event_ref": f"evidence/spine/events/{json_path.name}",
                "content_hash": _sha256_text(canonical) if canonical is not None else None,
                "md_hash": _sha256_text(md_text),
            }
        )

    if not ok:
        return None
    if not entries:
        violations.append(f"{events_dir}: u5_5_live spine has no events")
        return None

    # order by sequence_index; verify sequence_index strictly increasing +
    # run_segment non-decreasing (events in one run share a segment), and
    # build the prev_hash chain over content_hash.
    entries.sort(key=lambda e: e["sequence_index"])
    prev_seq: int | None = None
    prev_segment: int | None = None
    prev_hash = GENESIS_PREV_HASH
    for entry in entries:
        seq_value = entry["sequence_index"]
        run_segment = entry["run_segment"]
        if prev_seq is not None and not (seq_value > prev_seq):
            violations.append(
                f"{entry['event_ref']}: sequence_index not strictly increasing "
                f"({seq_value} after {prev_seq})"
            )
            ok = False
        if prev_segment is not None and run_segment < prev_segment:
            violations.append(
                f"{entry['event_ref']}: run_segment decreased "
                f"({run_segment} after {prev_segment})"
            )
            ok = False
        entry["prev_hash"] = prev_hash
        prev_seq = seq_value
        prev_segment = run_segment
        prev_hash = entry["content_hash"]

    if not ok:
        return None
    return entries


def _index_entry_view(entry: dict[str, Any]) -> dict[str, Any]:
    """The canonical per-event index projection that spine.json MUST match."""

    return {
        "sequence_index": entry["sequence_index"],
        "run_segment": entry["run_segment"],
        "event_type": entry["event_type"],
        "event_ref": entry["event_ref"],
        "content_hash": entry["content_hash"],
        "md_hash": entry["md_hash"],
        "prev_hash": entry["prev_hash"],
    }


def render_spine_md(building_id: str, derived_view: list[dict[str, Any]]) -> str:
    """Deterministic overview projection of the ordered index (shared writer/checker).

    Pure function of (building_id, derived index). A header then one bullet per
    event in sequence order. The slice-1B writer produces this exact text.
    """

    lines = [f"# Evidence Spine · {building_id} · {len(derived_view)} event(s)"]
    for view in derived_view:
        lines.append(
            f"- seg {view['run_segment']} seq {view['sequence_index']} "
            f"{view['event_type']} :: {view['event_ref']} "
            f"[content {view['content_hash']}] [prev {view['prev_hash']}]"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The SINGLE shared structural validator (the convergent slice-1B fix).
#
# Both the structural checker (check_evidence_spine.validate_spine) and the disk
# writer's all-or-nothing preflight call THIS — so the writer refuses to append to
# anything the checker would RED, sharing ONE validation. It returns EVERY
# structural RED for a building's spine (it judges NOTHING about content / success
# / quality — structure only):
#   * events/ derivability (the full set of _derive_index_from_events violations,
#     not merely its None result: events/junk.txt records a violation yet the
#     remaining events still derive);
#   * spine.json TOP-LEVEL == {"events"} + per-event EXACT match to the
#     re-derivation (no non-derived field can ride in the index);
#   * spine.jsonl == the canonical line projection;
#   * spine.md == render_spine_md(...);
#   * each of spine.{json,jsonl,md} is a plain FILE (a path that exists but is a
#     directory is a RED in BOTH modes).
#
# require_index_present toggles the ONE difference between the two callers:
#   * True  (checker): a MISSING spine/ or events/ dir, or a MISSING
#     spine.{json,jsonl,md}, is a RED (a u5_5_live building must already carry a
#     complete spine). This branch reproduces check_evidence_spine.validate_spine's
#     historical RED text BYTE-FOR-BYTE (verified by the FIRE captures).
#   * False (writer preflight): a MISSING index/dir is NOT a RED (the writer
#     legitimately creates it); but a PRESENT-but-directory or a PRESENT-but-
#     disagreeing index file still REDs (so the writer never launders / partial-
#     writes onto a checker-RED spine).
# ---------------------------------------------------------------------------

_INDEX_RECORD_NAMES = ("spine_json", "spine_jsonl", "spine_md")


def _index_list_from_spine_json(spine_json: Any) -> list[Any] | None:
    if not isinstance(spine_json, dict):
        return None
    events = spine_json.get("events")
    if not isinstance(events, list):
        return None
    return events


def _index_comparison_violations(
    building_root: Path,
    paths: Mapping[str, Path],
    derived_view: list[dict[str, Any]],
    violations: list[str],
) -> None:
    """Compare PRESENT spine.{json,jsonl,md} to the events/ re-derivation.

    Only PRESENT plain files are compared (presence/type is handled by the caller).
    The RED text is byte-identical to check_evidence_spine.validate_spine's prior
    inline comparison so the checker stays unchanged through the refactor.
    """

    spine_json_path = paths["spine_json"]
    spine_jsonl_path = paths["spine_jsonl"]
    spine_md_path = paths["spine_md"]

    # spine.json index == re-derived projection of events/.
    if spine_json_path.is_file():
        spine_json = _load_json(spine_json_path, violations)
        on_disk_events = _index_list_from_spine_json(spine_json)
        if on_disk_events is None:
            violations.append(
                f"{spine_json_path}: spine.json must be an object with an 'events' list"
            )
        else:
            # TOP-LEVEL exactness: spine.json is a PURE projection of events/ — its
            # only top-level key is 'events'. Reject any non-derived top-level field
            # (e.g. {"events": [...], "success": true}) the per-event scan can't see.
            extra_top = sorted(set(spine_json) - {"events"})
            if extra_top:
                violations.append(
                    f"{spine_json_path}: spine.json has non-derived top-level key(s) "
                    f"{extra_top!r} (the index must be a PURE projection of events/; "
                    "the only top-level key is 'events')"
                )
            # Compare per-event so a mutated .json (content_hash mismatch), a broken
            # prev_hash chain, or a stale md_hash all surface precisely.
            if len(on_disk_events) != len(derived_view):
                violations.append(
                    f"{spine_json_path}: spine.json lists {len(on_disk_events)} event(s) "
                    f"but events/ re-derives {len(derived_view)}"
                )
            for index, expected in enumerate(derived_view):
                actual = on_disk_events[index] if index < len(on_disk_events) else None
                if not isinstance(actual, dict):
                    violations.append(
                        f"{spine_json_path}: spine.json event #{index} is not an object"
                    )
                    continue
                # EXACT match: the on-disk index entry must equal the re-derivation
                # with NO extra keys — else a non-derived field (e.g. success /
                # quality_judgment) could ride in spine.json undetected (the body
                # forbidden-key scan does not see the index).
                extra = sorted(set(actual) - set(expected))
                if extra:
                    violations.append(
                        f"{spine_json_path}: spine.json event #{index} carries non-derived "
                        f"field(s) {extra!r} (index must EXACTLY equal the re-derivation; "
                        "events/ is source of truth)"
                    )
                for key, value in expected.items():
                    if actual.get(key) != value:
                        violations.append(
                            f"{spine_json_path}: spine.json event #{index} field {key!r} "
                            f"disagrees with re-derivation (events/ is source of truth)"
                        )

    # spine.jsonl == one canonical line per derived event, in order.
    if spine_jsonl_path.is_file():
        jsonl_text = _read_text(spine_jsonl_path, violations)
        if jsonl_text is not None:
            expected_jsonl = "".join(
                canonical_json(view) + "\n" for view in derived_view
            )
            if jsonl_text != expected_jsonl:
                violations.append(
                    f"{spine_jsonl_path}: spine.jsonl does not equal the canonical "
                    "line projection re-derived from events/"
                )

    # spine.md == deterministic projection of the derived index.
    if spine_md_path.is_file():
        md_text = _read_text(spine_md_path, violations)
        if md_text is not None:
            expected_md = render_spine_md(building_root.name, derived_view)
            if md_text != expected_md:
                violations.append(
                    f"{spine_md_path}: spine.md does not equal the deterministic "
                    "overview re-derived from events/"
                )


def spine_structural_violations(
    building_root: Path | str,
    *,
    require_index_present: bool,
) -> list[str]:
    """EVERY structural RED for a building's spine — the SINGLE shared validator.

    Called by BOTH the checker (require_index_present=True) and the writer preflight
    (require_index_present=False). Structure only; it judges nothing about content,
    success, or quality. Pure read (writes nothing). See the section header above
    for the full contract and the meaning of require_index_present.
    """

    root = Path(building_root)
    paths = _spine_paths(root)
    spine_dir = paths["spine_dir"]
    events_dir = paths["events_dir"]
    violations: list[str] = []

    # --- spine/ directory ------------------------------------------------------
    if not spine_dir.is_dir():
        if spine_dir.exists():
            # exists but is a FILE (not a dir) — a RED in both modes (the writer
            # cannot mkdir over it; the checker treats a non-dir spine/ as missing).
            violations.append(
                f"{spine_dir}: u5_5_live building is missing evidence/spine/"
            )
            return violations
        if require_index_present:
            violations.append(
                f"{spine_dir}: u5_5_live building is missing evidence/spine/"
            )
            return violations
        # writer mode + genuinely absent: nothing exists yet -> no structural RED.
        return violations

    # --- events/ directory -----------------------------------------------------
    if not events_dir.is_dir():
        if events_dir.exists():
            violations.append(
                f"{events_dir}: u5_5_live spine is missing events/"
            )
            return violations
        if require_index_present:
            violations.append(
                f"{events_dir}: u5_5_live spine is missing events/"
            )
            return violations
        # writer mode + events/ absent: no events to derive; still validate any
        # PRESENT index records — compare to the EMPTY re-derivation so a present
        # tampered/stray spine.{json,jsonl,md} is REFUSED, not laundered on first
        # append (codex 1B pass-7: the absent-events variant of the pass-6 launder;
        # mirrors the events/-empty branch below).
        _index_presence_violations(paths, require_index_present, violations)
        _index_comparison_violations(root, paths, [], violations)
        return violations

    # --- index record presence / type ----------------------------------------
    _index_presence_violations(paths, require_index_present, violations)

    events_present = any(events_dir.iterdir())
    # HONEST append-only (writer mode): a genuinely-absent index record is tolerated
    # ONLY pre-first-write (events/ empty). With events PRESENT, a missing index is
    # crash residue the writer must REFUSE rather than silently derive (= launder a
    # checker-RED state). The checker (require_index_present=True) already REDs a
    # missing record via the call above; this adds the same refusal to writer mode.
    if not require_index_present and events_present:
        for _index_key in _INDEX_RECORD_NAMES:
            if not paths[_index_key].exists():
                violations.append(
                    f"{paths[_index_key]}: events/ holds events but this index record "
                    "is absent (crash residue); the append-only writer refuses — run "
                    "the explicit repair slice to rebuild the index"
                )

    # --- writer-mode empty events/ -------------------------------------------
    # A TRULY EMPTY events/ (zero entries) is the legitimate pre-first-write state
    # in writer mode: there is nothing to DERIVE and "no events" is NOT a RED (the
    # writer is about to create the first events). Skip derivation so the writer can
    # write onto an externally-created empty events/. (The checker —
    # require_index_present=True — always derives, so an empty events/ is a "no
    # events" RED there, byte-identical to the prior checker.) Any NON-empty events/
    # — even residue / a torn pair — still derives and REDs below.
    # BUT a PRESENT index file must still be validated against the EMPTY
    # re-derivation: else a pre-existing tampered spine.json (e.g.
    # {"events":[],"success":true}) on an empty-events building would be silently
    # OVERWRITTEN on first append = a launder of a checker-RED state (codex 1B
    # pass-6). So compare present index files to the empty derivation here too.
    if not require_index_present and not events_present:
        _index_comparison_violations(root, paths, [], violations)
        return violations

    # --- events/ derivability (the FULL violation set, not just None) ---------
    derived = _derive_index_from_events(events_dir, violations)
    if derived is None:
        return violations  # events/ already failed; index comparison would be noise.

    derived_view = [_index_entry_view(entry) for entry in derived]

    # --- spine.{json,jsonl,md} == the re-derivation ---------------------------
    _index_comparison_violations(root, paths, derived_view, violations)
    return violations


def _index_presence_violations(
    paths: Mapping[str, Path],
    require_index_present: bool,
    violations: list[str],
) -> None:
    """Presence / plain-file checks for spine.{json,jsonl,md}.

    A present plain file is left for _index_comparison_violations to compare. A
    path that exists but is a DIRECTORY is a RED in both modes. A genuinely MISSING
    record is a RED only when require_index_present (the checker); in writer mode it
    is the recoverable post-crash state the writer legitimately creates.

    require_index_present=True reproduces validate_spine's historical
    "missing this record" RED byte-for-byte for BOTH the missing and the
    present-but-directory case (is_file() is False for a directory).
    """

    for key in _INDEX_RECORD_NAMES:
        path = paths[key]
        if path.is_file():
            continue
        if require_index_present:
            # byte-identical to the prior checker for missing AND directory.
            violations.append(f"{path}: u5_5_live spine is missing this record")
        elif path.exists():
            # writer mode: a present-but-directory index path is a RED (the writer
            # cannot atomically replace a directory); a genuinely absent record is
            # not (the writer creates it).
            violations.append(f"{path}: exists but is not a plain file")


# ---------------------------------------------------------------------------
# The slice-1B disk WRITER (append-only, atomic, .json canonical + .md derived).
# ---------------------------------------------------------------------------

# evidence manifest field the spine emits so the generation-gate engages.
EVIDENCE_GENERATION_FIELD = "evidence_generation"
U5_5_LIVE = "u5_5_live"


class SpineWriteError(RuntimeError):
    """A spine write that would violate append-only/write-once immutability.

    Raised when a target event ``.json`` already exists on disk with DIFFERENT
    bytes (a rewrite of a prior at-time record), or when an event body is not a
    well-formed, canonical-serializable JSON object. NOT raised for a same-bytes
    re-write (idempotent) — append-only by construction.
    """


def _spine_paths(building_root: Path) -> dict[str, Path]:
    spine_dir = building_root / "evidence" / "spine"
    return {
        "spine_dir": spine_dir,
        "events_dir": spine_dir / "events",
        "spine_json": spine_dir / "spine.json",
        "spine_jsonl": spine_dir / "spine.jsonl",
        "spine_md": spine_dir / "spine.md",
    }


def _atomic_write_text(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` atomically (temp in the SAME dir + os.replace).

    The temp file is created in ``target``'s directory so ``os.replace`` is a
    same-filesystem rename (atomic). A unique temp name per call avoids collision
    when two events in one pass share a directory.
    """

    directory = target.parent
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f"{target.name}.{os.getpid()}.{id(target)}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, target)


def _write_event_pair_once(events_dir: Path, body: Mapping[str, Any]) -> None:
    """Write one event's ``.json`` (canonical) + ``.md`` (derived) write-once.

    WRITE-ONCE: if the target ``.json`` already exists with DIFFERENT bytes,
    raise SpineWriteError (a prior at-time record must never be rewritten); the
    same bytes are a no-op-equivalent (idempotent). Each file is written
    atomically. The ``.md`` is a PURE rendering of the SAME body, so it cannot
    carry independent content.
    """

    seq = body["sequence_index"]
    event_type = body["event_type"]
    stem = f"{int(seq):04d}-{event_type}"
    json_path = events_dir / f"{stem}.json"
    md_path = events_dir / f"{stem}.md"

    try:
        json_text = canonical_json(body)
    except (TypeError, ValueError) as exc:
        raise SpineWriteError(
            f"{json_path}: event body is not canonical-serializable JSON ({exc})"
        ) from exc
    md_text = render_event_md(body)

    if json_path.exists():
        existing = json_path.read_text(encoding="utf-8")
        if existing != json_text:
            raise SpineWriteError(
                f"{json_path}: write-once violation — a prior event .json exists "
                "with different bytes (append-only: a replay must take a NEW "
                "sequence_index, never rewrite a prior event)"
            )
        # same bytes: re-writing the .json is an idempotent no-op (write-once is
        # satisfied). The .md below is a pure re-render of the SAME body. This is the
        # THIS-call idempotent-replay guard, NOT orphan recovery: a PRE-EXISTING torn
        # pair is refused at preflight, so this never completes another call's orphan.
    _atomic_write_text(json_path, json_text)
    _atomic_write_text(md_path, md_text)


# NOTE (narrowed slice-1B contract): the writer does NOT repair. Stale-`.tmp`
# cleanup and orphan `.md` completion are DELIBERATELY NOT here — they belong to a
# SEPARATE explicit repair slice. The append-only writer refuses (preflight) on any
# unclean spine; the checker DETECTS the anomaly; an explicit repair step fixes it.


def _disk_seed(events_dir: Path) -> tuple[int, int]:
    """Disk-stateful seed: (next sequence_index, next run_segment).

    next sequence_index = (max COMPLETE .json sequence_index on disk) + 1;
    next run_segment = (max run_segment on disk) + 1 (a NEW segment per
    invocation). An empty / absent spine seeds (1, 1). ``.tmp`` is ignored.
    The number is keyed on the canonical ``.json`` bodies (the source of truth),
    re-readable from disk — deterministic GIVEN the on-disk spine.
    """

    max_seq = 0
    max_segment = 0
    if events_dir.is_dir():
        for path in sorted(events_dir.iterdir()):
            if not path.is_file() or path.name.endswith(".tmp"):
                continue
            match = EVENT_FILENAME_RE.match(path.name)
            if match is None or match.group("ext") != "json":
                continue
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # an unreadable .json is a checker RED, not a seed source; skip it
                # for seeding (the checker will reject the spine).
                continue
            if not isinstance(body, Mapping):
                continue
            seq = body.get("sequence_index")
            if isinstance(seq, int) and not isinstance(seq, bool) and seq > max_seq:
                max_seq = seq
            segment = body.get("run_segment")
            if (
                isinstance(segment, int)
                and not isinstance(segment, bool)
                and segment > max_segment
            ):
                max_segment = segment
    return max_seq + 1, max_segment + 1


def _rebuild_index(building_root: Path, paths: Mapping[str, Path]) -> None:
    """Rebuild spine.{json,jsonl,md} PURELY from events/ (reuse the checker's derivation).

    Uses ``_derive_index_from_events`` — the SAME function the checker imports —
    so the produced index matches the checker's re-derivation BY CONSTRUCTION. If
    the derivation cannot produce a coherent set (which would mean the writer
    produced an inconsistent spine), raise rather than emit a divergent index.
    """

    violations: list[str] = []
    derived = _derive_index_from_events(paths["events_dir"], violations)
    if derived is None:
        raise SpineWriteError(
            "spine index re-derivation failed after write (the writer produced an "
            f"inconsistent events/ set): {violations}"
        )
    derived_view = [_index_entry_view(entry) for entry in derived]

    spine_json_text = canonical_json({"events": derived_view})
    spine_jsonl_text = "".join(canonical_json(view) + "\n" for view in derived_view)
    spine_md_text = render_spine_md(building_root.name, derived_view)

    _atomic_write_text(paths["spine_json"], spine_json_text)
    _atomic_write_text(paths["spine_jsonl"], spine_jsonl_text)
    _atomic_write_text(paths["spine_md"], spine_md_text)


def _ensure_manifest_generation(building_root: Path) -> None:
    """Ensure evidence/evidence-manifest.json carries evidence_generation == u5_5_live.

    Emits the NEW field so the generation-gate engages for this building. If the
    manifest is absent it is created (a fixture convenience); an existing manifest
    is read and only the generation field is set (other fields preserved). The
    write is atomic.
    """

    manifest_path = building_root / "evidence" / "evidence-manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            manifest = loaded
    if manifest.get(EVIDENCE_GENERATION_FIELD) == U5_5_LIVE:
        return
    manifest[EVIDENCE_GENERATION_FIELD] = U5_5_LIVE
    _atomic_write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )


def append_spine_events(
    building_root: Path | str,
    event_bodies: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Append Truth events to a building's spine (the slice-1B disk WRITER).

    An HONEST APPEND-ONLY pen (narrowed slice-1B contract, Smith): the writer does
    NO repair, NO cleanup, NO orphan completion. It appends ONLY to a spine that is
    ALREADY clean, and otherwise REFUSES (raises SpineWriteError) with ZERO writes.
    Separation of concerns: writer = append / checker = detect anomalies / repair =
    a SEPARATE explicit slice. So the writer never adds a new event seq on refusal,
    never launders a checker-RED state, never overwrites a clean prior .json, and
    never silently fixes torn writes (that is the repair slice's job).

    Order (NO disk write until every preflight passes):
      (b) PREFLIGHT (all read-only; raise before any write):
            * MANIFEST: a present evidence-manifest.json that is a directory /
              unparseable / non-dict -> raise.
            * STRUCTURE: spine_structural_violations(require_index_present=False)
              non-empty -> raise. The SAME validator the checker uses, so the writer
              refuses on ANY anomaly the checker would RED: a torn pair
              (.json-without-.md OR .md-without-.json), a stale .tmp, events/junk.txt,
              a mutated prior event, a present-but-disagreeing/directory index file.
              A MISSING index/dir is NOT a RED ONLY pre-first-write (events/ absent
              or empty — the writer creates the index then); a MISSING index WITH
              events present is crash residue the writer REFUSES.
            * NEW BATCH: each new body validated (admitted type, non-empty axis_scope
              subset, no forbidden success/quality/fault key, canonical-serializable)
              and assigned its disk-stateful seq / run_segment.
      (c) ONLY AFTER the preflight passes: mkdir events/, write each event pair
          (atomic temp + os.replace, write-once), rebuild the DERIVED index
          spine.{json,jsonl,md} PURELY from events/ (the checker's derivation, so
          they match by construction), ensure evidence_generation == u5_5_live.

    Disk-stateful seed: next sequence_index = (max complete .json seq)+1,
    run_segment = (max run_segment on disk)+1 (a NEW segment per call). The run-wide
    overwrite_existing flag is IGNORED (append-only). REPLAY = APPEND: a 2nd call
    appends NEW events (strictly-greater seq, new run_segment); it NEVER rewrites a
    prior event's .json. An empty batch returns [] without touching disk (no create,
    no index rebuild, no refresh).

    Returns the written event bodies (with sequence_index / run_segment /
    spine_schema_version filled in), in write order. A one-shot read-back-then-append:
    nothing is held between invocations (no daemon / scheduler / queue).
    """

    root = Path(building_root)
    paths = _spine_paths(root)
    events_dir = paths["events_dir"]

    # === (b.MANIFEST) read-only manifest preflight — BEFORE any mutation, so a
    # broken manifest never even triggers the repair below (and the post-write
    # _ensure_manifest_generation can never be the thing that raises after events
    # have landed = a partial write).
    manifest_path = root / "evidence" / "evidence-manifest.json"
    if manifest_path.exists() and not manifest_path.is_file():
        raise SpineWriteError(
            f"evidence-manifest.json exists but is not a file: {manifest_path}"
        )
    if manifest_path.is_file():
        try:
            loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SpineWriteError(
                "existing evidence-manifest.json is not parseable JSON; refusing to "
                f"append (would leave a partial write): {exc}"
            ) from exc
        if not isinstance(loaded_manifest, dict):
            raise SpineWriteError(
                "existing evidence-manifest.json is not a JSON object; refusing to append"
            )

    # === (b.STRUCTURE) — the writer is an HONEST APPEND-ONLY pen: NO repair, NO
    # cleanup, NO orphan completion. It refuses unless the spine is ALREADY clean,
    # using the SAME shared validator the checker uses (require_index_present=False so
    # a MISSING index/dir is not a RED ONLY pre-first-write — events/ absent/empty —
    # which the writer legitimately creates below; a MISSING index WITH events present
    # is crash residue it refuses). ANY anomaly refuses here with ZERO writes: a torn pair
    # (.json-without-.md OR .md-without-.json), a stale .tmp, events/junk.txt, a
    # mutated prior event, a present-but-disagreeing-or-directory index file. Cleanup
    # / orphan completion is a SEPARATE explicit repair slice — run it first.
    structural = spine_structural_violations(root, require_index_present=False)
    if structural:
        raise SpineWriteError(
            "spine is not clean; the append-only writer refuses (it never repairs / "
            f"cleans / completes — run the explicit repair slice first): {structural}"
        )

    # Disk-stateful seed (reads only; (1, 1) when events/ is absent/empty).
    next_seq, run_segment = _disk_seed(events_dir)

    # === (b.NEW BATCH) validate + number EVERY new body BEFORE touching disk, so a
    # bad body rejects the WHOLE batch with NO partial write (otherwise events
    # 1..N-1 land then event N raises = a torn spine the next pass would adopt). The
    # writer applies the SAME structural rules the checker enforces (admitted type,
    # non-empty axis_scope subset, no forbidden success/quality/fault KEY — design
    # §2/§6: the graph envelope does NOT enforce the forbidden-key rule, so the
    # writer must) so it never produces a spine the checker would reject.
    prepared: list[dict[str, Any]] = []
    seq = next_seq
    for raw_body in event_bodies:
        if not isinstance(raw_body, Mapping):
            raise SpineWriteError("each event body must be a JSON object mapping")
        body: dict[str, Any] = dict(raw_body)
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or event_type not in SPINE_EVENT_TYPES:
            raise SpineWriteError(
                f"event_type {event_type!r} is not an admitted spine event_type"
            )
        axis_scope = body.get("axis_scope")
        if not isinstance(axis_scope, list) or not axis_scope:
            raise SpineWriteError(
                f"{event_type}: axis_scope must be a non-empty list of "
                f"{sorted(SPINE_AXIS_SCOPE_LITERALS)!r}"
            )
        bad_axis = [a for a in axis_scope if a not in SPINE_AXIS_SCOPE_LITERALS]
        if bad_axis:
            raise SpineWriteError(
                f"{event_type}: axis_scope outside "
                f"{sorted(SPINE_AXIS_SCOPE_LITERALS)!r}: {bad_axis!r}"
            )
        # assign the disk-stateful ordinal + this pass's run_segment + schema
        # version. The writer OWNS these mechanical fields (caller-supplied values
        # are overwritten so numbering stays disk-authoritative).
        body["sequence_index"] = seq
        body["run_segment"] = run_segment
        body.setdefault("spine_schema_version", SPINE_SCHEMA_VERSION)
        forbidden = _forbidden_keys_in_body(body)
        if forbidden:
            raise SpineWriteError(
                f"{event_type}: event body carries forbidden success/quality/fault "
                f"key(s) {sorted(forbidden)!r} (support records facts, judges "
                "nothing — store mechanical refs / enums / counts, never a verdict)"
            )
        # canonical-serializability up front (a NaN / non-JSON value here would
        # otherwise fail mid-write).
        try:
            canonical_json(body)
        except (TypeError, ValueError) as exc:
            raise SpineWriteError(
                f"{event_type}: event body is not canonical-serializable JSON ({exc})"
            ) from exc
        prepared.append(body)
        seq += 1

    # === EMPTY APPEND — nothing to append, so the HONEST append-only writer touches
    # NOTHING on disk and returns []. It does NOT create, rebuild, or refresh an
    # index. (The preflight above already proved the spine is clean-or-absent;
    # deriving/refreshing an index for an existing spine on an EMPTY call would be
    # repair, not append — that is the separate repair slice's job.)
    if not prepared:
        return prepared

    # === (c) PREFLIGHT PASSED — now mutate. Create events/ then write the validated
    # batch (each pair write-once + atomic).
    events_dir.mkdir(parents=True, exist_ok=True)
    for body in prepared:
        _write_event_pair_once(events_dir, body)

    # Rebuild the derived index purely from events/ (matches the checker) and emit
    # the generation tag so the gate engages.
    _rebuild_index(root, paths)
    _ensure_manifest_generation(root)

    return prepared


__all__ = [
    "SPINE_EVENT_TYPES",
    "SPINE_AXIS_SCOPE_LITERALS",
    "SPINE_SCHEMA_VERSION",
    "GENESIS_PREV_HASH",
    "EVENT_FILENAME_RE",
    "EVIDENCE_GENERATION_FIELD",
    "U5_5_LIVE",
    "SpineWriteError",
    "canonical_json",
    "content_hash",
    "render_event_md",
    "render_spine_md",
    "graph_ready_json_object",
    "append_spine_events",
    # The SINGLE shared structural validator (checker + writer preflight call it).
    "spine_structural_violations",
    # Pure derivation helpers single-sourced for the checker (import direction
    # checker -> recording).
    "_derive_index_from_events",
    "_index_entry_view",
    "_collect_event_files",
    "_event_body_violations",
    "_forbidden_keys_in_body",
    "_normalize_key",
    "_sha256_text",
    "_load_json",
    "_read_text",
]
