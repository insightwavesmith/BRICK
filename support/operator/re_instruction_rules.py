"""Shared support rules for human/COO ``re_instruction`` text.

This module is support mechanics only. It reads declared Brick template rule
lines and returns narrow validation observations; it authors no Link facts,
chooses no Movement or route, and judges neither quality nor success.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_RE_INSTRUCTION_RULES_REL = Path("brick/templates/reroute-defaults.yaml")
_RE_INSTRUCTION_RULES_KEY = "re_instruction_endline_rules"
_RE_INSTRUCTION_ENDLINE_MARKERS = ("종료선",)
_RE_INSTRUCTION_DONE_RE = re.compile(r"(?<![A-Za-z0-9_])done(?![A-Za-z0-9_])", re.IGNORECASE)
_RE_INSTRUCTION_NONEXECUTABLE_PROOF_PATTERNS = (
    "git commit",
    "git push",
)
_RE_INSTRUCTION_PROHIBITION_CONTEXT_MARKERS = (
    "do not ",
    "don't ",
    "must not ",
    "mustn't ",
    "never ",
    "금지",
    "하지 마",
    "하지 말",
    "하면 안",
)
_RE_INSTRUCTION_SAFE_MENTION_CONTEXT_MARKERS = (
    "bad example",
    "example only",
    "fixture",
    "mentioned",
    "prior",
    "previous",
    "not asking",
    "금지 예시",
)
_RE_INSTRUCTION_READ_ONLY_ALL_MARKERS = (
    "read-only",
    "read only",
    "readonly",
    "읽기 전용",
)
_RE_INSTRUCTION_SCOPE_OUTSIDE_MARKERS = (
    "outside the receiving lane's scope",
    "outside scope",
    "out-of-scope",
    "out of scope",
    "scope 밖",
    "범위 밖",
    "write_scope 밖",
    "write scope 밖",
)
_RE_INSTRUCTION_REPAIR_MARKERS = (
    "repair",
    "fix",
    "change",
    "edit",
    "수리",
    "수정",
    "고쳐",
    "바꿔",
)
_RE_INSTRUCTION_COO_GATE_MARKERS = (
    "COO gate",
    "COO 게이트",
    "COO disposition",
    "COO 처분",
    "COO item",
    "COO 항목",
)
_RE_INSTRUCTION_SCOPE_DELEGATION_MARKERS = (
    "gate",
    "disposition",
    "handoff",
    "item",
    "escalate",
    "defer",
    "not re-dispatch",
    "not redispatch",
    "게이트",
    "처분",
    "위임",
)


def re_instruction_endline_rules(repo: Path) -> list[str]:
    """Read the declared reroute re_instruction rule lines from Brick YAML."""

    path = repo / _RE_INSTRUCTION_RULES_REL
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    rules: list[str] = []
    in_rules = False
    for line in lines:
        stripped = line.strip()
        if not in_rules:
            if stripped == f"{_RE_INSTRUCTION_RULES_KEY}:":
                in_rules = True
            continue
        if not stripped:
            continue
        if not line.startswith((" ", "\t")):
            break
        if stripped.startswith("- "):
            rule = stripped[2:].strip()
            if rule:
                rules.append(rule)
    return rules


def re_instruction_rule_violations(text: str, rules: Sequence[str]) -> list[str]:
    """Return narrow support-observation violations for re_instruction text."""

    violations: list[str] = []
    if len([rule for rule in rules if str(rule).strip()]) < 3:
        return [
            "declared re_instruction_endline_rules must contain at least three rules"
        ]

    if not _re_instruction_has_endline_marker(text):
        violations.append(str(rules[0]))

    lowered = text.lower()
    for pattern in _RE_INSTRUCTION_NONEXECUTABLE_PROOF_PATTERNS:
        if _re_instruction_has_nonexecutable_proof_request(lowered, pattern):
            violations.append(str(rules[1]))
            break
    else:
        if _re_instruction_has_read_only_all_request(lowered):
            violations.append(str(rules[1]))

    if _re_instruction_has_scope_repair_without_coo_gate(lowered):
        violations.append(str(rules[2]))

    return violations


def invalid_re_instruction_endline_result(violations: Sequence[str]) -> dict[str, Any]:
    details = "; ".join(str(item) for item in violations)
    return {
        "error_kind": "re_instruction_endline_rule_violation",
        "error_message": (
            "human/COO re_instruction violates declared endline rule(s): "
            f"{details}"
        ),
        "message_ko": (
            "재시도 지시문은 종료선을 재진술하고, 수신 레인에서 실행 가능한 "
            "증명만 요구하고, scope 밖 수리는 COO 게이트로 위임해야 해요."
        ),
        "re_instruction_endline_rule_violations": [str(item) for item in violations],
    }


def _re_instruction_has_endline_marker(text: str) -> bool:
    if any(marker in text for marker in _RE_INSTRUCTION_ENDLINE_MARKERS):
        return True
    return bool(_RE_INSTRUCTION_DONE_RE.search(text))


def _re_instruction_has_nonexecutable_proof_request(
    lowered_text: str,
    pattern: str,
) -> bool:
    start = 0
    while True:
        index = lowered_text.find(pattern, start)
        if index == -1:
            return False
        context = lowered_text[max(0, index - 120) : index + len(pattern) + 120]
        if not _re_instruction_context_marks_safe_mention(context):
            return True
        start = index + len(pattern)


def _re_instruction_has_read_only_all_request(lowered_text: str) -> bool:
    start = 0
    while True:
        index = lowered_text.find("--all", start)
        if index == -1:
            return False
        context = lowered_text[max(0, index - 120) : index + 120]
        if (
            any(marker in context for marker in _RE_INSTRUCTION_READ_ONLY_ALL_MARKERS)
            and not _re_instruction_context_marks_safe_mention(context)
        ):
            return True
        start = index + len("--all")


def _re_instruction_context_marks_safe_mention(context: str) -> bool:
    if any(marker in context for marker in _RE_INSTRUCTION_PROHIBITION_CONTEXT_MARKERS):
        return True
    if re.search(r"(?<![A-Za-z0-9_])no(?![A-Za-z0-9_])", context):
        return True
    return any(marker in context for marker in _RE_INSTRUCTION_SAFE_MENTION_CONTEXT_MARKERS)


def _re_instruction_has_scope_repair_without_coo_gate(lowered_text: str) -> bool:
    if any(marker.lower() in lowered_text for marker in _RE_INSTRUCTION_COO_GATE_MARKERS):
        return False
    for outside_marker in _RE_INSTRUCTION_SCOPE_OUTSIDE_MARKERS:
        start = 0
        while True:
            index = lowered_text.find(outside_marker, start)
            if index == -1:
                break
            context = lowered_text[max(0, index - 120) : index + len(outside_marker) + 120]
            has_repair = any(marker in context for marker in _RE_INSTRUCTION_REPAIR_MARKERS)
            has_delegation = any(
                marker in context for marker in _RE_INSTRUCTION_SCOPE_DELEGATION_MARKERS
            )
            if has_repair and not has_delegation:
                return True
            start = index + len(outside_marker)
    return False


# Backwards-compatible private aliases for existing checker imports.
_re_instruction_endline_rules = re_instruction_endline_rules
_re_instruction_rule_violations = re_instruction_rule_violations
_invalid_re_instruction_endline_result = invalid_re_instruction_endline_result
