"""Read-only product menus for Building Call authoring.

GOAL ⑤d: this module gives the future order-authoring Brick/Agent a small,
provider-neutral vocabulary for drafting a Building call request. It is a menu
surface only: it does not select a preset, lower a request, launch a Building,
choose Link disposition, or judge the work.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


MENU_SCHEMA_VERSION = "building-call-menus-v1"

ORDER_AUTHORING_SEQUENCE_V1: tuple[dict[str, Any], ...] = (
    {
        "step_ref": "STEP1_SCOPE",
        "label": "업무 파악",
        "authoring_rule": "Extract scope, source facts, allowed paths, forbidden paths, and missing fields first.",
        "must_not_decide_yet": ("structure", "per_brick_intensity", "agent_strength"),
    },
    {
        "step_ref": "STEP2_BUILDING_INTENSITY",
        "label": "building 전체 과중과 라우팅",
        "authoring_rule": "Classify the whole request as easy, normal, complex, or critical before drawing nodes.",
        "must_not_decide_yet": ("per_brick_intensity", "agent_strength"),
    },
    {
        "step_ref": "STEP3_STRUCTURE",
        "label": "구조 그리기",
        "authoring_rule": (
            "Draft Brick nodes and Link-shaped edges using role/capability needs only; "
            "optional structure_plan_draft stays nested in structure_draft and may use "
            "nodes/edges/coo_gate_edge/fan_out_groups/fan_in_groups/reroute_budgets/terminal. "
            "fan_out_groups require a coo_gate_edge with state held_for_coo_review before lowering."
        ),
        "must_not_decide_yet": ("concrete_agent", "agent_strength"),
    },
    {
        "step_ref": "STEP4_PER_BRICK_INTENSITY",
        "label": "각 Brick 과중",
        "authoring_rule": "Assign easy, normal, complex, or critical to each drafted Brick node.",
        "must_not_decide_yet": ("concrete_agent",),
    },
    {
        "step_ref": "STEP5_AGENT_CANDIDATES",
        "label": "Agent 후보와 수준",
        "authoring_rule": "Place provider-neutral agent role and strength candidates only in the Agent column.",
        "must_not_decide_yet": (),
    },
)

BRICK_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "brick-menu:planning",
        "product_role": "planning",
        "brick_kind": "plan",
        "summary": "Bound objective, scope, constraints, and next work boundary without implementation.",
        "write_need": False,
    },
    {
        "menu_ref": "brick-menu:architecture",
        "product_role": "architecture",
        "brick_kind": "design",
        "summary": "Shape architecture, invariants, edge cases, and verifier plan without source mutation.",
        "write_need": False,
    },
    {
        "menu_ref": "brick-menu:deep_architecture",
        "product_role": "deep_architecture",
        "brick_kind": "deep-design",
        "summary": "Close detailed design decisions and hand a transcription-narrow plan to implementation.",
        "write_need": False,
    },
    {
        "menu_ref": "brick-menu:implementation",
        "product_role": "implementation",
        "brick_kind": "work",
        "summary": "Implement the declared work inside the Brick write scope.",
        "write_need": True,
    },
    {
        "menu_ref": "brick-menu:code_qa",
        "product_role": "code_qa",
        "brick_kind": "code-attack-qa",
        "summary": "Probe implementation, regressions, and negative paths in a disposable work area.",
        "write_need": True,
    },
    {
        "menu_ref": "brick-menu:boundary_qa",
        "product_role": "boundary_qa",
        "brick_kind": "axis-attack-qa",
        "summary": "Probe Brick, Agent, Link, support, projection, and evidence-boundary leakage.",
        "write_need": True,
    },
    {
        "menu_ref": "brick-menu:evidence_qa",
        "product_role": "evidence_qa",
        "brick_kind": "evidence-integrity",
        "summary": "Probe persisted evidence roots, proof limits, and checker-overclaim risk.",
        "write_need": True,
    },
    {
        "menu_ref": "brick-menu:read_review",
        "product_role": "read_review",
        "brick_kind": "review",
        "summary": "Read-only comparison of the prior Brick output against declared work and return shape.",
        "write_need": False,
    },
    {
        "menu_ref": "brick-menu:boundary_inspect",
        "product_role": "boundary_inspect",
        "brick_kind": "inspect",
        "summary": "Read-only inspection of axis boundaries, structure, evidence, and policy drift.",
        "write_need": False,
    },
    {
        "menu_ref": "brick-menu:closure",
        "product_role": "closure",
        "brick_kind": "closure",
        "summary": "Synthesize observed evidence, narrowly proven scope, remaining delta, and next candidates.",
        "write_need": False,
    },
)

AGENT_ROLE_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "agent-role:planner",
        "product_role": "planner",
        "role_need": "leader",
        "write_need": False,
        "summary": "Plans scope and boundaries; use after STEP1 scope is known.",
    },
    {
        "menu_ref": "agent-role:architect",
        "product_role": "architect",
        "role_need": "leader",
        "write_need": False,
        "summary": "Designs structure and invariants; use after STEP2 routing is known.",
    },
    {
        "menu_ref": "agent-role:builder",
        "product_role": "builder",
        "role_need": "worker",
        "write_need": True,
        "summary": "Implements declared source or document work inside the Brick write scope.",
    },
    {
        "menu_ref": "agent-role:code_qa",
        "product_role": "code_qa",
        "role_need": "reviewer",
        "write_need": True,
        "summary": "Runs disposable negative probes and regression checks.",
    },
    {
        "menu_ref": "agent-role:boundary_qa",
        "product_role": "boundary_qa",
        "role_need": "reviewer",
        "write_need": True,
        "summary": "Attacks axis and support-authority leakage.",
    },
    {
        "menu_ref": "agent-role:evidence_qa",
        "product_role": "evidence_qa",
        "role_need": "reviewer",
        "write_need": True,
        "summary": "Checks evidence-root and proof-limit integrity.",
    },
    {
        "menu_ref": "agent-role:closure",
        "product_role": "closure",
        "role_need": "leader",
        "write_need": False,
        "summary": "Synthesizes closure evidence and remaining delta without judging outcome.",
    },
)

WORK_INTENSITY_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "work-intensity:easy",
        "label": "easy",
        "entry_condition": "Single clear task, known paths, one to three files expected, obvious proof, simple rollback.",
        "routing_boundary": "May request direct quick_check or quick_fix only after admission and fast confirm.",
    },
    {
        "menu_ref": "work-intensity:normal",
        "label": "normal",
        "entry_condition": "Clear task but needs structure, multiple surfaces, or non-trivial verification.",
        "routing_boundary": "Use order_authoring draft.",
    },
    {
        "menu_ref": "work-intensity:complex",
        "label": "complex",
        "entry_condition": "Cross-axis, multi-lane, checker, recovery, materialization, or architecture choices are involved.",
        "routing_boundary": "Use order_authoring draft with explicit review gate.",
    },
    {
        "menu_ref": "work-intensity:critical",
        "label": "critical",
        "entry_condition": "Constitution, security, credential, migration, walker, route, AgentFact, or human-gate concern.",
        "routing_boundary": "Use human_gate_first before launch planning.",
    },
)

AGENT_STRENGTH_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "agent-strength:cheap",
        "label": "cheap",
        "use_when": "Small mechanical checks, formatting, or bounded read-only summaries.",
        "casting_rule": "Provider-neutral; do not name adapter or model here.",
    },
    {
        "menu_ref": "agent-strength:default",
        "label": "default",
        "use_when": "Ordinary implementation or review with known scope.",
        "casting_rule": "Provider-neutral; concrete casting belongs to later Agent selection provenance.",
    },
    {
        "menu_ref": "agent-strength:deep",
        "label": "deep",
        "use_when": "Architecture, difficult debugging, multi-file design, or adversarial review.",
        "casting_rule": "Provider-neutral; concrete casting belongs to later Agent selection provenance.",
    },
    {
        "menu_ref": "agent-strength:critical",
        "label": "critical",
        "use_when": "High-impact protocol, security, migration, or human-gated reasoning.",
        "casting_rule": "Provider-neutral; requires explicit gate handling before execution.",
    },
)

GRAPH_MOTIF_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "graph-motif:linear",
        "label": "linear",
        "shape": "one lane, ordered steps",
        "use_when": "The task has one obvious road and no sibling verification lanes.",
    },
    {
        "menu_ref": "graph-motif:plan_work_qa_close",
        "label": "plan-work-qa-close",
        "shape": "plan/design, implementation, verification, closure",
        "use_when": "The common product-feature or protocol-change road fits without custom graph design.",
    },
    {
        "menu_ref": "graph-motif:fan_out_review",
        "label": "fan-out-review",
        "shape": "one work product, multiple independent review lenses, fan-in synthesis",
        "use_when": "Review lanes must remain independent before closure synthesis.",
    },
    {
        "menu_ref": "graph-motif:parallel_dev",
        "label": "parallel-dev",
        "shape": "multiple disjoint implementation branches with a later integration/check lane",
        "use_when": "Write scopes are disjoint and the integration boundary is declared up front.",
    },
    {
        "menu_ref": "graph-motif:human_gate_cut",
        "label": "human-gate-cut",
        "shape": "draft or evidence stops before confirmed launch materialization",
        "use_when": "The next decision belongs to Smith or COO review before execution.",
    },
    {
        "menu_ref": "graph-motif:recovery_tail",
        "label": "recovery-tail",
        "shape": "repair evidence, replay scope, verification, closure",
        "use_when": "A prior boundary must be repaired and replay evidence must be carried forward.",
    },
)

ROUTING_MODE_MENU_V1: tuple[dict[str, Any], ...] = (
    {
        "menu_ref": "routing-mode:direct_quick_check",
        "label": "direct_quick_check",
        "allowed_only_if": "easy intensity is proven, admission passes, and fast confirm is recorded.",
        "launch_authority": "none; this menu does not launch",
    },
    {
        "menu_ref": "routing-mode:direct_quick_fix",
        "label": "direct_quick_fix",
        "allowed_only_if": "easy intensity is proven, admission passes, and fast confirm is recorded.",
        "launch_authority": "none; this menu does not launch",
    },
    {
        "menu_ref": "routing-mode:order_authoring",
        "label": "order_authoring",
        "allowed_only_if": "normal or complex intensity, or any uncertainty about direct eligibility.",
        "launch_authority": "draft only until confirmed by review gate",
    },
    {
        "menu_ref": "routing-mode:human_gate_first",
        "label": "human_gate_first",
        "allowed_only_if": "critical concern or unresolved authority/admission question.",
        "launch_authority": "none; human/COO decision is required first",
    },
)

EXPOSURE_POLICY_V1: tuple[str, ...] = (
    "Expose product roles, intensity, strength, graph motifs, and routing modes only.",
    "Do not expose provider casting fields in Brick menu rows.",
    "Do not expose raw preset identifiers as a product selection menu.",
    "Do not expose Agent Object internals in product menus.",
    "Do not expose route or walker integration details in the Building Call menu.",
)

_MENU_BY_SECTION: Mapping[str, tuple[dict[str, Any], ...]] = {
    "authoring_sequence": ORDER_AUTHORING_SEQUENCE_V1,
    "brick_menu": BRICK_MENU_V1,
    "agent_role_menu": AGENT_ROLE_MENU_V1,
    "work_intensity_menu": WORK_INTENSITY_MENU_V1,
    "agent_strength_menu": AGENT_STRENGTH_MENU_V1,
    "graph_motif_menu": GRAPH_MOTIF_MENU_V1,
    "routing_mode_menu": ROUTING_MODE_MENU_V1,
}


def render_building_call_menus() -> dict[str, Any]:
    """Return the read-only Building Call authoring menu packet."""

    return {
        "kind": MENU_SCHEMA_VERSION,
        "source": "brick_protocol/support/operator/building_call_menus.py",
        "sections": {key: _copy_rows(rows) for key, rows in _MENU_BY_SECTION.items()},
        "sequence_rule": "STEP1_SCOPE -> STEP2_BUILDING_INTENSITY -> STEP3_STRUCTURE -> STEP4_PER_BRICK_INTENSITY -> STEP5_AGENT_CANDIDATES",
        "exposure_policy": list(EXPOSURE_POLICY_V1),
        "proof_limits": [
            "support product menu only",
            "read-only",
            "not source truth",
            "not launch authorization",
            "not outcome judgment",
            "not route integration authority",
        ],
        "not_proven": [
            "semantic fitness of a future authored request",
            "future authoring module behavior",
            "future lowering behavior",
            "future Building execution behavior",
        ],
    }


def render_building_call_menus_json() -> str:
    """Return deterministic JSON for the Building Call authoring menu packet."""

    return json.dumps(render_building_call_menus(), ensure_ascii=False, sort_keys=True)


def get_building_call_menu_section(section: str) -> list[dict[str, Any]]:
    """Return one menu section by stable section key."""

    try:
        rows = _MENU_BY_SECTION[section]
    except KeyError as exc:
        known = ", ".join(sorted(_MENU_BY_SECTION))
        raise KeyError(f"unknown Building Call menu section {section!r}; known: {known}") from exc
    return _copy_rows(rows)


def _copy_rows(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


__all__ = [
    "MENU_SCHEMA_VERSION",
    "ORDER_AUTHORING_SEQUENCE_V1",
    "BRICK_MENU_V1",
    "AGENT_ROLE_MENU_V1",
    "WORK_INTENSITY_MENU_V1",
    "AGENT_STRENGTH_MENU_V1",
    "GRAPH_MOTIF_MENU_V1",
    "ROUTING_MODE_MENU_V1",
    "EXPOSURE_POLICY_V1",
    "render_building_call_menus",
    "render_building_call_menus_json",
    "get_building_call_menu_section",
]
