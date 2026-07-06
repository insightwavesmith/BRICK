"""Write-scope default exclude behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


def run_write_scope_default_exclude_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "write_scope_default_exclude_case")
    if not items:
        return 0
    count = 0
    for item in items:
        mapping = require_mapping(item, "write_scope_default_exclude_case item")
        label = require_string(mapping.get("label"), "write_scope_default_exclude_case.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        if case_kind == "provider_residue_excluded":
            _check_provider_residue_excluded(label)
        elif case_kind == "directory_allowed_path_is_not_recursive":
            _check_directory_allowed_path_is_not_recursive(label)
        elif case_kind == "explicit_wildcard_allows_children":
            _check_explicit_wildcard_allows_children(label)
        elif case_kind == "segment_wildcard_rejects_nested_child":
            _check_segment_wildcard_rejects_nested_child(label)
        elif case_kind == "recursive_wildcard_allows_nested_child":
            _check_recursive_wildcard_allows_nested_child(label)
        elif case_kind == "root_wildcard_matches_single_segment_only":
            _check_root_wildcard_matches_single_segment_only(label)
        elif case_kind == "token_shaped_filename_short_marker_accepted":
            _check_token_shaped_filename_short_marker_accepted(label)
        elif case_kind == "raw_secret_rejected":
            _check_raw_secret_rejected(label)
        elif case_kind == "building_plan_support_result_no_record_converter":
            _check_building_plan_support_result_no_record_converter(label)
        elif case_kind == "dirty_root_reuse_requires_overwrite_or_new_root":
            _check_dirty_root_reuse_requires_overwrite_or_new_root(label)
        else:
            raise ProfileError(f"unknown write_scope_default_exclude case_kind: {case_kind}")
        count += 1
    return count


def _check_provider_residue_excluded(label: str) -> None:
    from support.operator.write_observation import (
        _is_write_observation_default_excluded_residue,
        _observed_file_snapshot,
    )

    if not _is_write_observation_default_excluded_residue(Path(".claude/launch.json")):
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: .claude residue not excluded")
    # W2 DOC-DECOUPLE FIRE (0611): the 3 provider-residue names were previously
    # stated only in the (now archived) 0526 spec doc text pin — decoration, not
    # enforcement (removing a name from the code set never REDed). Probe the
    # exact residue set membership so a silent narrowing of the default-exclude
    # set goes RED via the CODE path.
    for residue_path in ("x/__pycache__/y.pyc", "x/.ruff_cache/z", "x/.DS_Store"):
        if not _is_write_observation_default_excluded_residue(Path(residue_path)):
            raise ProfileError(
                f"write_scope_default_exclude_case rejected {label}: provider residue {residue_path} not excluded"
            )
    with tempfile.TemporaryDirectory(prefix="bp-write-scope-default-exclude-") as tmpdir:
        root = Path(tmpdir)
        (root / ".claude").mkdir()
        (root / ".claude" / "launch.json").write_text("{}", encoding="utf-8")
        (root / "work").mkdir()
        (root / "work" / "kept.txt").write_text("kept", encoding="utf-8")
        snapshot = _observed_file_snapshot(root)
    if ".claude/launch.json" in snapshot:
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: .claude file observed")
    if "work/kept.txt" not in snapshot:
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: non-residue file missing")


def _check_directory_allowed_path_is_not_recursive(label: str) -> None:
    # REDO (Smith 0623 struct-surgery): a directory-style allowed path is still NOT
    # recursive -- the child path falls outside the declared scope -- but the
    # written-vs-scope classification moved OUT of write_observation INTO the Brick
    # axis (brick.comparison) and the disposition is a RECORDED FACT, not a raise.
    # The probe asserts the Brick comparison records the child under
    # observed_paths_outside_declared_scope (an explicit wildcard still admits the
    # child, covered by _check_explicit_wildcard_allows_children).
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["project/example/work/building-map.json"],
        {"allowed_paths": ["project/example"]},
    )
    outside = facts.get("observed_paths_outside_declared_scope", [])
    if "project/example/work/building-map.json" not in outside:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: a directory-allowed "
            "child path must be RECORDED as observed_paths_outside_declared_scope by "
            f"brick.comparison (directory scope is not recursive; move+record only), "
            f"observed {facts!r}"
        )


def _check_explicit_wildcard_allows_children(label: str) -> None:
    # REDO (Smith 0623 struct-surgery): the written-vs-scope comparison moved to the
    # Brick axis. An explicit ``**`` wildcard must admit the child -- i.e. the Brick
    # comparison records NO out-of-scope bucket for it.
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["project/example/work/building-map.json"],
        {"allowed_paths": ["project/example/**"]},
    )
    if facts.get("observed_paths_outside_declared_scope"):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: wildcard did not "
            f"allow child (brick.comparison recorded it out-of-scope), observed {facts!r}"
        )


def _check_segment_wildcard_rejects_nested_child(label: str) -> None:
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["a/b/c"],
        {"allowed_paths": ["a/*"]},
    )
    outside = facts.get("observed_paths_outside_declared_scope", [])
    if "a/b/c" not in outside:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: segment wildcard "
            f"accepted nested child; observed {facts!r}"
        )


def _check_recursive_wildcard_allows_nested_child(label: str) -> None:
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["a/b/c"],
        {"allowed_paths": ["a/**"]},
    )
    if facts.get("observed_paths_outside_declared_scope"):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: recursive wildcard "
            f"did not allow nested child; observed {facts!r}"
        )


def _check_root_wildcard_matches_single_segment_only(label: str) -> None:
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    single = compare_changed_paths_to_write_scope(
        ["leaf.txt"],
        {"allowed_paths": ["*"]},
    )
    if single.get("observed_paths_outside_declared_scope"):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: root wildcard "
            f"did not allow one segment; observed {single!r}"
        )
    nested = compare_changed_paths_to_write_scope(
        ["dir/leaf.txt"],
        {"allowed_paths": ["*"]},
    )
    outside = nested.get("observed_paths_outside_declared_scope", [])
    if "dir/leaf.txt" not in outside:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: root wildcard "
            f"accepted nested child; observed {nested!r}"
        )


def _check_token_shaped_filename_short_marker_accepted(label: str) -> None:
    from support.operator.primitives import _FORBIDDEN_PAYLOAD_KEYS, _validate_no_payload_forbidden

    try:
        _validate_no_payload_forbidden(
            "plan",
            # W2 DOC-DECOUPLE (0611): synthetic NON-EXISTENT filename (in-memory
            # payload only); the probe needs a short 'sk-' basename that must
            # NOT be misdetected as a raw secret. Neutral template-tree prefix,
            # no status/kernel doc-shape reference.
            {"task_source_ref": "brick/templates/tasks/sk-demo.md"},
            _FORBIDDEN_PAYLOAD_KEYS,
        )
    except ValueError as exc:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: short marker filename rejected"
        ) from exc


def _check_raw_secret_rejected(label: str) -> None:
    from support.operator.primitives import _FORBIDDEN_PAYLOAD_KEYS, _validate_no_payload_forbidden

    raw_secret = "sk-" + ("a" * 16)
    try:
        _validate_no_payload_forbidden(
            "plan",
            {"task_source_ref": raw_secret},
            _FORBIDDEN_PAYLOAD_KEYS,
        )
    except ValueError as exc:
        if "raw credential-looking text" not in str(exc):
            raise ProfileError(
                f"write_scope_default_exclude_case rejected {label}: wrong raw secret rejection {exc}"
            ) from exc
        return
    raise ProfileError(f"write_scope_default_exclude_case expected raw secret rejection: {label}")


def _check_building_plan_support_result_no_record_converter(label: str) -> None:
    from support.operator.contracts import BuildingPlanSupportResult

    method_name = "to_" + "record"
    if hasattr(BuildingPlanSupportResult, method_name):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: unexpected record converter API"
        )


def _check_dirty_root_reuse_requires_overwrite_or_new_root(label: str) -> None:
    from support.operator.run import _preflight_step_output_building_root

    with tempfile.TemporaryDirectory(prefix="bp-dirty-root-reuse-") as tmpdir:
        root = Path(tmpdir)
        building_id = "checker-dirty-root"
        (root / building_id).mkdir()
        try:
            _preflight_step_output_building_root(
                root,
                building_id,
                overwrite_existing=False,
            )
        except FileExistsError as exc:
            if "choose a new building_id or pass overwrite_existing=True" not in str(exc):
                raise ProfileError(
                    f"write_scope_default_exclude_case rejected {label}: wrong root reuse rejection {exc}"
                ) from exc
            return
    raise ProfileError(f"write_scope_default_exclude_case expected dirty-root rejection: {label}")
