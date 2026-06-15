#!/usr/bin/env python3
"""H2b -- compose_building_from_task: design AI reads the board + task and
PROPOSES a VALIDATED graph (anti-lazy), for operator cross-verify + human
approval. It does NOT run / compose-commit the graph (that is H2a,
``run_composed_graph_intake``, post-approval and separate).

This is operator-level support mechanics. It owns NO axis and authors NO
Movement / success / quality / target. It:

  1. builds a deterministic prompt from ``render_building_board(repo)`` + the
     inline ``task_statement`` + a fixed OUTPUT-CONTRACT instruction block;
  2. invokes an INJECTABLE ``ai_invoke(prompt: str) -> str`` (the design AI). The
     default refuses honestly (Phase-1 has no public prompt->text adapter seam
     and wiring one would require modifying ``agent_adapter.py``, which this
     module is forbidden to touch); a checker FIRE / a real caller injects the
     callable, so the seam is deterministic and provider-agnostic;
  3. parses + whitelists the returned JSON envelope ``{requirements, graph,
     requirement_node_map, preset_delta}`` -- MIRRORING the agent_adapter return
     idiom (``_structured_return_payload`` one-object parse + the recursive
     forbidden-key reject ``_validate_returned_payload``). The forbidden-key scan
     runs over the FREEFORM envelope ONLY (requirements / requirement_node_map /
     preset_delta); the ``graph`` sub-object is a ``compose_building`` argument
     structure whose ``movement`` / ``target`` keys are the LEGITIMATE Link
     contract (and are in RETURNED_FORBIDDEN_KEYS), so it is validated against the
     compose_building contract instead -- never against the return-fact reject;
  4. VALIDATES the graph by handing nodes/edges/groups to the REAL
     ``compose_building`` (it raises ``CompositionError`` on any node/edge/gate
     contract break -- duplicate node_id, unresolved step_template_ref, missing
     work_statement, bad movement literal, a node with no outgoing edge, malformed
     fan-in group, ...). ``compose_building`` is pure in-memory; it writes nothing;
  5. enforces the ANTI-LAZY rule (NET-NEW): EVERY declared requirement must map,
     through ``requirement_node_map``, to a REAL node in the proposed graph. An
     unmapped requirement (or a map pointing at a non-existent node) RAISES; and
  6. RETURNS the validated proposal ``{requirements, graph, requirement_node_map,
     preset_delta, board_ref, composed_plan}``.

A proposal that fails ANY validation RAISES (anti-lazy is load-bearing). Nothing
is written to the live tree.
"""

from __future__ import annotations

import json
import re

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

from brick_protocol.agent.return_fact import RETURNED_FORBIDDEN_KEYS
from brick_protocol.support.connection.building_design_toolkit import (
    render_building_board,
)
from brick_protocol.support.operator.composition import (
    CompositionError,
    compose_building,
)

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]

# The structured envelope keys the design AI returns. NONE of these is in
# RETURNED_FORBIDDEN_KEYS, so the top-level envelope is admissible (the graph's
# inner movement/target keys are validated by compose_building, not the reject).
_ENVELOPE_KEYS: frozenset[str] = frozenset(
    {"requirements", "graph", "requirement_node_map", "preset_delta"}
)

AiInvoke = Callable[[str], str]

# The work-area write_scope a composed WRITE node is stamped with when the design
# AI omits one (fail-closed default). MIRRORS the C4 work-area constant the W1/
# brain FIRE drives (case_runners.py:2016): a broad allowed_paths (the step runs
# inside an ISOLATED work-area worktree, so the worktree boundary is the real
# protection) with .git forbidden. SUPPLYING this scope is the whole point of
# H3d -- it never weakens the observed-write invariant (plan_validation still
# requires requires_brick_write_scope + a non-empty write_scope + an observed-
# write adapter); it just stops the goal-composed write node landing EMPTY.
_WORK_AREA_WRITE_SCOPE: Mapping[str, Any] = {
    "allowed_paths": ["**"],
    "forbidden_paths": [".git/**"],
}


