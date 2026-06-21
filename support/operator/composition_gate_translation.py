"""Gate-concept token -> gate-ref translation + portfolio closure-gate stamping.

Extracted verbatim from composition.py (cluster ``composition_gate_translation``).
The materializer TRANSLATES a preset's DECLARED ``gate_concept_profile`` tokens
into live ``declared_gate_refs`` on specific rows (mechanical; provenance = the
preset declared the label). The token -> ref map is the Link plan grammar,
single-sourced in link/spec.py via ``translate_gate_concept``; this support
module imports the reader instead of re-stating it. Support invents no gate, no
provenance, and judges no quality/success.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.link.spec import translate_gate_concept
from brick_protocol.support.operator.building_operation_common import (
    _clean_text,
)
from brick_protocol.support.operator.plan_rendering import (
    _load_shape_registry,
)


UNSUPPORTED_MATERIALIZER_TARGET_WORDS = ("child_building_runs", "portfolio_closure")
_QA_ROLE_NEED = "reviewer"


def _materializer_gate_concept_tokens(preset: Mapping[str, Any]) -> tuple[str, ...]:
    """Read the preset's DECLARED gate_concept_profile tokens (verbatim order).

    Mechanical read only: absent / non-list profile -> empty tuple (nothing is
    stamped). Unknown tokens stay in the tuple untouched; only tokens present in
    GATE_CONCEPT_TOKEN_GATE_REFS ever translate to a live gate ref.
    """

    raw = preset.get("gate_concept_profile", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(
        str(item).strip() for item in raw if isinstance(item, str) and str(item).strip()
    )


def _materializer_profile_gate_translations(
    tokens: Sequence[str],
    *,
    qa_row: bool,
    final_transition_row: bool,
) -> tuple[tuple[str, str], ...]:
    """The (token, gate_ref) pairs that translate onto ONE row.

    Single placement source of truth (operator design rule, see the
    GATE_CONCEPT_TOKEN_GATE_REFS comment): strict on QA rows; coo + human on
    the final transition row only. Both the stamped refs and the stamped
    provenance derive from this list, so they cannot drift apart.
    """

    pairs: list[tuple[str, str]] = []
    if qa_row and "strict-evidence" in tokens:
        pairs.append(("strict-evidence", translate_gate_concept("strict-evidence")))
    if final_transition_row:
        if "coo-review" in tokens:
            pairs.append(("coo-review", translate_gate_concept("coo-review")))
        if "human-review" in tokens:
            pairs.append(("human-review", translate_gate_concept("human-review")))
    return tuple(pairs)


def _materializer_gate_concept_provenance(
    translations: Sequence[tuple[str, str]],
    *,
    chain_preset_ref: str,
) -> dict[str, Any]:
    """Machine-readable provenance for one TRANSLATED gate stamp (A1, 0610).

    Recorded ONLY when translation happened (caller guards on non-empty
    translations): tokens = the preset-declared gate_concept_profile tokens
    that landed on THIS row, declared_by = the declaring chain preset ref
    verbatim. Mirrors the budget / closure-policy provenance stamps (an
    auditor can confirm support never injected the gate); support invents
    neither tokens nor the declaring ref.
    """

    return {
        "tokens": [token for token, _gate_ref in translations],
        "declared_by": chain_preset_ref,
    }


def _materializer_human_gate_hold_policy() -> list[Mapping[str, Any]]:
    """The canonical declared hold policy for a human-review final gate.

    FIXED translation of the human-review token (not a support choice): the
    link/gate.yaml meaning of link-gate:human is "human disposition evidence
    required before transition resumes", so the policy HOLDs (existing
    gate_sequence machinery, required_disposition_owner=caller-or-coo) while
    route_decision_basis.human_review_refs is absent and forwards once the
    human disposition fact exists. Support decides nothing at run time; the
    walk pauses via the SAME hold path every declared policy uses.

    SCOPE (codex review, 0610): this policy is the ONLY hold surface ADDED BY
    THE GATE-CONCEPT TRANSLATION. It does NOT replace or claim exclusivity
    over pre-existing AUTHOR-declared gate_sequence_policy holds (e.g.
    brick-protocol-engine-feature-hard's design->work coo HOLD), which are
    untouched and still hold on their own rows.
    """

    return [
        {
            "gate_ref": translate_gate_concept("human-review"),
            "on_missing_required_facts": {
                "action": "hold",
                "pending_target_basis": "source_brick",
                "required_disposition_owner": "caller-or-coo",
                "reason_refs": ["observation:human-gate-disposition-missing"],
            },
            "on_sufficient": {"action": "forward"},
        }
    ]


def declared_portfolio_gate_translations(
    chain_preset_ref: str,
    *,
    repo_root: str | Path | None = None,
) -> Mapping[str, Any]:
    """Translate a DECLARED portfolio preset's gate_concept_profile tokens.

    DRIVER-PATH GATE WIRING (0611, completes the 0610 option-가 translation):
    the portfolio presets (steps routed through the portfolio target words)
    cannot pass ``materialize_building_intent`` -- their gate labels were
    therefore decorative on the driver path. This helper is the SAME
    single-source translation the materializer uses
    (``_materializer_profile_gate_translations`` over
    ``GATE_CONCEPT_TOKEN_GATE_REFS``), applied with the portfolio's only
    placement: the FINAL transition row (the closure of the LAST driven child
    Building == the portfolio closure boundary). It translates; it does not
    judge, hold, or choose Movement. MODE tokens (portfolio-policy /
    fan-in-wait-all / default-transition) still translate to NO gate ref.

    Fail-closed: an unknown preset ref, or a preset that is NOT a portfolio
    route, is a loud ValueError -- a declared label never silently evaporates.
    """

    from brick_protocol.support.operator.composition_common import _chain_preset_steps

    repo = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    ref = _clean_text("chain_preset_ref", chain_preset_ref)
    registry = _load_shape_registry(repo)
    chain_presets = registry.get("chain_presets", {})
    if not isinstance(chain_presets, Mapping):
        raise ValueError("shape registry chain_presets must be a mapping")
    preset = chain_presets.get(ref)
    if not isinstance(preset, Mapping):
        raise ValueError(f"portfolio chain_preset_ref is not in the Brick template catalog: {ref}")
    target_words = tuple(
        str(step.get("target_word", "")).strip()
        for step in _chain_preset_steps(preset)
        if isinstance(step, Mapping)
    )
    if not any(word in UNSUPPORTED_MATERIALIZER_TARGET_WORDS for word in target_words):
        raise ValueError(
            f"chain_preset_ref {ref} is not a portfolio preset; "
            "non-portfolio presets translate at materialize_building_intent"
        )
    tokens = _materializer_gate_concept_tokens(preset)
    translations = _materializer_profile_gate_translations(
        tokens,
        qa_row=False,
        final_transition_row=True,
    )
    return {
        "chain_preset_ref": ref,
        "declared_tokens": tokens,
        "translations": translations,
        "gate_refs": tuple(gate_ref for _token, gate_ref in translations),
    }


def stamp_declared_portfolio_closure_gates(
    plan: Mapping[str, Any],
    *,
    chain_preset_ref: str,
    repo_root: str | Path | None = None,
    route_decision_basis: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Stamp a portfolio preset's translated closure gates onto ONE child plan.

    The TERMINAL driven child's closing Link row IS the portfolio closure
    boundary, so the preset-declared review gates land there -- mechanically,
    with ``gate_concept_provenance`` recording WHICH tokens and WHICH preset
    declared them (support invents nothing; no declaring preset -> the caller
    never reaches this function). The stamped plan is a NEW mapping; the
    declared input is not mutated. Runtime evaluation stays entirely with the
    EXISTING engine gate machinery (run.py / link/gate.py untouched).

    Mechanics, all fail-closed:
    * closing rows = Link rows whose ``building_lifecycle.state == "closed"``
      (both plan shapes: linear ``steps[].rows[]`` and graph
      ``link_edges[].rows[]``); none found -> ValueError.
    * a closing row that already carries ``gate_concept_provenance`` cannot be
      re-declared by a second preset (single-declarer provenance law) ->
      ValueError when a new ref would be stamped there.
    * the human gate needs its canonical hold policy; a closing row that
      already carries its OWN ``gate_sequence_policy`` cannot be merged
      mechanically -> ValueError when the human ref would be stamped there.
    * translated refs already declared on the row -> nothing stamped there
      (recorded as already_declared; no provenance is invented).
    * ``route_decision_basis`` (caller/COO-declared disposition facts from the
      portfolio packet) is copied onto a stamped review-gated row only when
      the row has no basis of its own -- the same mechanical carry rule as
      ``_materializer_apply_route_decision_basis``.
    """

    summary_base = declared_portfolio_gate_translations(
        chain_preset_ref,
        repo_root=repo_root,
    )
    translations = summary_base["translations"]
    if not translations:
        return plan, {
            **summary_base,
            "stamped": False,
            "stamped_gate_refs": (),
            "reason": "declared gate_concept_profile carries no translating tokens",
        }
    human_ref = translate_gate_concept("human-review")
    basis: Mapping[str, Any] | None = None
    if route_decision_basis:
        if not isinstance(route_decision_basis, Mapping):
            raise TypeError("route_decision_basis must be a mapping")
        basis = dict(route_decision_basis)

    stamped_rows = 0
    already_declared_rows = 0
    stamped_gate_refs: list[str] = []

    def _stamped_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal stamped_rows, already_declared_rows, stamped_gate_refs
        lifecycle = row.get("building_lifecycle")
        if (
            row.get("axis") != "Link"
            or not isinstance(lifecycle, Mapping)
            or lifecycle.get("state") != "closed"
        ):
            return row
        declared_refs = list(row.get("declared_gate_refs") or [])
        row_translations = tuple(
            (token, gate_ref)
            for token, gate_ref in translations
            if gate_ref not in declared_refs
        )
        if not row_translations:
            already_declared_rows += 1
            return row
        if "gate_concept_provenance" in row:
            raise ValueError(
                "portfolio closure row already carries gate_concept_provenance "
                "from its own declaring preset; a second declarer cannot stamp "
                f"over it (row {row.get('row_ref')!r})"
            )
        new_row = dict(row)
        new_row["declared_gate_refs"] = [
            *declared_refs,
            *(gate_ref for _token, gate_ref in row_translations),
        ]
        new_row["gate_concept_provenance"] = _materializer_gate_concept_provenance(
            row_translations,
            chain_preset_ref=summary_base["chain_preset_ref"],
        )
        if any(gate_ref == human_ref for _token, gate_ref in row_translations):
            if "gate_sequence_policy" in row:
                raise ValueError(
                    "portfolio closure row already carries its own "
                    "gate_sequence_policy; the human-review hold policy cannot "
                    f"be merged mechanically (row {row.get('row_ref')!r})"
                )
            new_row["gate_sequence_policy"] = _materializer_human_gate_hold_policy()
        if basis is not None and "route_decision_basis" not in row:
            new_row["route_decision_basis"] = dict(basis)
        stamped_rows += 1
        for _token, gate_ref in row_translations:
            if gate_ref not in stamped_gate_refs:
                stamped_gate_refs.append(gate_ref)
        return new_row

    def _stamped_groups(groups: Any) -> Any:
        if not isinstance(groups, list):
            return groups
        patched_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, Mapping) or not isinstance(group.get("rows"), list):
                patched_groups.append(group)
                continue
            patched_group = dict(group)
            patched_group["rows"] = [
                _stamped_row(row) if isinstance(row, Mapping) else row
                for row in group["rows"]
            ]
            patched_groups.append(patched_group)
        return patched_groups

    stamped_plan = dict(plan)
    for group_key in ("steps", "link_edges"):
        if group_key in stamped_plan:
            stamped_plan[group_key] = _stamped_groups(stamped_plan[group_key])
    if stamped_rows == 0 and already_declared_rows == 0:
        raise ValueError(
            "portfolio terminal child plan carries no closing Link row "
            "(building_lifecycle.state == 'closed'); the declared portfolio "
            "closure gates have nowhere to land"
        )
    return stamped_plan, {
        **summary_base,
        "stamped": stamped_rows > 0,
        "stamped_rows": stamped_rows,
        "already_declared_rows": already_declared_rows,
        "stamped_gate_refs": tuple(stamped_gate_refs),
    }
