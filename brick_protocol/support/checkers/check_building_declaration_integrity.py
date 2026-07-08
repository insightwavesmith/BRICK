#!/usr/bin/env python3
"""Validate Building declaration-chain authenticity.

A ``project/<project-id>/buildings/<building-id>/`` root ASSERTS an engine run:
its work is the persisted declared launch chain, not raw ``task.md`` and not an
ephemeral in-memory plan. This checker enforces the three declaration-integrity
gaps that no other checker covers today (engine blueprint 0531 §2.1):

  gap 1 — composition-mode authenticity: a recorded plan_ref ending
          ``:in-memory-composed`` is rejected unless the building records a
          one-off COO ``composition_mode`` AND a persisted declared-building-plan
          copy exists in the root.
  gap 2 — declaration-chain artifact requirement: a building root that records
          ``declaration_provenance`` (i.e. asserts it ran the declared launch
          chain) MUST persist ``work/building-intake.json`` +
          ``work/preset-expansion.json`` + ``work/declared-building-plan.json`` +
          ``work/link-launch-policy.json``.
  gap 3 — provenance<->returned acceptance bar: composition origin must be
          recorded (``declaration_provenance.composition_mode``) AND every
          returned Agent fact must reference the declared Agent/Brick binding it
          answered (its ``agent_object_ref`` is a declared performer and its
          ``received_work`` resolves to a declared binding/Brick instance).
  gap 4 — declared-plan purity (FQ-2, codex review P2): the persisted
          ``work/declared-building-plan.json`` is the Building birth certificate;
          its ``declared_plan_copy`` must hold ONLY the declared launch
          declaration. A copy that carries RUNTIME walker state
          (``dynamic_walker_evidence`` / ``node_reroute_budgets`` / ... -- runtime
          belongs in evidence-manifest.plan_snapshot / frontier / traces) is
          rejected.

This checker is support evidence only. It decides nothing; it is not source
truth, not success judgment, not quality judgment, and not Movement authority.
It admits no axis/fact class and imports no axis module. The four gaps each
carry an anti-tautological negative probe (a synthesized violating building root
that the validator MUST reject); the kernel check raises if any probe was not
rejected, so a validator that silently stops rejecting drives ``--all`` RED.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROJECT_ROOT = "project"
BUILDINGS_SEGMENT = "buildings"

# A building root that records declaration_provenance ASSERTS the declared
# launch chain; these upstream artifacts must then be persisted (gap 2). The
# path-shape checker treats them as OPTIONAL, so roots that never claimed a
# declaration_provenance (older task.md roots, minimal roots) are out of scope
# and keep passing.
DECLARATION_CHAIN_ARTIFACTS = (
    ("work", "building-intake.json"),
    ("work", "preset-expansion.json"),
    ("work", "declared-building-plan.json"),
    ("work", "link-launch-policy.json"),
)
DECLARED_BUILDING_PLAN_REL = ("work", "declared-building-plan.json")
BUILDING_MAP_REL = ("work", "building-map.json")
RETURNED_CLAIMS_REL = ("evidence", "claim_trace", "agent", "returned_claims.json")

IN_MEMORY_COMPOSED_SUFFIX = ":in-memory-composed"
AGENT_PERFORMER_PREFIX = "agent-performer:"

# gap 4 (FQ-2): top-level keys that are RUNTIME walker state, never part of the
# declared launch declaration. The walker threads these onto the plan dict
# before the evidence write (brick_protocol/support/operator/walker_kernel.py /
# walker_resume.py), and a round-tripped persisted plan can carry a top-level
# ``node_reroute_budgets``. Their authentic home is
# evidence-manifest.plan_snapshot.plan_rows_copy / frontier / traces -- NOT the
# birth-certificate ``declared_plan_copy``. Mirror of
# brick_protocol/support/recording/declaration_packets.py::_DECLARED_PLAN_RUNTIME_KEYS (kept in
# sync; a fresh engine run strips exactly these from the declared copy).
DECLARED_PLAN_RUNTIME_KEYS = (
    "dynamic_walker_evidence",
    "node_reroute_budgets",
    "node_reroute_landings",
    "reroute_adoption_records",
    "fan_in_wait_all_observations",
    "resume_observations",
    "held",
    "hold",
    "walker_mode",
)

# A one-off COO composition is the only authentic origin for an
# in-memory-composed plan ref. Recorded composition_mode values that name a
# caller/coo declared composition satisfy gap 1's "records a one-off COO
# composition" requirement; an empty / derived-default mode does not.
ONE_OFF_COO_COMPOSITION_MARKERS = ("coo", "caller_or_coo", "caller-or-coo")

PROOF_LIMIT = (
    "proof limit: declaration-integrity support check only; this does not prove "
    "content correctness, source truth, success judgment, quality judgment, or "
    "Movement authority."
)


# ---------------------------------------------------------------------------
# evidence readers
# ---------------------------------------------------------------------------
def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, Mapping) else {}


def _declaration_provenance(building_map: Mapping[str, Any]) -> Mapping[str, Any]:
    provenance = building_map.get("declaration_provenance")
    return provenance if isinstance(provenance, Mapping) else {}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _recorded_plan_refs(building_map: Mapping[str, Any], declared_plan: Mapping[str, Any]) -> list[str]:
    """Every plan_ref the persisted building root records about itself."""

    refs: list[str] = []
    provenance = _declaration_provenance(building_map)
    candidates: list[Any] = [
        building_map.get("plan_ref"),
        building_map.get("active_plan_ref"),
        provenance.get("plan_ref"),
        declared_plan.get("plan_ref"),
    ]
    declared_copy = declared_plan.get("declared_plan_copy")
    if isinstance(declared_copy, Mapping):
        candidates.append(declared_copy.get("plan_ref"))
    for candidate in candidates:
        ref = _text(candidate)
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _records_one_off_coo_composition(provenance: Mapping[str, Any]) -> bool:
    mode = _text(provenance.get("composition_mode")).lower()
    if not mode:
        return False
    return any(marker in mode for marker in ONE_OFF_COO_COMPOSITION_MARKERS)


def _ref_tail(value: str) -> str:
    """The ``<attempt>:<step-slug>`` tail shared by binding/fact/work refs.

    Declared bindings use ``binding:<NN>:<step-slug>``; returned facts use
    ``agent-fact:<NN>:<step-slug>`` and ``received_work``
    ``brick-work:<NN>:<step-slug>``. The portion after the first ``:`` is the
    binding tail they all share, so a returned fact resolves to a declared
    binding when their tails match.
    """

    text = _text(value)
    if ":" not in text:
        return ""
    return text.split(":", 1)[1].strip()


def _declared_performer_object_refs(building_map: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    bindings = building_map.get("agent_bindings")
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            performer = _text(binding.get("agent_performer_ref"))
            if performer.startswith(AGENT_PERFORMER_PREFIX):
                object_ref = performer[len(AGENT_PERFORMER_PREFIX) :].strip()
                if object_ref:
                    refs.add(object_ref)
            object_ref = _text(binding.get("agent_object_ref"))
            if object_ref:
                refs.add(object_ref)
    return refs


def _declared_binding_tails(building_map: Mapping[str, Any]) -> set[str]:
    tails: set[str] = set()
    bindings = building_map.get("agent_bindings")
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            tail = _ref_tail(_text(binding.get("agent_binding_id")))
            if tail:
                tails.add(tail)
    return tails


def _declared_brick_instance_refs(building_map: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    instances = building_map.get("brick_instances")
    if isinstance(instances, list):
        for instance in instances:
            if not isinstance(instance, Mapping):
                continue
            for key in ("brick_instance_id", "brick_work_ref", "id"):
                ref = _text(instance.get(key))
                if ref:
                    refs.add(ref)
    return refs


def _returned_agent_facts(returned_claims: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    facts = returned_claims.get("facts")
    out: list[Mapping[str, Any]] = []
    if isinstance(facts, list):
        for fact in facts:
            if isinstance(fact, Mapping) and fact.get("axis") == "Agent":
                out.append(fact)
    return out


# ---------------------------------------------------------------------------
# the three gap validators
# ---------------------------------------------------------------------------
def validate_composition_mode_authenticity(
    building_root: Path,
    building_map: Mapping[str, Any],
    declared_plan: Mapping[str, Any],
    *,
    label: str,
    violations: list[str],
) -> None:
    """Gap 1: an in-memory-composed plan_ref needs COO origin + persisted copy."""

    provenance = _declaration_provenance(building_map)
    for ref in _recorded_plan_refs(building_map, declared_plan):
        if not ref.endswith(IN_MEMORY_COMPOSED_SUFFIX):
            continue
        if not _records_one_off_coo_composition(provenance):
            violations.append(
                f"{label}: plan_ref {ref!r} ends ':in-memory-composed' but the "
                "building does not record a one-off COO composition_mode in "
                "declaration_provenance"
            )
        if not (building_root / Path(*DECLARED_BUILDING_PLAN_REL)).is_file():
            violations.append(
                f"{label}: plan_ref {ref!r} ends ':in-memory-composed' but no "
                "persisted work/declared-building-plan.json copy exists"
            )


def validate_declaration_chain_artifacts(
    building_root: Path,
    *,
    label: str,
    violations: list[str],
) -> None:
    """Gap 2: a declaration-provenance root must persist the 4 chain artifacts."""

    for artifact in DECLARATION_CHAIN_ARTIFACTS:
        if not (building_root / Path(*artifact)).is_file():
            violations.append(
                f"{label}: building root records declaration_provenance but is "
                f"missing required declaration-chain artifact work/{artifact[1]}"
            )


def validate_provenance_returned_acceptance(
    building_root: Path,
    building_map: Mapping[str, Any],
    *,
    label: str,
    violations: list[str],
) -> None:
    """Gap 3: composition origin recorded + returned references declared binding.

    Scoped subset (see module docstring / return note): the full invariant says
    a returned record must reference the declared Agent/Brick binding it
    answered. From the persisted evidence shape this is checkable as: every
    returned Agent fact (a) names a declared performer ``agent_object_ref`` and
    (b) its ``received_work`` resolves to a declared binding (shared
    ``<attempt>:<step-slug>`` tail) or a declared Brick instance. Composition
    authorship is the recorded ``declaration_provenance.composition_mode``.
    """

    provenance = _declaration_provenance(building_map)
    if not _text(provenance.get("composition_mode")):
        violations.append(
            f"{label}: declaration_provenance must record a composition_mode "
            "(composition authorship/origin) for a declared launch-chain root"
        )

    returned_path = building_root / Path(*RETURNED_CLAIMS_REL)
    if not returned_path.is_file():
        # A declaration-provenance root may legitimately be at a pre-returned
        # frontier (path-shape governs which trace files are required); gap 3's
        # returned-binding bar only applies once returned_claims exists.
        return
    returned_claims = _read_json_mapping(returned_path)
    agent_facts = _returned_agent_facts(returned_claims)
    if not agent_facts:
        return

    declared_object_refs = _declared_performer_object_refs(building_map)
    declared_tails = _declared_binding_tails(building_map)
    declared_brick_refs = _declared_brick_instance_refs(building_map)
    for index, fact in enumerate(agent_facts):
        envelope = fact.get("fact")
        envelope_map = envelope if isinstance(envelope, Mapping) else {}
        fact_ref = _text(fact.get("fact_ref"))
        object_ref = _text(envelope_map.get("agent_object_ref"))
        received_work = _text(envelope_map.get("received_work"))

        if not object_ref or object_ref not in declared_object_refs:
            violations.append(
                f"{label}: returned Agent fact {fact_ref or f'#{index}'} "
                f"agent_object_ref {object_ref!r} is not a declared Agent binding"
            )

        received_tail = _ref_tail(received_work)
        resolves = (
            (received_tail and received_tail in declared_tails)
            or (received_work and received_work in declared_brick_refs)
        )
        if not resolves:
            violations.append(
                f"{label}: returned Agent fact {fact_ref or f'#{index}'} "
                f"received_work {received_work!r} does not reference a declared "
                "Brick/Agent binding"
            )


def validate_declared_plan_purity(
    declared_plan: Mapping[str, Any],
    *,
    label: str,
    violations: list[str],
) -> None:
    """Gap 4 (FQ-2): the declared_plan_copy must carry no runtime walker state."""

    declared_copy = declared_plan.get("declared_plan_copy")
    if not isinstance(declared_copy, Mapping):
        return
    for key in DECLARED_PLAN_RUNTIME_KEYS:
        if key in declared_copy:
            violations.append(
                f"{label}: work/declared-building-plan.json declared_plan_copy "
                f"carries runtime walker key {key!r}; the declared launch "
                "declaration must be pure (runtime belongs in "
                "evidence-manifest.plan_snapshot / frontier / traces)"
            )


# ---------------------------------------------------------------------------
# per-root + repo orchestration
# ---------------------------------------------------------------------------
def validate_building_root(building_root: Path, *, label: str | None = None) -> list[str]:
    """Validate one persisted building root; return declaration-integrity violations."""

    root_label = label or building_root.name
    violations: list[str] = []
    building_map = _read_json_mapping(building_root / Path(*BUILDING_MAP_REL))
    declared_plan = _read_json_mapping(building_root / Path(*DECLARED_BUILDING_PLAN_REL))

    # Gap 1 applies to ANY persisted root that records an in-memory-composed
    # plan ref (independent of declaration_provenance).
    validate_composition_mode_authenticity(
        building_root,
        building_map,
        declared_plan,
        label=root_label,
        violations=violations,
    )

    # Gap 4 (FQ-2) applies to ANY persisted root that has a declared-building-plan
    # copy -- the birth-certificate purity invariant is about the artifact itself,
    # independent of declaration_provenance.
    validate_declared_plan_purity(
        declared_plan,
        label=root_label,
        violations=violations,
    )

    # Gaps 2 & 3 apply only to roots that ASSERT the declared launch chain by
    # recording declaration_provenance. Roots that never claimed it are not in
    # scope (path-shape already governs their required shape).
    if _declaration_provenance(building_map):
        validate_declaration_chain_artifacts(
            building_root,
            label=root_label,
            violations=violations,
        )
        validate_provenance_returned_acceptance(
            building_root,
            building_map,
            label=root_label,
            violations=violations,
        )
    return violations


def collect_building_roots(repo: Path) -> list[Path]:
    project_root = repo / PROJECT_ROOT
    if not project_root.is_dir():
        return []
    roots: list[Path] = []
    for map_path in sorted(project_root.glob(f"*/{BUILDINGS_SEGMENT}/*/work/building-map.json")):
        roots.append(map_path.parent.parent)
    return roots


def check_repo(repo: Path) -> list[str]:
    violations: list[str] = []
    for building_root in collect_building_roots(repo):
        label = building_root.relative_to(repo).as_posix()
        violations.extend(validate_building_root(building_root, label=label))
    return violations


# ---------------------------------------------------------------------------
# anti-tautological FIRE probes (one per gap)
# ---------------------------------------------------------------------------
def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _probe_building_map(*, with_provenance: bool = True, **overrides: Any) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "composition_mode": "coo-declared-dogfood-plan",
        "plan_ref": "building-plan:probe",
    }
    building_map: dict[str, Any] = {
        "kind": "building_graph_map",
        "building_id": "declaration-integrity-probe",
        "agent_bindings": [
            {
                "agent_binding_id": "binding:01:probe-step",
                "agent_performer_ref": "agent-performer:agent-object:dev",
                "brick_instance_ref": "brick-probe",
            }
        ],
        "brick_instances": [
            {"brick_instance_id": "brick-probe", "brick_work_ref": "work:probe-step"}
        ],
    }
    if with_provenance:
        building_map["declaration_provenance"] = provenance
    building_map.update(overrides)
    return building_map


def _probe_returned_claims(*, object_ref: str, received_work: str) -> dict[str, Any]:
    return {
        "facts": [
            {
                "axis": "Agent",
                "fact_ref": "agent-fact:01:probe-step",
                "fact": {
                    "agent_fact_fields": ["received_work", "returned"],
                    "agent_object_ref": object_ref,
                    "received_work": received_work,
                    "returned": {"observed_evidence": ["probe"], "not_proven": ["probe"]},
                },
                "raw_refs": ["raw:probe"],
                "proof_limits": ["probe"],
                "not_proven": ["probe"],
            }
        ]
    }


def _write_full_chain(root: Path) -> None:
    for artifact in DECLARATION_CHAIN_ARTIFACTS:
        _write_json(root / Path(*artifact), {"kind": "probe_provenance"})


def gap1_composition_mode_authenticity_probe() -> Mapping[str, Any]:
    """FIRE gap 1: an in-memory-composed plan_ref without COO origin must reject."""

    with tempfile.TemporaryDirectory(prefix="bp-decl-integrity-gap1-") as tmp:
        root = Path(tmp) / "buildings" / "gap1-probe"
        # Violating: plan_ref ends :in-memory-composed, composition_mode is a
        # plain derived default (not a one-off COO composition) and there is no
        # persisted declared-building-plan.json copy.
        _write_json(
            root / Path(*BUILDING_MAP_REL),
            {
                "kind": "building_graph_map",
                "building_id": "gap1-probe",
                "plan_ref": "building-plan:gap1-probe:in-memory-composed",
                "declaration_provenance": {"composition_mode": "declared-graph"},
            },
        )
        violations = validate_building_root(root, label="gap1-probe")
        rejected = any("in-memory-composed" in violation for violation in violations)
    return {
        "probe_ref": "building-declaration-integrity-probe:gap1_composition_mode_authenticity",
        "rejected": rejected,
        "violations": violations,
        "proof_limits": ["negative probe support evidence only"],
    }


def gap2_declaration_chain_artifact_probe() -> Mapping[str, Any]:
    """FIRE gap 2: a declaration-provenance root missing a chain artifact must reject."""

    with tempfile.TemporaryDirectory(prefix="bp-decl-integrity-gap2-") as tmp:
        root = Path(tmp) / "buildings" / "gap2-probe"
        _write_json(root / Path(*BUILDING_MAP_REL), _probe_building_map())
        # Persist only 3 of the 4 chain artifacts (drop link-launch-policy.json).
        for artifact in DECLARATION_CHAIN_ARTIFACTS[:-1]:
            _write_json(root / Path(*artifact), {"kind": "probe_provenance"})
        violations = validate_building_root(root, label="gap2-probe")
        rejected = any("link-launch-policy.json" in violation for violation in violations)
    return {
        "probe_ref": "building-declaration-integrity-probe:gap2_declaration_chain_artifacts",
        "rejected": rejected,
        "violations": violations,
        "proof_limits": ["negative probe support evidence only"],
    }


def gap3_provenance_returned_acceptance_probe() -> Mapping[str, Any]:
    """FIRE gap 3: a returned fact with no declared-binding reference must reject."""

    with tempfile.TemporaryDirectory(prefix="bp-decl-integrity-gap3-") as tmp:
        root = Path(tmp) / "buildings" / "gap3-probe"
        _write_json(root / Path(*BUILDING_MAP_REL), _probe_building_map())
        _write_full_chain(root)
        # Violating: returned fact answers an UNDECLARED Agent/Brick binding
        # (object_ref not in agent_bindings, received_work tail not declared).
        _write_json(
            root / Path(*RETURNED_CLAIMS_REL),
            _probe_returned_claims(
                object_ref="agent-object:undeclared-ghost",
                received_work="brick-work:99:undeclared-step",
            ),
        )
        violations = validate_building_root(root, label="gap3-probe")
        rejected = any("declared" in violation for violation in violations)
    return {
        "probe_ref": "building-declaration-integrity-probe:gap3_provenance_returned_acceptance",
        "rejected": rejected,
        "violations": violations,
        "proof_limits": ["negative probe support evidence only"],
    }


def gap4_declared_plan_purity_probe() -> Mapping[str, Any]:
    """FIRE gap 4: a declared_plan_copy carrying runtime walker state must reject."""

    with tempfile.TemporaryDirectory(prefix="bp-decl-integrity-gap4-") as tmp:
        root = Path(tmp) / "buildings" / "gap4-probe"
        _write_json(root / Path(*BUILDING_MAP_REL), _probe_building_map())
        _write_full_chain(root)
        # Violating: the declared-building-plan birth certificate's
        # declared_plan_copy carries RUNTIME walker state (dynamic_walker_evidence
        # + a top-level node_reroute_budgets) that belongs in the
        # evidence-manifest plan_snapshot, not the declared launch declaration.
        _write_json(
            root / Path(*DECLARED_BUILDING_PLAN_REL),
            {
                "kind": "declared_building_plan_provenance",
                "building_id": "gap4-probe",
                "plan_ref": "building-plan:gap4-probe",
                "plan_hash": "probe",
                "plan_hash_algorithm": "sha256",
                "declared_plan_copy": {
                    "building_id": "gap4-probe",
                    "plan_ref": "building-plan:gap4-probe",
                    "steps": [],
                    "dynamic_walker_evidence": {
                        "kind": "dynamic_walker_evidence",
                        "walker_mode": "dynamic",
                        "reroute_adoption_records": [],
                        "node_reroute_budgets": {"brick-probe": 1},
                        "held": False,
                    },
                    "node_reroute_budgets": {"brick-probe": 1},
                },
            },
        )
        violations = validate_building_root(root, label="gap4-probe")
        rejected = any("runtime walker key" in violation for violation in violations)
    return {
        "probe_ref": "building-declaration-integrity-probe:gap4_declared_plan_purity",
        "rejected": rejected,
        "violations": violations,
        "proof_limits": ["negative probe support evidence only"],
    }


def declaration_integrity_negative_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations that each gap's violating case is rejected."""

    return (
        gap1_composition_mode_authenticity_probe(),
        gap2_declaration_chain_artifact_probe(),
        gap3_provenance_returned_acceptance_probe(),
        gap4_declared_plan_purity_probe(),
    )


