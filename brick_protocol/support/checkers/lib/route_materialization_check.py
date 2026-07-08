"""Route materialization behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    load_yaml_subset_file,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)


def run_route_materialization_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "route_materialization_case")
    if not items:
        return 0
    from brick_protocol.support.operator.route_materialization import materialize_route_transition
    count = 0
    for item in items:
        mapping = require_mapping(item, "route_materialization_case item")
        case, relative = _profile_case_document(repo, mapping, "route_materialization_case")
        policy = load_yaml_subset_file(
            repo,
            require_string(case.get("route_policy_path"), f"{relative}: route_policy_path"),
        )
        result = materialize_route_transition(
            require_mapping(case.get("route_request"), f"{relative}: route_request"),
            policy,
            require_mapping(case.get("declared_route_replay_plan"), f"{relative}: declared_route_replay_plan"),
        )
        expected = require_mapping(case.get("expected"), f"{relative}: expected")
        for key in ("match_state", "route_path_ref", "movement", "target_ref"):
            if key in expected and result.get(key) != expected.get(key):
                raise ProfileError(
                    f"route_materialization_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {result.get(key)!r}"
                )
        expected_replay_refs = expected.get("replay_segment_refs")
        if expected_replay_refs is not None:
            replay_refs = result.get("link_row", {}).get("route_replay_plan", {}).get("replay_segment_refs")
            if replay_refs != require_string_list(expected_replay_refs, f"{relative}: expected.replay_segment_refs"):
                raise ProfileError(
                    f"route_materialization_case rejected {relative}: replay_segment_refs mismatch"
                )
        count += 1
    return count