class AutoComposeError(ValueError):
    """Raised when the design-AI proposal fails an H2b validation gate.

    Carries the human-facing ``detail`` and, when the graph itself broke the
    compose_building contract, the underlying ``CompositionError`` problems so the
    operator cross-verify surface can render exactly which node/edge failed.
    """

    def __init__(self, detail: str, *, problems: Sequence[Any] = ()) -> None:
        self.detail = detail
        self.problems = tuple(problems)
        super().__init__(detail)


# ---------------------------------------------------------------------------
# OUTPUT-CONTRACT prompt text. The instruction block the design AI is handed,
# verbatim, alongside the board JSON + the task. It pins the JSON shape, the
# board-only node/agent rule, the forward/reroute movement literals, the
# anti-lazy requirement->node coverage rule, and the preset_delta convention.
# ---------------------------------------------------------------------------

OUTPUT_CONTRACT_INSTRUCTIONS = (
    "You are a BRICK building DESIGN assistant. You are handed THE BOARD (a "
    "read-only manifest of every Brick kind, Agent, Link movement/gate, chain "
    "preset, and building shape this repo admits) and a TASK STATEMENT. Propose a "
    "building GRAPH that delivers the task, drawn ONLY from the board.\n"
    "\n"
    "Return EXACTLY ONE JSON object and NOTHING else (no prose, no code fence is "
    "required but is tolerated). The object MUST have these four keys:\n"
    "  - \"requirements\": a list of the distinct work requirements you read out "
    "of the task statement (each a short string id or phrase).\n"
    "  - \"graph\": an object {\"nodes\": [...], \"edges\": [...], "
    "\"groups\": [...]} laid out EXACTLY as compose_building arguments:\n"
    "      * each node: a UNIQUE \"node_id\", a \"step_template_ref\" that is an "
    "EXACT, character-for-character copy of one of the step_template_ref strings "
    "present in the board's brick step-template catalog (do NOT invent, abbreviate, "
    "or reword it; copy a real board value verbatim), the matching brick fields "
    "(\"brick_instance_ref\", \"brick_work_ref\", \"work_statement\", "
    "\"comparison_rule\", \"required_return_shape\"). ALWAYS include "
    "\"required_return_shape\": copy the chosen brick's required_return_shape "
    "string from the board verbatim (never omit it). Pick the brick kind + its "
    "agent ONLY from the board.\n"
    "      * each edge: a \"source\" and \"target\" that each resolve to a "
    "declared node_id OR a \"building-boundary:\"-prefixed terminal, and a "
    "\"movement\" that is one of EXACTLY \"forward\" or \"reroute\". Every node "
    "must have at least one outgoing edge; the building must reach a "
    "\"building-boundary:\" close.\n"
    "      * each group (optional): a fan-in is {\"group_role\": \"fan_in\", "
    "\"member_refs\": [...]}.\n"
    "  - \"requirement_node_map\": an object mapping EVERY requirement (every "
    "entry in \"requirements\") to the node_id that satisfies it. EVERY "
    "requirement MUST appear here and MUST point at a real node in the graph. "
    "Leaving a requirement unmapped is a HARD failure.\n"
    "  - \"preset_delta\": if a board chain preset fits the task, base the graph "
    "on it and state here, as text or an object, WHAT you changed relative to that "
    "preset (and name the preset). If you composed the graph fresh, set this to "
    "the string \"fresh\".\n"
    "\n"
    "Do not invent brick kinds, agents, movements, or gates that are absent from "
    "the board. Do not author a Movement decision, a success/quality verdict, or a "
    "route target outside the edges. Propose only; you do not run the building.\n"
    "\n"
    "GRAPH SHAPE: prefer a LINEAR chain — give each node EXACTLY ONE outgoing edge, "
    "and the LAST node's edge targets a \"building-boundary:\"-prefixed close that "
    "ENDS IN \"-closed\" (e.g. \"building-boundary:done-closed\"); keep it to about "
    "3-5 nodes. If you DO fan a node "
    "out to more than one outgoing edge, that node MUST also carry a "
    "\"completion_edge_ref\" naming the edge_ref of its single forward-completion "
    "edge (support must not guess which edge completes the node).\n"
    "\n"
    "WRITE SCOPE (a node that WRITES files must say so): the board marks each brick "
    "row with \"requires_brick_write_scope\". For ANY node whose chosen board brick "
    "has \"requires_brick_write_scope\": true, the real brain that performs the step "
    "will ONLY be allowed to write files when the node carries a write_scope — "
    "otherwise it can do no real work. So for EVERY such node you MUST emit BOTH "
    "\"requires_brick_write_scope\": true AND a work-area "
    "\"write_scope\": {\"allowed_paths\": [\"**\"], \"forbidden_paths\": "
    "[\".git/**\"]} (the step runs inside an isolated work-area worktree, so a "
    "broad allowed_paths with .git forbidden is correct). For IMPLEMENTATION / "
    "code-writing steps pick the \"work\" brick (it is write-needing), NOT the "
    "\"development\" brick (which is assign-only and does NOT write). Read-only "
    "steps (review / inspect / closure / plan / design — bricks whose "
    "requires_brick_write_scope is false) emit NO write_scope and NO "
    "requires_brick_write_scope marker."
)


