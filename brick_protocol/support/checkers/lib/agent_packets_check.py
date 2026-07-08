"""Agent packet behavioral profile runners.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)


# Pick/rank field names that would betray the axis law if support emitted them:
# the packet records candidates + a mechanical match reason ONLY, and must NEVER
# pick among >= 2, rank, or recommend. The AXIS FIRE asserts NONE of these appear
# anywhere in the packet (top-level or per-row). If the packet were reverted to
# pick/rank one, the case goes RED here.
_AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS = frozenset(
    {
        "selected",
        "selected_agent",
        "chosen",
        "chosen_agent",
        "recommended",
        "recommended_agent",
        "recommendation",
        "pick",
        "picked",
        "winner",
        "best",
        "rank",
        "ranking",
        "ranked",
        "score",
        "preferred",
        # A "default" is still a support-side PICK among >= 2 candidates: it
        # silently elevates one ref over the others. The packet records the brick
        # NEED + every matching CAPABILITY; choosing a default belongs to the
        # author/COO, never to this read-only surface.
        "default",
        "default_agent",
    }
)


def run_agent_candidate_packet_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """Exercise the READ-ONLY agent NEED<->CAPABILITY candidate packet (PART-2 P3).

    For each declared item this drives ``render_agent_candidate_packet`` over the
    real Agent Object set and asserts:

    * MULTI: an ambiguous need (>= 2 candidates) records ALL qualifying agents
      (none omitted), marks ``ambiguous``/``disposition_required`` True with
      ``required_disposition_owner == 'caller-or-coo'``, and gives each row a
      MECHANICAL ``match_reason`` that states lane + write scope ONLY.
    * SINGLE: a single-candidate need is unambiguous (``disposition_required``
      False).
    * AXIS FIRE: support does NOT auto-pick among >= 2. The packet carries NO
      pick/rank/recommend field (top-level or per-row), AND the matcher
      ``_resolve_agent_for_need`` still RAISES for the >= 2 case (unchanged). This
      is the self-FIRE guard: making the packet pick/rank one reverts to RED.
    """
    items = rule_items(profile, "agent_candidate_packet_case")
    if not items:
        return 0
    from brick_protocol.support.connection.building_design_toolkit import (
        render_agent_candidate_packet,
    )
    from brick_protocol.support.operator.plan_rendering import _resolve_agent_for_need

    count = 0
    for item in items:
        mapping = require_mapping(item, "agent_candidate_packet_case item")
        label = require_string(mapping.get("label"), "agent_candidate_packet_case.label")
        role_need = require_string(mapping.get("role_need"), f"{label}: role_need")
        selected_adapter_raw = mapping.get("selected_adapter_ref")
        selected_adapter_ref = (
            require_string(selected_adapter_raw, f"{label}: selected_adapter_ref")
            if selected_adapter_raw is not None
            else None
        )
        write_need_raw = mapping.get("write_need", False)
        if not isinstance(write_need_raw, bool):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: write_need must be a YAML bool"
            )
        write_need = write_need_raw
        expect_ambiguous_raw = mapping.get("expect_ambiguous")
        if not isinstance(expect_ambiguous_raw, bool):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: expect_ambiguous must be a YAML bool"
            )
        expect_ambiguous = expect_ambiguous_raw
        expect_min_candidates = int(
            require_string(
                str(mapping.get("expect_min_candidates", "0")),
                f"{label}: expect_min_candidates",
            )
        )
        expected_refs = require_string_list(
            mapping.get("expected_candidate_refs", []),
            f"{label}: expected_candidate_refs",
        )

        packet = render_agent_candidate_packet(
            role_need,
            write_need,
            selected_adapter_ref=selected_adapter_ref,
            repo_root=repo,
        )

        if packet.get("kind") != "agent-candidate-packet":
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: "
                f"kind expected 'agent-candidate-packet', observed {packet.get('kind')!r}"
            )
        if packet.get("role_need") != role_need or packet.get("write_need") != write_need:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: packet did not echo the need "
                f"(role_need={packet.get('role_need')!r}, write_need={packet.get('write_need')!r})"
            )
        if selected_adapter_ref is None:
            if "selected_adapter_ref" in packet:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: omitted selected_adapter_ref "
                    "must not be invented by support"
                )
        elif packet.get("selected_adapter_ref") != selected_adapter_ref:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: selected_adapter_ref expected "
                f"{selected_adapter_ref!r}, observed {packet.get('selected_adapter_ref')!r}"
            )

        rows = packet.get("candidate_rows")
        if not isinstance(rows, list):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: candidate_rows must be a list"
            )
        observed_refs = [row.get("agent_object_ref") for row in rows]
        total = packet.get("total_candidates")
        if total != len(rows):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: total_candidates {total!r} "
                f"!= len(candidate_rows) {len(rows)}"
            )
        if total < expect_min_candidates:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: total_candidates {total} "
                f"< expect_min_candidates {expect_min_candidates}"
            )

        # ambiguity / disposition mechanics
        ambiguous = packet.get("ambiguous")
        if ambiguous != expect_ambiguous:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: ambiguous expected "
                f"{expect_ambiguous}, observed {ambiguous!r}"
            )
        if ambiguous != (total >= 2):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: ambiguous {ambiguous!r} "
                f"inconsistent with total_candidates {total}"
            )
        if packet.get("disposition_required") != ambiguous:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: disposition_required must "
                f"track ambiguous; got {packet.get('disposition_required')!r} vs {ambiguous!r}"
            )
        if packet.get("required_disposition_owner") != "caller-or-coo":
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: required_disposition_owner "
                f"expected 'caller-or-coo', observed {packet.get('required_disposition_owner')!r}"
            )

        # ALL qualifying agents present (none omitted) when an explicit set is declared.
        if expected_refs and sorted(observed_refs) != sorted(expected_refs):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: candidate refs mismatch; "
                f"expected {sorted(expected_refs)}, observed {sorted(observed_refs)}"
            )

        # Each row's match_reason is MECHANICAL: it states lane + write scope ONLY.
        write_scope_word = "yes" if write_need else "no"
        expected_reason = f"lane={role_need}, write_scope={write_scope_word}"
        for row in rows:
            if not isinstance(row, Mapping):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: each candidate row must be a mapping"
                )
            if row.get("match_reason") != expected_reason:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} match_reason expected {expected_reason!r}, "
                    f"observed {row.get('match_reason')!r} (must be MECHANICAL: lane + write only)"
                )
            if row.get("lane") != role_need:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} lane {row.get('lane')!r} != role_need {role_need!r}"
                )
            adapter_refs = row.get("adapter_refs")
            if not isinstance(adapter_refs, list) or not all(
                isinstance(ref, str) and ref for ref in adapter_refs
            ):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} adapter_refs must be a non-empty string list"
                )
            for preferred_key in ("preferred_adapter_ref", "preferred_model_ref"):
                if not isinstance(row.get(preferred_key), str):
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} {preferred_key} must be rendered as text"
                    )
            if selected_adapter_ref is None:
                for compatibility_key in (
                    "selected_adapter_compatible",
                    "preferred_adapter_matches_selected",
                ):
                    if compatibility_key in row:
                        raise ProfileError(
                            f"agent_candidate_packet_case rejected {label}: row "
                            f"{row.get('agent_object_ref')!r} must not invent {compatibility_key} "
                            "when selected_adapter_ref is omitted"
                        )
            else:
                expected_compatible = selected_adapter_ref in set(adapter_refs)
                if row.get("selected_adapter_compatible") != expected_compatible:
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} selected_adapter_compatible expected "
                        f"{expected_compatible}, observed {row.get('selected_adapter_compatible')!r}"
                    )
                expected_preferred_match = row.get("preferred_adapter_ref") == selected_adapter_ref
                if row.get("preferred_adapter_matches_selected") != expected_preferred_match:
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} preferred_adapter_matches_selected expected "
                        f"{expected_preferred_match}, observed "
                        f"{row.get('preferred_adapter_matches_selected')!r}"
                    )
            # capability >= need: when the brick NEEDS write, EVERY candidate row
            # must be writer_capable; when the need is read-only, writer-capability
            # is UNCONSTRAINED (a write-capable agent may serve a read-only need;
            # effective write stays gated by the Brick write_scope NEED downstream).
            if write_need and not bool(row.get("writer_capable")):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} writer_capable {row.get('writer_capable')!r} "
                    f"does not satisfy write_need {write_need}"
                )
            if bool(row.get("qualifies")) != ambiguous:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} qualifies must track ambiguity "
                    f"({row.get('qualifies')!r} vs {ambiguous!r})"
                )

        # AXIS FIRE 1: NO pick/rank/recommend field anywhere (top-level or per-row).
        top_hits = sorted(set(packet.keys()) & _AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS)
        if top_hits:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: packet carries forbidden "
                f"pick/rank field(s) at top level {top_hits}; support must NOT pick among candidates"
            )
        for row in rows:
            row_hits = sorted(set(row.keys()) & _AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS)
            if row_hits:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: candidate row "
                    f"{row.get('agent_object_ref')!r} carries forbidden pick/rank field(s) "
                    f"{row_hits}; support must NOT rank or recommend"
                )

        # AXIS FIRE 2: the matcher's >= 2 fail-closed halt is UNCHANGED.
        if ambiguous:
            try:
                _resolve_agent_for_need(repo, role_need, write_need)
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: _resolve_agent_for_need did NOT "
                    f"raise for the ambiguous need (role_need={role_need!r}, write_need={write_need}); "
                    "the fail-closed >= 2 halt must stay (the packet is the surface beside it, not a bypass)"
                )
        else:
            # Single candidate must still auto-resolve to that one candidate (unchanged).
            resolved = _resolve_agent_for_need(repo, role_need, write_need)
            if observed_refs and resolved != observed_refs[0]:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: single-candidate need must "
                    f"auto-resolve to {observed_refs[0]!r}, matcher returned {resolved!r}"
                )

        for rejected_ref in require_string_list(
            mapping.get("rejected_selected_adapter_refs", []),
            f"{label}: rejected_selected_adapter_refs",
        ):
            try:
                render_agent_candidate_packet(
                    role_need,
                    write_need,
                    selected_adapter_ref=rejected_ref,
                    repo_root=repo,
                )
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: selected_adapter_ref "
                    f"{rejected_ref!r} was not rejected"
                )

        count += 1
    return count


# Pick/recommend field names that would betray the axis law if the preset-ranking
# packet emitted them: the packet ORDERS presets by a MECHANICAL hint-token count
# and MUST NEVER pick one, recommend one, or call one "best"/"use_this". Unlike the
# agent-candidate packet, ``rank`` / ``ranked`` / ``score`` are LEGITIMATE here (the
# mechanical ordering IS the surface), so they are deliberately NOT in this set; only
# decision/recommendation words are forbidden. The AXIS FIRE asserts NONE of these
# appear anywhere (top-level or per-row). Inject any of them and the case goes RED.
_PRESET_RANKING_FORBIDDEN_PICK_FIELDS = frozenset(
    {
        "selected",
        "selected_preset",
        "chosen",
        "chosen_preset",
        "recommended",
        "recommended_preset",
        "recommendation",
        "pick",
        "picked",
        "winner",
        "best",
        "best_preset",
        "use_this",
        "preferred",
        # A "default" preset is a recommendation-to-use by another name: it picks
        # one preset for the caller. The ranking ORDERS by mechanical hint-match
        # only; declaring the active preset stays a caller/COO act.
        "default",
        "default_preset",
    }
)


def run_preset_ranking_packet_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """Exercise the READ-ONLY, NON-BINDING preset-ranking packet (PART-2 P4).

    For each declared item this drives ``render_preset_ranking_packet`` over the
    real chain-preset catalog and asserts:

    * RANK: ranked_rows are ordered by MECHANICAL hint-match (descending
      hint_match_score, deterministic tiebreak by chain_preset_ref ascending);
      total_candidates equals len(ranked_rows); ranking_basis states it is
      "mechanical hint-match (not quality)"; rank is 1-based contiguous; each
      row's hint_match_score is a non-negative int. An optional
      expect_top_ref / expect_min_top_score pins a real hint to its top preset.
    * NON-BINDING / NO-PICK (axis FIRE): the packet carries NO
      selected/chosen/recommended/best/use_this field (top-level or per-row).
      Inject such a field and this goes RED.
    * MATERIALIZER STILL HARD-REFUSES (the biggest-unknown guard): even WITH a
      ranking available, ``materialize_building_intent`` STILL raises for an
      intent with no/blank chain_preset_ref -- the ranking NEVER auto-applies.
      If the materializer were made to fall back to the top-ranked preset, this
      assertion goes RED (proving the ranking is non-binding).
    """
    items = rule_items(profile, "preset_ranking_packet_case")
    if not items:
        return 0
    from brick_protocol.support.connection.building_design_toolkit import (
        render_preset_ranking_packet,
    )
    from brick_protocol.support.operator.composition_intent import materialize_building_intent

    count = 0
    for item in items:
        mapping = require_mapping(item, "preset_ranking_packet_case item")
        label = require_string(mapping.get("label"), "preset_ranking_packet_case.label")
        selection_hint = require_string(
            mapping.get("selection_hint"), f"{label}: selection_hint"
        )
        catalog_scope_raw = mapping.get("catalog_scope")
        if catalog_scope_raw is not None and not isinstance(catalog_scope_raw, str):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: catalog_scope must be a string or omitted"
            )
        catalog_scope = catalog_scope_raw
        expect_min_candidates = int(
            require_string(
                str(mapping.get("expect_min_candidates", "0")),
                f"{label}: expect_min_candidates",
            )
        )
        expect_top_ref = mapping.get("expect_top_ref")
        if expect_top_ref is not None and not isinstance(expect_top_ref, str):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: expect_top_ref must be a string or omitted"
            )
        expect_min_top_score = int(
            require_string(
                str(mapping.get("expect_min_top_score", "0")),
                f"{label}: expect_min_top_score",
            )
        )

        packet = render_preset_ranking_packet(
            selection_hint, catalog_scope, repo_root=repo
        )

        if packet.get("kind") != "preset-ranking-packet":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: kind expected "
                f"'preset-ranking-packet', observed {packet.get('kind')!r}"
            )
        if packet.get("source") != "brick_protocol/brick/":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: source expected 'brick_protocol/brick/', "
                f"observed {packet.get('source')!r}"
            )
        if packet.get("selection_rule") != "caller_or_coo_declared_only":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: selection_rule expected "
                f"'caller_or_coo_declared_only', observed {packet.get('selection_rule')!r}"
            )
        if packet.get("catalog_scope") != catalog_scope:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: catalog_scope echo expected "
                f"{catalog_scope!r}, observed {packet.get('catalog_scope')!r}"
            )

        rows = packet.get("ranked_rows")
        if not isinstance(rows, list):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: ranked_rows must be a list"
            )
        total = packet.get("total_candidates")
        if total != len(rows):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: total_candidates {total!r} "
                f"!= len(ranked_rows) {len(rows)}"
            )
        if total < expect_min_candidates:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: total_candidates {total} "
                f"< expect_min_candidates {expect_min_candidates}"
            )

        # ranking_basis must state it is mechanical hint-match, NOT quality.
        basis = packet.get("ranking_basis")
        if not isinstance(basis, str) or "mechanical hint-match" not in basis or "not quality" not in basis:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: ranking_basis must state "
                f"'mechanical hint-match' and 'not quality'; observed {basis!r}"
            )

        # RANK mechanics: 1-based contiguous, sorted by (-score, ref).
        prev_key: tuple[int, str] | None = None
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: each ranked row must be a mapping"
                )
            rank = row.get("rank")
            if rank != index + 1:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {index} rank {rank!r} "
                    f"is not 1-based contiguous (expected {index + 1})"
                )
            ref = row.get("chain_preset_ref")
            if not isinstance(ref, str) or not ref:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {index} chain_preset_ref "
                    f"must be a non-empty string; observed {ref!r}"
                )
            score = row.get("hint_match_score")
            if not isinstance(score, int) or isinstance(score, bool) or score < 0:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {ref!r} hint_match_score "
                    f"must be a non-negative int; observed {score!r}"
                )
            this_key = (-score, ref)
            if prev_key is not None and this_key < prev_key:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: ranked_rows not ordered by "
                    f"(-hint_match_score, chain_preset_ref) at row {ref!r} "
                    f"(score={score}); the ordering must be the mechanical relevance sort"
                )
            prev_key = this_key

        # Optional pin: a real hint must rank a known preset at the top with a
        # minimum mechanical score (proving the mechanical match actually ranks).
        if expect_top_ref is not None:
            if not rows:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: expect_top_ref {expect_top_ref!r} "
                    "but ranked_rows is empty"
                )
            top = rows[0]
            if top.get("chain_preset_ref") != expect_top_ref:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: top ranked preset expected "
                    f"{expect_top_ref!r}, observed {top.get('chain_preset_ref')!r}"
                )
            if int(top.get("hint_match_score", -1)) < expect_min_top_score:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: top preset hint_match_score "
                    f"{top.get('hint_match_score')!r} < expect_min_top_score {expect_min_top_score}"
                )

        # scope filter: if a scope was declared, EVERY row must carry it.
        if catalog_scope is not None:
            offending = [
                row.get("chain_preset_ref")
                for row in rows
                if row.get("catalog_scope") != catalog_scope
            ]
            if offending:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: scope filter {catalog_scope!r} "
                    f"leaked off-scope presets {offending}"
                )

        # AXIS FIRE 1: NO pick/recommend field anywhere (top-level or per-row).
        # (rank / hint_match_score / ranked_rows are the LEGITIMATE mechanical
        # surface and are deliberately NOT forbidden.)
        top_hits = sorted(set(packet.keys()) & _PRESET_RANKING_FORBIDDEN_PICK_FIELDS)
        if top_hits:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: packet carries forbidden "
                f"pick/recommend field(s) at top level {top_hits}; the ranking is NON-BINDING "
                "and support must NEVER pick or recommend a preset"
            )
        for row in rows:
            row_hits = sorted(set(row.keys()) & _PRESET_RANKING_FORBIDDEN_PICK_FIELDS)
            if row_hits:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: ranked row "
                    f"{row.get('chain_preset_ref')!r} carries forbidden pick/recommend field(s) "
                    f"{row_hits}; the ranking is NON-BINDING"
                )

        # AXIS FIRE 2 (the biggest-unknown guard): even WITH this ranking
        # available, the materializer STILL hard-refuses a run with no/blank
        # chain_preset_ref. The ranking NEVER auto-applies. If the materializer
        # were made to fall back to the top-ranked preset, this goes RED.
        base_intent = {
            "declared_by": "coo",
            "task_source_ref": "brick_protocol/brick/templates/tasks/source-template.md",
            "selected_adapter_ref": "adapter:codex-local",
            "write_scope": {
                "allowed_paths": ["brick_protocol/support/operator/**"],
                "forbidden_paths": [".git/**"],
            },
        }
        for variant_name, variant in (
            ("omitted-chain-preset-ref", dict(base_intent)),
            ("blank-chain-preset-ref", dict(base_intent, chain_preset_ref="")),
        ):
            try:
                materialize_building_intent(variant, repo_root=repo)
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: materialize_building_intent did "
                    f"NOT raise for {variant_name}; with a ranking available the materializer MUST "
                    "still hard-refuse a run without an explicit confirmed preset (the ranking is "
                    "non-binding and must NEVER auto-apply the top-ranked preset)"
                )

        count += 1
    return count

