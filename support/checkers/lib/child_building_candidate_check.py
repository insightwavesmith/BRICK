"""Child Building candidate behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.rule_runners import (
    _admitted_agent_object_refs,
    validate_building_plan_boundary,
)
from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    rule_items,
)


def run_child_building_candidate_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "child_building_candidate_case")
    if not items:
        return 0
    from support.operator.child_building_generation import prepare_child_building_candidate_case
    count = 0
    for item in items:
        mapping = require_mapping(item, "child_building_candidate_case item")
        case, relative = _profile_case_document(repo, mapping, "child_building_candidate_case")
        prepared = prepare_child_building_candidate_case(case)
        validate_building_plan_boundary(
            prepared["candidate_plan"],
            f"{relative}: candidate_plan",
            _admitted_agent_object_refs(repo),
            repo,
        )
        expected = require_mapping(mapping.get("expected", {}), "child_building_candidate_case.expected")
        for key in ("selected_delta_ref", "candidate_building_id"):
            if key in expected and prepared.get(key) != expected.get(key):
                raise ProfileError(
                    f"child_building_candidate_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {prepared.get(key)!r}"
                )
        count += 1
    return count
