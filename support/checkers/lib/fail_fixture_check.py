"""Fail fixture rejection behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.rule_runners import (
    _admitted_agent_object_refs,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)
from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    require_string,
    rule_items,
)


def run_fail_fixture_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    validators = {
        "building_plan_boundary": lambda document, label: validate_building_plan_boundary(
            document,
            label,
            _admitted_agent_object_refs(repo),
            repo,
        ),
        "route_policy_boundary": validate_route_policy_boundary,
    }
    for item in rule_items(profile, "fail_fixture_rejects"):
        mapping = require_mapping(item, "fail_fixture_rejects item")
        kind = require_string(mapping.get("kind"), "fail_fixture_rejects.kind")
        document, relative = _profile_case_document(repo, mapping, "fail_fixture_rejects")
        validator = validators.get(kind)
        if validator is None:
            raise ProfileError(f"fail_fixture_rejects has unknown kind: {kind}")
        try:
            validator(document, relative)
        except ProfileError:
            count += 1
            continue
        raise ProfileError(f"fail_fixture_rejects expected rejection but passed: {relative}")
    return count

