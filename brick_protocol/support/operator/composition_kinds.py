"""Kind / step-template resolution + did-you-mean hints.

Smallest clean leaf extracted from the pre-split composition module: maps a chain preset's
step_template_ref to its catalog entry, and turns an unresolved ref into a
discoverable error suffix (nearest-kind suggestion + the live kind list).
"""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from typing import Any

from brick_protocol.support.operator.building_operation_common import _clean_text
from brick_protocol.support.operator.plan_rendering import RETIRED_STEP_TEMPLATE_REFS


_STEP_TEMPLATE_PREFIX = "building-step-template:"

# Semantic synonyms a caller naturally reaches for that are NOT lexical typos
# (difflib can't bridge them -- 'implementation' vs 'development' share too few
# characters). Each maps a natural word to the live kind it means. Kept tiny and
# explicit; difflib still catches ordinary spelling slips on top of this.
_KIND_SYNONYMS = {
    "implementation": "development",
    "implement": "development",
    "build": "work",
    "code": "work",
    "qa": "code-attack-qa",
    "verify": "review",
    "verification": "review",
}


def _known_kinds(registry: Mapping[str, Any]) -> list[str]:
    """The catalog's live kinds (step_templates keys, prefix stripped), sorted."""
    step_templates = registry.get("step_templates", {})
    if not isinstance(step_templates, Mapping):
        return []
    kinds = {
        str(ref).removeprefix(_STEP_TEMPLATE_PREFIX)
        for ref in step_templates
        if isinstance(ref, str)
    }
    return sorted(kinds)


def _unknown_kind_hint(step_template_ref: str, registry: Mapping[str, Any]) -> str:
    """Discoverability suffix for an unresolved step_template_ref: a nearest-kind
    suggestion (e.g. a 'implementation' typo points at 'development') plus the
    full list of live kinds, sourced from the catalog so it never drifts. Returns
    '' when no kinds are enumerable."""
    kinds = _known_kinds(registry)
    if not kinds:
        return ""
    typed = step_template_ref.removeprefix(_STEP_TEMPLATE_PREFIX)
    suggestion = _KIND_SYNONYMS.get(typed.lower())
    if suggestion not in kinds:  # synonym must point at a live kind, else fall back
        suggestion = None
    if suggestion is None:
        close = difflib.get_close_matches(typed, kinds, n=1, cutoff=0.6)
        suggestion = close[0] if close else None
    did_you_mean = f"; did you mean {suggestion!r}?" if suggestion else ""
    return f"{did_you_mean} (known kinds: {', '.join(kinds)})"


def _materializer_step_template(
    registry: Mapping[str, Any],
    step_template_ref: str,
) -> Mapping[str, Any]:
    step_templates = registry.get("step_templates", {})
    if not isinstance(step_templates, Mapping):
        raise ValueError("shape registry step_templates must be a mapping")
    step_template = step_templates.get(step_template_ref)
    if not isinstance(step_template, Mapping):
        if step_template_ref in RETIRED_STEP_TEMPLATE_REFS:
            raise ValueError(
                f"chain preset step_template_ref {step_template_ref} is retired: "
                f"use {RETIRED_STEP_TEMPLATE_REFS[step_template_ref]}"
            )
        raise ValueError(
            f"chain preset step_template_ref is not in catalog: {step_template_ref}"
            f"{_unknown_kind_hint(step_template_ref, registry)}"
        )
    return step_template


def _materializer_step_alias(raw_step: Mapping[str, Any], index: int) -> str | None:
    if "step_alias" not in raw_step:
        return None
    return _clean_text(
        f"chain preset steps[{index}].step_alias",
        raw_step.get("step_alias", ""),
    )
