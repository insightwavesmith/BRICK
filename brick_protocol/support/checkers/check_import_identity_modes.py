#!/usr/bin/env python3
"""Check two-mode operator import identity and parents[N] binding registry.

Support checker only. It records source/install identity observations and
static binding coverage; it does not judge source truth, success, quality, or
Movement.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError
from brick_protocol.support.operator.import_identity import (
    _OFFICIAL_LAUNCH_TOKEN,
    OfficialLaunchProof,
    mint_official_launch_token,
    official_launch_token_observation,
    reset_official_launch_token,
    resolve_operator_identity,
    suppress_official_launch_token_for_probe,
)
from brick_protocol.support.operator.walker_frontier import _dynamic_frontier_write_plan


PARENTS_BINDING_REGISTRY = {
    "brick_protocol/support/operator/cli.py": {3},
    "brick_protocol/support/operator/dashboard_export.py": {3},
    "brick_protocol/support/operator/primitives.py": {3},
    "brick_protocol/support/operator/report_sinks.py": {3},
    "brick_protocol/support/operator/reporter.py": {3},
    "brick_protocol/support/operator/task_order_preflight.py": {3},
    "brick_protocol/support/checkers/check_adapter_usage_meter.py": {3},
    "brick_protocol/support/checkers/check_agent_object_schema_single_source.py": {3},
    "brick_protocol/support/checkers/check_agent_resource_resolution.py": {3},
    "brick_protocol/support/checkers/check_assembly_equivalence.py": {3},
    "brick_protocol/support/checkers/check_axis_crossing_elegance.py": {3},
    "brick_protocol/support/checkers/check_bounded_agent_proposed_routing_loop0.py": {3},
    "brick_protocol/support/checkers/check_brick_template_catalog_restructure.py": {3},
    "brick_protocol/support/checkers/check_bricks_spec_completeness.py": {3},
    "brick_protocol/support/checkers/check_builder_consumes_axis_api.py": {3},
    "brick_protocol/support/checkers/check_building_lifecycle_path_shape.py": {3},
    "brick_protocol/support/checkers/check_building_operator_driver0.py": {3},
    "brick_protocol/support/checkers/check_chained_carry_dependency.py": {3},
    "brick_protocol/support/checkers/check_charter_injection.py": {3},
    "brick_protocol/support/checkers/check_cli_runner_stdin_devnull.py": {3},
    "brick_protocol/support/checkers/check_declaration_enforcement_parity.py": {3},
    "brick_protocol/support/checkers/check_driver_public_intake_seal.py": {3},
    "brick_protocol/support/checkers/check_evidence_spine.py": {3},
    "brick_protocol/support/checkers/check_evidence_spine_projection.py": {3},
    "brick_protocol/support/checkers/check_fan_out_sibling_evidence_independence.py": {3},
    "brick_protocol/support/checkers/check_first_use_wizard.py": {3},
    "brick_protocol/support/checkers/check_gate_policy_action_single_source.py": {3},
    "brick_protocol/support/checkers/check_gate_registry_single_source.py": {3},
    "brick_protocol/support/checkers/check_graph_draft_rules.py": {3},
    "brick_protocol/support/checkers/check_import_identity_modes.py": {3},
    "brick_protocol/support/checkers/check_interactive_provider_intake.py": {3},
    "brick_protocol/support/checkers/check_link_gate_measurement_separation.py": {3},
    "brick_protocol/support/checkers/check_mcp_dispatch_wire.py": {3},
    "brick_protocol/support/checkers/check_model_lane_matching_discipline.py": {3},
    "brick_protocol/support/checkers/check_package_path_admission.py": {3},
    "brick_protocol/support/checkers/check_pin_estate_integrity.py": {3},
    "brick_protocol/support/checkers/check_plan_revision_chain.py": {3},
    "brick_protocol/support/checkers/check_positive_int_bool_boundary.py": {3},
    "brick_protocol/support/checkers/check_preflight_injection_survival.py": {3},
    "brick_protocol/support/checkers/check_project_declaration.py": {3},
    "brick_protocol/support/checkers/check_recording_checker_derived_contract.py": {3},
    "brick_protocol/support/checkers/check_report_env_autoload.py": {3},
    "brick_protocol/support/checkers/check_resume_declaration.py": {3},
    "brick_protocol/support/checkers/check_resume_disposition_surface.py": {3},
    "brick_protocol/support/checkers/check_resume_replay_disposition_mirror.py": {3},
    "brick_protocol/support/checkers/check_return_field_merge_set_parity.py": {3},
    "brick_protocol/support/checkers/check_route_v2_views.py": {3},
    "brick_protocol/support/checkers/check_rule13_durable_evidence_ref.py": {3},
    "brick_protocol/support/checkers/check_session_continuity_adapter.py": {3},
    "brick_protocol/support/checkers/check_step_output_evidence_field_set_parity.py": {3},
    "brick_protocol/support/checkers/check_tier_a_three_axis_conformance.py": {3},
    "brick_protocol/support/checkers/lib/adapter_error_check.py": {4},
    "brick_protocol/support/checkers/lib/agent_adapter_return_shape_check.py": {4},
    "brick_protocol/support/checkers/lib/agent_output_text_preservation_check.py": {4},
    "brick_protocol/support/checkers/lib/agent_session_id_redaction_check.py": {4},
    "brick_protocol/support/checkers/lib/axis_vocab_drift_check.py": {4},
    "brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py": {4},
    "brick_protocol/support/checkers/lib/building_plan_graph_check.py": {4},
    "brick_protocol/support/checkers/lib/building_result_summary_check.py": {4},
    "brick_protocol/support/checkers/lib/chat_session_park_check.py": {4},
    "brick_protocol/support/checkers/lib/dashboard_productization_projection_check.py": {4},
    "brick_protocol/support/checkers/lib/deliverable_crosscheck_gate_check.py": {4},
    "brick_protocol/support/checkers/lib/mcp_connect_projection_check.py": {4},
    "brick_protocol/support/checkers/lib/raw_evidence_stream_scrub_check.py": {4},
    "brick_protocol/support/checkers/lib/re_instruction_endline_gate_check.py": {4},
    "brick_protocol/support/checkers/lib/reporter_notification_projection_check.py": {4},
    "brick_protocol/support/checkers/probe_prompt_behavior_red.py": {3},
    "brick_protocol/support/checkers/probe_wheel_smoke_stale_build_red.py": {3},
    "brick_protocol/support/connection/adapter_constants.py": {3},
    "brick_protocol/support/connection/agent_resources.py": {3},
    "brick_protocol/support/connection/building_design_toolkit.py": {3},
    "brick_protocol/support/connection/connect.py": {3},
    "brick_protocol/support/connection/coo_sync.py": {3},
    "brick_protocol/support/connection/mcp_projection.py": {3},
    "brick_protocol/support/recording/capture.py": {3},
}
IDENTITY_HELPER_CONSUMERS = {
    "brick_protocol/support/operator/cli.py",
    "brick_protocol/support/operator/onboard.py",
    "brick_protocol/support/operator/run.py",
}
PARENTS_BINDING_SCAN_ROOTS = (
    "brick_protocol/support/operator",
    "brick_protocol/support/checkers",
    "brick_protocol/support/connection",
    "brick_protocol/support/recording",
)
PARENTS_BINDING_RE = re.compile(
    r"Path\(__file__\)\.resolve\(\)\.parents\[(?P<index>\d+)\]"
)


@contextlib.contextmanager
def _checker_tempdir(repo: Path, prefix: str):
    scratch_parent = repo / "brick_protocol/support/checkers/.tmp-import-identity"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=prefix, dir=scratch_parent) as tmp:
            yield Path(tmp)
    finally:
        with contextlib.suppress(OSError):
            scratch_parent.rmdir()


def _parents_bindings(repo: Path) -> dict[str, set[int]]:
    observed: dict[str, set[int]] = {}
    for root in PARENTS_BINDING_SCAN_ROOTS:
        for path in sorted((repo / root).rglob("*.py")):
            rel = path.relative_to(repo).as_posix()
            text = path.read_text(encoding="utf-8")
            indices = {int(match.group("index")) for match in PARENTS_BINDING_RE.finditer(text)}
            if indices:
                observed[rel] = indices
    return observed


def _identity_text_violations(rel: str, text: str) -> list[str]:
    violations: list[str] = []
    if "resolve_operator_identity(__file__)" not in text:
        violations.append(f"{rel} does not consume resolve_operator_identity(__file__)")
    if "install_source_import_paths(_OPERATOR_IMPORT_IDENTITY)" not in text:
        violations.append(f"{rel} does not install source import paths through the helper")
    return violations


def _identity_source_violations(repo: Path) -> list[str]:
    violations: list[str] = []
    for rel in sorted(IDENTITY_HELPER_CONSUMERS):
        text = (repo / rel).read_text(encoding="utf-8")
        violations.extend(_identity_text_violations(rel, text))
    return violations


def _assert_guard_removal_probe_fires(repo: Path) -> int:
    cli_path = repo / "brick_protocol/support/operator/cli.py"
    original = cli_path.read_text(encoding="utf-8")
    mutated = original.replace(
        "resolve_operator_identity(__file__)",
        "Path(__file__).resolve().parents[3]",
        1,
    )
    if mutated == original:
        raise ProfileError("import_identity_modes guard-removal probe could not mutate cli.py")
    violations = _identity_text_violations("brick_protocol/support/operator/cli.py", mutated)
    if any("resolve_operator_identity" in violation for violation in violations):
        return 1
    raise ProfileError(
        "import_identity_modes guard-removal probe did not reject cli.py "
        "without resolve_operator_identity(__file__)"
    )
    return 1


def _assert_bad_marker_rejected(repo: Path) -> int:
    with _checker_tempdir(repo, "bp-identity-bad-marker-") as tmp:
        root = tmp / "repo"
        operator_dir = root / "brick_protocol/support/operator"
        package_root = root / "brick_protocol"
        operator_dir.mkdir(parents=True)
        package_root.mkdir(parents=True, exist_ok=True)
        anchor = operator_dir / "cli.py"
        anchor.write_text("", encoding="utf-8")
        (package_root / "__init__.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            "[project]\nname = \"not-brick-protocol\"\n",
            encoding="utf-8",
        )
        try:
            resolve_operator_identity(anchor)
        except RuntimeError as exc:
            if "repo identity marker mismatch" in str(exc):
                return 1
            raise
        raise ProfileError("import_identity_modes accepted a contaminated pyproject marker")


def _assert_installed_mode_fixture(repo: Path) -> int:
    helper_text = (repo / "brick_protocol/support/operator/import_identity.py").read_text(encoding="utf-8")
    with _checker_tempdir(repo, "bp-identity-installed-") as tmp:
        site = tmp / "site"
        operator_dir = site / "brick_protocol/support/operator"
        dist_info = site / "brick_protocol-0.0.0.dist-info"
        operator_dir.mkdir(parents=True)
        dist_info.mkdir(parents=True)
        for init in (
            site / "brick_protocol/__init__.py",
            site / "brick_protocol/support/__init__.py",
            operator_dir / "__init__.py",
        ):
            init.write_text("", encoding="utf-8")
        (operator_dir / "import_identity.py").write_text(helper_text, encoding="utf-8")
        (operator_dir / "cli.py").write_text("", encoding="utf-8")
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: brick-protocol\nVersion: 0.0.0\n",
            encoding="utf-8",
        )
        code = """
