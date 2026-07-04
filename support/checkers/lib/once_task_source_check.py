"""Once task-source admission behavioral profile runner.

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


def _once_task_source_packet(task_source_ref: str | None) -> dict[str, Any]:
    """Single-step run_building_once packet for the task-source admission FIRE."""

    packet: dict[str, Any] = {
        "building_id": "once-task-source-admission-case",
        "selected_adapter_ref": "adapter:codex-local",
        "step_rows": {
            "step_ref": "once-task-source-admission",
            "rows": [
                {
                    "axis": "Brick",
                    "row_ref": "brick-row:once-task-source-admission",
                    "brick_work_ref": "work:once-task-source-admission",
                    "brick_instance_ref": "brick-once-task-source-admission",
                    "work_statement": "Exercise single-step task-source admission.",
                    "comparison_rule": "Support observes admission rejects only.",
                    "required_return_shape": "observed_evidence, not_proven",
                },
                {
                    "axis": "Agent",
                    "row_ref": "agent-row:once-task-source-admission",
                    "agent_object_ref": "agent-object:dev",
                },
                {
                    "axis": "Link",
                    "row_ref": "link-row:once-task-source-admission",
                    "movement": "forward",
                    "target_ref": "brick-once-task-source-closure",
                    "next_brick_instance_ref": "brick-once-task-source-closure",
                    "declared_gate_refs": ["link-gate:default-transition"],
                },
            ],
        },
        "caller_supplied_link_facts": {
            "movement_fact": {"movement": "forward"},
            "transition_fact": {
                "movement": "forward",
                "target_fact": "brick-once-task-source-closure",
            },
        },
    }
    if task_source_ref is not None:
        packet["task_source_ref"] = task_source_ref
    return packet


def run_once_task_source_admission_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIX-C (codex review 0611): run_building_once validates the task source.

    Before the fix, run_building_once performed NO task_source_ref validation:
    a fixture declaring a missing task file silently skipped the body
    (_source_fact_bodies returns {} for unreadable refs) and the run proceeded
    without its declared task. This case pins the HARD-FAIL at single-step
    admission, parity with run_building_plan strictness (P11b):

      1. MISSING-FILE REJECT: a once-packet declaring a repo-path
         task_source_ref that does not exist must reject with the VERBATIM
         walker message ("task_source_ref declared file does not exist: ...")
         BEFORE the provider boundary (sentinel command runner never invoked).
      2. VALID PROCEEDS: the SAME packet with an existing task file proceeds
         past admission to the provider sentinel (no over-restriction);
         AdapterFrontierEvidenceWritten is the expected surfaced outcome.
      3. INLINE SENTINEL HONESTY (TASK-BY-TEXT 0611): the
         task-source:inline-statement sentinel WITHOUT a carried
         task_statement body rejects; WITH the body it proceeds to the
         provider sentinel -- both task-source forms stay honest on the
         single-step surface.

    Anti-tautology: remove the run_building_once admission guard and (1) and
    the no-body leg of (3) go RED (the run reaches the provider sentinel,
    which raises and fails the case).
    """
    items = rule_items(profile, "run_once_task_source_admission_case")
    if not items:
        return 0
    from support.operator.run import AdapterFrontierEvidenceWritten, run_building_once

    count = 0
    for item in items:
        mapping = require_mapping(item, "run_once_task_source_admission_case item")
        label = require_string(
            mapping.get("label"), "run_once_task_source_admission_case.label"
        )
        missing_ref = require_string(
            mapping.get("missing_task_source_ref"),
            f"{label}: missing_task_source_ref",
        )
        valid_ref = require_string(
            mapping.get("valid_task_source_ref"), f"{label}: valid_task_source_ref"
        )
        if (repo / missing_ref).exists():
            raise ProfileError(
                f"run_once_task_source_admission_case rejected {label}: the declared "
                f"missing_task_source_ref EXISTS in the repo: {missing_ref}"
            )
        if not (repo / valid_ref).is_file():
            raise ProfileError(
                f"run_once_task_source_admission_case rejected {label}: the declared "
                f"valid_task_source_ref does not exist in the repo: {valid_ref}"
            )

        def _probe(
            packet: dict[str, Any],
            *,
            expect_reject_fragment: str | None,
            leg: str,
        ) -> None:
            sentinel_invocations: list[Any] = []

            def _sentinel_command_runner(args: Any, _cwd: Any, _timeout: Any) -> Any:
                sentinel_invocations.append(args)
                raise _OnceTaskSourceSentinelReached(
                    "provider sentinel reached past single-step admission"
                )

            with tempfile.TemporaryDirectory(
                prefix="bp-once-task-source-admission-"
            ) as tmpdir:
                try:
                    run_building_once(
                        packet,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        command_runner=_sentinel_command_runner,
                        adapter_cwd=Path(tmpdir),
                        adapter_timeout_seconds=10,
                    )
                except AdapterFrontierEvidenceWritten:
                    if expect_reject_fragment is not None:
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            "the packet reached the provider boundary; the task-source "
                            "admission guard did not fire"
                        ) from None
                except ValueError as exc:
                    if expect_reject_fragment is None:
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            f"expected the packet to proceed past admission, got {exc!r}"
                        ) from exc
                    if expect_reject_fragment not in str(exc):
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            f"rejected for the WRONG reason: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"run_once_task_source_admission_case rejected {label}/{leg}: "
                        "run_building_once returned without reject or provider sentinel"
                    )
            if expect_reject_fragment is not None and sentinel_invocations:
                raise ProfileError(
                    f"run_once_task_source_admission_case rejected {label}/{leg}: the "
                    "provider sentinel WAS invoked despite the expected admission reject"
                )
            if expect_reject_fragment is None and not sentinel_invocations:
                raise ProfileError(
                    f"run_once_task_source_admission_case rejected {label}/{leg}: the "
                    "packet never reached the provider sentinel (over-restriction or a "
                    "pre-provider failure)"
                )

        # (1) missing-file -> VERBATIM loud reject before the provider boundary.
        _probe(
            _once_task_source_packet(missing_ref),
            expect_reject_fragment=(
                f"task_source_ref declared file does not exist: {missing_ref}"
            ),
            leg="missing-file-reject",
        )
        # (2) valid file -> proceeds past admission (no over-restriction).
        _probe(
            _once_task_source_packet(valid_ref),
            expect_reject_fragment=None,
            leg="valid-proceeds",
        )
        # (3) inline sentinel honesty on the once surface.
        _probe(
            _once_task_source_packet("task-source:inline-statement"),
            expect_reject_fragment=(
                "requires the plan to carry a non-empty task_statement body"
            ),
            leg="inline-sentinel-without-body-reject",
        )
        inline_packet = _once_task_source_packet("task-source:inline-statement")
        inline_packet["task_statement"] = "단일 스텝 인라인 본문 허용 확인.\n"
        _probe(
            inline_packet,
            expect_reject_fragment=None,
            leg="inline-sentinel-with-body-proceeds",
        )
        count += 1
    return count


class _OnceTaskSourceSentinelReached(Exception):
    """Marker raised by the FIX-C provider sentinel (never escapes the probe)."""

