"""Checker for adopted-reroute re_instruction endline-rule consumption.

Support checker mechanics only: this imports the onboarding support surface and
observes that declared Brick template re_instruction rules are consumed before a
human/COO reroute disposition row can be written. It authors no Link facts,
chooses no Movement, and judges neither success nor quality.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _entry in (_REPO_ROOT, _REPO_ROOT / "support" / "import_identity"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError  # noqa: E402

CHECK_ID = "re_instruction_endline_gate"
_LEDGER_CONSUMER_TEXT = (
    "Consumed by support/operator/onboard.py run_approve_entry adoption-time "
    "check + support/checkers/lib/re_instruction_endline_gate_check.py kernel "
    "check re_instruction_endline_gate; runtime Link-side gate placement remains "
    "outside this non-walker slice."
)

_COMPLIANT_RE_INSTRUCTION = (
    "Done endline: D1-D4 are addressed with evidence before the reroute is "
    "treated as DONE. Proof requests must be executable in the receiving dev "
    "lane: run the focused re_instruction_endline_gate profile and the existing "
    "resume/onboard fixture checks. Repairs outside the receiving lane's scope "
    "are COO gate items, not re-dispatch."
)
_CARRIED_REAL_SAMPLE_RE_INSTRUCTION = (
    "종료선: D1~D4 전수면 DONE. 수신 레인의 환경에서 실행 가능한 증명만 요구한다: "
    "focused profile과 기존 reroute/resume/onboard fixtures를 실행한다. "
    "scope 밖 수리는 COO 게이트로 위임한다."
)
_PROHIBITION_FORM_RE_INSTRUCTION = (
    "done endline: return D1-D4 evidence before treating the reroute as done. "
    "Proof must be executable in the receiving lane. Do not git push or git "
    "commit; repairs outside the receiving lane's scope are COO gate items."
)
_KOREAN_POSTFIX_PROHIBITION_RE_INSTRUCTION = (
    "종료선: D1-D4 증거를 반환하면 DONE. 수신 레인에서 실행 가능한 증명만 "
    "요구한다. git push나 git commit은 증명으로 요구하지 말고, 범위 밖 "
    "수리는 COO 처분 항목으로 위임한다."
)
_DESCRIPTIVE_MENTION_RE_INSTRUCTION = (
    "Done endline: return D1-D4 evidence before DONE. The previous review "
    "mentioned git push only as a bad example; do not request it. Repairs "
    "outside the receiving lane's scope are gate items, not redispatch."
)
_TOKEN_BOUNDARY_RE_INSTRUCTION = (
    "Done endline: return D1-D4 evidence before DONE. Run lane-local proof. "
    "A piano note is not a no marker, and abandoned text must not count as "
    "the endline. Repairs outside scope are deferred items."
)


def run_re_instruction_endline_gate(repo: Path) -> KernelResult:
    from brick_protocol.support.operator import onboard as onboard_module
    from brick_protocol.support.operator.onboard import (
        _re_instruction_endline_rules,
        _re_instruction_rule_violations,
        run_approve_entry,
    )

    rules = _re_instruction_endline_rules(repo)
    if len(rules) != 3:
        raise ProfileError(
            f"{CHECK_ID} expected exactly three declared rules, observed {len(rules)}"
        )
    _assert_ledger_consumer(repo)

    red_cases: dict[str, str] = {
        "missing-endline": (
            "Retry the work and prove it with focused checks only. Repairs outside "
            "the receiving lane's scope are COO gate items, not re-dispatch."
        ),
        "non-executable-proof": (
            "Done endline: finish D1. Then git push the repair branch as proof. "
            "Repairs outside the receiving lane's scope are COO gate items, not "
            "re-dispatch."
        ),
        "read-only-all-proof": (
            "Done endline: finish D2. In the read-only lane, rerun --all as the "
            "required proof. Repairs outside the receiving lane's scope are COO "
            "gate items, not re-dispatch."
        ),
        "standalone-done-required": (
            "The abandoned marker is not an endline. Proof must be executable in "
            "the receiving lane. Repairs outside scope are deferred items."
        ),
        "scope-repair-without-coo-gate": (
            "Done endline: finish D3. Fix any outside scope defect directly before "
            "returning."
        ),
    }
    for label, text in red_cases.items():
        _assert_rejects(_re_instruction_rule_violations(text, rules), label)

    for label, text in {
        "compliant": _COMPLIANT_RE_INSTRUCTION,
        "carried-real-sample": _CARRIED_REAL_SAMPLE_RE_INSTRUCTION,
        "prohibition-form": _PROHIBITION_FORM_RE_INSTRUCTION,
        "korean-postfix-prohibition": _KOREAN_POSTFIX_PROHIBITION_RE_INSTRUCTION,
        "descriptive-mention": _DESCRIPTIVE_MENTION_RE_INSTRUCTION,
        "token-boundary": _TOKEN_BOUNDARY_RE_INSTRUCTION,
    }.items():
        violations = _re_instruction_rule_violations(text, rules)
        if violations:
            raise ProfileError(f"{CHECK_ID} valid fixture rejected {label}: {violations!r}")

    with tempfile.TemporaryDirectory(prefix="bp-re-instruction-gate-") as tmp:
        root = Path(tmp) / "building"
        (root / "raw").mkdir(parents=True, exist_ok=True)
        link_path = root / "raw" / "link.jsonl"
        link_path.write_text("", encoding="utf-8")
        result = run_approve_entry(
            root,
            action="reroute",
            author_ref="coo:checker",
            reroute_target_ref="brick-retry-target",
            re_instruction=red_cases["missing-endline"],
            repo_root=repo,
        )
        if result.get("error_kind") != "re_instruction_endline_rule_violation":
            raise ProfileError(
                f"{CHECK_ID} invalid reroute was not refused before adoption: {result!r}"
            )
        if link_path.read_text(encoding="utf-8") != "":
            raise ProfileError(f"{CHECK_ID} invalid reroute wrote raw/link.jsonl")

    held_frontier = {
        "frontier_kind": "link_paused",
        "latest_transition_lifecycle": {
            "transition_lifecycle_pending_target_ref": "brick-held-work",
            "transition_lifecycle_paused_at_ref": "link-transition:held",
        },
    }
    original_observe = onboard_module.observe_building_frontier
    onboard_module.observe_building_frontier = lambda *_args, **_kwargs: dict(held_frontier)
    try:
        with tempfile.TemporaryDirectory(prefix="bp-re-instruction-valid-") as tmp:
            root = Path(tmp) / "building"
            valid_result = run_approve_entry(
                root,
                action="reroute",
                author_ref="coo:checker",
                reroute_target_ref="brick-retry-target",
                re_instruction=_COMPLIANT_RE_INSTRUCTION,
                repo_root=repo,
            )
    finally:
        onboard_module.observe_building_frontier = original_observe
    if valid_result.get("error_kind") == "re_instruction_endline_rule_violation":
        raise ProfileError(f"{CHECK_ID} compliant reroute was refused: {valid_result!r}")

    return KernelResult(
        check_id=CHECK_ID,
        inspected=8,
        output=(
            "re_instruction_endline_gate passed: three declared rules loaded; "
            "missing endline, non-executable proof, read-only --all proof, and "
            "scope repair without COO gate RED fixtures rejected before raw link "
            "write; compliant, carried real-sample, Korean postfix prohibition, "
            "descriptive mention, and token-boundary fixtures accepted."
        ),
    )


def _assert_rejects(violations: list[str], label: str) -> None:
    if not violations:
        raise ProfileError(f"{CHECK_ID} RED fixture did not reject: {label}")


def _assert_ledger_consumer(repo: Path) -> None:
    ledger = repo / "brick" / "templates" / "enforcement-ledger.yaml"
    text = ledger.read_text(encoding="utf-8")
    if text.count(_LEDGER_CONSUMER_TEXT) != 2:
        raise ProfileError(
            f"{CHECK_ID} enforcement ledger must name this consumer exactly twice"
        )
