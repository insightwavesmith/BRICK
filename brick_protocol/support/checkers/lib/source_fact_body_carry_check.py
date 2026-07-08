"""Source fact body carry behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from brick_protocol.support.checkers.lib.adapter_capability_checks import _optional_non_negative_int
from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)


def run_source_fact_body_carry_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "source_fact_body_carry_case")
    if not items:
        return 0
    from brick_protocol.support.operator.walker_kernel import _source_fact_body_carry_for_step

    count = 0
    for item in items:
        mapping = require_mapping(item, "source_fact_body_carry_case item")
        label = require_string(mapping.get("label"), "source_fact_body_carry_case.label")
        target_step_ref = require_string(
            mapping.get("target_step_ref"),
            f"{label}: target_step_ref",
        )
        cascade_depth = _optional_non_negative_int(
            mapping.get("cascade_depth", 0),
            f"{label}: cascade_depth",
        )
        source_facts = require_string_list(
            mapping.get("consumer_source_facts", []),
            f"{label}: consumer_source_facts",
        )
        step_results, step_result_events = _source_fact_body_carry_step_results(
            mapping,
            label=label,
            default_cascade_depth=cascade_depth,
        )
        building_id = str(mapping.get("building_id", "") or "checker-source-fact-body-carry")
        with tempfile.TemporaryDirectory(prefix="bp-source-fact-body-carry-") as tmpdir:
            building_root = Path(tmpdir) / building_id
            _write_source_fact_body_carry_outputs(
                building_root,
                building_id,
                step_results,
            )
            result = _source_fact_body_carry_for_step(
                building_root=building_root,
                building_id=building_id,
                target_step_ref=target_step_ref,
                cascade_depth=cascade_depth,
                step={"rows": [{"axis": "Brick", "source_facts": source_facts}]},
                step_results=step_results,
                step_result_events=step_result_events,
                fan_in_sources_by_target=_source_fact_body_carry_fan_in_sources(mapping, label),
            )
        observation = result.get("observation")
        if not isinstance(observation, Mapping):
            raise ProfileError(f"source_fact_body_carry_case rejected {label}: observation missing")
        expected = require_mapping(
            mapping.get("expected", {}),
            f"{label}: expected",
        )
        _check_expected_bool(
            observation,
            expected,
            key="body_absent",
            label=label,
        )
        _check_expected_sequence(
            list(result.get("source_fact_bodies", {})),
            expected,
            key="source_fact_body_refs",
            label=label,
        )
        _check_expected_sequence(
            list(observation.get("declared_source_fact_refs", ())),
            expected,
            key="declared_source_fact_refs",
            label=label,
        )
        _check_expected_sequence(
            list(observation.get("missing_source_fact_refs", ())),
            expected,
            key="missing_source_fact_refs",
            label=label,
        )
        _check_expected_sequence_contains(
            list(observation.get("missing_source_fact_refs", ())),
            expected,
            key="missing_source_fact_refs_contains",
            label=label,
        )
        _check_source_fact_body_expectations(
            result.get("source_fact_bodies", {}),
            expected.get("body_expectations", []),
            label=label,
        )
        count += 1
    return count


def _write_source_fact_body_carry_outputs(
    building_root: Path,
    building_id: str,
    step_results: list[Any],
) -> None:
    from brick_protocol.support.recording.contracts import StepOutputObservation
    from brick_protocol.support.recording.step_outputs import write_step_output

    counts: dict[str, int] = {}
    for index, result in enumerate(step_results, start=1):
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        write_step_output(
            building_root,
            building_id,
            StepOutputObservation(
                building_id=building_id,
                step_ref=step_ref,
                brick_instance_ref=result.preparation.brick_instance_ref,
                agent_object_ref=result.preparation.agent_object.object_ref,
                returned=result.adapter_result.returned_value,
                received_work_ref=f"brick-work:{index:02d}:{step_ref}",
                returned_fact_ref=f"agent-fact:{index:02d}:{step_ref}",
                raw_ref=f"raw:agent:{index:02d}",
                not_proven=tuple(result.not_proven),
                recorded_at="2026-01-01T00:00:00Z",
            ),
            attempt_index=counts[step_ref],
            proof_limits=("support checker synthetic result only",),
            recorded_at="2026-01-01T00:00:00Z",
        )


def _source_fact_body_carry_step_results(
    mapping: Mapping[str, Any],
    *,
    label: str,
    default_cascade_depth: int,
) -> tuple[list[Any], list[Mapping[str, Any]]]:
    raw_items = mapping.get("upstream_results", [])
    if not isinstance(raw_items, list):
        raise ProfileError(f"{label}: upstream_results must be a list")
    step_results: list[Any] = []
    step_result_events: list[Mapping[str, Any]] = []
    for index, raw_item in enumerate(raw_items, start=1):
        item = require_mapping(raw_item, f"{label}: upstream_results[{index}]")
        step_ref = require_string(item.get("step_ref"), f"{label}: upstream_results[{index}].step_ref")
        cascade_depth = _optional_non_negative_int(
            item.get("cascade_depth", default_cascade_depth),
            f"{label}: upstream_results[{index}].cascade_depth",
        )
        returned = item.get("returned", {})
        if not isinstance(returned, Mapping):
            raise ProfileError(f"{label}: upstream_results[{index}].returned must be a mapping")
        step_results.append(_source_fact_body_carry_synthetic_result(step_ref, returned))
        step_result_events.append({"step_ref": step_ref, "cascade_depth": cascade_depth})
    return step_results, step_result_events


def _source_fact_body_carry_synthetic_result(step_ref: str, returned: Mapping[str, Any]) -> Any:
    return SimpleNamespace(
        preparation=SimpleNamespace(
            step_rows=SimpleNamespace(step_ref=step_ref),
            brick_instance_ref=f"brick:{step_ref}",
            agent_object=SimpleNamespace(object_ref="agent-object:checker-local"),
        ),
        adapter_result=SimpleNamespace(returned_value=dict(returned)),
        proof_limits=("support checker synthetic result only",),
        not_proven=("semantic sufficiency of carried body",),
    )


def _source_fact_body_carry_fan_in_sources(
    mapping: Mapping[str, Any],
    label: str,
) -> Mapping[str, tuple[str, ...]]:
    raw_sources = mapping.get("fan_in_sources_by_target", {})
    if not isinstance(raw_sources, Mapping):
        raise ProfileError(f"{label}: fan_in_sources_by_target must be a mapping")
    return {
        require_string(target, f"{label}: fan_in_sources_by_target target"): tuple(
            require_string_list(sources, f"{label}: fan_in_sources_by_target[{target}]")
        )
        for target, sources in raw_sources.items()
    }


def _check_expected_bool(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_value = expected[key]
    if not isinstance(expected_value, bool):
        raise ProfileError(f"{label}: expected.{key} must be a boolean")
    if bool(observed.get(key)) != expected_value:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} expected {expected_value!r}, observed {observed.get(key)!r}"
        )


def _check_expected_sequence(
    observed: Sequence[str],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_items = require_string_list(expected.get(key, []), f"{label}: expected.{key}")
    if list(observed) != expected_items:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} expected {expected_items!r}, observed {list(observed)!r}"
        )


def _check_expected_sequence_contains(
    observed: Sequence[str],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_items = require_string_list(expected.get(key, []), f"{label}: expected.{key}")
    missing = [item for item in expected_items if item not in observed]
    if missing:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} missing {missing!r}, observed {list(observed)!r}"
        )


def _check_source_fact_body_expectations(
    source_fact_bodies: Any,
    raw_expectations: Any,
    *,
    label: str,
) -> None:
    if not raw_expectations:
        return
    if not isinstance(source_fact_bodies, Mapping):
        raise ProfileError(f"source_fact_body_carry_case rejected {label}: bodies missing")
    if not isinstance(raw_expectations, list):
        raise ProfileError(f"{label}: expected.body_expectations must be a list")
    for index, raw in enumerate(raw_expectations, start=1):
        item = require_mapping(raw, f"{label}: expected.body_expectations[{index}]")
        source_fact_ref = require_string(
            item.get("source_fact_ref"),
            f"{label}: expected.body_expectations[{index}].source_fact_ref",
        )
        returned_marker = require_string(
            item.get("returned_marker"),
            f"{label}: expected.body_expectations[{index}].returned_marker",
        )
        body = source_fact_bodies.get(source_fact_ref)
        if not isinstance(body, str):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"missing body for {source_fact_ref}"
            )
        from brick_protocol.support.operator.walker_kernel import (
            _WIKI_CARRY_NOTE,
            _WIKI_CARRY_VIEW_HEADER,
            wiki_carry_path_text,
            wiki_carry_summary_text,
        )

        # WIKI-CARRY shape pin: the carried body is a compact wiki VIEW
        # (summary + absolute path + note), NOT the full step-output envelope.
        if not body.startswith(_WIKI_CARRY_VIEW_HEADER):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} body is not a wiki carry view"
            )
        if _WIKI_CARRY_NOTE not in body:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing note"
            )
        carry_path = wiki_carry_path_text(body)
        if not carry_path or not Path(carry_path).is_absolute():
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing absolute path"
            )
        if not carry_path.endswith("step-output.json"):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry path does not point at a step-output file"
            )
        summary = wiki_carry_summary_text(body)
        if summary is None:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing summary"
            )
        try:
            returned = json.loads(summary)
        except json.JSONDecodeError as exc:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry summary is not JSON"
            ) from exc
        if not isinstance(returned, Mapping) or returned.get("body_marker") != returned_marker:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} returned_marker mismatch"
            )
        # The FULL step-output envelope must NOT be inline: only `returned`
        # rides in the summary. ``raw_stream_ref``/``agent_fact_fields`` are
        # envelope-only keys (never inside the agent's ``returned``); their
        # presence means the full body leaked in.
        for envelope_only_key in ("raw_stream_ref", "agent_fact_fields"):
            if envelope_only_key in body:
                raise ProfileError(
                    f"source_fact_body_carry_case rejected {label}: "
                    f"{source_fact_ref} full step-output envelope leaked into carry "
                    f"({envelope_only_key})"
                )
