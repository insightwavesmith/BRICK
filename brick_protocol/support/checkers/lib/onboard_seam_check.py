"""Onboard seam behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import importlib
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.preset_completion_fixture import _preset_completion_command_runner
from brick_protocol.support.checkers.lib.yaml_subset import ProfileError, require_mapping, require_string, rule_items


def run_onboard_seam_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """ONBOARDING-WIZARD-0 PART-2: assert the example routes through the PART-1 seam.

    Drives the REAL ``support.operator.onboard.run_onboard`` end-to-end on the
    default (no real-provider opt-in) path with a TEMP output_root and asserts the
    PART-2 contract:

      1. ROUTED-THROUGH-SEAM: the example_result records ``routed_through ==
         support.operator.driver.run_building_intake`` (the PART-1 seam), not the
         old raw run_building_plan path.
      2. PREFLIGHT-READINESS-EVIDENCE: the result carries a structured
         ``preflight_readiness`` token (ready/unauthed/missing/unknown), mirrored
         onto the example_result -- preflight is auditable evidence, not just a
         Korean string. The example_result also records the adapter it used and the
         ``adapter_choice_basis`` (WHY), so the real-vs-local routing is auditable.
      3. HANDOFF-NAMES-SEAM: the closing handoff_message_ko NAMES the seam verb.
      4. FRONTIER-EVIDENCE: the default example routes through the seam and
         reaches the expected frontier with landed evidence under the TEMP
         output_root (never the repo). After preferred step-adapter resolution,
         no-provider machines may honestly record agent_incomplete for verdict
         rows that resolve to non-local preferred adapters.
      5. NEVER-RAISES-MISSING-PROVIDER: a bogus / missing-provider host stays
         ok-friendly (no raise) and STILL routes the friendly fallback through the
         seam on adapter:local.

    SELF-FIRE: the case REDs if the example bypasses the seam (routed_through is not
    the seam verb, or the default branch did not run on adapter:local) OR if the
    handoff omits the seam pointer OR if preflight readiness is not recorded. The
    last item additionally asserts run_onboard NEVER raises for a missing provider.
    """
    items = rule_items(profile, "onboard_seam_case")
    if not items:
        return 0

    onboard = importlib.import_module("brick_protocol.support.operator.onboard")
    agent_adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    seam_verb = onboard.SEAM_VERB
    command_runner = _preset_completion_command_runner(agent_adapter.LocalCliCompleted)
    expected_local_adapter = "adapter:local"
    allowed_readiness = {"ready", "unauthed", "missing", "unknown"}

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

        # (1)-(4) Default path: no real-provider opt-in -> adapter:local through seam.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-") as tmp:
            tmp_root = Path(tmp)
            try:
                result = onboard.run_onboard(
                    host,
                    repo_root=repo,
                    run_example=True,
                    output_root=tmp_root,
                    allow_real_provider=False,
                    command_runner=command_runner,
                )
            except Exception as exc:  # noqa: BLE001 -- no-raise is under test
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: run_onboard raised "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

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
            if not str(example.get("adapter_choice_basis") or "").strip():
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example must record an "
                    "adapter_choice_basis (WHY the adapter was chosen)"
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

        # (5) FIRE / friendliness: a bogus / missing-provider host must NOT raise and
        #     must STILL route the friendly fallback through the seam on adapter:local.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-missing-") as tmp:
            tmp_root = Path(tmp)
            try:
                missing = onboard.run_onboard(
                    bogus_host,
                    repo_root=repo,
                    run_example=True,
                    output_root=tmp_root,
                    allow_real_provider=True,
                    command_runner=command_runner,
                )
            except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: run_onboard raised for a "
                    f"missing/bogus provider host (friendly contract broken): "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            missing_example = missing.get("example_result")
            if not isinstance(missing_example, Mapping):
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider example_result "
                    "must be a mapping"
                )
            if missing_example.get("routed_through") != seam_verb:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider fallback must still "
                    f"route through the seam {seam_verb!r}; got "
                    f"{missing_example.get('routed_through')!r}"
                )
            if missing_example.get("adapter_ref") != expected_local_adapter:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider fallback must use "
                    f"{expected_local_adapter!r}; got {missing_example.get('adapter_ref')!r}"
                )
            if missing.get("preflight_readiness") not in {"missing", "unauthed", "unknown"}:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: a bogus/missing-provider host must NOT "
                    "record preflight_readiness 'ready' (a readiness mislabel) and must record one "
                    f"of missing/unauthed/unknown; got {missing.get('preflight_readiness')!r}"
                )
        count += 1
    return count