def build_design_prompt(
    task_statement: str,
    board: Mapping[str, Any],
    *,
    output_contract: str = OUTPUT_CONTRACT_INSTRUCTIONS,
) -> str:
    """Assemble the deterministic design prompt: contract + board JSON + task."""

    task_text = _clean_task_statement(task_statement)
    board_json = json.dumps(board, ensure_ascii=False, sort_keys=True)
    return (
        f"{output_contract}\n"
        "\n"
        "=== THE BOARD (read-only manifest; draw nodes/agents/movements/presets "
        "ONLY from here) ===\n"
        f"{board_json}\n"
        "\n"
        "=== TASK STATEMENT (build a graph that delivers this) ===\n"
        f"{task_text}\n"
        "\n"
        "Return ONE JSON object {requirements, graph, requirement_node_map, "
        "preset_delta} as specified above."
    )


def _default_ai_invoke(_prompt: str) -> str:
    """Honest default: Phase-1 has NO public prompt->text adapter seam.

    ``connect_agent_brain`` is node-shaped (it takes an AgentAdapterRequest and
    returns a structured return-fact, not raw text) and the gemini-api text
    helpers are private. Wiring a clean prompt->text invoke would require editing
    ``agent_adapter.py``, which this module is forbidden to touch. So the default
    REFUSES rather than fabricate a live call: a real caller (or a checker FIRE)
    injects ``ai_invoke``. This keeps the seam deterministic and provider-agnostic
    and never silently pretends a provider ran.
    """

    raise AutoComposeError(
        "compose_building_from_task requires an injected ai_invoke(prompt)->text: "
        "Phase-1 exposes no public prompt->text adapter seam (connect_agent_brain "
        "is node-shaped; the gemini-api text helpers are private) and wiring one "
        "would modify agent_adapter.py, which H2b may not touch. Inject a real "
        "design-AI callable to run live (H3 / dogfood), or a canned callable for a "
        "deterministic FIRE."
    )


