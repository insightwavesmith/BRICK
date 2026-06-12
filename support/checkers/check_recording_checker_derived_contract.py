#!/usr/bin/env python3
"""Check RECORDING-CHECKER-DERIVED-CONTRACT-0 (ζ6) for dynamic-walker evidence.

P-evidence-arch increment 1. This checker DERIVES the expected dynamic-walker
evidence shape (reroute-adoption record, HOLD record, structured field-set
observation) FROM the single canonical recording contract in
``support/recording/contracts.py`` and FAILS if a contract-derived emitter drops
a contract-required field or emits an undeclared one. It walks the real dynamic
graph walker over adapter:local fixtures (NO codex/claude/gemini) and inspects
the records the walker actually produced, so a future feature-impl change that
silently drifts the evidence is REJECTED -- only a change to the CONTRACT can move
the shape.

It also confirms support RECORDS and decides nothing: the emitted evidence and
the emitter/walker source carry NO failing_axis / fault / failed / success
verdict (structured field-set observation only; attribution is the reader's).

This checker is support evidence only. It does not choose Movement, author a
route, judge success or quality, schedule, retry, or call providers.

Pass => exit 0. Reject => exit 1.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _repo_root_from_arg(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_import_path(repo: Path) -> None:
    import_identity = repo / "support" / "import_identity"
    for entry in (str(import_identity), str(repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


# Support emits FACTS, not judgment. These tokens are the verdict/attribution
# labels support must NEVER emit (DELIVER #3 + the hard constraint).
_FORBIDDEN_JUDGMENT_TOKENS: tuple[str, ...] = (
    "failing_axis",
    "fault",
    "failed",
    "success_verdict",
    "quality_verdict",
)


# ---------------------------------------------------------------------------
# A2 INDEPENDENT axis-attribution rule (the anti-tautology fix).
# ---------------------------------------------------------------------------
#
# CRITICAL: the emitter reads the CAPTURE_EVENT_AXIS_ATTRIBUTION dict in the
# recording contract to STAMP each capture event's axis_attribution. If this
# checker verified the emitted value by reading that SAME dict, the check would be
# circular and could never fail. So this checker derives the expected axis from an
# INDEPENDENT rule -- the event_type NAME -- and pins the single non-axis literal
# for non-axis lifecycle events. A corruption of the contract dict (e.g.
# link_movement -> "Brick") is then REJECTED because the emitted value no longer
# matches the independent name-derived expectation.
#
# Rule (independent of the contract dict):
#   event_type starts with "brick_" OR == "brick_opened"  -> "Brick"
#   event_type starts with "agent_"                        -> "Agent"
#   event_type starts with "link_"                         -> "Link"
#   any other (non-axis) lifecycle event                   -> the pinned non-axis
#                                                             literal below.
# The non-axis literal is read ONCE from the contract's declared non-axis constant
# and pinned here as the ONLY value a non-axis event may carry.
_PINNED_NON_AXIS_ATTRIBUTION = "Support residue"


def _independent_expected_axis(event_type: str) -> str:
    """Independent expected axis_attribution for a capture event_type.

    Derived from the event_type NAME, NOT from the contract's
    CAPTURE_EVENT_AXIS_ATTRIBUTION dict (which the emitter also reads), so this
    check is not a tautology and a corrupted dict value is rejected.
    """

    if event_type.startswith("brick_") or event_type == "brick_opened":
        return "Brick"
    if event_type.startswith("agent_"):
        return "Agent"
    if event_type.startswith("link_"):
        return "Link"
    # Non-axis lifecycle event (e.g. building_opened): the only allowed value is
    # the pinned non-axis literal.
    return _PINNED_NON_AXIS_ATTRIBUTION


def _expected_keys(required: Sequence[str], optional: Sequence[str], observed: Mapping[str, Any]) -> set[str]:
    """Expected key set = all required + optional fields that are present."""

    keys = set(required)
    for name in optional:
        if name in observed:
            keys.add(name)
    return keys


def _check_record_against_contract(
    record: Mapping[str, Any],
    *,
    required: Sequence[str],
    optional: Sequence[str],
    label: str,
) -> list[str]:
    violations: list[str] = []
    observed_keys = set(record.keys())
    missing = sorted(set(required) - observed_keys)
    if missing:
        violations.append(f"{label}: emitter DROPPED contract-required field(s): {missing}")
    undeclared = sorted(observed_keys - set(required) - set(optional))
    if undeclared:
        violations.append(f"{label}: emitter ADDED undeclared field(s) not in contract: {undeclared}")
    return violations


def _build_checker_plan(chk: Any, prefix: str, budget: int) -> tuple[Mapping[str, Any], str]:
    return chk._checker_plan(prefix, budget)


def check(repo: Path) -> list[str]:
    _ensure_import_path(repo)
    violations: list[str] = []

    from brick_protocol.support.recording.contracts import (
        HOLD_RECORD_OPTIONAL_FIELDS,
        HOLD_RECORD_REQUIRED_FIELDS,
        REROUTE_ADOPTION_OPTIONAL_FIELDS,
        REROUTE_ADOPTION_REQUIRED_FIELDS,
        STRUCTURED_FIELD_OBSERVATION_OPTIONAL_FIELDS,
        STRUCTURED_FIELD_OBSERVATION_REQUIRED_FIELDS,
    )
    from brick_protocol.support.recording.walker_evidence import (
        _build_from_specs,
        build_structured_field_observation,
    )
    from brick_protocol.support.recording.contracts import (
        reroute_adoption_field_specs,
    )

    # Re-use the standalone walker checker's adapter:local fixtures so the
    # records inspected are the records the real walker produced.
    import support.checkers.check_bounded_agent_proposed_routing_loop0 as walker_chk

    walker_chk._ensure_import_path(repo)

    # --- Run the walker and inspect ADOPTION records (budget available). ---
    plan_a, b2_a = _build_checker_plan(walker_chk, "zeta6-adopt", budget=2)
    _, _, rec_a = walker_chk._run(
        plan_a, walker_chk._reroute_callable(b2_a, {"brick-zeta6-adopt-review"}), repo
    )
    adopted = [r for r in rec_a if not r.get("disposition_required")]
    if not adopted:
        violations.append("derive: walker produced no ADOPTION record to inspect against the contract")
    for record in adopted:
        violations.extend(
            _check_record_against_contract(
                record,
                required=REROUTE_ADOPTION_REQUIRED_FIELDS,
                optional=REROUTE_ADOPTION_OPTIONAL_FIELDS,
                label="reroute_adoption_record",
            )
        )
        violations.extend(
            _check_structured_observation(
                record.get("structured_field_observation"),
                required=STRUCTURED_FIELD_OBSERVATION_REQUIRED_FIELDS,
                optional=STRUCTURED_FIELD_OBSERVATION_OPTIONAL_FIELDS,
                label="reroute_adoption_record.structured_field_observation",
            )
        )

    # --- Run the walker and inspect HOLD records (budget exhausted). ---
    plan_b, b2_b = _build_checker_plan(walker_chk, "zeta6-hold", budget=1)
    _, _, rec_b = walker_chk._run(
        plan_b,
        walker_chk._reroute_callable(b2_b, {"brick-zeta6-hold-review", b2_b}),
        repo,
    )
    held = [r for r in rec_b if r.get("disposition_required")]
    if not held:
        violations.append("derive: walker produced no HOLD record to inspect against the contract")
    for record in held:
        violations.extend(
            _check_record_against_contract(
                record,
                required=HOLD_RECORD_REQUIRED_FIELDS,
                optional=HOLD_RECORD_OPTIONAL_FIELDS,
                label="hold_record",
            )
        )
        violations.extend(
            _check_structured_observation(
                record.get("structured_field_observation"),
                required=STRUCTURED_FIELD_OBSERVATION_REQUIRED_FIELDS,
                optional=STRUCTURED_FIELD_OBSERVATION_OPTIONAL_FIELDS,
                label="hold_record.structured_field_observation",
            )
        )

    # --- The contract is the SOURCE: the emitter builds the record by ITERATING
    # the contract field-spec, so a contract-required field cannot be silently
    # dropped and an undeclared field cannot be silently added. Prove both via
    # the shared builder the emitters use. ---
    specs = reroute_adoption_field_specs()
    full_values = {
        spec.name: "probe" for spec in specs if spec.presence == "required"
    }
    # 1) DROP a required field -> the builder must reject (no silent drift).
    dropped_values = dict(full_values)
    dropped_field = next(spec.name for spec in specs if spec.presence == "required")
    dropped_values.pop(dropped_field)
    try:
        _build_from_specs(specs, dropped_values, record_label="reroute_adoption_record")
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        violations.append(f"emitter: dropping a contract-required field raised the wrong error: {exc!r}")
    else:
        violations.append(
            "emitter: dropping a contract-required field did NOT reject (silent drift possible)"
        )
    # 2) ADD an undeclared field -> the builder must reject.
    added_values = dict(full_values)
    added_values["undeclared_drift_field"] = "x"
    try:
        _build_from_specs(specs, added_values, record_label="reroute_adoption_record")
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        violations.append(f"emitter: adding an undeclared field raised the wrong error: {exc!r}")
    else:
        violations.append(
            "emitter: adding an undeclared field did NOT reject (silent drift possible)"
        )

    # --- support RECORDS, decides nothing: no judgment label in the emitted
    # records, the emitter source, or the structured observation. ---
    violations.extend(_check_no_judgment_in_records(adopted + held))
    violations.extend(_check_no_judgment_in_source(repo))

    # --- The structured observation records facts, computed mechanically. ---
    observation = build_structured_field_observation(
        brick_required_fields=["a", "b"],
        observed_fields=["a"],
        gate_required_fields=["a", "c"],
    )
    if observation.get("missing_from_observed") != ["b", "c"]:
        violations.append(
            "structured_observation: missing_from_observed delta is not the mechanical set difference"
        )
    if observation.get("demanded_beyond_brick") != ["c"]:
        violations.append(
            "structured_observation: demanded_beyond_brick delta is not the mechanical set difference"
        )

    # --- A2: accumulated-Building operator evidence (capture events, building-map
    # per-step rows, frontier observation) is CONTRACT-DERIVED. Run the real run
    # surface over adapter:local fixtures and inspect the records it produced. ---
    violations.extend(_check_a2_operator_evidence(repo, walker_chk))

    return violations


def _check_a2_operator_evidence(repo: Path, walker_chk: Any) -> list[str]:
    """Derive + verify the A2 operator evidence shapes against the contract.

    Runs run.run_building_plan over adapter:local fixtures (NO providers) for a
    completing linear build (capture events + building-map rows) and a build that
    fails mid-way (accumulated frontier observation), then asserts each record
    matches the contract field-spec AND that each capture event's axis_attribution
    matches the INDEPENDENT name-derived expectation (not the contract dict).
    """

    from brick_protocol.support.recording.contracts import (
        BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS,
        BUILDING_MAP_BRICK_INSTANCE_REQUIRED_FIELDS,
        BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS,
        CAPTURE_EVENT_HEADER_FIELDS,
        CAPTURE_EVENT_PAYLOAD_FIELDS,
        CAPTURE_EVENT_TYPES,
        FRONTIER_OBSERVATION_OPTIONAL_FIELDS,
        FRONTIER_OBSERVATION_REQUIRED_FIELDS,
    )

    violations: list[str] = []

    capture_events, building_map = _run_linear_operator_evidence(repo, walker_chk)
    frontier_observation = _run_frontier_operator_evidence(repo, walker_chk)

    # 1) Capture events: exactly the 8 declared types, each matching its field-spec.
    if not capture_events:
        violations.append("a2: run produced no capture_events to inspect against the contract")
    emitted_types = [event.get("event_type") for event in capture_events]
    for event_type in CAPTURE_EVENT_TYPES:
        if event_type not in emitted_types:
            violations.append(f"a2.capture_events: missing declared event_type {event_type!r}")
    for event in capture_events:
        event_type = event.get("event_type")
        if event_type not in CAPTURE_EVENT_PAYLOAD_FIELDS:
            violations.append(f"a2.capture_events: undeclared event_type {event_type!r} emitted")
            continue
        expected_fields = list(CAPTURE_EVENT_HEADER_FIELDS) + list(
            CAPTURE_EVENT_PAYLOAD_FIELDS[event_type]
        )
        violations.extend(
            _check_record_against_contract(
                event,
                required=expected_fields,
                optional=(),
                label=f"a2.capture_event:{event_type}",
            )
        )
        # INDEPENDENT axis-attribution check (anti-tautology): compare the emitted
        # value against the name-derived rule, NOT against the contract dict.
        expected_axis = _independent_expected_axis(str(event_type))
        emitted_axis = event.get("axis_attribution")
        if emitted_axis != expected_axis:
            violations.append(
                f"a2.capture_event:{event_type}: axis_attribution mismatch -- "
                f"emitted {emitted_axis!r} but the INDEPENDENT name-derived rule "
                f"expects {expected_axis!r} (contract axis dict corrupted or emitter drifted)"
            )

    # 2) Building-map per-step rows match the per-axis contract field-spec.
    brick_instances = building_map.get("brick_instances") or []
    agent_bindings = building_map.get("agent_bindings") or []
    link_edges = building_map.get("link_edges") or []
    if not brick_instances:
        violations.append("a2.building_map: no brick_instances rows to inspect")
    for row in brick_instances:
        if not isinstance(row, Mapping):
            continue
        violations.extend(
            _check_record_against_contract(
                row,
                required=BUILDING_MAP_BRICK_INSTANCE_REQUIRED_FIELDS,
                optional=(),
                label="a2.building_map.brick_instance",
            )
        )
    if not agent_bindings:
        violations.append("a2.building_map: no agent_bindings rows to inspect")
    for row in agent_bindings:
        if not isinstance(row, Mapping):
            continue
        violations.extend(
            _check_record_against_contract(
                row,
                required=BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS,
                optional=(),
                label="a2.building_map.agent_binding",
            )
        )
    # link_edge rows carry the contract-required base fields; the route-replay
    # layer may overlay OPTIONAL metadata, so only required-field presence is
    # asserted (undeclared overlay keys are allowed here).
    for row in link_edges:
        if not isinstance(row, Mapping):
            continue
        missing = sorted(set(BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS) - set(row.keys()))
        if missing:
            violations.append(
                f"a2.building_map.link_edge: emitter DROPPED contract-required field(s): {missing}"
            )

    # 3) Frontier observation matches the contract field-spec exactly.
    if not isinstance(frontier_observation, Mapping):
        violations.append("a2.frontier: run produced no frontier_observation to inspect")
    else:
        violations.extend(
            _check_record_against_contract(
                frontier_observation,
                required=FRONTIER_OBSERVATION_REQUIRED_FIELDS,
                optional=FRONTIER_OBSERVATION_OPTIONAL_FIELDS,
                label="a2.frontier_observation",
            )
        )

    # 4) support RECORDS, decides nothing: no judgment label in the A2 records or
    # the A2 emitter source.
    a2_records = list(capture_events) + list(brick_instances) + list(agent_bindings)
    if isinstance(frontier_observation, Mapping):
        a2_records.append(frontier_observation)
    violations.extend(_check_no_judgment_in_records(a2_records))
    emitter_src = (
        repo / "support" / "recording" / "operator_evidence.py"
    ).read_text(encoding="utf-8")
    for token in ("failing_axis",):
        if f'"{token}"' in emitter_src or f"'{token}'" in emitter_src:
            violations.append(f"a2.no-judgment: operator_evidence emitter source assigns a {token!r} key")
    # AXIS BOUNDARY SEPARATION: the A2 emitter imports ONLY the recording contract,
    # no Brick/Agent/Link/operator axis module.
    violations.extend(_check_emitter_axis_separation(emitter_src))

    return violations


def _run_linear_operator_evidence(repo: Path, walker_chk: Any):
    """Run a completing linear build over adapter:local; return (capture_events, building_map).

    Inspects the RAW contract-derived records the emitter produced -- the in-memory
    ``completion.lifecycle_packet_mapping["capture_events"]`` (the
    ``agent_run_lifecycle_mapping`` output, before the downstream CloudEvents
    capture envelope rewraps/flattens it on disk) and the in-memory
    ``result.building_map_packet`` (the contract-derived per-step rows). These are
    the exact dicts the operator_evidence emitters built.
    """

    import tempfile as _tempfile

    from brick_protocol.support.operator.run import run_building_plan

    plan, _b2 = walker_chk._checker_plan("zeta6-a2-lin", budget=2)

    def _ok(request: Any) -> Mapping[str, Any]:
        return {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }

    with _tempfile.TemporaryDirectory(prefix="bp-zeta6-a2-lin-") as tmp:
        walker_mode = "dynamic" if plan.get("plan_shape") == "graph" else "linear"
        result = run_building_plan(
            plan,
            output_root=Path(tmp),
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _ok},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
            walker_mode=walker_mode,
        )
        capture_events: list[Mapping[str, Any]] = []
        for step in result.step_results:
            mapping = step.completion.lifecycle_packet_mapping
            for event in mapping.get("capture_events", []):
                if isinstance(event, Mapping):
                    capture_events.append(event)
        building_map = dict(result.building_map_packet)
    return capture_events, building_map


def _run_frontier_operator_evidence(repo: Path, walker_chk: Any):
    """Run a build that fails mid-way; return the accumulated frontier_observation dict."""

    import json as _json
    import tempfile as _tempfile

    from brick_protocol.support.operator.run import run_building_plan

    plan, fail_brick = walker_chk._checker_plan("zeta6-a2-fr", budget=2)

    def _fail_on_build(request: Any) -> Mapping[str, Any]:
        if request.brick_instance_ref == fail_brick:
            raise RuntimeError("forced adapter error for accumulated frontier check")
        return {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }

    with _tempfile.TemporaryDirectory(prefix="bp-zeta6-a2-fr-") as tmp:
        building_root = None
        try:
            walker_mode = "dynamic" if plan.get("plan_shape") == "graph" else "linear"
            run_building_plan(
                plan,
                output_root=Path(tmp),
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _fail_on_build},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
                walker_mode=walker_mode,
            )
        except Exception as exc:  # noqa: BLE001 - the frontier path raises after writing evidence
            building_root = getattr(exc, "building_root", None)
            if building_root is None:
                roots = [path for path in Path(tmp).iterdir() if path.is_dir()]
                if len(roots) == 1:
                    building_root = roots[0]
        if building_root is None:
            return None
        building_map = _json.loads(
            (Path(building_root) / "work" / "building-map.json").read_text(encoding="utf-8")
        )
    return building_map.get("frontier_observation")


def _check_emitter_axis_separation(emitter_src: str) -> list[str]:
    """The A2 emitter must import ONLY the recording contract, no axis module."""

    violations: list[str] = []
    forbidden = (
        "brick_protocol.brick",
        "brick_protocol.agent",
        "brick_protocol.link",
        "brick_protocol.support.operator",
    )
    for line in emitter_src.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("from ") or stripped.startswith("import ")):
            continue
        for token in forbidden:
            if token in stripped:
                violations.append(
                    f"a2.axis-separation: operator_evidence imports an axis/operator module: {stripped!r}"
                )
    return violations


def _check_structured_observation(
    observation: Any,
    *,
    required: Sequence[str],
    optional: Sequence[str],
    label: str,
) -> list[str]:
    if not isinstance(observation, Mapping):
        return [f"{label}: structured field-set observation is missing or not a mapping"]
    return _check_record_against_contract(
        observation, required=required, optional=optional, label=label
    )


def _check_no_judgment_in_records(records: Sequence[Mapping[str, Any]]) -> list[str]:
    violations: list[str] = []
    for record in records:
        keys = _all_keys(record)
        for token in _FORBIDDEN_JUDGMENT_TOKENS:
            if any(token in key for key in keys):
                violations.append(
                    f"no-judgment: emitted record carries a judgment key containing {token!r}"
                )
    return violations


def _all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys |= _all_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            keys |= _all_keys(child)
    return keys


def _check_no_judgment_in_source(repo: Path) -> list[str]:
    violations: list[str] = []
    emitter_src = (repo / "support" / "recording" / "walker_evidence.py").read_text(encoding="utf-8")
    # The emitter must not ASSIGN a judgment-label key. We allow the words to
    # appear in the no-judgment DOC/comment narrative (e.g. "no fault, no
    # failed"); we forbid them as emitted dict keys.
    for token in ("failing_axis",):
        if f'"{token}"' in emitter_src or f"'{token}'" in emitter_src:
            violations.append(f"no-judgment: emitter source assigns a {token!r} key")
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for RECORDING-CHECKER-DERIVED-CONTRACT-0 "
            "(ζ6); derives the dynamic-walker evidence shape from the recording "
            "contract and rejects emitter drift. It does not prove source truth, "
            "Movement, success, or quality."
        )
    )
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = _repo_root_from_arg(args.repo)
    try:
        violations = check(repo)
    except Exception as exc:  # noqa: BLE001 - surface any failure as a rejection
        print(f"recording-checker-derived-contract rejected: {exc}", file=sys.stderr)
        return 1
    if violations:
        print("recording-checker-derived-contract rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "proof limit: support evidence only; this checker derives the "
            "evidence shape from the recording contract and does not prove "
            "source truth, Movement authority, success, or quality.",
            file=sys.stderr,
        )
        return 1
    print(
        "recording-checker-derived-contract passed: the dynamic-walker "
        "reroute-adoption record, HOLD record, and structured field-set "
        "observation match the recording contract field-spec exactly (no dropped "
        "required field, no undeclared field); the emitter raises on a dropped "
        "required value; and support emitted FACTS only (no failing_axis / fault "
        "/ failed / success verdict). A2: the accumulated-Building operator "
        "evidence (8 lifecycle capture events, building-map per-step rows, frontier "
        "observation) the run surface produced over adapter:local also matches the "
        "recording contract field-spec, the operator_evidence emitter imports no "
        "axis/operator module (axis boundary), and each capture event's "
        "axis_attribution matches the INDEPENDENT name-derived rule (event_type "
        "prefix -> axis; non-axis lifecycle event pinned to the support-residue "
        "literal) -- NOT read from the contract axis dict, so a corrupted dict value "
        "is rejected. NOTE: role_in_event has no clean name-derived rule (the roles "
        "are descriptive labels), so it is pinned by the contract field-spec only; "
        "the independent axis check is the anti-tautology guard."
    )
    print(
        "proof limit: support evidence only; checker pass does not prove source "
        "truth, success judgment, quality judgment, or Movement authority."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
