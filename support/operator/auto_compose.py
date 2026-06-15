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
    "      * each node: a UNIQUE \"node_id\", a \"step_template_ref\" that "
    "RESOLVES in the board's brick step-template catalog, the matching brick "
    "fields (\"brick_instance_ref\", \"brick_work_ref\", \"work_statement\", "
    "\"comparison_rule\", \"required_return_shape\"). Pick the brick kind + its "
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
    "route target outside the edges. Propose only; you do not run the building."
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
) -> Mapping[str, Any]:
    """Board + task -> design AI -> VALIDATED graph PROPOSAL (anti-lazy).

    PROPOSES only. Returns the validated proposal mapping; RAISES
    ``AutoComposeError`` on a malformed envelope, a graph that breaks the
    compose_building contract, or an unmapped requirement (anti-lazy). Writes
    nothing to the live tree.
    """

    repo = (
        Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    )
    task_text = _clean_task_statement(task_statement)
    invoke = ai_invoke if ai_invoke is not None else _default_ai_invoke

    # 1. Build the prompt from the board + the task + the output contract.
    board = render_building_board(repo_root=repo)
    prompt = build_design_prompt(task_text, board, output_contract=output_contract)

    # 2. Invoke the (injectable) design AI.
    output_text = invoke(prompt)
    if not isinstance(output_text, str):
        raise AutoComposeError("ai_invoke must return text (str)")

    # 3. Parse one JSON object + whitelist the envelope (mirror the adapter
    #    return idiom). The forbidden-key reject runs over the FREEFORM envelope
    #    fields ONLY -- NOT the graph (its movement/target are the Link contract).
    envelope = _structured_proposal_payload(output_text)
    if envelope is None:
        raise AutoComposeError(
            "design AI did not return a single JSON object proposal"
        )
    requirements, graph, requirement_node_map, preset_delta = _whitelist_envelope(
        envelope
    )

    # 4. VALIDATE the graph against the REAL compose_building contract. This is
    #    the authoritative node/edge/group validator (it raises CompositionError
    #    on any break). compose_building is pure in-memory; it writes nothing.
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    groups = graph.get("groups", [])
    _require_list("graph.nodes", nodes)
    _require_list("graph.edges", edges)
    _require_list("graph.groups", groups)
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

    # 6. Return the VALIDATED proposal. PROPOSES only -- no run, no commit.
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