def compose_building_from_task(
    task_statement: str,
    *,
    ai_invoke: AiInvoke | None = None,
    repo_root: str | Path | None = None,
    declared_by: str = "coo",
    output_contract: str = OUTPUT_CONTRACT_INSTRUCTIONS,
    selected_adapter_ref: str = "adapter:local",
    selected_model_ref: str = "model:default",
    max_attempts: int = 3,
) -> Mapping[str, Any]:
    """Board + task -> design AI -> VALIDATED graph PROPOSAL (anti-lazy).

    PROPOSES only. Returns the validated proposal mapping; RAISES
    ``AutoComposeError`` on a malformed envelope, a graph that breaks the
    compose_building contract, or an unmapped requirement (anti-lazy). Writes
    nothing to the live tree.

    RELIABILITY (bounded retry): the design AI is NON-DETERMINISTIC (it can emit
    a step_template_ref that does not resolve, omit required_return_shape, or
    return a malformed envelope). ``max_attempts`` (default 3) re-invokes
    ``ai_invoke`` up to N times; the FIRST attempt that validates is returned,
    and only the LAST attempt's error is raised if every attempt fails. Each
    retry appends the prior attempt's error to the prompt to nudge the AI. When
    attempt 1 validates this is single-attempt behavior (the loop returns at
    once) -- existing canned-valid callers are unchanged.
    """

    repo = (
        Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    )
    task_text = _clean_task_statement(task_statement)
    invoke = ai_invoke if ai_invoke is not None else _default_ai_invoke
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise AutoComposeError("max_attempts must be a positive integer")

    # 1. Build the base prompt from the board + the task + the output contract.
    #    The board render is deterministic, so it is computed once and reused;
    #    each retry only appends the prior error as a nudge.
    board = render_building_board(repo_root=repo)
    # The board's per-brick write-need flags drive the H3d fail-closed default
    # (a write-needing node that lands without a write_scope is stamped). Built
    # once from the same deterministic board the prompt is built from.
    write_need_by_ref = _board_write_need_by_template_ref(board)
    base_prompt = build_design_prompt(
        task_text, board, output_contract=output_contract
    )

    def _one_attempt(prompt: str) -> Mapping[str, Any]:
        # 2. Invoke the (injectable) design AI.
        output_text = invoke(prompt)
        if not isinstance(output_text, str):
            raise AutoComposeError("ai_invoke must return text (str)")

        # 3. Parse one JSON object + whitelist the envelope (mirror the adapter
        #    return idiom). The forbidden-key reject runs over the FREEFORM
        #    envelope fields ONLY -- NOT the graph (its movement/target are the
        #    Link contract).
        envelope = _structured_proposal_payload(output_text)
        if envelope is None:
            raise AutoComposeError(
                "design AI did not return a single JSON object proposal"
            )
        requirements, graph, requirement_node_map, preset_delta = (
            _whitelist_envelope(envelope)
        )

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        groups = graph.get("groups", [])
        _require_list("graph.nodes", nodes)
        _require_list("graph.edges", edges)
        _require_list("graph.groups", groups)

        # 3b. TERMINAL CLOSE DISCIPLINE: a building reaches frontier=complete only
        #     when the executed terminal link record's target is a
        #     ``building-boundary:`` ref ENDING in ``closed`` (frontier_observation
        #     _is_closed_boundary_ref). The design AI may emit a boundary target
        #     that is NOT closed (e.g. ``building-boundary:done``), which composes
        #     fine but lands at ``closure_pending``. NORMALIZE here, BEFORE
        #     validating/composing: any edge target that startswith
        #     ``building-boundary:`` and does NOT endwith ``closed`` gets
        #     ``-closed`` appended. A target that already ends in ``closed`` is
        #     left untouched (no-op for already-closed callers).
        edges = _normalize_terminal_boundaries(edges)

        # 3c. FAIL-CLOSED WRITE_SCOPE (H3d): a goal-composed node whose RESOLVED
        #     board brick is write-needing but that lands WITHOUT a non-empty
        #     write_scope is stamped with the work-area write_scope + marker, so a
        #     real write-capable brain can actually write. Read-only-brick nodes
        #     and nodes already carrying a non-empty write_scope are UNCHANGED. The
        #     write-need map is read from THE BOARD (render_building_board) only;
        #     compose_building remains the authority that REJECTS an unresolved
        #     brick ref. This SUPPLIES scope; it never weakens the observed-write
        #     invariant plan_validation enforces.
        nodes = _stamp_write_scope_fail_closed(nodes, write_need_by_ref)

        # 3d. BRAIN/WRITE MATCH (H3d): a node carrying a write_scope can only do
        #     real work with a write-capable execution brain (codex-local /
        #     claude-local). If the run adapter is read-only (e.g. adapter:local)
        #     yet a write node exists, FAIL EARLY with a friendly, actionable
        #     message — instead of compose_building's cryptic
        #     missing_adapter_write_capability, or a silent no-work link_paused
        #     (the read-only brain honestly does nothing, QA catches it, the
        #     building pauses). Read-only goals (no write node) are UNAFFECTED.
        from support.connection.agent_adapter import (  # noqa: PLC0415
            adapter_is_write_capable,
        )
        if not adapter_is_write_capable(selected_adapter_ref):
            _write_node_ids = [
                n.get("node_id")
                for n in nodes
                if (n.get("write_scope") or {}).get("allowed_paths")
                or (
                    isinstance(n.get("brick"), Mapping)
                    and (n["brick"].get("write_scope") or {}).get("allowed_paths")
                )
            ]
            if _write_node_ids:
                raise AutoComposeError(
                    "이 골은 코드/파일 작성이 필요해요 (write 노드 "
                    f"{len(_write_node_ids)}개). 지금 실행 두뇌(brain) "
                    f"'{selected_adapter_ref}' 는 읽기 전용이라 실제 작업을 할 수 "
                    "없어요. `--brain claude` 또는 `--brain codex` 로 다시 "
                    "실행하세요."
                )

        # 4. VALIDATE the graph against the REAL compose_building contract. This is
        #    the authoritative node/edge/group validator (it raises
        #    CompositionError on any break). compose_building is pure in-memory; it
        #    writes nothing.
        try:
            composed_plan = compose_building(
                nodes,
                edges,
                declared_by=declared_by,
                groups=groups,
                selected_adapter_ref=selected_adapter_ref,
                selected_model_ref=selected_model_ref,
                repo_root=repo,
            )
        except CompositionError as exc:
            raise AutoComposeError(
                f"proposed graph failed the compose_building contract: {exc}",
                problems=exc.problems,
            ) from exc

        # 5. ANTI-LAZY (NET-NEW): every requirement must map -> a real node.
        node_ids = _graph_node_ids(nodes)
        _enforce_requirement_coverage(requirements, requirement_node_map, node_ids)

        return _build_proposal(
            requirements=requirements,
            nodes=nodes,
            edges=edges,
            groups=groups,
            requirement_node_map=requirement_node_map,
            preset_delta=preset_delta,
            board=board,
            declared_by=declared_by,
            composed_plan=composed_plan,
        )

    # BOUNDED RETRY: return the FIRST valid proposal; raise the LAST error after
    # exhausting max_attempts. Each retry appends the prior error as a nudge.
    last_error: AutoComposeError | None = None
    for attempt in range(1, max_attempts + 1):
        prompt = base_prompt
        if last_error is not None:
            prompt = (
                f"{base_prompt}\n"
                "\n"
                "=== PRIOR ATTEMPT FAILED — FIX THIS AND RETURN A VALID PROPOSAL ===\n"
                f"Attempt {attempt - 1} of {max_attempts} was rejected with: "
                f"{last_error.detail}\n"
                "Return ONE corrected JSON object that resolves the error above."
            )
        try:
            return _one_attempt(prompt)
        except AutoComposeError as exc:
            last_error = exc
    # Exhausted: raise the last attempt's error (carrying its problems).
    assert last_error is not None  # max_attempts >= 1, so the loop ran at least once
    raise last_error


