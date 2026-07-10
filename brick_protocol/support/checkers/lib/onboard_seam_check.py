"""Onboard seam behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import importlib
import inspect
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.preset_completion_fixture import _preset_completion_command_runner
from brick_protocol.support.checkers.lib.yaml_subset import ProfileError, require_mapping, require_string, rule_items


def run_onboard_seam_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """ONBOARDING-WIZARD-0 PART-2: assert the example routes through the PART-1 seam.

    Drives the REAL ``support.operator.onboard.run_onboard`` end-to-end with an
    explicit ``adapter:local`` declaration and a TEMP output_root, and asserts the
    PART-2 contract:

      1. ROUTED-THROUGH-SEAM: the example_result records ``routed_through ==
         support.operator.driver.run_building_intake`` (the PART-1 seam), not the
         old raw run_building_plan path.
      2. DECLARATION-ONLY CASTING: the result carries a structured
         ``preflight_readiness`` token (ready/unauthed/missing/unknown), mirrored
         onto the example_result, but the declared adapter is stable across those
         states. Preflight verifies; it never selects or substitutes casting.
      3. HANDOFF-NAMES-SEAM: the closing handoff_message_ko NAMES the seam verb.
      4. FRONTIER-EVIDENCE: the default example routes through the seam and
         reaches the expected frontier with landed evidence under the TEMP
         output_root (never the repo). After preferred step-adapter resolution,
         no-provider machines may honestly record agent_incomplete for verdict
         rows that resolve to non-local preferred adapters.
      5. FAIL-CLOSED-MISSING-PROVIDER: an explicitly declared provider adapter
         that is missing/mismatched stays no-raise but stops before dispatch. It
         is never replaced with adapter:local.

    SELF-FIRE: the case REDs if removing the explicit declaration reintroduces a
    readiness-driven choice, if an unready declaration dispatches, or if it is
    silently substituted with adapter:local.
    """
    items = rule_items(profile, "onboard_seam_case")
    if not items:
        return 0

    onboard_source = (
        repo / "brick_protocol" / "support" / "operator" / "onboard.py"
    ).read_text(encoding="utf-8")
    if "def main(" in onboard_source or 'if __name__ == "__main__"' in onboard_source:
        raise ProfileError(
            "onboard_seam_case rejected module CLI: operator/onboard.py must remain "
            "an import-only support library; public commands enter through brick CLI"
        )
    if '_BUILD_SELECTED_ADAPTER = "codex-local"' in onboard_source:
        raise ProfileError(
            "onboard_seam_case rejected hidden adapter default: onboard.build must "
            "require the caller/COO to declare selected_adapter_ref"
        )

    onboard = importlib.import_module("brick_protocol.support.operator.onboard")
    build_signature = inspect.signature(onboard.build)
    selected_adapter = build_signature.parameters.get("selected_adapter_ref")
    if selected_adapter is None or selected_adapter.default is not inspect.Parameter.empty:
        raise ProfileError(
            "onboard_seam_case rejected onboard.build signature: "
            "selected_adapter_ref must be an explicit required declaration"
        )
    run_onboard_signature = inspect.signature(onboard.run_onboard)
    selected_example_adapter = run_onboard_signature.parameters.get(
        "selected_example_adapter_ref"
    )
    if (
        selected_example_adapter is None
        or selected_example_adapter.default is not inspect.Parameter.empty
    ):
        raise ProfileError(
            "onboard_seam_case rejected run_onboard signature: "
            "selected_example_adapter_ref must be an explicit required declaration"
        )
    if "allow_real_provider" in run_onboard_signature.parameters:
        raise ProfileError(
            "onboard_seam_case rejected readiness-driven casting toggle: "
            "allow_real_provider must not select an example adapter"
        )
    wizard_signature = inspect.signature(onboard.run_install_wizard)
    declared_wizard_adapter = wizard_signature.parameters.get("example_adapter_ref")
    if (
        declared_wizard_adapter is None
        or declared_wizard_adapter.default is not inspect.Parameter.empty
    ):
        raise ProfileError(
            "onboard_seam_case rejected install wizard signature: "
            "example_adapter_ref must be an explicit required declaration"
        )
    if hasattr(onboard, "_choose_example_adapter"):
        raise ProfileError(
            "onboard_seam_case rejected environment casting selector: "
            "_choose_example_adapter must be removed"
        )
    agent_adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    from brick_protocol.support.operator.import_identity import (
        mint_official_launch_token,
        reset_official_launch_token,
    )

    seam_verb = onboard.SEAM_VERB
    command_runner = _preset_completion_command_runner(agent_adapter.LocalCliCompleted)
    expected_local_adapter = "adapter:local"
    allowed_readiness = {"ready", "unauthed", "missing", "unknown"}

    # RED/GREEN seam: the same local declaration must resolve identically across
    # opposite readiness observations, while an unready provider declaration
    # remains itself and is refused before execution.
    local_ready = onboard._resolve_declared_example_casting(
        {"adapter_ref": "adapter:codex-local"},
        "ready",
        selected_example_adapter_ref=expected_local_adapter,
    )
    local_missing = onboard._resolve_declared_example_casting(
        {"adapter_ref": "adapter:codex-local"},
        "missing",
        selected_example_adapter_ref=expected_local_adapter,
    )
    for packet in (local_ready, local_missing):
        if packet.get("adapter_ref") != expected_local_adapter:
            raise ProfileError(
                "onboard_seam_case: machine readiness changed the declared local adapter"
            )
        if packet.get("substitution_performed") is not False:
            raise ProfileError(
                "onboard_seam_case: local declaration reported adapter substitution"
            )
    unready_provider = onboard._resolve_declared_example_casting(
        {"adapter_ref": "adapter:codex-local"},
        "missing",
        selected_example_adapter_ref="adapter:codex-local",
    )
    if (
        unready_provider.get("dispatch_allowed") is not False
        or unready_provider.get("adapter_ref") != "adapter:codex-local"
        or unready_provider.get("error_kind") != "declared_example_adapter_not_ready"
        or unready_provider.get("substitution_performed") is not False
        or unready_provider.get("execution_started") is not False
    ):
        raise ProfileError(
            "onboard_seam_case: unready declared provider did not fail closed "
            f"without substitution: {unready_provider!r}"
        )

    count = 0
    for item in items:
        mapping = require_mapping(item, "onboard_seam_case item")
        label = require_string(mapping.get("label"), "onboard_seam_case.label")
        host = require_string(mapping.get("host", "codex"), f"{label}: host")
        bogus_host = require_string(
            mapping.get("bogus_host", "definitely-not-a-host"), f"{label}: bogus_host"
        )
        # FRONTIER is provider-availability dependent (see docstring): the example's
        # preferred-step adapters resolve to non-local providers whose readiness + the
        # design-step outcome decide whether verdict rows complete or honestly record
        # agent_incomplete. BOTH are honest. Accept the declared honest SET, not a
        # single machine-dependent value -- a single pin makes this profile flaky on
        # provider-equipped machines (brick verify / --all). Anything OUTSIDE the set
        # (error/empty/unexpected) still REDs.
        acceptable_raw = mapping.get("acceptable_frontier_kinds")
        if acceptable_raw is not None:
            if not isinstance(acceptable_raw, (list, tuple)) or not acceptable_raw:
                raise ProfileError(
                    f"{label}: acceptable_frontier_kinds must be a non-empty list"
                )
            acceptable_frontiers = {
                require_string(value, f"{label}: acceptable_frontier_kinds item")
                for value in acceptable_raw
            }
        else:
            acceptable_frontiers = {
                require_string(
                    mapping.get("expected_frontier_kind", "complete"),
                    f"{label}: expected_frontier_kind",
                )
            }

        # (1)-(4) Explicit bundled declaration: adapter:local through the seam.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-") as tmp:
            tmp_root = Path(tmp)
            launch_token = mint_official_launch_token()
            try:
                try:
                    result = onboard.run_onboard(
                        host,
                        repo_root=repo,
                        selected_example_adapter_ref=expected_local_adapter,
                        run_example=True,
                        output_root=tmp_root,
                        command_runner=command_runner,
                    )
                except Exception as exc:  # noqa: BLE001 -- no-raise is under test
                    raise ProfileError(
                        f"onboard_seam_case rejected {label}: run_onboard raised "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
            finally:
                reset_official_launch_token(launch_token)

            readiness = result.get("preflight_readiness")
            if readiness not in allowed_readiness:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: preflight_readiness must be "
                    f"recorded as one of {sorted(allowed_readiness)}, got {readiness!r}"
                )

            handoff = str(result.get("handoff_message_ko") or "")
            if seam_verb not in handoff:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: handoff must NAME the seam verb "
                    f"{seam_verb!r}; got handoff without it"
                )

            example = result.get("example_result")
            if not isinstance(example, Mapping):
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example_result must be a mapping"
                )
            if example.get("routed_through") != seam_verb:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example must route through the seam "
                    f"{seam_verb!r}; got routed_through={example.get('routed_through')!r} "
                    "(the example bypassed the PART-1 seam)"
                )
            if example.get("preflight_readiness") != readiness:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example_result must mirror the "
                    f"recorded preflight_readiness {readiness!r}; got "
                    f"{example.get('preflight_readiness')!r}"
                )
            if not str(example.get("adapter_declaration_basis") or "").strip():
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example must record an "
                    "adapter_declaration_basis (which declaration was verified)"
                )
            if example.get("declared_adapter_ref") != expected_local_adapter:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example did not preserve "
                    "its explicit adapter declaration"
                )
            if example.get("substitution_performed") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example substituted adapters"
                )
            if example.get("adapter_ref") != expected_local_adapter:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: default (no opt-in) example must "
                    f"use {expected_local_adapter!r}; got {example.get('adapter_ref')!r}"
                )
            if example.get("real_provider") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: default example must record "
                    f"real_provider False; got {example.get('real_provider')!r}"
                )
            if example.get("ran") is not True:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example did not run (ran != True)"
                )
            if example.get("frontier_kind") not in acceptable_frontiers:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example frontier "
                    f"{example.get('frontier_kind')!r} is not one of the honest "
                    f"provider-dependent outcomes {sorted(acceptable_frontiers)}"
                )
            evidence_root = str(example.get("evidence_root") or "")
            if not evidence_root:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example missing evidence_root"
                )
            try:
                Path(evidence_root).resolve().relative_to(tmp_root.resolve())
            except ValueError as exc:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example evidence must land under "
                    f"the TEMP output_root, not {evidence_root}"
                ) from exc
            if int(example.get("written_file_count") or 0) <= 0:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example produced no evidence files"
                )

        # (5) FIRE: a missing/mismatched explicitly declared provider adapter
        #     must NOT raise, dispatch, or silently substitute adapter:local.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-missing-") as tmp:
            tmp_root = Path(tmp)
            launch_token = mint_official_launch_token()
            try:
                try:
                    missing = onboard.run_onboard(
                        bogus_host,
                        repo_root=repo,
                        selected_example_adapter_ref="adapter:codex-local",
                        run_example=True,
                        output_root=tmp_root,
                        command_runner=command_runner,
                    )
                except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
                    raise ProfileError(
                        f"onboard_seam_case rejected {label}: run_onboard raised for a "
                        f"missing/bogus provider host (friendly contract broken): "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
            finally:
                reset_official_launch_token(launch_token)
            missing_example = missing.get("example_result")
            if not isinstance(missing_example, Mapping):
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider example_result "
                    "must be a mapping"
                )
            if missing_example.get("ran") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing declared provider dispatched"
                )
            if missing_example.get("adapter_ref") != "adapter:codex-local":
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing declared provider was "
                    f"substituted: {missing_example!r}"
                )
            if missing_example.get("substitution_performed") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing provider substitution flag drifted"
                )
            if missing_example.get("execution_started") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing provider execution started"
                )
            if missing_example.get("error_kind") not in {
                "example_adapter_preflight_mismatch",
                "declared_example_adapter_not_ready",
            }:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing provider stop reason drifted: "
                    f"{missing_example!r}"
                )
            if missing.get("preflight_readiness") not in {"missing", "unauthed", "unknown"}:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: a bogus/missing-provider host must NOT "
                    "record preflight_readiness 'ready' (a readiness mislabel) and must record one "
                    f"of missing/unauthed/unknown; got {missing.get('preflight_readiness')!r}"
                )
        count += 1
    return count