import json
from pathlib import Path
from brick_protocol.support.operator.import_identity import resolve_operator_identity
identity = resolve_operator_identity(Path('brick_protocol/support/operator/cli.py'))
print(json.dumps({
    'mode': identity.mode,
    'distribution_name': identity.distribution_name,
    'distribution_version': identity.distribution_version,
    'import_identity_root': identity.import_identity_root is None,
}, sort_keys=True))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=site,
            env={"PYTHONPATH": str(site)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise ProfileError(
                "import_identity_modes installed fixture failed:\n"
                + (result.stderr or result.stdout)
            )
        packet = json.loads(result.stdout)
        expected = {
            "mode": "installed",
            "distribution_name": "brick-protocol",
            "distribution_version": "0.0.0",
            "import_identity_root": True,
        }
        if packet != expected:
            raise ProfileError(
                f"import_identity_modes installed fixture mismatch: {packet!r}"
            )
        return 1


def _assert_official_launch_token_fixture() -> int:
    from brick_protocol.support.operator.import_identity import enforce_official_launch_token

    suppress_token = suppress_official_launch_token_for_probe()
    try:
        absent = official_launch_token_observation()
        if absent.get("token_present") is not False:
            raise ProfileError("official-launch token fixture observed token before mint")
        if absent.get("forged_non_proof_observed") is not False:
            raise ProfileError("official-launch token fixture observed forge before mint")
        if absent.get("forged_unminted_proof_observed") is not False:
            raise ProfileError("official-launch token fixture observed unminted proof before mint")
        if absent.get("absence_action") != "raise_runtime_error":
            raise ProfileError("official-launch token absence is not lethal Stage 3b")
        if absent.get("observation_mode") != "gate_lethal":
            raise ProfileError("official-launch token observation_mode is not gate_lethal")
        if absent.get("pure_dev_d3_building_id") != "pure-dev-d3-r7-body-reland-0709c":
            raise ProfileError("official-launch token observation missing pure-dev D3 id")
        if absent.get("harden_ref") != "official_launch_typed_proof_v1":
            raise ProfileError("official-launch token observation missing D3 harden_ref")
        try:
            enforce_official_launch_token(absent)
        except RuntimeError as exc:
            if "official launch token absent" not in str(exc):
                raise ProfileError(
                    f"lethal gate message unexpected: {exc}"
                ) from exc
        else:
            raise ProfileError("lethal official-launch gate did not raise when token absent")
    finally:
        reset_official_launch_token(suppress_token)

    forge_token = _OFFICIAL_LAUNCH_TOKEN.set(object())
    try:
        forged = official_launch_token_observation()
        if forged.get("token_present") is not False:
            raise ProfileError("official-launch non-proof forge was counted as present")
        if forged.get("forged_non_proof_observed") is not True:
            raise ProfileError("official-launch non-proof forge was not observed")
        if forged.get("forged_unminted_proof_observed") is not False:
            raise ProfileError("official-launch non-proof forge was marked unminted proof")
        try:
            enforce_official_launch_token(forged)
        except RuntimeError as exc:
            if "official launch proof forged" not in str(exc):
                raise ProfileError(
                    f"official-launch forge refuse message unexpected: {exc}"
                ) from exc
        else:
            raise ProfileError("official-launch non-proof forge was not refused")
    finally:
        reset_official_launch_token(forge_token)

    try:
        OfficialLaunchProof(nonce="fake", minter_module="attacker")
    except RuntimeError as exc:
        if "mint only via mint_official_launch_token" not in str(exc):
            raise ProfileError(
                f"official-launch direct proof construction message unexpected: {exc}"
            ) from exc
    else:
        raise ProfileError("official-launch direct proof construction was not refused")

    with _checker_tempdir(_REPO_ROOT, "bp-official-launch-main-forge-") as tmp:
        script = tmp / "evil_main.py"
        script.write_text(
            "\n".join(
                [
                    "from brick_protocol.support.operator.import_identity import mint_official_launch_token",
                    "try:",
                    "    mint_official_launch_token()",
                    "except RuntimeError as exc:",
                    "    print(str(exc))",
                    "else:",
                    "    raise SystemExit('standalone __main__ mint unexpectedly accepted')",
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=_REPO_ROOT,
            env={"PYTHONPATH": str(_REPO_ROOT)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise ProfileError(
                "official-launch standalone __main__ mint probe failed:\n"
                + (result.stderr or result.stdout)
            )
        if "official launch mint refused" not in result.stdout:
            raise ProfileError(
                "official-launch standalone __main__ mint probe did not observe refusal"
            )

    token = mint_official_launch_token()
    try:
        proof = _OFFICIAL_LAUNCH_TOKEN.get()
        if type(proof) is not OfficialLaunchProof:
            raise ProfileError("official-launch mint did not set OfficialLaunchProof")
        if not proof.nonce or not proof.minter_module:
            raise ProfileError("official-launch proof missing nonce or minter_module")
        present = official_launch_token_observation()
        if present.get("token_present") is not True:
            raise ProfileError("official-launch token fixture did not observe minted token")
        if present.get("forged_non_proof_observed") is not False:
            raise ProfileError("official-launch minted proof was marked forged")
        if present.get("forged_unminted_proof_observed") is not False:
            raise ProfileError("official-launch minted proof was marked unminted")
        enforced = enforce_official_launch_token(present)
        if enforced.get("token_present") is not True:
            raise ProfileError("lethal gate rejected a present official-launch token")
        stale_observation = dict(present)
        stale_observation["token_present"] = False
        try:
            enforce_official_launch_token(stale_observation)
        except RuntimeError as exc:
            if "caller-supplied observation disagrees" not in str(exc):
                raise ProfileError(
                    f"official-launch stale observation message unexpected: {exc}"
                ) from exc
        else:
            raise ProfileError("official-launch stale caller observation was trusted")
    finally:
        reset_official_launch_token(token)

    suppress_token = suppress_official_launch_token_for_probe()
    try:
        reset = official_launch_token_observation()
        if reset.get("token_present") is not False:
            raise ProfileError("official-launch token fixture leaked after reset")
    finally:
        reset_official_launch_token(suppress_token)
    return 1


def _assert_official_launch_walker_wiring(repo: Path) -> int:
    kernel_text = (repo / "brick_protocol/support/operator/walker_kernel.py").read_text(
        encoding="utf-8"
    )
    frontier_text = (repo / "brick_protocol/support/operator/walker_frontier.py").read_text(
        encoding="utf-8"
    )
    if "enforce_official_launch_token" not in kernel_text:
        raise ProfileError("official-launch lethal enforce is not wired at walker entry")
    if "official_launch_token_observation()" not in kernel_text:
        raise ProfileError("official-launch token observation is not called at walker entry")
    if kernel_text.count("official_launch_observation=official_launch_observation") < 4:
        raise ProfileError(
            "official-launch token observation is not threaded through every frontier path"
        )
    if '"official_launch_token_observation": dict(official_launch_observation)' not in kernel_text:
        raise ProfileError(
            "official-launch token observation is not recorded in normal dynamic walker evidence"
        )
    if "official_launch_observation: Mapping[str, Any]" not in frontier_text:
        raise ProfileError(
            "official-launch token observation is not a required frontier write-plan input"
        )
    if '"official_launch_token_observation": dict(official_launch_observation)' not in frontier_text:
        raise ProfileError(
            "official-launch token observation is not recorded in frontier dynamic walker evidence"
        )

    observation: Mapping[str, Any] = {
        "kind": "official_launch_token_observation",
        "token_present": False,
        "observation_mode": "gate_lethal",
        "absence_action": "raise_runtime_error",
    }
    plan = _dynamic_frontier_write_plan(
        {"plan_ref": "building-plan:test"},
        reroute_records=[],
        node_budget={},
        node_landings={},
        official_launch_observation=observation,
        held=True,
        hold_record={"hold_reason": "adapter_error_frontier"},
        fan_in_wait_all_observations=[],
        has_fan_groups=False,
    )
    evidence = plan.get("dynamic_walker_evidence")
    if not isinstance(evidence, Mapping):
        raise ProfileError("frontier write-plan did not attach dynamic_walker_evidence")
    recorded = evidence.get("official_launch_token_observation")
    if recorded != dict(observation):
        raise ProfileError(
            "frontier write-plan did not preserve official-launch token evidence"
        )
    if evidence.get("held") is not True:
        raise ProfileError("frontier write-plan fixture did not preserve held state")
    return 1


def run_import_identity_modes(repo: Path) -> KernelResult:
    source_identity = resolve_operator_identity(repo / "brick_protocol/support/operator/cli.py")
    if source_identity.mode != "source" or source_identity.repo_root != repo.resolve():
        raise ProfileError(
            "import_identity_modes source fixture resolved unexpected identity: "
            f"{source_identity!r}"
        )

    observed = _parents_bindings(repo)
    expected = {key: set(value) for key, value in PARENTS_BINDING_REGISTRY.items()}
    if observed != expected:
        raise ProfileError(
            "import_identity_modes parents[N] registry mismatch:\n"
            f"observed={observed!r}\nexpected={expected!r}"
        )

    violations = _identity_source_violations(repo)
    if violations:
        raise ProfileError(
            "import_identity_modes entrypoint helper wiring rejected:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )

    inspected = (
        1
        + len(observed)
        + len(IDENTITY_HELPER_CONSUMERS)
        + _assert_guard_removal_probe_fires(repo)
        + _assert_bad_marker_rejected(repo)
        + _assert_installed_mode_fixture(repo)
        + _assert_official_launch_token_fixture()
        + _assert_official_launch_walker_wiring(repo)
    )
    return KernelResult(
        check_id="import_identity_modes",
        inspected=inspected,
        output=(
            "import identity modes passed: source checkout identity uses the "
            "pyproject marker plus brick_protocol/support/import_identity marker, installed "
            "fixture falls back to importlib.metadata without requiring a "
            "site-packages repo marker, cli/onboard/run consume the helper, "
            "the parents[N] binding registry covers every scanned "
            "brick_protocol/support/operator, brick_protocol/support/checkers, brick_protocol/support/connection, "
            "brick_protocol/support/recording, and brick_protocol/support/import_identity binding, and bad "
            "marker / guard-removal probes fired RED. PROOF LIMIT: support "
            "evidence only; not source truth, success, quality, or Movement "
            "authority."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        print(run_import_identity_modes(repo).output)
    except ProfileError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
