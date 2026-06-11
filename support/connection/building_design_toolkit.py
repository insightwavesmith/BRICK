"""Read-only support toolkit for Brick-owned Building design inputs.

The toolkit exposes task source, split shape catalog, and Human+AI design contract
templates as support context. It does not choose a shape, write Building Plans,
call providers, or own Brick / Agent / Link meaning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.plan_rendering import (
    SPLIT_SHAPE_CATALOG_PATH,
    _load_shape_registry,
    _render_candidate_agents_for_need,
)

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_RESOURCE_PATHS = {
    "task_source_template": Path("brick/templates/tasks/source-template.md"),
    "human_ai_design_contract": Path("brick/templates/building-design-contract.yaml"),
}
_RAW_SECRET_MARKERS = (
    "xoxb-",
    "ghp_",
    "gho_",
    "github_pat_",
    "-----BEGIN ",
)
_OPENAI_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
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
    try:
        candidate_rows = _render_candidate_agents_for_need(repo, role_need, write_need)
    except ValueError as exc:
        raise BuildingDesignToolkitError(str(exc)) from exc
    write_need = bool(write_need)
    total_candidates = len(candidate_rows)
    ambiguous = total_candidates >= 2
    return {
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


def render_agent_candidate_packet_json(
    role_need: str,
    write_need: bool,
    *,
    repo_root: str | Path | None = None,
) -> str:
    """Render the agent-candidate packet as deterministic JSON text."""

    return json.dumps(
        render_agent_candidate_packet(role_need, write_need, repo_root=repo_root),
        ensure_ascii=False,
        sort_keys=True,
    )


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
    if _OPENAI_KEY_PATTERN.search(text):
        raise BuildingDesignToolkitError(f"design resource contains raw credential-looking text: {path}")
    for marker in _RAW_SECRET_MARKERS:
        if marker in text:
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
    "render_agent_candidate_packet",
    "render_agent_candidate_packet_json",
    "render_preset_ranking_packet",
    "render_preset_ranking_packet_json",
]
