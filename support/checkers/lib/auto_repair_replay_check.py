"""Auto repair replay behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    require_string_list,
    rule_items,
)


def run_auto_repair_replay_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "auto_repair_replay_case")
    if not items:
        return 0
    from support.operator.auto_repair_replay import prepare_declared_auto_repair_replay_case
    count = 0
    for item in items:
        mapping = require_mapping(item, "auto_repair_replay_case item")
        case, relative = _profile_case_document(repo, mapping, "auto_repair_replay_case")
        prepared = prepare_declared_auto_repair_replay_case(case, repo)
        expected = require_mapping(mapping.get("expected", {}), "auto_repair_replay_case.expected")
        for key in (
            "movement",
            "target_ref",
            "repair_replay_building_id",
            "materialized",
            "materialization_state",
            "materialization_reason",
            "required_disposition_owner",
        ):
            if key in expected and prepared.get(key) != expected.get(key):
                raise ProfileError(
                    f"auto_repair_replay_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {prepared.get(key)!r}"
                )
        for absent_key in require_string_list(
            expected.get("absent_keys", []),
            "auto_repair_replay_case.expected.absent_keys",
        ):
            if prepared.get(absent_key) is not None:
                raise ProfileError(
                    f"auto_repair_replay_case rejected {relative}: "
                    f"{absent_key} must be absent"
                )
        count += 1
    return count
