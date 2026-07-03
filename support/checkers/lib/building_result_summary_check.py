"""Building-result-summary kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes the onboard Building result summary read-side projection; it owns no
axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError


def run_building_result_summary(repo: Path) -> KernelResult:
    """Pin the onboard Building result summary read-side projection."""

    from brick_protocol.support.operator import onboard

    forbidden_keys = {
        "ok",
        "success",
        "complete",
        "quality",
        "verdict",
        "status",
        "pass",
        "fail",
    }
    with tempfile.TemporaryDirectory(prefix="bp-building-result-summary-") as tmp:
        tmp_repo = Path(tmp)
        _init_git_repo_with_wip_anchor(tmp_repo, "summary-vessel")
        root = tmp_repo / "project" / "brick-protocol" / "buildings" / "summary-vessel"
        (root / "work" / "step-outputs" / "summary-vessel-work-attempt-1").mkdir(
            parents=True
        )
        (root / "work" / "step-outputs" / "summary-vessel-work-attempt-2").mkdir(
            parents=True
        )
        (root / "work" / "step-outputs" / "summary-vessel-closure-attempt-1").mkdir(
            parents=True
        )
        _write_json(
            root / "work" / "step-outputs" / "summary-vessel-work-attempt-1" / "step-output.json",
            {
                "step_ref": "summary-vessel-work",
                "attempt_index": 1,
                "returned": {"observed_evidence": ["work attempt one"]},
            },
        )
        _write_json(
            root / "work" / "step-outputs" / "summary-vessel-work-attempt-2" / "step-output.json",
            {
                "step_ref": "summary-vessel-work",
                "attempt_index": 2,
                "returned": {"observed_evidence": ["work attempt two"]},
            },
        )
        carried_crosscheck = [
            {
                "label": "summary-field-pin",
                "success": "carried closure evidence is preserved",
                "nested": {"ok": True},
            }
        ]
        _write_json(
            root / "work" / "step-outputs" / "summary-vessel-closure-attempt-1" / "step-output.json",
            {
                "step_ref": "summary-vessel-closure",
                "step_template_ref": "building-step-template:closure",
                "attempt_index": 1,
                "returned": {
                    "deliverable_crosscheck": carried_crosscheck,
                    "transition_concern_evidence": {
                        "concern_kind": "verification_gap",
                        "binding": False,
                    },
                },
            },
        )
        _write_jsonl(
            root / "raw" / "link.jsonl",
            [
                {
                    "raw_ref": "raw:link:01",
                    "step_ref": "summary-vessel-work",
                    "transition_lifecycle_state": "paused",
                    "transition_lifecycle_pending_target_ref": "brick-summary-vessel-closure",
                    "transition_lifecycle_reason_refs": ["reason:summary-vessel"],
                    "transition_lifecycle_required_disposition_owner": "caller-or-coo",
                }
            ],
        )
        _write_jsonl(
            root / "raw" / "adapter-error.jsonl",
            [
                {
                    "step_ref": "summary-vessel-work",
                    "error_kind": "local_cli_error",
                    "exception_type": "RuntimeError",
                    "message_excerpt": "adapter reported a useful operator triage message",
                    "status": "packet-synthesized forbidden probe",
                }
            ],
        )
        _write_jsonl(
            root / "raw" / "adapter-usage.jsonl",
            [
                {
                    "support_record_role": "adapter-token-meter",
                    "adapter_dispatch_timing": {"duration_ms": 9999},
                },
                {
                    "support_record_role": "adapter-dispatch-timing",
                    "adapter_dispatch_timing": {"duration_ms": 12.5},
                },
                {
                    "support_record_role": "adapter-dispatch-timing",
                    "adapter_dispatch_timing": {"duration_ms": 7.25},
                },
            ],
        )

        original_observer = onboard.observe_building_frontier

        def fake_frontier(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
            return {
                "frontier_kind": "mutation-frontier-kind",
                "frontier_reason": "mutation-frontier-reason",
            }

        try:
            onboard.observe_building_frontier = fake_frontier
            summary = onboard.summarize_building_result(root, repo_root=tmp_repo)
            anchored_summary = onboard._result_summary_with_sandbox_anchors(
                root,
                repo_root=tmp_repo,
                building_id="summary-vessel",
                commit_sha="",
            )
            missing_anchor_summary = onboard._result_summary_with_sandbox_anchors(
                root,
                repo_root=tmp_repo,
                building_id="summary-vessel-missing",
                commit_sha="abc123",
            )
            unknown_anchor = onboard._result_summary_wip_anchor_present(
                None,
                "summary-vessel",
            )
        finally:
            onboard.observe_building_frontier = original_observer

        if summary.get("frontier_kind") != "mutation-frontier-kind":
            raise ProfileError(
                "building_result_summary mutation-RED: frontier_kind was not copied "
                "from observe_building_frontier"
            )
        if summary.get("frontier_reason") != "mutation-frontier-reason":
            raise ProfileError(
                "building_result_summary mutation-RED: frontier_reason was not copied "
                "from observe_building_frontier"
            )
        _assert_no_forbidden_summary_key(summary, forbidden_keys, path="result_summary")
        if summary.get("step_attempts") != [
            {"step_ref": "summary-vessel-closure", "attempt_count": 1},
            {"step_ref": "summary-vessel-work", "attempt_count": 2},
        ]:
            raise ProfileError(
                f"building_result_summary step attempts drifted: {summary.get('step_attempts')!r}"
            )
        closure = summary.get("closure")
        if not isinstance(closure, Mapping):
            raise ProfileError("building_result_summary closure field is not a mapping")
        if closure.get("deliverable_crosscheck") != carried_crosscheck:
            raise ProfileError(
                "building_result_summary closure carry evidence was not preserved"
            )
        concern = closure.get("transition_concern_evidence")
        if not isinstance(concern, Mapping) or concern.get("concern_kind") != "verification_gap":
            raise ProfileError("building_result_summary closure transition concern drifted")
        if summary.get("link_paused_rows") != [
            {
                "step_ref": "summary-vessel-work",
                "pending_target_ref": "brick-summary-vessel-closure",
                "reason_refs": ["reason:summary-vessel"],
                "required_disposition_owner": "caller-or-coo",
            }
        ]:
            raise ProfileError(
                f"building_result_summary paused rows drifted: {summary.get('link_paused_rows')!r}"
            )
        if summary.get("adapter_error_rows") != [
            {
                "step_ref": "summary-vessel-work",
                "error_kind": "local_cli_error",
                "exception_type": "RuntimeError",
                "message_excerpt": "adapter reported a useful operator triage message",
            }
        ]:
            raise ProfileError(
                "building_result_summary adapter-error row projection drifted"
            )
        if summary.get("dispatch_timing_ms_total") != 19.75:
            raise ProfileError(
                "building_result_summary dispatch timing must sum only "
                "adapter-dispatch-timing rows"
            )
        if summary.get("wip_anchor_present") is not True:
            raise ProfileError(
                "building_result_summary direct WIP anchor ref lookup did not return True"
            )
        if anchored_summary.get("wip_anchor_present") is not True:
            raise ProfileError("building_result_summary WIP anchor ref lookup did not return True")
        if missing_anchor_summary.get("wip_anchor_present") is not False:
            raise ProfileError("building_result_summary absent WIP anchor must be False")
        if missing_anchor_summary.get("commit_sha_present") is not True:
            raise ProfileError("building_result_summary commit_sha_present drifted")
        if unknown_anchor is not None:
            raise ProfileError("building_result_summary absent repo_root anchor state must be None")

        absent_root = tmp_repo / "project" / "brick-protocol" / "buildings" / "absent-vessel"
        absent_summary = onboard.summarize_building_result(absent_root, repo_root=tmp_repo)
        if absent_summary.get("step_attempts") is not None:
            raise ProfileError("building_result_summary absent step outputs must be None")
        if absent_summary.get("closure") is not None:
            raise ProfileError("building_result_summary absent closure must be None")
        if absent_summary.get("link_paused_rows") is not None:
            raise ProfileError("building_result_summary absent link rows must be None")
        if absent_summary.get("adapter_error_rows") is not None:
            raise ProfileError("building_result_summary absent adapter errors must be None")
        if absent_summary.get("dispatch_timing_ms_total") is not None:
            raise ProfileError("building_result_summary absent timing must be None")
        if absent_summary.get("wip_anchor_present") is not False:
            raise ProfileError(
                "building_result_summary direct absent WIP anchor must be False"
            )
        _assert_no_forbidden_summary_key(
            absent_summary,
            forbidden_keys,
            path="absent_result_summary",
        )
        strip_probe_carried_crosscheck = [
            {"label": "strip-exempt-pin", "success": "preserved", "nested": {"ok": True}}
        ]
        strip_probe = {
            "non_exempt": {
                "items": [
                    {
                        "ok": True,
                        "nested": {"success": "must be stripped", "kept": "observed"},
                    }
                ]
            },
            "deliverable_crosscheck": strip_probe_carried_crosscheck,
        }
        stripped_probe = onboard._strip_result_summary_forbidden_keys(strip_probe)
        _assert_no_forbidden_summary_key(
            stripped_probe.get("non_exempt"),
            forbidden_keys,
            path="strip_probe.non_exempt",
        )
        if stripped_probe.get("deliverable_crosscheck") != strip_probe_carried_crosscheck:
            raise ProfileError(
                "building_result_summary carried closure strip exemption drifted"
            )

    return KernelResult(
        check_id="building_result_summary",
        inspected=25,
        output=(
            "building_result_summary passed: synthetic vessel fields, absence-None "
            "handling, observer mutation-RED, adapter error message projection, "
            "real WIP ref lookup, recursive forbidden summary keys with closure "
            "carry preservation, paused rows, and dispatch timing sum inspected."
        ),
    )


def _init_git_repo_with_wip_anchor(path: Path, building_id: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "brick-checker"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "checker@brick.local"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "checker anchor"],
        cwd=path,
        check=True,
    )
    ref = f"refs/brick/wip/{building_id}"
    subprocess.run(["git", "update-ref", ref, "HEAD"], cwd=path, check=True)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _assert_no_forbidden_summary_key(
    value: Any,
    forbidden: set[str],
    *,
    path: str,
) -> None:
    key = path.rsplit(".", 1)[-1].split("[", 1)[0]
    if key in {"deliverable_crosscheck", "transition_concern_evidence"}:
        return
    if isinstance(value, Mapping):
        for item_key, item in value.items():
            if str(item_key) in forbidden:
                raise ProfileError(
                    f"building_result_summary forbidden key {item_key!r} at {path}"
                )
            _assert_no_forbidden_summary_key(
                item,
                forbidden,
                path=f"{path}.{item_key}",
            )
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _assert_no_forbidden_summary_key(
                item,
                forbidden,
                path=f"{path}[{index}]",
            )


def _run_building_operator_driver0_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "building_operator_driver0",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_building_result_summary(repo: Path) -> KernelResult:"
    poisoned = "def run_building_result_summary_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(
            "building_result_summary mutation probe could not find summary entrypoint"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".building-result-summary-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_building_operator_driver0_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "building_result_summary mutation probe did not turn "
                "building_operator_driver0 profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_building_operator_driver0_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "building_result_summary mutation probe restored source but "
            f"building_operator_driver0 remained RED:\n{excerpt}"
        )

    return [
        "building-result summary mutation RED probe passed: disabling the moved "
        "run_building_result_summary entrypoint made check_profile.py --profile "
        "building_operator_driver0 exit non-zero, then restoring the temp-backed "
        "self file returned building_operator_driver0 to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for building result summary."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_building_result_summary "
            "entrypoint, assert building_operator_driver0 profile exits RED, "
            "restore from a temp backup, then assert building_operator_driver0 GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_building_result_summary(repo).output]
        )
    except ProfileError as exc:
        print("building-result summary check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
