#!/usr/bin/env python3
"""Fail loud when a WRITE/QA node depends on an upstream step but no carry delivers it.

F2 FAKE-GREEN GUARD (brick-to-brick CARRY binds to the brick contract): a chain
edge ``upstream -> downstream`` is a Link MOVEMENT edge (run order), not a data
carry. A downstream node that ACTS ON the upstream artifact -- a writer/QA node
(``write_need = True`` in its step template: ``work`` + the QA kinds) -- must
RECEIVE the upstream step-output, or it works blind: it sees only the original
task, does nothing meaningful, and the walk greens anyway (exactly how F2 failed
-- the work node changed 0 files yet the build greened).

The DEPENDENCY is satisfied when, for every incoming forward edge into a
write/QA node, EITHER
  * the node DECLARES a step-output ``source_fact`` carrying that upstream node's
    output (``work/step-outputs/<upstream>-attempt-N/step-output.json`` form,
    which the walker matches and ``_adapter_source_fact_bodies`` delivers), OR
  * the node is a FAN-IN convergence target -- the walker auto-carries every
    fan-in source's step-output to its convergence target
    (``fan_in_sources_by_target``), so no declared source_fact is required.
Otherwise the dependency is UNMET and the node fails RED here, instead of
silently greening at run time.

EXEMPT (no false-RED): read-only / inspect / review / design / plan / closure
nodes (``write_need = False``) legitimately depend only on the repo, so a missing
upstream carry is not a fault for them.

This guard runs IN-PROCESS over the real EASY-tier ``assemble()`` composition the
operator actually builds with (not a disk scan of hand-authored fixtures, which
legitimately deliver carry via fan-in/reroute packets in other ref forms and
would false-RED). It asserts:
  (1) POSITIVE: a chained design->work->qa graph upholds the invariant (every
      write/QA node receives its upstream carry), and
  (2) MUTATION-RED: stripping the auto-declared carry from a write node makes the
      same invariant REJECT it -- so the guard is not vacuously green.

This checker is support evidence only. It does NOT call providers, run a CLI,
choose Movement, judge source truth, judge success or quality, or classify
Building outcomes.
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

PROOF_LIMIT = (
    "proof limit: chained-carry dependency guard support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or that the carried body is semantically "
    "sufficient -- only that every writer/QA node with an upstream forward edge "
    "either declares a step-output carry for that upstream or is a fan-in "
    "convergence target the walker auto-carries (the F2 fake-green regression pin)."
)


class ChainedCarryDependencyError(ValueError):
    """Raised when a write/QA node depends on an upstream step with no carry."""


def _is_step_output_carry(source_fact: str, upstream_node_id: str) -> bool:
    """True when ``source_fact`` is the step-output manifest carry for ``upstream``.

    Uses the SAME generator the walker labels completed step-outputs with, so the
    declared carry is checked against exactly what the run-time matcher consumes.
    The attempt index is not pinned (forward flow is attempt-1, but a reroute may
    raise it); a carry counts as long as it names this upstream's step-output dir.
    """

    from brick_protocol.support.recording.step_outputs import _step_output_dir_ref

    text = str(source_fact).replace("\\", "/").strip()
    dir_prefix = _step_output_dir_ref(upstream_node_id, 1)
    # strip the trailing "-attempt-1" so any attempt index matches this upstream
    dir_stem = dir_prefix.rsplit("-attempt-", 1)[0]
    return text.startswith(dir_stem + "-attempt-") and text.endswith("/step-output.json")


def _node_source_facts(node: Mapping[str, object]) -> list[str]:
    raw = node.get("source_facts")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _write_need_by_template(repo: Path) -> Mapping[str, bool]:
    from brick_protocol.support.operator.plan_rendering import _load_shape_registry

    registry = _load_shape_registry(repo)
    step_templates = registry.get("step_templates", {})
    out: dict[str, bool] = {}
    if isinstance(step_templates, Mapping):
        for ref, row in step_templates.items():
            if isinstance(row, Mapping):
                out[str(ref)] = bool(row.get("write_need"))
    return out


def assert_carry_invariant(
    nodes: Sequence[Mapping[str, object]],
    edges: Sequence[Mapping[str, object]],
    *,
    write_need_by_template: Mapping[str, bool],
    fan_in_target_ids: frozenset[str],
    label: str,
) -> list[str]:
    """Every write/QA node with an upstream forward edge must receive a carry.

    Returns the list of node ids that legitimately received an upstream carry
    (proof the invariant is non-vacuous); raises ChainedCarryDependencyError on
    the first write/QA node whose upstream dependency is unmet.
    """

    nodes_by_id = {str(node.get("node_id", "")).strip(): node for node in nodes}
    incoming: dict[str, list[str]] = {}
    for edge in edges:
        if str(edge.get("movement", "forward")).strip() != "forward":
            continue
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if not source or target not in nodes_by_id:
            continue
        incoming.setdefault(target, []).append(source)

    carried_nodes: list[str] = []
    for node_id, node in nodes_by_id.items():
        template_ref = str(node.get("step_template_ref", "")).strip()
        if not write_need_by_template.get(template_ref, False):
            continue  # read-only / inspect / review / design / plan / closure -> EXEMPT
        upstreams = incoming.get(node_id, [])
        if not upstreams:
            continue  # a write node with no upstream depends only on the task/repo
        if node_id in fan_in_target_ids:
            carried_nodes.append(node_id)
            continue  # walker auto-carries every fan-in source to its convergence target
        declared = _node_source_facts(node)
        for upstream_id in upstreams:
            if not any(_is_step_output_carry(sf, upstream_id) for sf in declared):
                raise ChainedCarryDependencyError(
                    f"{label}: write/QA node {node_id!r} ({template_ref}) has a "
                    f"forward edge from upstream {upstream_id!r} but declares NO "
                    "step-output source_fact carrying that upstream's output -- it "
                    "would run blind (see only the task) and the build would green "
                    "with no real work (the F2 fake-green failure). Declare the "
                    f"carry: work/step-outputs/{upstream_id}-attempt-1/step-output.json"
                )
        carried_nodes.append(node_id)
    return carried_nodes


def _assemble_design_work_qa(repo: Path):
    """The real EASY-tier composition: design -> work -> code-attack-qa."""

    from brick_protocol.support.operator.assembly import build, assemble, Authority

    graph = build(
        [
            ["design", "Produce a bounded reading-scope map for the repair.",
             {"returns": "reading_scope_map, design_summary"}],
            ["work", "Implement the change the upstream design describes.", {"write": True}],
            ["code-attack-qa", "Adversarially attack the upstream work output.",
             {"adapter": "codex-local", "model": "gpt-5-codex"}],
        ]
    )
    composed = assemble(
        graph,
        declared_by="chained-carry-guard",
        authority=Authority.COO,
        task="Guard the chained brick-to-brick carry.",
        building_id="chained-carry-guard-fixture",
        adapter="codex-local",
        model="gpt-5-codex",
        repo_root=repo,
    )
    return list(composed.nodes), list(composed.edges)


def check(repo: Path) -> list[str]:
    write_need_by_template = _write_need_by_template(repo)
    if not any(write_need_by_template.values()):
        raise ChainedCarryDependencyError(
            "no write-needing step templates found; the registry shape changed "
            "(re-pin this guard deliberately)"
        )

    nodes, edges = _assemble_design_work_qa(repo)
    fan_in_target_ids: frozenset[str] = frozenset()  # the fixture is a pure chain

    # (1) POSITIVE: the real composition upholds the invariant.
    carried = assert_carry_invariant(
        nodes,
        edges,
        write_need_by_template=write_need_by_template,
        fan_in_target_ids=fan_in_target_ids,
        label="design->work->qa fixture",
    )
    if not carried:
        raise ChainedCarryDependencyError(
            "invariant vacuous: the fixture produced no write/QA node with an "
            "upstream carry to check (composition shape changed; re-pin)"
        )

    # (2) MUTATION-RED: strip the auto-declared carry from a write node and
    #     confirm the SAME invariant rejects it.
    mutated_nodes = copy.deepcopy(nodes)
    victim_id = ""
    for node in mutated_nodes:
        template_ref = str(node.get("step_template_ref", "")).strip()
        if write_need_by_template.get(template_ref, False) and node.get("source_facts"):
            node["source_facts"] = []
            victim_id = str(node.get("node_id", "")).strip()
            break
    if not victim_id:
        raise ChainedCarryDependencyError(
            "mutation RED setup failed: no write/QA node carried a source_fact to strip"
        )
    try:
        assert_carry_invariant(
            mutated_nodes,
            edges,
            write_need_by_template=write_need_by_template,
            fan_in_target_ids=fan_in_target_ids,
            label="design->work->qa fixture (carry stripped)",
        )
    except ChainedCarryDependencyError:
        mutation_line = (
            f"mutation RED observed: stripping the carry from write/QA node "
            f"{victim_id!r} is rejected by the dependency invariant."
        )
    else:
        raise ChainedCarryDependencyError(
            f"mutation RED failed: stripping the carry from {victim_id!r} was still "
            "accepted as green (the guard does not actually bite)"
        )

    return [
        "chained-carry dependency green: every write/QA node with an upstream "
        f"forward edge receives its carry ({sorted(carried)}).",
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: a write/QA node depending on an upstream "
            "step must receive a step-output carry (or be a fan-in target), so a "
            "chained build cannot fake-green with a downstream node that ran blind "
            "(the F2 fake-green regression pin)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except ChainedCarryDependencyError as exc:
        print("chained-carry dependency rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
