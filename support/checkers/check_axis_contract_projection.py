#!/usr/bin/env python3
"""Check Phase 4 YAML contract projection boundaries.

This checker is support evidence only. It is not source truth, not a success
judgment, and not Movement authority.

INTENTIONAL INDEPENDENT CONTRACT ORACLE: the contract constants below
(AGENT_REQUIRED, COMPARISON_*, TRANSITION_*, TRANSFER_REQUIRED, CARRY_REQUIRED,
ENGLISH_MOVEMENT_LITERALS, etc.) deliberately RE-ENCODE the axis contracts as a
second, independent statement so this oracle can catch axis-YAML-projection and
doc drift on both sides. This checker is NOT the axis source of truth and must NOT
be made to import or derive the axis contracts from the axis modules: doing so
would make it tautological (it would always agree with the source it is meant to
cross-check) and unable to catch both-sides drift. When the axis contracts
legitimately change, update this oracle DELIBERATELY and by hand so the
re-encoding stays an independent check.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys
from typing import Iterable


PHASE4_PROJECTIONS = {
    "brick/work.yaml": "Brick work YAML",
    "agent/return_fact.yaml": "Agent return_fact YAML",
    "link/movement.yaml": "Link movement YAML",
    "agent/receipt.yaml": "Agent receipt YAML",
    "agent/performance.yaml": "Agent performance YAML",
    "brick/building.yaml": "Brick building YAML",
    "brick/comparison.yaml": "Brick comparison YAML",
    "link/gate.yaml": "Link gate YAML",
    "link/transition.yaml": "Link transition YAML",
    "link/transfer.yaml": "Link transfer YAML",
    "link/carry.yaml": "Link carry YAML",
}

BRICK_FORBIDDEN = {
    "agent",
    "performer",
    "movement",
    "route",
    "retry",
    "rollback",
    "runtime",
    "storage",
    "success",
    "failure",
    "result",
}

AGENT_REQUIRED = {"received_work", "returned"}
AGENT_RETURN_TOP_LEVEL_ALLOWED = {
    "kind",
    "contract",
    "owner",
    "bal_owner",
    "module",
    "projection_only",
    "public_fact",
    "received_work",
    "returned",
    "allowed_facts",
    "forbidden_ownership",
    "verifiers",
    "proof_limits",
}
AGENT_FORBIDDEN = {
    "success",
    "failure",
    "done",
    "not_done",
    "failed",
    "result",
    "FailureFact",
    "SuccessResult",
    "FailureResult",
    "movement",
    "quality",
    "verdict",
    "quality_verdict",
}
AGENT_FACT_FIELD_KEYS = {"fields", "allowed_public_fields"}
RECEIPT_REQUIRED = {"received_work"}
RECEIPT_FORBIDDEN = {
    "work_rewrite",
    "rewrite_work",
    "work rewrite",
    "movement",
    "target",
    "success",
    "failure",
    "done",
    "not_done",
    "result",
}
PERFORMANCE_REQUIRED = {"name", "lane", "callable_performers"}
PERFORMANCE_SUPPORT_PROMOTIONS = {
    "provider",
    "model",
    "prompt",
    "adapter",
    "session",
    "brain",
}
PERFORMANCE_VERDICT_FORBIDDEN = {
    "success",
    "failure",
    "verdict",
    "success_lane",
    "failure_lane",
    "verdict_lane",
}
BUILDING_REQUIRED_GROUPS = ({"work_units", "ordered_work_units"},)
BUILDING_FORBIDDEN = {
    "scheduler",
    "queue",
    "launcher",
    "route",
    "movement",
    "merge_result",
    "runtime",
    "storage",
}
COMPARISON_REQUIRED = {"work_reference"}
COMPARISON_EVIDENCE_FIELDS = {
    "comparison_evidence",
    "comparison_text",
    "comparison_rule",
    "required_return_shape_evidence",
    "observed_match",
    "observed_missing",
    "observed_mismatch",
    "match_evidence",
    "missing_evidence",
    "mismatch_evidence",
    "forbidden_shortcut_evidence",
}
COMPARISON_FORBIDDEN = {
    "movement",
    "quality",
    "approval",
    "quality_approval",
    "success",
    "failure",
    "verdict",
    "result",
}
TRANSITION_REQUIRED = {"movement"}
TRANSITION_HANDOFF_FIELDS = {
    "not_proven",
    "target",
    "target_fact",
    "handoff",
    "handoff_fact",
    "handoff_facts",
    "handoff_target",
    "handoff_target_fact",
}
TRANSITION_FORBIDDEN = {
    "route_executor",
    "route executor",
    "retry_executor",
    "retry executor",
    "rollback_executor",
    "rollback executor",
    "scheduler",
    "queue",
    "quality_gate",
    "quality gate",
    "approval_verdict",
    "approval verdict",
    "storage_truth",
    "storage truth",
    "runtime_execution",
    "runtime execution",
}
LINK_GATE_REQUIRED_STAGES = {"transfer", "carry", "movement"}
LINK_GATE_REQUIRED_SUFFICIENCY = {
    "sufficient",
    "insufficient",
    "missing_required_facts",
}
LINK_GATE_FORBIDDEN_TEXT = {
    "quality",
    "success",
    "failure",
    "verdict",
}
LINK_GATE_FORBIDDEN_KEYS = {
    "movement",
    "movement_authority",
    "movement_choice",
    "movement_literal",
    "destination",
    "route",
    "rollback",
    "retry",
    "hold",
    "next_target",
}
LINK_GATE_FIELD_CONTEXTS = {"fields", "allowed_facts"}
LINK_GATE_MOVEMENT_BOUNDARY_PHRASES = {
    "movement authority",
    "does not choose movement",
    "without movement authority",
}

ENGLISH_MOVEMENT_LITERALS = {
    "forward",
    "reroute",
}
MOVEMENT_PUBLIC_FIELDS = {
    "movement",
    "reason",
    "handoff_target_fact",
    "gatefact_reference",
    "transition_history_reference",
}
NONCANONICAL_MOVEMENT_VALUES = {
    "HOLD",
    "FORWARD",
    "NEXT",
    "return",
    "hold",
    "stop",
    "pass",
    "앞으로 넘김",
    "되돌림",
    "보류",
    "중지",
    "다른 곳으로 넘김",
    "그냥 넘김",
}
GATE_CONTEXT_KEYS = {"gate", "gatefact", "gate_fact"}
GATE_FORBIDDEN_FIELDS = {
    "movement",
    "destination",
    "route",
    "rollback",
    "retry",
    "hold",
    "next_target",
    "success",
    "failure",
}
TRANSFER_REQUIRED = {
    "source_boundary_ref",
    "target_boundary_ref",
    "public_fact_refs",
    "work_context_ref",
    "required_public_facts",
    "transfer_gate_reference",
    "proof_limits",
    "not_proven",
    "evidence_reference",
}
CARRY_REQUIRED = {
    "carried_fact_refs",
    "source_owner_axis",
    "target_boundary_ref",
    "carry_gate_reference",
    "proof_limits",
    "not_proven",
    "evidence_reference",
}
TRANSFER_CARRY_FORBIDDEN_KEYS = {
    "success",
    "failure",
    "done",
    "not_done",
    "failed",
    "result",
    "approved",
    "complete",
    "pass",
    "fail",
    "quality",
    "quality_verdict",
    "verdict",
    "source_truth",
    "runtime",
    "provider",
    "providers",
    "model",
    "tool",
    "tools",
    "session",
    "storage",
    "wiki",
    "movement",
    "movement_choice",
    "movement_literal",
    "movement_gate_reference",
    "destination",
    "destination_choice",
    "performer",
    "performer_choice",
    "route",
    "rollback",
    "retry",
    "scheduler",
    "queue",
}
TRANSFER_CARRY_CONTEXTS_ALLOWED_TO_NAME_FORBIDDEN = {
    "allowed",
    "forbidden_ownership",
    "proof_limits",
}

ACTIVE_SEQUENCE_CONTROL_DOCS = (
    "AGENTS.md",
    "project/brick-protocol/status/kernel/current-working-context.md",
    "support/docs/spec/brick-protocol-seq-0-bal-sequence-constitution-closure-0522.md",
)
ACTIVE_SEQUENCE_FIXTURE_MARKER = "seq0_active_sequence"
ACTIVE_SEQUENCE_REQUIRED_PATTERNS = (
    ("BrickWork boundary", re.compile(r"\bBrickWork\b.*\bboundary\b", re.IGNORECASE | re.DOTALL)),
    ("ReceiptFact", re.compile(r"\bReceiptFact\b", re.IGNORECASE)),
    ("AgentFact.returned", re.compile(r"\bAgentFact\b.*\breturned\b", re.IGNORECASE | re.DOTALL)),
    ("optional BrickComparisonFact", re.compile(r"\boptional\b.*\bBrickComparisonFact\b|\bBrickComparisonFact\b.*\boptional\b", re.IGNORECASE | re.DOTALL)),
    ("contract observation", re.compile(r"\bcontract[- ]observation\b|\bcontract observation\b", re.IGNORECASE)),
    ("TransferFact", re.compile(r"\bTransferFact\b", re.IGNORECASE)),
    ("CarryFact", re.compile(r"\bCarryFact\b", re.IGNORECASE)),
    ("GateFact", re.compile(r"\bGateFact\b", re.IGNORECASE)),
    ("MovementFact", re.compile(r"\bMovementFact\b", re.IGNORECASE)),
    ("TransitionFact", re.compile(r"\bTransitionFact\b", re.IGNORECASE)),
    ("next Brick boundary", re.compile(r"\bnext\b.*\bBrick(?:Work)?\b.*\bboundary\b", re.IGNORECASE | re.DOTALL)),
)
ACTIVE_SEQUENCE_FORBIDDEN_PATTERNS = (
    ("old Brick-Link-Agent active sequence", re.compile(r"\bBrick\b\s*(?:->|→).{0,120}\bLink\b\s*(?:->|→).{0,120}\bAgent\b", re.IGNORECASE | re.DOTALL)),
    ("Link launches/meets/binds Agent", re.compile(r"\bLink\b.{0,100}\b(?:launch(?:es|ed|ing)?|meet(?:s|ing)?|bind(?:s|ing)?|execute(?:s|d|ing)?|call(?:s|ed|ing)?)\b.{0,80}\bAgent\b", re.IGNORECASE | re.DOTALL)),
    ("Link transfers work to Agent", re.compile(r"\bLink\b.{0,100}\btransfer(?:s|red|ring)?\b.{0,80}\b(?:work|context|Brick/work)\b.{0,40}\bto\s+Agent\b", re.IGNORECASE | re.DOTALL)),
    ("Agent returns to Link", re.compile(r"\bAgent\b.{0,80}\breturn(?:s|ed|ing)?\b.{0,40}\bto\s+Link\b", re.IGNORECASE | re.DOTALL)),
    ("Link receives Agent return", re.compile(r"\bLink\b.{0,80}\breceiv(?:es|ed|ing)?\b.{0,80}\bAgent\b.{0,40}\breturn", re.IGNORECASE | re.DOTALL)),
    ("Link endpoint is Agent", re.compile(r"\bLink\s+edge\s+endpoint(?:s)?\b.{0,100}\bAgent\b|\bLink\s+endpoint(?:s)?\b.{0,100}\bAgent\b", re.IGNORECASE | re.DOTALL)),
)
ACTIVE_SEQUENCE_ALLOWED_CONTEXT_MARKERS = (
    "historical",
    "support-only",
    "support only",
    "not active",
    "not active flow",
    "forbidden",
    "must not",
    "does not",
    "do not",
    "never",
    " is not",
    " not ",
    "not a link edge",
    "reject",
    "rejected",
    "superseded",
    "may appear only",
)
BRICK_COMPARISON_VERDICT_TERMS = (
    "success",
    "failure",
    "approved",
    "approval",
    "quality judgment",
    "quality",
    "completion verdict",
    "complete",
    "done",
    "movement authority",
)
FINAL_KERNEL_FORBIDDEN_KEYS = {
    "support_axis",
    "support_owner",
    "support_authority",
    "provider_axis",
    "provider_owner",
    "provider_authority",
    "runtime_axis",
    "runtime_owner",
    "runtime_authority",
    "quality_axis",
    "quality_owner",
    "quality_authority",
    "quality_judgment",
    "quality_judgement",
    "source_truth",
    "source_truth_owner",
    "movement_authority",
    "motion_authority",
    "movement_choice",
    "motion_choice",
}
FINAL_KERNEL_FORBIDDEN_FIELD_ITEMS = {
    "support",
    "support_axis",
    "support_owner",
    "provider",
    "provider_axis",
    "provider_owner",
    "runtime",
    "runtime_axis",
    "runtime_owner",
    "quality",
    "quality_judgment",
    "quality_judgement",
    "source_truth",
    "movement_authority",
    "motion_authority",
}
FINAL_KERNEL_FORBIDDEN_OWNER_VALUES = {
    "support",
    "provider",
    "runtime",
    "quality",
    "source_truth",
    "movement_authority",
    "motion_authority",
}
FINAL_KERNEL_FIELD_CONTEXTS = {
    "fields",
    "allowed_public_fields",
}

KEY_RE = re.compile(r"^\s*(?:-\s*)?([A-Za-z_][A-Za-z0-9_-]*)\s*:")


def to_posix(path: Path | str) -> str:
    value = str(path).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def normalized_key(key: str) -> str:
    return key.replace("-", "_").lower()


def core_projection_key(path: Path) -> str | None:
    path_text = to_posix(path)
    for suffix in PHASE4_PROJECTIONS:
        if path_text.endswith(suffix):
            return suffix
    return None


def active_sequence_doc_key(path: Path) -> str | None:
    if path.suffix != ".md":
        return None
    path_text = to_posix(path)
    if any(path_text.endswith(doc) for doc in ACTIVE_SEQUENCE_CONTROL_DOCS):
        return "SEQ-0 active control doc"
    if ACTIVE_SEQUENCE_FIXTURE_MARKER in path_text:
        return "SEQ-0 active sequence fixture"
    return None


# INTENTIONAL INDEPENDENT ORACLE (shape-selection authority): rehomed from the
# retiring taskshape_and_design_contract profile. The needles/keys below RE-ENCODE
# the Brick-owned shape-selection-authority invariant as a second, independent
# statement: the selected Building shape is declared by caller/COO only, candidate
# generation is support evidence only, and no key may act as a hidden Movement /
# shape chooser. Update by hand if the contract legitimately changes.
DESIGN_CONTRACT_DOCS = (
    "brick/templates/building-design-contract.yaml",
)
SHAPE_MENU_DOCS = (
    "brick/templates/shapes/shapes.yaml",
    "brick/templates/shapes/catalog.yaml",
)
DESIGN_CONTRACT_REQUIRED_NEEDLES = (
    "selected_shape_ref requires caller_or_coo_declaration",
    "candidate generation is support evidence only",
    "hidden Movement chooser",
)
SHAPE_MENU_REQUIRED_NEEDLES = (
    "selection_rule: caller_or_coo_declared_only",
)
SHAPE_SELECTION_FORBIDDEN_KEYS = {
    "auto_select",
    "auto_selected",
    "automatic_selection",
    "automatic_shape_selection",
    "auto_shape",
    "shape_chooser",
    "movement_chooser",
    "runner_selects",
    "adapter_selects",
    "mcp_selects",
    "selected_by",
    "chosen_by",
}
SHAPE_SELECTION_DECLARER_VALUES_ALLOWED = {
    "caller-or-coo",
    "caller_or_coo",
    "caller / coo",
    "caller/coo",
}


def shape_selection_doc_key(path: Path) -> tuple[str, tuple[str, ...]] | None:
    if path.suffix != ".yaml":
        return None
    path_text = to_posix(path)
    if any(path_text.endswith(doc) for doc in DESIGN_CONTRACT_DOCS):
        return ("design contract", DESIGN_CONTRACT_REQUIRED_NEEDLES)
    if any(path_text.endswith(doc) for doc in SHAPE_MENU_DOCS):
        return ("shape menu", SHAPE_MENU_REQUIRED_NEEDLES)
    return None


def check_shape_selection_doc(
    path: Path,
    lines: list[str],
    label: str,
    required_needles: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []
    text = "\n".join(lines)
    for needle in required_needles:
        if needle not in text:
            violations.append(
                f"{path}: {label} missing shape-selection-authority needle: {needle!r}"
            )
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        key = yaml_key(line)
        if not key:
            continue
        key_normalized = normalized_key(key)
        if key_normalized in SHAPE_SELECTION_FORBIDDEN_KEYS:
            violations.append(
                f"{path}:{line_no}: {label} defines forbidden hidden-Movement/shape-chooser key {key}"
            )
        if key_normalized == "declared_by" and ":" in line:
            value = line.split(":", 1)[1].strip().lower()
            if value and value not in SHAPE_SELECTION_DECLARER_VALUES_ALLOWED:
                violations.append(
                    f"{path}:{line_no}: {label} selected_shape declared_by must be "
                    f"caller-or-coo, not {value!r}"
                )
    return sorted(set(violations))


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if not path.exists():
            yield path
        elif path.is_file():
            yield path
        elif path.is_dir():
            for child in sorted(
                item
                for pattern in ("*.yaml", "*.md")
                for item in path.rglob(pattern)
            ):
                if child.is_file():
                    yield child


def yaml_key(line: str) -> str | None:
    match = KEY_RE.match(strip_comment(line))
    if not match:
        return None
    return match.group(1)


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def token_pattern(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def forbidden_text_findings(
    path: Path,
    lines: list[str],
    forbidden: set[str],
    label: str,
) -> list[str]:
    violations: list[str] = []
    patterns = {token: token_pattern(token) for token in forbidden}
    lowercase_patterns = {
        token: token_pattern(token) for token in forbidden if token.islower()
    }

    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue

        key = yaml_key(line)
        text_segment = line
        if key:
            key_normalized = normalized_key(key)
            for token in forbidden:
                if key_normalized == normalized_key(token):
                    violations.append(
                        f"{path}:{line_no}: {label} forbidden key {key}"
                    )
            text_segment = line.split(":", 1)[1]

        for token, pattern in patterns.items():
            if pattern.search(text_segment):
                violations.append(
                    f"{path}:{line_no}: {label} forbidden text pattern {token}"
                )
        for token, pattern in lowercase_patterns.items():
            if pattern.search(text_segment.lower()):
                violations.append(
                    f"{path}:{line_no}: {label} forbidden text pattern {token}"
                )

    return sorted(set(violations))


def present_keys(lines: list[str]) -> set[str]:
    keys: set[str] = set()
    for line in lines:
        key = yaml_key(line)
        if key:
            keys.add(normalized_key(key))
    return keys


def present_terms(lines: list[str]) -> set[str]:
    terms = present_keys(lines)
    for raw_line in lines:
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        terms.update(normalized_key(match) for match in re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", line))
    return terms


def list_items_under(lines: list[str], key_name: str) -> set[str]:
    items: set[str] = set()
    wanted = normalized_key(key_name)
    collecting = False
    parent_indent = 0
    for raw_line in lines:
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        indent = indentation(line)
        key = yaml_key(line)
        if collecting and indent <= parent_indent:
            collecting = False
        if key and normalized_key(key) == wanted:
            collecting = True
            parent_indent = indent
            continue
        if collecting:
            stripped = line.strip()
            if stripped.startswith("-"):
                items.add(normalized_key(stripped[1:].strip()))
    return items


def list_mapping_values_under(lines: list[str], key_name: str, child_key_name: str) -> set[str]:
    items: set[str] = set()
    wanted = normalized_key(key_name)
    child_wanted = normalized_key(child_key_name)
    collecting = False
    parent_indent = 0
    for raw_line in lines:
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        indent = indentation(line)
        key = yaml_key(line)
        if collecting and indent <= parent_indent:
            collecting = False
        if key and normalized_key(key) == wanted:
            collecting = True
            parent_indent = indent
            continue
        if not collecting:
            continue
        stripped = line.strip()
        prefix = f"- {child_key_name}:"
        if stripped.startswith(prefix):
            items.add(normalized_key(stripped.removeprefix(prefix).strip()))
            continue
        if key and normalized_key(key) == child_wanted and ":" in stripped:
            items.add(normalized_key(stripped.split(":", 1)[1].strip()))
    return items


def final_kernel_smuggling_findings(path: Path, lines: list[str], label: str) -> list[str]:
    violations: list[str] = []
    context_stack: list[tuple[int, str]] = []
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        indent = indentation(line)
        while context_stack and indent <= context_stack[-1][0]:
            context_stack.pop()

        key = yaml_key(line)
        if key:
            key_normalized = normalized_key(key)
            if key_normalized in FINAL_KERNEL_FORBIDDEN_KEYS:
                violations.append(
                    f"{path}:{line_no}: {label} smuggles forbidden authority/support key {key}"
                )
            if key_normalized in {"owner", "bal_owner"} and ":" in line:
                owner_value = normalized_key(line.split(":", 1)[1].strip())
                if owner_value in FINAL_KERNEL_FORBIDDEN_OWNER_VALUES:
                    violations.append(
                        f"{path}:{line_no}: {label} owner must remain Brick, Agent, or Link, not {owner_value}"
                    )
            context_stack.append((indent, key_normalized))

        if any(context in FINAL_KERNEL_FIELD_CONTEXTS for _, context in context_stack):
            stripped = line.strip()
            if stripped.startswith("-"):
                item = normalized_key(stripped[1:].strip())
                if item in FINAL_KERNEL_FORBIDDEN_FIELD_ITEMS:
                    violations.append(
                        f"{path}:{line_no}: {label} field list smuggles forbidden item {item}"
                    )
    return sorted(set(violations))


def require_terms(
    path: Path,
    label: str,
    terms: set[str],
    required: set[str],
) -> list[str]:
    missing = sorted(required - terms)
    if not missing:
        return []
    return [f"{path}: {label} missing required term(s): {', '.join(missing)}"]


def require_one_term(
    path: Path,
    label: str,
    terms: set[str],
    candidates: set[str],
    description: str,
) -> list[str]:
    if terms & candidates:
        return []
    return [f"{path}: {label} missing required {description} term"]


def markdown_paragraphs(lines: list[str]) -> Iterable[tuple[int, str]]:
    start_line: int | None = None
    parts: list[str] = []
    for line_no, raw_line in enumerate(lines, 1):
        if raw_line.strip():
            if start_line is None:
                start_line = line_no
            parts.append(raw_line)
            continue
        if parts and start_line is not None:
            yield start_line, "\n".join(parts)
        start_line = None
        parts = []
    if parts and start_line is not None:
        yield start_line, "\n".join(parts)


def active_sequence_allowed_context(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ACTIVE_SEQUENCE_ALLOWED_CONTEXT_MARKERS)


def check_active_sequence_doc(path: Path, lines: list[str]) -> list[str]:
    text = "\n".join(lines)
    violations: list[str] = []

    for label, pattern in ACTIVE_SEQUENCE_REQUIRED_PATTERNS:
        if not pattern.search(text):
            violations.append(f"{path}: SEQ-0 active doc missing {label}")

    for start_line, paragraph in markdown_paragraphs(lines):
        if active_sequence_allowed_context(paragraph):
            continue
        for label, pattern in ACTIVE_SEQUENCE_FORBIDDEN_PATTERNS:
            if pattern.search(paragraph):
                violations.append(
                    f"{path}:{start_line}: SEQ-0 active doc uses forbidden {label}"
                )

        if active_sequence_allowed_context(paragraph):
            continue
        comparison_text = paragraph.lower()
        if "brickcomparisonfact" in comparison_text:
            for term in BRICK_COMPARISON_VERDICT_TERMS:
                if term in comparison_text:
                    violations.append(
                        f"{path}:{start_line}: BrickComparisonFact must stay optional observation, not {term}"
                    )

    return sorted(set(violations))


def check_brick_work(path: Path, lines: list[str]) -> list[str]:
    return forbidden_text_findings(path, lines, BRICK_FORBIDDEN, "Brick work YAML")


def check_agent_return_fact(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(
        path, lines, AGENT_FORBIDDEN, "Agent return_fact YAML"
    )
    violations.extend(final_kernel_smuggling_findings(path, lines, "Agent return_fact YAML"))
    violations.extend(
        require_terms(path, "Agent return_fact YAML", present_terms(lines), AGENT_REQUIRED)
    )
    top_level_keys = {
        normalized_key(key)
        for line in lines
        if line.strip() and indentation(strip_comment(line)) == 0 and (key := yaml_key(line))
    }
    extra_top_level = sorted(top_level_keys - {normalized_key(key) for key in AGENT_RETURN_TOP_LEVEL_ALLOWED})
    if extra_top_level:
        violations.append(
            f"{path}: AgentFact closed shape has unadmitted top-level key(s): "
            + ", ".join(extra_top_level)
        )
    for field_key in sorted(AGENT_FACT_FIELD_KEYS):
        fields = list_items_under(lines, field_key)
        if fields and fields != AGENT_REQUIRED:
            missing = sorted(AGENT_REQUIRED - fields)
            extra = sorted(fields - AGENT_REQUIRED)
            if missing:
                violations.append(
                    f"{path}: AgentFact {field_key} missing closed field(s): "
                    + ", ".join(missing)
                )
            if extra:
                violations.append(
                    f"{path}: AgentFact {field_key} has unadmitted field(s): "
                    + ", ".join(extra)
                )
    return violations


def check_link_movement(path: Path, lines: list[str]) -> list[str]:
    violations: list[str] = []
    violations.extend(final_kernel_smuggling_findings(path, lines, "Link movement YAML"))
    text = "\n".join(strip_comment(line) for line in lines)

    missing_literals = sorted(
        literal for literal in ENGLISH_MOVEMENT_LITERALS if literal not in text
    )
    if missing_literals:
        violations.append(
            f"{path}: Link movement YAML missing English literal(s): "
            + ", ".join(missing_literals)
        )
    literal_values = list_mapping_values_under(lines, "movement_literals", "movement")
    if literal_values and literal_values != ENGLISH_MOVEMENT_LITERALS:
        missing = sorted(ENGLISH_MOVEMENT_LITERALS - literal_values)
        extra = sorted(literal_values - ENGLISH_MOVEMENT_LITERALS)
        if missing:
            violations.append(
                f"{path}: Link movement YAML movement_literals missing: "
                + ", ".join(missing)
            )
        if extra:
            violations.append(
                f"{path}: Link movement YAML movement_literals has unadmitted literal(s): "
                + ", ".join(extra)
            )
    public_fields = list_items_under(lines, "fields")
    if public_fields and not MOVEMENT_PUBLIC_FIELDS.issubset(public_fields):
        violations.append(
            f"{path}: Link movement YAML public_fact.fields must preserve MovementFact closed support fields"
        )
    if public_fields:
        extra_fields = sorted(public_fields - MOVEMENT_PUBLIC_FIELDS)
        if extra_fields:
            violations.append(
                f"{path}: Link movement YAML public_fact.fields has unadmitted field(s): "
                + ", ".join(extra_fields)
            )

    noncanonical_patterns = {
        value: token_pattern(value) for value in NONCANONICAL_MOVEMENT_VALUES
    }
    gate_indent: int | None = None

    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        stripped = line.strip()
        if not stripped:
            continue

        indent = indentation(line)
        if gate_indent is not None and indent <= gate_indent:
            gate_indent = None

        for value, pattern in noncanonical_patterns.items():
            if pattern.search(line):
                violations.append(
                    f"{path}:{line_no}: Link movement YAML rejects noncanonical movement value {value}"
                )

        key = yaml_key(line)
        if not key:
            continue

        key_normalized = normalized_key(key)
        if key_normalized in GATE_CONTEXT_KEYS:
            gate_indent = indent
            continue

        if gate_indent is not None and indent > gate_indent:
            if key_normalized in GATE_FORBIDDEN_FIELDS:
                violations.append(
                    f"{path}:{line_no}: GateFact field {key} must not choose movement"
                )

    return sorted(set(violations))


def check_agent_receipt(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(path, lines, RECEIPT_FORBIDDEN, "Agent receipt YAML")
    violations.extend(final_kernel_smuggling_findings(path, lines, "Agent receipt YAML"))
    violations.extend(require_terms(path, "Agent receipt YAML", present_terms(lines), RECEIPT_REQUIRED))
    return violations


def check_agent_performance(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(
        path,
        lines,
        PERFORMANCE_VERDICT_FORBIDDEN,
        "Agent performance YAML",
    )
    violations.extend(final_kernel_smuggling_findings(path, lines, "Agent performance YAML"))
    violations.extend(
        require_terms(
            path,
            "Agent performance YAML",
            present_terms(lines),
            PERFORMANCE_REQUIRED,
        )
    )

    owner_contexts = {
        "axis",
        "native_module",
        "native module",
        "module",
        "owner",
        "ownership",
    }
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue

        key = yaml_key(line)
        key_normalized = normalized_key(key) if key else ""
        value = line.split(":", 1)[1] if key and ":" in line else line
        value_normalized = normalized_key(value)
        value_lower = value.lower()

        for support_term in PERFORMANCE_SUPPORT_PROMOTIONS:
            if key_normalized == support_term:
                violations.append(
                    f"{path}:{line_no}: Agent performance YAML promotes support key {key}"
                )
            if key_normalized in {
                f"{support_term}_axis",
                f"{support_term}_module",
                f"{support_term}_native_module",
                f"{support_term}_owner",
                f"{support_term}_ownership",
            }:
                violations.append(
                    f"{path}:{line_no}: Agent performance YAML promotes {support_term} as native owner/module"
                )
            if key_normalized in owner_contexts and support_term in value_normalized:
                violations.append(
                    f"{path}:{line_no}: Agent performance YAML promotes {support_term} as native owner/module"
                )
            if support_term in value_normalized and (
                "native_module" in value_normalized
                or "native module" in value_lower
                or "owner" in value_normalized
                or "ownership" in value_normalized
                or "axis" in value_normalized
            ):
                violations.append(
                    f"{path}:{line_no}: Agent performance YAML promotes {support_term} as native owner/module"
                )

    return sorted(set(violations))


def check_brick_building(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(path, lines, BUILDING_FORBIDDEN, "Brick building YAML")
    violations.extend(final_kernel_smuggling_findings(path, lines, "Brick building YAML"))
    terms = present_terms(lines)
    for required_group in BUILDING_REQUIRED_GROUPS:
        violations.extend(
            require_one_term(
                path,
                "Brick building YAML",
                terms,
                required_group,
                "work_units or ordered_work_units",
            )
        )
    return violations


def check_brick_comparison(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(path, lines, COMPARISON_FORBIDDEN, "Brick comparison YAML")
    violations.extend(final_kernel_smuggling_findings(path, lines, "Brick comparison YAML"))
    terms = present_terms(lines)
    violations.extend(require_terms(path, "Brick comparison YAML", terms, COMPARISON_REQUIRED))
    violations.extend(
        require_one_term(
            path,
            "Brick comparison YAML",
            terms,
            COMPARISON_EVIDENCE_FIELDS,
            "comparison evidence",
        )
    )
    return violations


def check_link_transition(path: Path, lines: list[str]) -> list[str]:
    violations = forbidden_text_findings(path, lines, TRANSITION_FORBIDDEN, "Link transition YAML")
    violations.extend(final_kernel_smuggling_findings(path, lines, "Link transition YAML"))
    terms = present_terms(lines)
    violations.extend(require_terms(path, "Link transition YAML", terms, TRANSITION_REQUIRED))
    violations.extend(
        require_one_term(
            path,
            "Link transition YAML",
            terms,
            TRANSITION_HANDOFF_FIELDS,
            "not_proven, target, or handoff",
        )
    )

    # REHOMED from retiring profile link_connection_route (text_absent
    # "Movement: return|hold|stop|pass" on link/transition.yaml). Run the SAME
    # NONCANONICAL_MOVEMENT_VALUES token scan that check_link_movement already
    # runs so the 2-literal Movement ban (forward/reroute) applies to
    # transition.yaml too, not just movement.yaml. An absent guard fires nothing.
    noncanonical_patterns = {
        value: token_pattern(value) for value in NONCANONICAL_MOVEMENT_VALUES
    }
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        for value, pattern in noncanonical_patterns.items():
            if pattern.search(line):
                violations.append(
                    f"{path}:{line_no}: Link transition YAML rejects noncanonical movement value {value}"
                )

    return violations


def check_link_gate(path: Path, lines: list[str]) -> list[str]:
    violations: list[str] = []
    violations.extend(final_kernel_smuggling_findings(path, lines, "Link gate YAML"))
    terms = present_terms(lines)
    violations.extend(
        require_terms(
            path,
            "Link gate YAML",
            terms,
            LINK_GATE_REQUIRED_STAGES,
        )
    )
    violations.extend(
        require_terms(
            path,
            "Link gate YAML",
            terms,
            LINK_GATE_REQUIRED_SUFFICIENCY,
        )
    )

    text_lower = "\n".join(strip_comment(line).lower() for line in lines)
    if not any(phrase in text_lower for phrase in LINK_GATE_MOVEMENT_BOUNDARY_PHRASES):
        violations.append(
            f"{path}: Link gate YAML missing explicit no-Movement-authority declaration"
        )

    context_stack: list[tuple[int, str]] = []
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue

        indent = indentation(line)
        while context_stack and indent <= context_stack[-1][0]:
            context_stack.pop()

        key = yaml_key(line)
        if key:
            key_normalized = normalized_key(key)
            if key_normalized in LINK_GATE_FORBIDDEN_KEYS:
                violations.append(
                    f"{path}:{line_no}: Link gate YAML must not define Movement authority key {key}"
                )
            if key_normalized in LINK_GATE_FORBIDDEN_TEXT:
                violations.append(
                    f"{path}:{line_no}: Link gate YAML must not define judgment key {key}"
                )
            context_stack.append((indent, key_normalized))

        in_field_context = any(
            context in LINK_GATE_FIELD_CONTEXTS for _, context in context_stack
        )
        stripped = line.strip()
        if in_field_context and stripped.startswith("-"):
            item = stripped[1:].strip()
            item_terms = present_terms([item])
            forbidden_items = sorted(
                (LINK_GATE_FORBIDDEN_KEYS | LINK_GATE_FORBIDDEN_TEXT) & item_terms
            )
            if forbidden_items:
                violations.append(
                    f"{path}:{line_no}: Link gate YAML field/allowed fact must not expose "
                    + ", ".join(forbidden_items)
                )

    return sorted(set(violations))


def check_link_transfer_or_carry(
    path: Path,
    lines: list[str],
    *,
    label: str,
    fact_name: str,
    module_name: str,
    required_fields: set[str],
) -> list[str]:
    violations: list[str] = []
    violations.extend(final_kernel_smuggling_findings(path, lines, label))
    terms = present_terms(lines)
    normalized_required = {normalized_key(value) for value in required_fields}
    fields = list_items_under(lines, "fields")

    violations.extend(
        require_terms(
            path,
            label,
            terms,
            {
                normalized_key(fact_name),
                "link",
                "projection_only",
                "closed_shape",
                "extra_keys_allowed",
            },
        )
    )
    violations.extend(require_terms(path, label, terms, normalized_required))

    if fields and fields != normalized_required:
        missing = sorted(normalized_required - fields)
        extra = sorted(fields - normalized_required)
        if missing:
            violations.append(
                f"{path}: {label} public_fact.fields missing: {', '.join(missing)}"
            )
        if extra:
            violations.append(
                f"{path}: {label} public_fact.fields has unadmitted field(s): "
                + ", ".join(extra)
            )

    text = "\n".join(strip_comment(line) for line in lines)
    if f"owner: Link" not in text:
        violations.append(f"{path}: {label} public_fact owner must be Link")
    if f"module: {module_name}" not in text:
        violations.append(f"{path}: {label} module must be {module_name}")
    if "extra_keys_allowed: false" not in text:
        violations.append(f"{path}: {label} must declare extra_keys_allowed: false")

    context_stack: list[tuple[int, str]] = []
    for line_no, raw_line in enumerate(lines, 1):
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        indent = indentation(line)
        while context_stack and indent <= context_stack[-1][0]:
            context_stack.pop()
        key = yaml_key(line)
        if key:
            key_normalized = normalized_key(key)
            if (
                key_normalized in TRANSFER_CARRY_FORBIDDEN_KEYS
                and not any(
                    context in TRANSFER_CARRY_CONTEXTS_ALLOWED_TO_NAME_FORBIDDEN
                    for _, context in context_stack
                )
            ):
                violations.append(
                    f"{path}:{line_no}: {label} must not expose forbidden key {key}"
                )
            context_stack.append((indent, key_normalized))

        if any(context in {"fields", "allowed_facts"} for _, context in context_stack):
            stripped = line.strip()
            if stripped.startswith("-"):
                item = normalized_key(stripped[1:].strip())
                if item in TRANSFER_CARRY_FORBIDDEN_KEYS:
                    violations.append(
                        f"{path}:{line_no}: {label} field/allowed fact must not expose {item}"
                    )

    return sorted(set(violations))


def check_file(path: Path) -> tuple[list[str], bool]:
    if not path.exists():
        return [f"{path}: target does not exist"], False

    projection = core_projection_key(path)
    active_doc = active_sequence_doc_key(path)
    shape_doc = shape_selection_doc_key(path)
    if projection is None and active_doc is None and shape_doc is None:
        return [], False

    lines = path.read_text(encoding="utf-8").splitlines()
    if active_doc is not None:
        return check_active_sequence_doc(path, lines), True
    if shape_doc is not None:
        label, required_needles = shape_doc
        return check_shape_selection_doc(path, lines, label, required_needles), True
    if projection == "brick/work.yaml":
        return check_brick_work(path, lines), True
    if projection == "agent/return_fact.yaml":
        return check_agent_return_fact(path, lines), True
    if projection == "link/movement.yaml":
        return check_link_movement(path, lines), True
    if projection == "agent/receipt.yaml":
        return check_agent_receipt(path, lines), True
    if projection == "agent/performance.yaml":
        return check_agent_performance(path, lines), True
    if projection == "brick/building.yaml":
        return check_brick_building(path, lines), True
    if projection == "brick/comparison.yaml":
        return check_brick_comparison(path, lines), True
    if projection == "link/gate.yaml":
        return check_link_gate(path, lines), True
    if projection == "link/transition.yaml":
        return check_link_transition(path, lines), True
    if projection == "link/transfer.yaml":
        return check_link_transfer_or_carry(
            path,
            lines,
            label="Link transfer YAML",
            fact_name="TransferFact",
            module_name="Link.transfer",
            required_fields=TRANSFER_REQUIRED,
        ), True
    if projection == "link/carry.yaml":
        return check_link_transfer_or_carry(
            path,
            lines,
            label="Link carry YAML",
            fact_name="CarryFact",
            module_name="Link.carry",
            required_fields=CARRY_REQUIRED,
        ), True

    return [], False


def active_sequence_control_paths(repo: Path) -> list[Path]:
    return [
        candidate
        for doc in ACTIVE_SEQUENCE_CONTROL_DOCS
        if (candidate := repo / doc).exists()
    ]


def collect_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if args.repo:
        repo = Path(args.repo)
        if repo.is_file() or repo.name in {"brick", "agent", "link"}:
            paths.append(repo)
        else:
            paths.extend(repo / value for value in ("brick", "agent", "link"))
            paths.extend(active_sequence_control_paths(repo))
    if args.target:
        paths.append(Path(args.target))
    if args.fixture:
        paths.append(Path(args.fixture))
    if not paths:
        paths.extend(Path(value) for value in ("brick", "agent", "link"))
        paths.extend(active_sequence_control_paths(Path.cwd()))
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for Phase 4 YAML contract projections; "
            "it does not prove source truth, Movement, or implementation correctness."
        )
    )
    parser.add_argument("--repo", help="Repository package or directory to inspect.")
    parser.add_argument("--target", help="Specific file or directory to inspect.")
    parser.add_argument("--fixture", help="Fixture file or directory to inspect.")
    args = parser.parse_args(argv)

    violations: list[str] = []
    inspected = 0

    for path in iter_files(collect_paths(args)):
        file_violations, was_inspected = check_file(path)
        if was_inspected:
            inspected += 1
        violations.extend(file_violations)

    if violations:
        print("axis contract projection rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker inspects current YAML projection fields/text "
            "and SEQ-0 active-doc wording only; it does not establish source truth, "
            "implementation correctness, Movement, or project success."
        )
        return 1

    if inspected:
        print(
            "axis contract projection passed: inspected Phase 4 YAML projections "
            "and SEQ-0 active docs avoid forbidden ownership/sequence keys/text "
            "and include required public facts."
        )
    else:
        print(
            "axis contract projection passed: no Phase 4 YAML projection files are present; "
            "and no SEQ-0 active docs were inspected; absent-state pass only."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