def _build_proposal(
    *,
    requirements: list[Any],
    nodes: Sequence[Any],
    edges: Sequence[Any],
    groups: Sequence[Any],
    requirement_node_map: Mapping[str, Any],
    preset_delta: Any,
    board: Mapping[str, Any],
    declared_by: str,
    composed_plan: Any,
) -> Mapping[str, Any]:
    """Assemble the validated-proposal return mapping. PROPOSES only."""

    return {
        "kind": "building-graph-proposal",
        "requirements": requirements,
        "graph": {"nodes": nodes, "edges": edges, "groups": groups},
        "requirement_node_map": requirement_node_map,
        "preset_delta": preset_delta,
        "board_ref": board.get("source", "brick/ + agent/ + link/"),
        "declared_by": declared_by,
        "composed_plan": composed_plan,
        "proof_limits": [
            "support proposal only -- not run, not committed, not approved",
            "graph validated vs compose_building contract + anti-lazy coverage only",
            "not source truth, not Movement authority, not success/quality judgment",
        ],
        "not_proven": [
            "semantic correctness of the proposed graph",
            "live design-AI behavior (a canned/injected ai_invoke was used here)",
        ],
    }


# ---------------------------------------------------------------------------
# Parse + whitelist (MIRROR of agent_adapter _structured_return_payload /
# _validate_returned_payload). One JSON object; recursive forbidden-key reject
# over the freeform envelope ONLY.
# ---------------------------------------------------------------------------


