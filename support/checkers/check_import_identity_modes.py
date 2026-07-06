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


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError
from support.operator.import_identity import resolve_operator_identity


PARENTS_BINDING_REGISTRY = {
    "support/checkers/check_adapter_usage_meter.py": {2},
    "support/checkers/check_agent_object_schema_single_source.py": {2},
    "support/checkers/check_assembly_equivalence.py": {2},
    "support/checkers/check_bounded_agent_proposed_routing_loop0.py": {2},
    "support/checkers/check_brick_template_catalog_restructure.py": {2},
    "support/checkers/check_bricks_spec_completeness.py": {2},
    "support/checkers/check_building_operator_driver0.py": {2},
    "support/checkers/check_chained_carry_dependency.py": {2},
    "support/checkers/check_cli_runner_stdin_devnull.py": {2},
    "support/checkers/check_declaration_enforcement_parity.py": {2},
    "support/checkers/check_driver_public_intake_seal.py": {2},
    "support/checkers/check_fan_out_sibling_evidence_independence.py": {2},
    "support/checkers/check_first_use_wizard.py": {2},
    "support/checkers/check_gate_policy_action_single_source.py": {2},
    "support/checkers/check_gate_registry_single_source.py": {2},
    "support/checkers/check_import_identity_modes.py": {2},
    "support/checkers/check_interactive_provider_intake.py": {2},
    "support/checkers/check_link_gate_measurement_separation.py": {2},
    "support/checkers/check_mcp_dispatch_wire.py": {2},
    "support/checkers/check_model_lane_matching_discipline.py": {2},
    "support/checkers/check_positive_int_bool_boundary.py": {2},
    "support/checkers/check_recording_checker_derived_contract.py": {2},
    "support/checkers/check_report_env_autoload.py": {2},
    "support/checkers/check_return_field_merge_set_parity.py": {2},
    "support/checkers/check_session_continuity_adapter.py": {2},
    "support/checkers/check_step_output_evidence_field_set_parity.py": {2},
    "support/checkers/lib/adapter_error_check.py": {3},
    "support/checkers/lib/agent_adapter_return_shape_check.py": {3},
    "support/checkers/lib/agent_output_text_preservation_check.py": {3},
    "support/checkers/lib/agent_session_id_redaction_check.py": {3},
    "support/checkers/lib/axis_vocab_drift_check.py": {3},
    "support/checkers/lib/brick_cli_entrypoint_check.py": {3},
    "support/checkers/lib/building_plan_graph_check.py": {3},
    "support/checkers/lib/building_result_summary_check.py": {3},
    "support/checkers/lib/chat_session_park_check.py": {3},
    "support/checkers/lib/dashboard_productization_projection_check.py": {3},
    "support/checkers/lib/deliverable_crosscheck_gate_check.py": {3},
    "support/checkers/lib/mcp_connect_projection_check.py": {3},
    "support/checkers/lib/raw_evidence_stream_scrub_check.py": {3},
    "support/checkers/lib/re_instruction_endline_gate_check.py": {3},
    "support/checkers/lib/reporter_notification_projection_check.py": {3},
    "support/checkers/probe_prompt_behavior_red.py": {2},
    "support/checkers/probe_wheel_smoke_stale_build_red.py": {2},
    "support/connection/adapter_constants.py": {2},
    "support/connection/agent_resources.py": {2},
    "support/connection/building_design_toolkit.py": {2},
    "support/connection/connect.py": {2},
    "support/connection/coo_sync.py": {2},
    "support/connection/mcp_projection.py": {2},
    "support/import_identity/brick_protocol/__init__.py": {3},
    "support/recording/capture.py": {2},
    "support/operator/cli.py": {2},
    "support/operator/dashboard_export.py": {2},
    "support/operator/primitives.py": {2},
    "support/operator/report_sinks.py": {2},
    "support/operator/reporter.py": {2},
    "support/operator/task_order_preflight.py": {2},
}
IDENTITY_HELPER_CONSUMERS = {
    "support/operator/cli.py",
    "support/operator/onboard.py",
    "support/operator/run.py",
}
PARENTS_BINDING_SCAN_ROOTS = (
    "support/operator",
    "support/checkers",
    "support/connection",
    "support/recording",
    "support/import_identity/brick_protocol",
)
PARENTS_BINDING_RE = re.compile(
    r"Path\(__file__\)\.resolve\(\)\.parents\[(?P<index>\d+)\]"
)


@contextlib.contextmanager
def _checker_tempdir(repo: Path, prefix: str):
    scratch_parent = repo / "support/checkers/.tmp-import-identity"
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
    cli_path = repo / "support/operator/cli.py"
    original = cli_path.read_text(encoding="utf-8")
    mutated = original.replace(
        "resolve_operator_identity(__file__)",
        "Path(__file__).resolve().parents[2]",
        1,
    )
    if mutated == original:
        raise ProfileError("import_identity_modes guard-removal probe could not mutate cli.py")
    violations = _identity_text_violations("support/operator/cli.py", mutated)
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
        operator_dir = root / "support/operator"
        import_identity_dir = root / "support/import_identity/brick_protocol"
        operator_dir.mkdir(parents=True)
        import_identity_dir.mkdir(parents=True)
        anchor = operator_dir / "cli.py"
        anchor.write_text("", encoding="utf-8")
        (import_identity_dir / "__init__.py").write_text("", encoding="utf-8")
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
    helper_text = (repo / "support/operator/import_identity.py").read_text(encoding="utf-8")
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


def run_import_identity_modes(repo: Path) -> KernelResult:
    source_identity = resolve_operator_identity(repo / "support/operator/cli.py")
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
    )
    return KernelResult(
        check_id="import_identity_modes",
        inspected=inspected,
        output=(
            "import identity modes passed: source checkout identity uses the "
            "pyproject marker plus support/import_identity marker, installed "
            "fixture falls back to importlib.metadata without requiring a "
            "site-packages repo marker, cli/onboard/run consume the helper, "
            "the parents[N] binding registry covers every scanned "
            "support/operator, support/checkers, support/connection, "
            "support/recording, and support/import_identity binding, and bad "
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
