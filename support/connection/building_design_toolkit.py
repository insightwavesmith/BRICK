"""Read-only support toolkit for Brick-owned Building design inputs.

The toolkit exposes task source, split shape catalog, and Human+AI design contract
templates as support context. It does not choose a shape, write Building Plans,
call providers, or own Brick / Agent / Link meaning.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.plan_rendering import (
    SPLIT_SHAPE_CATALOG_PATH,
    _agent_is_writer,
    _load_shape_registry,
    _load_yaml_mapping,
    _render_candidate_agents_for_need,
)
from brick_protocol.support.connection.agent_resources import (
    list_agent_object_refs,
    resolve_agent_object,
)
from brick_protocol.link.gate import (
    DECLARED_GATE_REFS,
    gate_required_return_fields,
)

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_RESOURCE_PATHS = {
    "task_source_template": Path("brick/templates/tasks/source-template.md"),
    "human_ai_design_contract": Path("brick/templates/building-design-contract.yaml"),
}
from brick_protocol.support.connection.secret_text import contains_raw_secret_text
_PROOF_LIMITS = (
    "support design context evidence only",
    "Brick meaning remains owned by brick/",
    "AI may propose candidates only",
    "caller / COO declaration is required for active shape",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_NOT_PROVEN = (
    "semantic fitness of future selected shapes",
    "automatic Building Plan authoring",
    "MCP client behavior",
    "provider behavior",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)
# The agent-candidate packet is the READ-ONLY informed surface beside the
# matcher's fail-closed >=2 ValueError. It MEASURES/RECORDS the candidate set and
# the MECHANICAL match reason ONLY; it picks nothing, ranks nothing, recommends
# nothing, judges no agent quality. The choice among >=2 candidates stays with
# the caller / COO (mirroring the address >=2 -> HOLD pattern).
_AGENT_CANDIDATE_MATCH_AUTHORITY = (
    "NEED<->CAPABILITY match owned by agent_resources.py (lane + writer policy)",
    "caller / COO declares the choice when candidates >= 2",
    "single candidate still auto-resolves via _resolve_agent_for_need (unchanged)",
)
_AGENT_CANDIDATE_PROOF_LIMITS = (
    "support matcher evidence only",
    "mechanical NEED<->CAPABILITY match reason only",
    "not a quality judgment of any agent",
    "not a recommendation",
    "not a ranking",
    "support does not pick among >= 2 candidates",
    "COO / author holds the decision when ambiguous",
    "not Movement authority",
)
_AGENT_CANDIDATE_NOT_PROVEN = (
    "which candidate the COO will choose",
    "semantic fitness of any candidate for the task",
    "success judgment",
    "quality judgment",
    "Movement authority",
)
_RETIRED_AGENT_CANDIDATE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
        "adapter:gemini-api",
    }
)
# The preset-ranking packet is the MOST axis-borderline read-only surface: it
# ORDERS chain presets by a MECHANICAL count of HUMAN-declared selection_hint
# tokens matched against each preset's own declared text (preset_ref + intent +
# selection_hint + catalog_scope). The ordering is relevance-by-token-overlap
# ONLY -- it is NOT a quality judgment, NOT a recommendation-to-use, NOT a pick.
# Support NEVER auto-selects a preset; the COO chooses + declares the active
# preset, and the materializer STILL hard-refuses a run with no/blank
# chain_preset_ref (composition.materialize_building_intent). This packet carries
# NO selected / chosen / recommended / best / use_this field by construction.
_PRESET_RANKING_BASIS = (
    "mechanical hint-match (not quality): rank = count of distinct human-declared "
    "selection_hint tokens matched against each preset's declared text "
    "(preset_ref + intent + selection_hint + catalog_scope), descending, with a "
    "deterministic tiebreak by chain_preset_ref"
)
_PRESET_RANKING_SELECTION_AUTHORITY = (
    "COO declares the active preset; the ranking never auto-applies",
    "the materializer still hard-refuses a run with no / blank chain_preset_ref",
    "support does not pick, recommend, or default a preset",
)
_PRESET_RANKING_PROOF_LIMITS = (
    "support ranking evidence only",
    "advisory ranking, non-binding",
    "mechanical hint-match relevance only",
    "not automatic preset selection",
    "not a quality judgment of any preset",
    "not a recommendation to use any preset",
    "COO declares the active preset",
    "the materializer still requires an explicit confirmed preset",
    "not Movement authority",
)
_PRESET_RANKING_NOT_PROVEN = (
    "which preset the COO will declare",
    "semantic fitness of any preset for the task",
    "success judgment",
    "quality judgment",
    "Movement authority",
)
# Token boundary for the mechanical hint match: split on any non-alphanumeric run
# so refs like "building-chain-preset:fast-fix" and prose both yield comparable
# lowercase tokens. Single-character tokens are dropped as noise.
_HINT_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# THE BOARD (H1): the single read-only manifest a design AI is handed to compose
# from. It UNIFIES the four already-machine-readable catalogs (Brick / Agent /
# Link / Preset, plus the Shape menu) into ONE projection. It READS the live
# catalogs and changes none of them. It is READ-ONLY in the same sense every
# other surface in this module is: it MEASURES/RECORDS the catalog rows but
# AUTHORS / DECIDES nothing -- it picks no shape, writes no Building Plan, names
# no Movement, and renders no success / quality judgment. The active selection
# stays a caller / COO declaration (selection_rule below), and the same
# proof_limits / not_proven envelope the design context carries rides along.
_BOARD_LINK_CATALOG_PATHS = {
    "movement": Path("link/movement.yaml"),
    "carry": Path("link/carry.yaml"),
    "transition": Path("link/transition.yaml"),
}
_BOARD_PROOF_LIMITS = (
    "support catalog projection evidence only",
    "the board unifies the four catalogs for reading; it changes none of them",
    "Brick / Agent / Link meaning stays owned by brick/ , agent/ , link/",
    "AI may propose a graph from the board; it does not select the active shape",
    "caller / COO declaration is required for the active shape / preset",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_BOARD_NOT_PROVEN = (
    "semantic fitness of any future composed graph",
    "automatic Building Plan authoring from the board",
    "which catalog rows a design AI will choose",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)


class BuildingDesignToolkitError(ValueError):
    """Raised when read-only design context cannot be rendered safely."""


def render_building_design_context(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render the admitted Brick-owned design context resources."""

    repo = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    resources: list[dict[str, Any]] = []
    for resource_ref, relative in _DESIGN_RESOURCE_PATHS.items():
        path = repo / relative
        text = _read_design_resource(path)
        resources.append(
            {
                "resource_ref": resource_ref,
                "path": relative.as_posix(),
                "text": text,
            }
        )
    shape_resource = _shape_catalog_resource(repo)
    resources.insert(1, shape_resource)
    registry = _shape_registry(repo)
    return {
        "kind": "building-design-context",
        "source": "brick/",
        "resource_refs": [str(resource["resource_ref"]) for resource in resources],
        "shape_catalog_source": shape_resource["catalog_source"],
        "shape_refs": list(registry["shape_refs"]),
        "step_templates": _registry_section_items(registry, "step_templates"),
        "chain_presets": _registry_section_items(registry, "chain_presets"),
        "common_chain_presets": _registry_section_items(registry, "common_chain_presets"),
        "dogfood_chain_presets": _registry_section_items(registry, "dogfood_chain_presets"),
        "chain_preset_aliases": dict(registry.get("chain_preset_aliases", {})),
        "selection_rule": "caller_or_coo_declared_only",
        "resources": resources,
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_building_design_context_json(repo_root: str | Path | None = None) -> str:
    """Render the design context as deterministic JSON text."""

    return json.dumps(
        render_building_design_context(repo_root=repo_root),
        ensure_ascii=False,
        sort_keys=True,
    )


def render_agent_candidate_packet(
    role_need: str,
    write_need: bool,
    *,
    selected_adapter_ref: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Render the READ-ONLY agent NEED<->CAPABILITY candidate packet for a COO.

    Given a brick NEED (``role_need`` lane + ``write_need`` write scope) this
    records EVERY Agent CAPABILITY that matches the need, the MECHANICAL match
    reason per candidate, and whether the need is ambiguous (>= 2 candidates).
    It is advisory only: support MEASURES/RECORDS the candidate set but NEVER
    picks among >= 2, never ranks, never recommends, and never judges agent
    quality. The packet carries NO ``selected`` / ``chosen`` / ``recommended``
    field by construction. When ambiguous, the disposition belongs to the caller
    / COO (mirroring the address >= 2 -> HOLD pattern); a single candidate still
    auto-resolves through the matcher (unchanged). This is the informed surface
    that sits BESIDE the matcher's fail-closed >= 2 ValueError, not a bypass of
    it.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    cleaned_selected_adapter_ref = _clean_agent_candidate_selected_adapter_ref(
        repo,
        selected_adapter_ref,
    )
    try:
        candidate_rows = _render_candidate_agents_for_need(repo, role_need, write_need)
    except ValueError as exc:
        raise BuildingDesignToolkitError(str(exc)) from exc
    if cleaned_selected_adapter_ref is not None:
        candidate_rows = [
            {
                **row,
                "selected_adapter_compatible": cleaned_selected_adapter_ref
                in set(row.get("adapter_refs", ())),
                "preferred_adapter_matches_selected": row.get("preferred_adapter_ref")
                == cleaned_selected_adapter_ref,
            }
            for row in candidate_rows
        ]
    write_need = bool(write_need)
    total_candidates = len(candidate_rows)
    ambiguous = total_candidates >= 2
    packet = {
        "kind": "agent-candidate-packet",
        "source": "agent/",
        "role_need": role_need,
        "write_need": write_need,
        "total_candidates": total_candidates,
        "ambiguous": ambiguous,
        "disposition_required": ambiguous,
        "required_disposition_owner": "caller-or-coo",
        "candidate_rows": candidate_rows,
        "match_authority": list(_AGENT_CANDIDATE_MATCH_AUTHORITY),
        "proof_limits": list(_AGENT_CANDIDATE_PROOF_LIMITS),
        "not_proven": list(_AGENT_CANDIDATE_NOT_PROVEN),
    }
    if cleaned_selected_adapter_ref is not None:
        packet["selected_adapter_ref"] = cleaned_selected_adapter_ref
    return packet


def render_agent_candidate_packet_json(
    role_need: str,
    write_need: bool,
    *,
    selected_adapter_ref: str | None = None,
    repo_root: str | Path | None = None,
) -> str:
    """Render the agent-candidate packet as deterministic JSON text."""

    return json.dumps(
        render_agent_candidate_packet(
            role_need,
            write_need,
            selected_adapter_ref=selected_adapter_ref,
            repo_root=repo_root,
        ),
        ensure_ascii=False,
        sort_keys=True,
    )


def _clean_agent_candidate_selected_adapter_ref(
    repo: Path,
    selected_adapter_ref: str | None,
) -> str | None:
    """Validate an optional adapter lens for the read-only candidate packet."""

    if selected_adapter_ref is None:
        return None
    if not isinstance(selected_adapter_ref, str) or not selected_adapter_ref.strip():
        raise BuildingDesignToolkitError("selected_adapter_ref must be non-empty text")
    selected = selected_adapter_ref.strip()
    if selected in _RETIRED_AGENT_CANDIDATE_ADAPTER_REFS:
        raise BuildingDesignToolkitError(
            f"{selected} is retired and not admitted as an active adapter"
        )
    admitted_adapter_refs: set[str] = set()
    for ref in list_agent_object_refs(repo):
        agent_object = resolve_agent_object(ref, repo_root=repo)["agent_object"]
        adapter_refs = agent_object.get("adapter_refs", ())
        if isinstance(adapter_refs, (list, tuple)):
            admitted_adapter_refs.update(str(item).strip() for item in adapter_refs)
    if selected not in admitted_adapter_refs:
        raise BuildingDesignToolkitError(
            f"selected_adapter_ref {selected} is not referenced by any admitted Agent Object"
        )
    return selected


def render_preset_ranking_packet(
    selection_hint: str,
    catalog_scope: str | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Render the READ-ONLY, NON-BINDING chain-preset ranking packet for a COO.

    Given a HUMAN-declared ``selection_hint`` (and an optional ``catalog_scope``
    filter: ``common`` or the dogfood scope), this lists the matching chain
    presets ranked by a MECHANICAL relevance score: the count of distinct hint
    tokens that appear in each preset's OWN declared text (its ``preset_ref`` +
    ``intent`` + ``selection_hint`` + ``catalog_scope``). The ordering is
    descending by score with a deterministic tiebreak by ``chain_preset_ref``.

    This is ADVISORY ONLY. Support does NOT auto-select a preset, does NOT treat
    the ordering as a decision, and the packet carries NO ``selected`` /
    ``chosen`` / ``recommended`` / ``best`` / ``use_this`` field by construction.
    The score is a token-overlap relevance count, NOT a quality judgment and NOT
    a recommendation-to-use. The COO chooses + declares the active preset, and
    ``composition.materialize_building_intent`` STILL hard-refuses a run with a
    missing / blank ``chain_preset_ref`` -- the ranking never auto-applies. The
    preset catalog is read through the existing ``_load_shape_registry`` chain
    presets (built from ``presets/<name>.md`` frontmatter); no new registry is
    invented here.
    """

    if not isinstance(selection_hint, str):
        raise TypeError("selection_hint must be text")
    hint_text = selection_hint.strip()
    if not hint_text:
        raise BuildingDesignToolkitError("selection_hint must not be blank")
    scope_filter: str | None
    if catalog_scope is None:
        scope_filter = None
    else:
        if not isinstance(catalog_scope, str):
            raise TypeError("catalog_scope must be text or None")
        scope_filter = catalog_scope.strip() or None

    repo = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    registry = _shape_registry(repo)
    chain_presets = registry.get("chain_presets", {})
    if not isinstance(chain_presets, dict):
        raise BuildingDesignToolkitError("shape registry chain_presets must be a mapping")

    hint_tokens = _hint_tokens(hint_text)

    scored: list[tuple[int, str, dict[str, Any]]] = []
    for ref, preset in sorted(chain_presets.items()):
        # CANONICAL presets only: skip alias entries (compat refs that point at a
        # canonical preset under a different key), so each preset appears once.
        if not isinstance(preset, dict) or preset.get("preset_ref") != ref:
            continue
        preset_scope = str(preset.get("catalog_scope", "")).strip()
        if scope_filter is not None and preset_scope != scope_filter:
            continue
        preset_tokens = _preset_match_tokens(ref, preset)
        matched = sorted(hint_tokens & preset_tokens)
        score = len(matched)
        row = {
            "chain_preset_ref": ref,
            "summary": str(preset.get("intent", "")).strip(),
            "selection_hint": str(preset.get("selection_hint", "")).strip(),
            "catalog_scope": preset_scope,
            "hint_match_score": score,
            "matched_hint_tokens": matched,
        }
        scored.append((score, ref, row))

    # Rank: descending score, deterministic tiebreak by chain_preset_ref ascending.
    scored.sort(key=lambda item: (-item[0], item[1]))
    ranked_rows: list[dict[str, Any]] = []
    for rank, (_score, _ref, row) in enumerate(scored, start=1):
        row["rank"] = rank
        ranked_rows.append(row)

    return {
        "kind": "preset-ranking-packet",
        "source": "brick/",
        "selection_hint": hint_text,
        "selection_hint_tokens": sorted(hint_tokens),
        "catalog_scope": scope_filter,
        "total_candidates": len(ranked_rows),
        "ranked_rows": ranked_rows,
        "ranking_basis": _PRESET_RANKING_BASIS,
        "selection_rule": "caller_or_coo_declared_only",
        "selection_authority": list(_PRESET_RANKING_SELECTION_AUTHORITY),
        "proof_limits": list(_PRESET_RANKING_PROOF_LIMITS),
        "not_proven": list(_PRESET_RANKING_NOT_PROVEN),
    }


def render_preset_ranking_packet_json(
    selection_hint: str,
    catalog_scope: str | None = None,
    *,
    repo_root: str | Path | None = None,
) -> str:
    """Render the preset-ranking packet as deterministic JSON text."""

    return json.dumps(
        render_preset_ranking_packet(selection_hint, catalog_scope, repo_root=repo_root),
        ensure_ascii=False,
        sort_keys=True,
    )


def render_building_board(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render THE BOARD: one read-only manifest unifying the four catalogs.

    A design AI is handed this single manifest (instead of four scattered
    readers) and proposes a graph (compose_building args) from it; the operator
    cross-verifies and the COO declares the active shape. The board carries ALL
    FIVE catalog sections, each grounded in the real on-disk fields:

    * ``bricks`` -- one row per Brick kind (the brick.md frontmatter the Builder
      reads + that kind's return contract: ``required_return_shape`` and
      ``forbidden_return_keys`` from its primary ``return.yaml``).
    * ``agents`` -- the Agent Object set (lane / tool_policy_refs / adapter_refs /
      ``writer_capable``), read through the Agent-axis resolver.
    * ``links`` -- the Link catalog: Movement literals (forward / reroute),
      declared Gate refs + each gate's required return fields, Carry fields, and
      Transition fields.
    * ``presets`` -- one row per chain preset (its frontmatter verbatim, incl.
      ``graph_topology`` when the preset declares one).
    * ``shapes`` -- the declared Building Shape menu refs.

    It REUSES the existing catalog readers: ``render_building_design_context``'s
    shape / preset registry, the Agent-axis ``resolve_agent_object`` rows, the
    brick-catalog ``step_templates`` glob, and the Link ``gate`` / ``movement`` /
    ``carry`` / ``transition`` sources. It READS the catalogs and mutates none of
    them. It AUTHORS / DECIDES nothing: no Movement, no success / quality verdict,
    no shape pick. ``selection_rule`` stays a caller / COO declaration and the
    ``proof_limits`` / ``not_proven`` envelope rides along.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    registry = _shape_registry(repo)
    bricks = _board_bricks(repo, registry)
    agents = _board_agents(repo)
    links = _board_links(repo)
    presets = _board_presets(registry)
    shapes = _board_shapes(registry)
    return {
        "kind": "building-board",
        "source": "brick/ + agent/ + link/",
        "section_refs": ["bricks", "agents", "links", "presets", "shapes"],
        "bricks": bricks,
        "agents": agents,
        "links": links,
        "presets": presets,
        "shapes": shapes,
        "catalog_counts": {
            "bricks": len(bricks),
            "agents": len(agents),
            "movements": len(links["movements"]),
            "gates": len(links["gates"]),
            "presets": len(presets),
            "shapes": len(shapes),
        },
        "selection_rule": "caller_or_coo_declared_only",
        "proof_limits": list(_BOARD_PROOF_LIMITS),
        "not_proven": list(_BOARD_NOT_PROVEN),
    }


def render_building_board_json(repo_root: str | Path | None = None) -> str:
    """Render the board as deterministic JSON text."""

    return json.dumps(
        render_building_board(repo_root=repo_root),
        ensure_ascii=False,
        sort_keys=True,
    )


def _board_bricks(repo: Path, registry: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per Brick kind: brick.md frontmatter + return contract.

    The frontmatter + primary ``required_return_shape`` are read by the EXISTING
    ``step_templates`` registry (the brick-catalog glob, the same source
    ``render_building_design_context`` exposes). The return contract is completed
    here by reading the kind's PRIMARY ``return.yaml`` for its
    ``forbidden_return_keys`` (the catalog file is READ, never written).
    """

    rows: list[dict[str, Any]] = []
    for item in _registry_section_items(registry, "step_templates"):
        kind = str(item.get("step_template_ref", "")).split(":", 1)[-1]
        return_template_refs = list(item.get("brick_template_refs", ()))
        required_return_shape = [
            field
            for field in str(item.get("required_return_shape", "")).split(",")
            if field
        ]
        primary_return_ref = return_template_refs[0] if return_template_refs else ""
        rows.append(
            {
                "brick_kind": kind,
                "brick_word": str(item.get("brick_word", "")),
                "performer_word": str(item.get("agent_word", "")),
                "performer_lane_need": str(item.get("role_need", "")),
                "requires_brick_write_scope": bool(item.get("write_need", False)),
                "agent_object_ref": str(item.get("agent_object_ref", "")),
                "link_movement_literal": str(item.get("link_word", "")),
                "brick_contract": str(item.get("brick_contract", "")),
                "brick_spec_ref": str(item.get("brick_spec_ref", "")),
                "return_contract": {
                    "primary_return_template_ref": primary_return_ref,
                    "required_return_template_refs": return_template_refs,
                    "required_return_shape": required_return_shape,
                    "forbidden_return_keys": _board_forbidden_return_keys(
                        repo, primary_return_ref
                    ),
                },
            }
        )
    return rows


def _board_forbidden_return_keys(repo: Path, primary_return_ref: str) -> list[str]:
    """Read a Brick kind's declared ``forbidden_return_keys`` from its return.yaml.

    READ-ONLY: the return template is loaded with the existing
    ``_load_yaml_mapping`` helper and only its declared ``forbidden_return_keys``
    list is projected; the file is never written.
    """

    if not primary_return_ref:
        return []
    path = repo / primary_return_ref
    doc = _load_yaml_mapping(path, f"return template {primary_return_ref}")
    forbidden = doc.get("forbidden_return_keys", ())
    if not isinstance(forbidden, (list, tuple)):
        raise BuildingDesignToolkitError(
            f"return template {primary_return_ref}: forbidden_return_keys must be a list"
        )
    return [str(key) for key in forbidden]


def _board_agents(repo: Path) -> list[dict[str, Any]]:
    """The Agent Object set: lane / tool_policy / adapter / writer_capable.

    Read through the EXISTING Agent-axis readers (``list_agent_object_refs`` +
    ``resolve_agent_object``); ``writer_capable`` uses the same ``_agent_is_writer``
    rule the matcher uses (capability owned by agent_resources.py). Rows are
    sorted by ``agent_object_ref`` for deterministic output -- no quality order.
    """

    rows: list[dict[str, Any]] = []
    for ref in sorted(list_agent_object_refs(repo)):
        agent_object = resolve_agent_object(ref, repo_root=repo)["agent_object"]
        rows.append(
            {
                "agent_object_ref": ref,
                "name": str(agent_object.get("name", "")),
                "lane": str(agent_object.get("lane", "")),
                "writer_capable": _agent_is_writer(agent_object),
                "tool_policy_refs": list(agent_object.get("tool_policy_refs", ())),
                "adapter_refs": list(agent_object.get("adapter_refs", ())),
                "preferred_adapter_ref": str(agent_object.get("preferred_adapter_ref") or ""),
                "preferred_model_ref": str(agent_object.get("preferred_model_ref") or ""),
            }
        )
    return rows


def _board_links(repo: Path) -> dict[str, Any]:
    """The Link catalog: movements + gates + carry fields + transition fields.

    Movement literals come from ``link/movement.yaml`` (forward / reroute); the
    declared Gate refs + each gate's required return fields come from the Link
    ``gate`` module (the canonical ``DECLARED_GATE_REFS`` source); Carry and
    Transition public-fact field lists come from their projection YAMLs. All
    sources are READ, never written.
    """

    movement_doc = _load_yaml_mapping(
        repo / _BOARD_LINK_CATALOG_PATHS["movement"], "link movement catalog"
    )
    movements = _board_movement_literals(movement_doc)
    gates = [
        {
            "gate_ref": gate_ref,
            # The Link-owned gate->required-fields mapping, via the canonical
            # combined helper called per single gate ref (one-ref list).
            "required_return_fields": list(gate_required_return_fields([gate_ref])),
        }
        for gate_ref in DECLARED_GATE_REFS
    ]
    return {
        "movements": movements,
        "gates": gates,
        "carry_fields": _board_public_fact_fields(
            repo, _BOARD_LINK_CATALOG_PATHS["carry"], "link carry catalog"
        ),
        "transition_fields": _board_public_fact_fields(
            repo, _BOARD_LINK_CATALOG_PATHS["transition"], "link transition catalog"
        ),
    }


def _board_movement_literals(movement_doc: Mapping[str, Any]) -> list[str]:
    """The admitted Movement literals declared in link/movement.yaml."""

    literals_raw = movement_doc.get("movement_literals", ())
    if not isinstance(literals_raw, (list, tuple)):
        raise BuildingDesignToolkitError(
            "link movement catalog: movement_literals must be a list"
        )
    literals: list[str] = []
    for entry in literals_raw:
        if isinstance(entry, Mapping):
            value = entry.get("movement")
        else:
            value = entry
        if not isinstance(value, str) or not value.strip():
            raise BuildingDesignToolkitError(
                "link movement catalog: each movement literal must be non-empty text"
            )
        literals.append(value.strip())
    return literals


def _board_public_fact_fields(repo: Path, relative: Path, label: str) -> list[str]:
    """The public_fact.fields list of a Link projection YAML (read-only)."""

    doc = _load_yaml_mapping(repo / relative, label)
    public_fact = doc.get("public_fact")
    if not isinstance(public_fact, Mapping):
        raise BuildingDesignToolkitError(f"{label}: public_fact must be a mapping")
    fields = public_fact.get("fields", ())
    if not isinstance(fields, (list, tuple)):
        raise BuildingDesignToolkitError(f"{label}: public_fact.fields must be a list")
    return [str(field) for field in fields]


def _board_presets(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per CANONICAL chain preset: its frontmatter verbatim.

    Sourced from the EXISTING ``chain_presets`` registry (built from
    ``presets/<name>.md`` frontmatter, the same source the design context
    exposes). Alias entries (whose ``preset_ref`` differs from the registry key)
    are skipped so each preset appears once; ``graph_topology`` rides along
    verbatim when the preset declares one. Sorted by ``preset_ref``.
    """

    rows: list[dict[str, Any]] = []
    for item in _registry_section_items(registry, "chain_presets"):
        preset_ref = str(item.get("preset_ref", ""))
        rows.append(dict(item))
    rows.sort(key=lambda row: str(row.get("preset_ref", "")))
    return rows


def _board_shapes(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """The declared Building Shape menu refs (read-only, from the shape registry)."""

    return [{"shape_ref": str(ref)} for ref in registry.get("shape_refs", ())]


def _hint_tokens(text: str) -> set[str]:
    """Tokenize a hint into the set of distinct >=2-char lowercase tokens."""

    return {token for token in _HINT_TOKEN_PATTERN.findall(text.lower()) if len(token) >= 2}


def _preset_match_tokens(ref: str, preset: dict[str, Any]) -> set[str]:
    """The token surface a preset declares for mechanical hint matching.

    Only the preset's OWN declared text participates: its ref, intent, declared
    selection_hint, and catalog_scope. No quality / skill / performance signal.
    """

    parts = [
        ref,
        str(preset.get("intent", "")),
        str(preset.get("selection_hint", "")),
        str(preset.get("catalog_scope", "")),
    ]
    tokens: set[str] = set()
    for part in parts:
        tokens |= _hint_tokens(part)
    return tokens


def _read_design_resource(path: Path) -> str:
    if not path.is_file():
        raise BuildingDesignToolkitError(f"design resource missing: {path}")
    text = path.read_text(encoding="utf-8")
    _reject_secret_text(path, text)
    return text


def _reject_secret_text(path: Path, text: str) -> None:
    if contains_raw_secret_text(text):
        raise BuildingDesignToolkitError(f"design resource contains raw credential-looking text: {path}")


def _shape_catalog_resource(repo: Path) -> dict[str, Any]:
    relative = SPLIT_SHAPE_CATALOG_PATH
    catalog_source = "split_catalog"
    path = repo / relative
    return {
        "resource_ref": "shape_catalog",
        "path": relative.as_posix(),
        "catalog_source": catalog_source,
        "text": _read_design_resource(path),
    }


def _registry_section_items(
    registry: dict[str, Any],
    section_name: str,
) -> list[dict[str, Any]]:
    items = registry.get(section_name, ())
    if not isinstance(items, dict):
        return []
    return [
        {str(key): value for key, value in item.items()}
        for item in items.values()
        if isinstance(item, dict)
    ]


def _shape_registry(repo: Path) -> dict[str, Any]:
    try:
        return dict(_load_shape_registry(repo))
    except ValueError as exc:
        raise BuildingDesignToolkitError(str(exc)) from exc


__all__ = [
    "BuildingDesignToolkitError",
    "render_building_design_context",
    "render_building_design_context_json",
    "render_building_board",
    "render_building_board_json",
    "render_agent_candidate_packet",
    "render_agent_candidate_packet_json",
    "render_preset_ranking_packet",
    "render_preset_ranking_packet_json",
]