def run_negative_probes() -> list[str]:
    """Run the three FIRE probes; return the probe_refs that were NOT rejected."""

    not_rejected: list[str] = []
    for observation in declaration_integrity_negative_probe_observations():
        if observation.get("rejected") is not True:
            not_rejected.append(str(observation.get("probe_ref") or "<missing-probe-ref>"))
    return not_rejected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check Building declaration-chain authenticity (composition-mode, "
            "declaration-chain artifacts, provenance<->returned acceptance bar). "
            "Support evidence only."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    not_rejected = run_negative_probes()
    if not_rejected:
        print(
            "building declaration integrity rejected: anti-tautological negative "
            "probe(s) were not rejected:",
            file=sys.stderr,
        )
        for probe_ref in not_rejected:
            print(f"- {probe_ref}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    repo = Path(args.repo).resolve() if args.repo else Path(".").resolve()
    try:
        violations = check_repo(repo)
    except OSError as exc:
        print(f"building declaration integrity rejected: {exc}", file=sys.stderr)
        return 1

    if violations:
        print("building declaration integrity rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    roots = collect_building_roots(repo)
    probe_count = len(declaration_integrity_negative_probe_observations())
    print(
        "building declaration integrity passed: "
        f"{probe_count} negative probe(s) rejected; {len(roots)} building root(s) "
        "inspected for composition-mode authenticity, declaration-chain artifacts, "
        "provenance-returned acceptance, and declared-plan purity."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
