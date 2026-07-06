"""QA-built negative probes for the selflock-0706n slice (NOT builder fixtures).

Probe A (concern 1): intake-vs-live rejection-set identity on the documented
  stop + adapter_error_frontier hold (paper-stop) path with an empty
  agent-return ledger. Live resume early-returns paper-stop BEFORE the
  recorded-returns check (walker_resume.py:305-320 vs :323-325); the new
  validate_disposition_intake runs the recorded-returns check unconditionally
  (walker_resume.py:1440-1442). Divergence = intake refuses a row the live
  path accepts.
Probe B (concern 3): a malformed void row addressed to the current hold makes
  the resume raise (fail-closed I5) and there is no void-a-void channel.
Probe C (concern 2): a grounded void can flip selection from the LATEST valid
  human row back to an EARLIER valid human row (selection lever); author gate
  parity for the void verb.
Probe D (concern 1, positive): the intake-only hold-identity drift literal
  actually fires for a drifted row (no SL fixture covers it behaviorally).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "support" / "import_identity"))
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location(
    "qa_mirror_checker",
    REPO / "support" / "checkers" / "check_resume_replay_disposition_mirror.py",
)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)

from brick_protocol.support.operator import onboard  # noqa: E402
from brick_protocol.support.operator import walker_resume  # noqa: E402

OUT: dict[str, object] = {}


def _held_building(prefix: str, tmp: Path):
    plan, _bricks = mc._chain_plan(
        prefix,
        ["design", "build", "review", "close"],
        {("design", "build"): "h1", ("review", "close"): "h2"},
        {"review": 5, "build": 5},
    )
    cb = mc._CountingCallable()
    result = mc._run_to_hold(REPO, plan, tmp.resolve(), cb)
    root = result.lifecycle_write.root
    assert mc._frontier_kind(root, REPO) == "link_paused", "setup did not hold"
    return plan, cb, result, root


def probe_a() -> dict[str, object]:
    obs: dict[str, object] = {"probe": "A-intake-vs-live-adapter-error-stop"}
    with tempfile.TemporaryDirectory(prefix="bp-qa-selflock-a-") as tmp:
        plan, cb, result, root = _held_building("qaselflock-a", Path(tmp))
        # Mutate the held evidence into the documented adapter-error hold shape
        # (quickstart.md:79) with an EMPTY recorded-return ledger (first-step
        # adapter-error class: no Agent return was ever recorded).
        manifest_path = root / "evidence" / "evidence-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plan_copy = json.loads(manifest["plan_snapshot"]["plan_rows_copy"])
        hold = plan_copy["dynamic_walker_evidence"]["hold"]
        hold["hold_reason"] = "adapter_error_frontier"
        manifest["plan_snapshot"]["plan_rows_copy"] = json.dumps(plan_copy)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (root / "raw" / "agent-return.jsonl").write_text("", encoding="utf-8")

        pending = hold["pending_target_ref"]
        paused = mc._current_hold_paused_at_ref(root)
        stop_row = {
            "raw_ref": "raw:link:disposition:stop",
            "building_id": plan["building_id"],
            "step_ref": "human-disposition-stop",
            "transition_lifecycle_state": "resumed",
            "transition_lifecycle_progress_state": "in_progress",
            "transition_lifecycle_resumed_from_ref": paused,
            "transition_lifecycle_pending_target_ref": pending,
            "transition_lifecycle_required_disposition_owner": "caller-or-coo",
            "transition_lifecycle_disposition_action": "stop",
            "transition_author_ref": "coo:smith",
        }
        # 1) the new intake gate on the SAME row/root
        try:
            walker_resume.validate_disposition_intake(root, stop_row, repo_root=REPO)
            obs["intake"] = "ACCEPTED"
        except ValueError as exc:
            obs["intake"] = f"REFUSED: {exc}"
        # 2) the live resume path on the SAME row/root (direct raw append)
        with (root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(stop_row, separators=(",", ":")) + "\n")
        try:
            mc._resume(REPO, root, cb)
            obs["live_resume"] = f"ACCEPTED (frontier={mc._frontier_kind(root, REPO)!r})"
        except ValueError as exc:
            obs["live_resume"] = f"REFUSED: {exc}"
    return obs


def probe_b() -> dict[str, object]:
    obs: dict[str, object] = {"probe": "B-malformed-void-reblocks-resume"}
    with tempfile.TemporaryDirectory(prefix="bp-qa-selflock-b-") as tmp:
        plan, cb, result, root = _held_building("qaselflock-b", Path(tmp))
        pending = mc._current_pending_target(result)
        paused = mc._current_hold_paused_at_ref(root)
        # a VALID forward disposition that would resume fine on its own
        mc._append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=pending, action="forward"
        )
        # a MALFORMED void row addressed to the current hold (foreign author)
        void_row = {
            "raw_ref": "raw:link:disposition-void:rogue",
            "building_id": plan["building_id"],
            "kind": walker_resume.DISPOSITION_VOID_RECORD_KIND,
            "paused_at_ref": paused,
            "voided_raw_ref": "raw:link:disposition:forward",
            "same_hold_index": 1,
            "transition_author_ref": "agent:rogue",
        }
        with (root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(void_row, separators=(",", ":")) + "\n")
        try:
            mc._resume(REPO, root, cb)
            obs["resume_with_malformed_void"] = "ACCEPTED"
        except ValueError as exc:
            obs["resume_with_malformed_void"] = f"REFUSED: {exc}"
        # is there a correction channel for the poisoned void? (void-a-void)
        counter = onboard.run_disposition_void_entry(
            root,
            author_ref="coo:smith",
            voided_raw_ref="raw:link:disposition-void:rogue",
            same_hold_index=1,
            repo_root=REPO,
        )
        obs["void_the_void"] = {
            "ok": counter.get("ok"),
            "error_kind": counter.get("error_kind"),
        }
        # can a corrected disposition still be authored through onboard?
        approve = onboard.run_approve_entry(
            root,
            action="forward",
            author_ref="coo:smith",
            repo_root=REPO,
            adapter_cwd=Path(tmp) / "adapter-cwd-b",
        )
        obs["onboard_after_poisoned_void"] = {
            "ok": approve.get("ok"),
            "error_kind": approve.get("error_kind"),
            "disposition_written": approve.get("disposition_written"),
            "error_message": str(approve.get("error_message"))[:160],
        }
    return obs


def probe_c() -> dict[str, object]:
    obs: dict[str, object] = {"probe": "C-void-flips-selection-between-valid-rows"}
    with tempfile.TemporaryDirectory(prefix="bp-qa-selflock-c-") as tmp:
        plan, cb, result, root = _held_building("qaselflock-c", Path(tmp))
        pending = mc._current_pending_target(result)
        # row 1: valid forward; row 2: valid reroute to a DECLARED node (the
        # later-authored human decision that would normally be selected)
        mc._append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=pending, action="forward"
        )
        mc._append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=f"{plan['building_id']}-design".replace(
                plan["building_id"], "brick-" + plan["building_id"]
            ),
            action="reroute",
        )
        # author-gate parity check for the void verb
        rogue = onboard.run_disposition_void_entry(
            root,
            author_ref="agent:rogue",
            voided_raw_ref="raw:link:disposition:reroute",
            same_hold_index=2,
            repo_root=REPO,
        )
        obs["rogue_author_void"] = {
            "ok": rogue.get("ok"),
            "error_kind": rogue.get("error_kind"),
        }
        # grounded void of the LATEST (valid reroute) row
        flip = onboard.run_disposition_void_entry(
            root,
            author_ref="coo:smith",
            voided_raw_ref="raw:link:disposition:reroute",
            same_hold_index=2,
            repo_root=REPO,
        )
        obs["void_latest_valid_row"] = {
            "ok": flip.get("ok"),
            "void_written": flip.get("void_written"),
            "error_kind": flip.get("error_kind"),
        }
        if flip.get("ok"):
            try:
                mc._resume(REPO, root, cb)
                obs["resume_after_flip"] = (
                    f"ACCEPTED (frontier={mc._frontier_kind(root, REPO)!r}) "
                    "-- EARLIER forward row applied instead of the LATER reroute row"
                )
            except ValueError as exc:
                obs["resume_after_flip"] = f"REFUSED: {exc}"
    return obs


def probe_d() -> dict[str, object]:
    obs: dict[str, object] = {"probe": "D-hold-identity-drift-literal-fires"}
    with tempfile.TemporaryDirectory(prefix="bp-qa-selflock-d-") as tmp:
        plan, cb, result, root = _held_building("qaselflock-d", Path(tmp))
        pending = mc._current_pending_target(result)
        drift_row = {
            "raw_ref": "raw:link:disposition:forward",
            "building_id": plan["building_id"],
            "step_ref": "human-disposition-forward",
            "transition_lifecycle_state": "resumed",
            "transition_lifecycle_progress_state": "in_progress",
            "transition_lifecycle_resumed_from_ref": "link-transition:STALE-hold-ref",
            "transition_lifecycle_pending_target_ref": pending,
            "transition_lifecycle_required_disposition_owner": "caller-or-coo",
            "transition_lifecycle_disposition_action": "forward",
            "transition_author_ref": "coo:smith",
        }
        try:
            walker_resume.validate_disposition_intake(root, drift_row, repo_root=REPO)
            obs["intake_drift_row"] = "ACCEPTED (drift guard did NOT fire)"
        except ValueError as exc:
            obs["intake_drift_row"] = f"REFUSED: {str(exc)[:220]}"
    return obs


def main() -> int:
    for fn in (probe_a, probe_b, probe_c, probe_d):
        name = fn.__name__
        try:
            OUT[name] = fn()
        except Exception:
            OUT[name] = {"probe": name, "CRASHED": traceback.format_exc()[-1500:]}
    print(json.dumps(OUT, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