def _structured_proposal_payload(output_text: str) -> Mapping[str, Any] | None:
    """Parse ONE JSON object from the design-AI text (mirror of the adapter's
    ``_structured_return_payload``: bare object first, then any ```json fence)."""

    text = output_text.strip()
    parsed = _try_json_value(_strip_code_fence(text))
    if isinstance(parsed, Mapping):
        return parsed
    for match in re.finditer(r"(?s)```(?:json)?\s*(.*?)```", output_text):
        parsed = _try_json_value(match.group(1).strip())
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _whitelist_envelope(
    envelope: Mapping[str, Any],
) -> tuple[list[Any], Mapping[str, Any], Mapping[str, Any], Any]:
    """Whitelist the top-level envelope keys and recursively reject forbidden
    return keys over the FREEFORM fields. The ``graph`` sub-object is exempt from
    the forbidden-key reject (its movement/target are the legitimate Link
    contract) and is validated by compose_building instead.
    """

    unknown = [
        str(key) for key in envelope.keys() if _normalize(key) not in _ENVELOPE_KEYS
    ]
    if unknown:
        raise AutoComposeError(
            f"proposal envelope has unexpected key(s): {sorted(unknown)}; "
            f"allowed: {sorted(_ENVELOPE_KEYS)}"
        )

    graph = envelope.get("graph")
    if not isinstance(graph, Mapping):
        raise AutoComposeError("proposal.graph must be an object")

    requirements = envelope.get("requirements", [])
    requirement_node_map = envelope.get("requirement_node_map", {})
    preset_delta = envelope.get("preset_delta", "fresh")

    _require_list("proposal.requirements", requirements)
    if not isinstance(requirement_node_map, Mapping):
        raise AutoComposeError("proposal.requirement_node_map must be an object")

    # Forbidden-key reject over the freeform fields ONLY (NOT the graph). This is
    # the recursive reject mirrored from the adapter's _validate_returned_payload.
    _reject_forbidden_keys("proposal.requirements", requirements)
    _reject_forbidden_keys("proposal.requirement_node_map", requirement_node_map)
    _reject_forbidden_keys("proposal.preset_delta", preset_delta)

    return (
        list(requirements),
        dict(graph),
        dict(requirement_node_map),
        preset_delta,
    )


