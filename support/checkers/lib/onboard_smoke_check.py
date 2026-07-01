import importlib
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


_ONBOARD_SMOKE_REQUIRED_KEYS = (
    "host",
    "preflight",
    "connect_hint",
    "example_result",
    "handoff_message_ko",
    "ok",
)


def run_onboard_smoke(repo: Path) -> KernelResult:
    """ONBOARDING-WIZARD-0 execution checker.

    Drives the real ``support/operator/onboard.run_onboard`` END-TO-END on
    ``adapter:local`` with a TEMP ``output_root`` (never the repo) and asserts:
      (a) it returns the structured dict {host, preflight, connect_hint,
          example_result, handoff_message_ko, ok},
      (b) ok is True and the bundled example actually ran (ran True) with a
          building_id + landed evidence under the temp root,
      (c) it NEVER raises, including for a bogus host (which must return ok False
          with a friendly message, not a stack-trace),
      (d) the bundled example plan is a valid linear Building plan (the
          building_plans_boundary_sweep already covers it; here we assert the
          plan file exists and the run produced evidence).
    If run_onboard EVER raises, this kernel check goes RED and --all EXITs
    non-zero. This is the no-raise guard for the guided onboarding experience.
    """

    _ensure_import_identity(repo)
    onboard = importlib.import_module("brick_protocol.support.operator.onboard")
    agent_adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    command_runner = _preset_completion_command_runner(agent_adapter.LocalCliCompleted)

    if "gemini" not in tuple(getattr(onboard, "SUPPORTED_HOSTS", ())):
        raise ProfileError("onboard_smoke: SUPPORTED_HOSTS must include gemini")
    doctor_packet = onboard.run_doctor(command_runner=command_runner)
    _assert_doctor_environment_rows(doctor_packet)
    doctor_targets = {
        str(row.get("target") or "")
        for row in doctor_packet.get("rows", [])
        if isinstance(row, Mapping)
    }
    if "gemini" not in doctor_targets:
        raise ProfileError(
            "onboard_smoke: doctor readiness rows must include gemini-local host evidence"
        )
    gemini_doctor_rows = [
        row
        for row in doctor_packet.get("rows", [])
        if isinstance(row, Mapping) and str(row.get("target") or "") == "gemini"
    ]
    gemini_doctor_row = gemini_doctor_rows[0] if gemini_doctor_rows else {}
    if "api_key_env_present" not in gemini_doctor_row:
        raise ProfileError(
            "onboard_smoke: gemini doctor row must expose API-key environment presence"
        )
    if gemini_doctor_row.get("credential_validity") != "not_proven":
        raise ProfileError(
            "onboard_smoke: gemini doctor row must mark credential_validity=not_proven"
        )
    gemini_message = str(gemini_doctor_row.get("message_ko") or "")
    if "키 유효성" not in gemini_message and "API key" not in gemini_message:
        raise ProfileError(
            "onboard_smoke: gemini doctor row must explain API-key readiness limits"
        )
    inspected = 1

    # The bundled example plan must exist (boundary sweep validates its shape).
    plan_path = repo / onboard.EXAMPLE_PLAN_REL
    if not plan_path.is_file():
        raise ProfileError(
            f"onboard_smoke: bundled example plan missing: {onboard.EXAMPLE_PLAN_REL}"
        )

    # (a)+(b)+(d) Happy path on adapter:local with a TEMP output_root (NOT repo).
    with tempfile.TemporaryDirectory(prefix="bp-onboard-smoke-") as tmp:
        tmp_root = Path(tmp)
        try:
            result = onboard.run_onboard(
                "codex",
                repo_root=repo,
                run_example=True,
                output_root=tmp_root,
                command_runner=command_runner,
            )
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                "onboard_smoke: run_onboard('codex', run_example=True) raised "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        _onboard_smoke_assert_shape("codex", result)

        if result["ok"] is not True:
            raise ProfileError(
                "onboard_smoke: adapter:local example must make ok True; got "
                f"{result['ok']!r} (example_result={result.get('example_result')})"
            )

        example = result["example_result"]
        if not isinstance(example, Mapping):
            raise ProfileError("onboard_smoke: example_result must be a mapping")
        if example.get("ran") is not True:
            raise ProfileError("onboard_smoke: bundled example did not run (ran != True)")
        building_id = example.get("building_id")
        if not isinstance(building_id, str) or not building_id.strip():
            raise ProfileError("onboard_smoke: example_result missing a building_id")
        evidence_root = example.get("evidence_root")
        if not isinstance(evidence_root, str) or not evidence_root.strip():
            raise ProfileError("onboard_smoke: example_result missing evidence_root")
        evidence_path = Path(evidence_root)
        if not evidence_path.is_dir():
            raise ProfileError(
                f"onboard_smoke: example evidence root is not a directory: {evidence_root}"
            )
        # Evidence MUST land under the temp root, never the repo working tree.
        try:
            evidence_path.resolve().relative_to(tmp_root.resolve())
        except ValueError as exc:
            raise ProfileError(
                "onboard_smoke: example evidence must land under the temp output_root, "
                f"not {evidence_root}"
            ) from exc
        if int(example.get("written_file_count") or 0) <= 0:
            raise ProfileError("onboard_smoke: example produced no written evidence files")
        step_adapters = example.get("materialized_step_adapters")
        if not isinstance(step_adapters, list) or not step_adapters:
            raise ProfileError(
                "onboard_smoke: example_result must expose materialized_step_adapters"
            )
        observed_adapter_refs = {
            str(row.get("selected_adapter_ref") or "")
            for row in step_adapters
            if isinstance(row, Mapping)
        }
        if "adapter:codex-local" not in observed_adapter_refs:
            raise ProfileError(
                "onboard_smoke: materialized_step_adapters must expose Agent "
                f"step casting, got {step_adapters!r}"
            )
        if observed_adapter_refs - {"adapter:local"} and "provider 없이" in str(
            example.get("message_ko") or ""
        ):
            raise ProfileError(
                "onboard_smoke: example message claimed provider-free execution "
                f"while step adapters were {sorted(observed_adapter_refs)}"
            )
        inspected += 1

    # (c) A bogus host must return ok False WITHOUT raising. Skip the example so
    #     this stays cheap; the never-raise guard is what matters here.
    try:
        bogus = onboard.run_onboard(
            "definitely-not-a-host",
            repo_root=repo,
            run_example=False,
            command_runner=command_runner,
        )
    except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
        raise ProfileError(
            "onboard_smoke: run_onboard must not raise for a bogus host; raised "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    _onboard_smoke_assert_shape("bogus", bogus)
    if bogus["ok"] is not False:
        raise ProfileError("onboard_smoke: bogus host must return ok False")
    inspected += 1

    return KernelResult(
        check_id="onboard_smoke",
        inspected=inspected,
        output=(
            "onboard smoke passed: doctor reports environment readiness rows "
            "(python, pipx, git, uv, disk, github network) and gemini host "
            "readiness evidence with API-key presence and credential_validity=not_proven; "
            "run_onboard drives the bundled adapter:local "
            "example end-to-end to a TEMP output_root, returns the structured "
            "{preflight, connect_hint, example_result, handoff_message_ko, ok} "
            "dict with ok True + a building_id + landed evidence, and never raises "
            f"(bogus host returns ok False) ({inspected} flow(s) inspected)."
        ),
    )


def _onboard_smoke_assert_shape(label: str, result: Any) -> None:
    if not isinstance(result, Mapping):
        raise ProfileError(
            f"onboard_smoke: {label} must return a dict, got {type(result).__name__}"
        )
    missing = [key for key in _ONBOARD_SMOKE_REQUIRED_KEYS if key not in result]
    if missing:
        raise ProfileError(
            f"onboard_smoke: {label} result missing required key(s): {', '.join(missing)}"
        )
    if not isinstance(result["ok"], bool):
        raise ProfileError(f"onboard_smoke: {label} 'ok' must be a bool")
    handoff = result["handoff_message_ko"]
    if not isinstance(handoff, str) or not handoff.strip():
        raise ProfileError(
            f"onboard_smoke: {label} 'handoff_message_ko' must be non-empty text"
        )
    preflight = result["preflight"]
    if not isinstance(preflight, Mapping) or not str(preflight.get("message_ko") or "").strip():
        raise ProfileError(
            f"onboard_smoke: {label} preflight must carry a non-empty message_ko"
        )


def _assert_doctor_environment_rows(doctor_packet: Mapping[str, Any]) -> None:
    rows = doctor_packet.get("rows")
    if not isinstance(rows, list):
        raise ProfileError("onboard_smoke: doctor rows must be a list")
    by_target = {
        str(row.get("target") or ""): row
        for row in rows
        if isinstance(row, Mapping)
    }
    required_targets = {
        "python",
        "pipx",
        "git",
        "uv",
        "disk",
        "github.com",
    }
    missing = sorted(required_targets - set(by_target))
    if missing:
        raise ProfileError(
            "onboard_smoke: doctor missing environment readiness row(s): "
            + ", ".join(missing)
        )
    for target in sorted(required_targets):
        row = by_target[target]
        if not isinstance(row.get("ok"), bool):
            raise ProfileError(
                f"onboard_smoke: doctor row {target!r} must expose boolean ok"
            )
        if not str(row.get("message_ko") or "").strip():
            raise ProfileError(
                f"onboard_smoke: doctor row {target!r} must expose message_ko"
            )
    if "version" not in by_target["python"]:
        raise ProfileError("onboard_smoke: python doctor row must expose version")
    if "free_bytes" not in by_target["disk"]:
        raise ProfileError("onboard_smoke: disk doctor row must expose free_bytes")