def _reject_forbidden_keys(label: str, value: Any) -> None:
    """Recursive forbidden-key reject (mirror of agent_adapter
    ``_validate_returned_payload``). Applied to the freeform envelope fields."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if _normalize(raw_key) in RETURNED_FORBIDDEN_KEYS:
                raise AutoComposeError(
                    f"{label} contains forbidden return key {raw_key!r}"
                )
            _reject_forbidden_keys(f"{label}.{raw_key}", child)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_forbidden_keys(f"{label}[{index}]", child)


# ---------------------------------------------------------------------------
# Anti-lazy requirement -> node coverage (NET-NEW).
# ---------------------------------------------------------------------------


def _enforce_requirement_coverage(
    requirements: Sequence[Any],
    requirement_node_map: Mapping[str, Any],
    node_ids: frozenset[str],
) -> None:
    """EVERY requirement must map, through requirement_node_map, to a REAL node.

    An unmapped requirement, a map value that is not a known node_id, or a map
    that names a requirement not in the requirements list all RAISE. Anti-lazy is
    load-bearing: a proposal that skips wiring a requirement to real work is
    rejected, not silently accepted.
    """

    requirement_keys = [_requirement_key(req) for req in requirements]
    if not requirement_keys:
        raise AutoComposeError(
            "anti-lazy: proposal declared no requirements (a real task has at "
            "least one requirement to satisfy)"
        )

    normalized_map = {
        _normalize(key): str(value) for key, value in requirement_node_map.items()
    }

    unmapped: list[str] = []
    dangling: list[str] = []
    for raw_req, key in zip(requirements, requirement_keys):
        mapped_node = normalized_map.get(_normalize(key))
        if not mapped_node:
            unmapped.append(_requirement_label(raw_req))
        elif mapped_node not in node_ids:
            dangling.append(f"{_requirement_label(raw_req)} -> {mapped_node!r}")

    if unmapped:
        raise AutoComposeError(
            "anti-lazy: requirement(s) not mapped to any node: "
            f"{unmapped} (every requirement MUST map to a real graph node)"
        )
    if dangling:
        raise AutoComposeError(
            "anti-lazy: requirement(s) mapped to a non-existent node: "
            f"{dangling} (the mapped node_id is not in the proposed graph)"
        )


def _graph_node_ids(nodes: Sequence[Any]) -> frozenset[str]:
    ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise AutoComposeError(f"graph.nodes[{index}] must be an object")
        node_id = str(node.get("node_id") or "").strip()
        if node_id:
            ids.add(node_id)
    return frozenset(ids)


def _is_closeable_boundary_target(target: str) -> bool:
    """A ``building-boundary:``-prefixed terminal target that does NOT already end
    in ``closed`` (so appending ``-closed`` makes it a complete-reaching close).

    Mirrors frontier_observation._is_closed_boundary_ref's prefix/suffix test:
    the prefix may be ``building-boundary:`` or ``building-boundary-``; ``closed``
    is matched case-insensitively. A target already ending in ``closed`` returns
    False (left untouched). The spec's normalize targets only ``building-boundary:``
    but we tolerate the ``-`` prefix too so we never mis-skip a real boundary.
    """

    normalized = target.strip().lower()
    is_boundary = normalized.startswith("building-boundary:") or normalized.startswith(
        "building-boundary-"
    )
    return is_boundary and not normalized.endswith("closed")


def _normalize_terminal_boundaries(edges: Sequence[Any]) -> list[Any]:
    """Append ``-closed`` to any edge ``target`` that is a building-boundary close
    NOT already ending in ``closed`` (so the executed terminal link reaches
    frontier=complete). Already-``closed`` targets are left byte-identical. Edges
    that are not Mappings, or whose target is not a building-boundary ref, are
    returned unchanged. Returns a NEW list of edges; never mutates the input.
    """

    normalized_edges: list[Any] = []
    for edge in edges:
        if isinstance(edge, Mapping):
            target = edge.get("target")
            if isinstance(target, str) and _is_closeable_boundary_target(target):
                new_edge = dict(edge)
                new_edge["target"] = f"{target.rstrip()}-closed"
                normalized_edges.append(new_edge)
                continue
        normalized_edges.append(edge)
    return normalized_edges


# ---------------------------------------------------------------------------
# H3d fail-closed write_scope default. A goal-composed node whose RESOLVED board
# brick is write-needing (requires_brick_write_scope=true) but that lands WITHOUT
# a non-empty write_scope is stamped with the work-area write_scope + the marker,
# so a real write-capable brain (claude / codex) can actually write. Read-only
# bricks and nodes already carrying a non-empty write_scope are LEFT UNCHANGED.
# This SUPPLIES write_scope; it never weakens the observed-write check.
# ---------------------------------------------------------------------------


def _board_write_need_by_template_ref(board: Mapping[str, Any]) -> dict[str, bool]:
    """Map each board brick's step_template_ref -> requires_brick_write_scope.

    The board (render_building_board) surfaces one ``bricks`` row per Brick kind
    carrying ``brick_kind`` + ``requires_brick_write_scope`` (building_design_
    toolkit.py:473-477). A node references its brick by ``step_template_ref`` in
    the ``building-step-template:<kind>`` form, whose suffix is exactly the board
    row's ``brick_kind``. We key the map on the FULL ``building-step-template:``
    ref the nodes carry (rebuilt from the row's kind). If a board row is missing
    ``brick_kind`` or its write-need flag, that is a board-projection defect: we
    RAISE rather than guess a node's write-need (fail-closed, per spec).
    """

    bricks = board.get("bricks")
    if not isinstance(bricks, Sequence):
        raise AutoComposeError(
            "board has no 'bricks' section to resolve node write-need from"
        )
    write_need: dict[str, bool] = {}
    for index, row in enumerate(bricks):
        if not isinstance(row, Mapping):
            raise AutoComposeError(f"board.bricks[{index}] is not an object")
        kind = str(row.get("brick_kind") or "").strip()
        if not kind:
            raise AutoComposeError(
                f"board.bricks[{index}] has no brick_kind; cannot resolve a "
                "node's brick write-need (board projection defect)"
            )
        if "requires_brick_write_scope" not in row:
            raise AutoComposeError(
                f"board.bricks[{index}] ({kind!r}) does not expose "
                "requires_brick_write_scope; cannot resolve write-need fail-closed"
            )
        write_need[f"building-step-template:{kind}"] = bool(
            row.get("requires_brick_write_scope")
        )
    return write_need


def _node_brick_view(node: Mapping[str, Any]) -> Mapping[str, Any]:
    """The mapping a node's brick fields live in: a nested ``brick`` object when
    present, else the node itself (MIRRORS composition._compose_brick_row:
    ``brick = raw_brick if isinstance(raw_brick, Mapping) else raw_node``)."""

    nested = node.get("brick")
    return nested if isinstance(nested, Mapping) else node


def _has_nonempty_write_scope(brick_view: Mapping[str, Any]) -> bool:
    """True iff the node already carries a write_scope with a NON-EMPTY
    allowed_paths (mirrors the plan_validation non-empty test: an empty/absent
    allowed_paths is NOT a real scope and must be stamped fail-closed)."""

    raw = brick_view.get("write_scope")
    if not isinstance(raw, Mapping):
        return False
    allowed = raw.get("allowed_paths")
    return isinstance(allowed, Sequence) and not isinstance(allowed, str) and bool(allowed)


def _stamp_write_scope_fail_closed(
    nodes: Sequence[Any],
    write_need_by_ref: Mapping[str, bool],
) -> list[Any]:
    """Return a NEW node list where each node whose resolved board brick is
    write-needing AND which lacks a non-empty write_scope is stamped with the
    work-area write_scope + requires_brick_write_scope marker. Read-only-brick
    nodes, and nodes already carrying a non-empty write_scope, are UNCHANGED.
    Never mutates the input nodes. A node whose step_template_ref is not a known
    board ref is left untouched (compose_building is the authority that REJECTS
    an unresolved ref; this default only SUPPLIES scope, never invents bricks)."""

    stamped: list[Any] = []
    for node in nodes:
        if not isinstance(node, Mapping):
            stamped.append(node)
            continue
        step_ref = str(node.get("step_template_ref") or "").strip()
        needs_write = write_need_by_ref.get(step_ref, False)
        brick_view = _node_brick_view(node)
        if not needs_write or _has_nonempty_write_scope(brick_view):
            stamped.append(node)
            continue
        # WRITE-needing brick + no non-empty write_scope -> stamp fail-closed.
        new_node = dict(node)
        nested = node.get("brick")
        if isinstance(nested, Mapping):
            new_brick = dict(nested)
            new_brick["write_scope"] = dict(_WORK_AREA_WRITE_SCOPE)
            new_brick["requires_brick_write_scope"] = True
            new_node["brick"] = new_brick
        else:
            new_node["write_scope"] = dict(_WORK_AREA_WRITE_SCOPE)
            new_node["requires_brick_write_scope"] = True
        stamped.append(new_node)
    return stamped


# ---------------------------------------------------------------------------
# Small text/JSON helpers (stdlib only; no new dependency).
# ---------------------------------------------------------------------------


def _clean_task_statement(task_statement: Any) -> str:
    if not isinstance(task_statement, str):
        raise AutoComposeError("task_statement must be text")
    cleaned = task_statement.strip()
    if not cleaned:
        raise AutoComposeError("task_statement must not be blank")
    return cleaned


def _requirement_key(requirement: Any) -> str:
    """The map key for a requirement entry: a bare string is its own key; an
    object carries an explicit id/ref/requirement field."""

    if isinstance(requirement, str):
        key = requirement.strip()
    elif isinstance(requirement, Mapping):
        key = str(
            requirement.get("id")
            or requirement.get("ref")
            or requirement.get("requirement")
            or requirement.get("name")
            or ""
        ).strip()
    else:
        key = ""
    if not key:
        raise AutoComposeError(
            f"requirement entry has no id/ref to map on: {requirement!r}"
        )
    return key


def _requirement_label(requirement: Any) -> str:
    try:
        return _requirement_key(requirement)
    except AutoComposeError:
        return repr(requirement)


def _require_list(label: str, value: Any) -> None:
    if not isinstance(value, (list, tuple)):
        raise AutoComposeError(f"{label} must be a list")


def _try_json_value(value: str) -> Any:
    text = value.strip()
    if not text or text[0] not in "[{":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "AiInvoke",
    "AutoComposeError",
    "OUTPUT_CONTRACT_INSTRUCTIONS",
    "build_design_prompt",
    "compose_building_from_task",
]
