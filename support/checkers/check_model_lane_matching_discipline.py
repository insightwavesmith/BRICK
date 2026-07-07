#!/usr/bin/env python3
"""Pin the model-lane matching discipline against stale absolute bans.

Support checker mechanics only. This observes the Agent-owned discipline text
and Agent Object defaults; it does not call providers, choose lanes, choose
Movement, or judge source truth, success, or quality.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DISCIPLINE_REL = Path("agent/disciplines/model-lane-matching.md")
_DESIGN_LEAD_REL = Path("agent/objects/design-lead.yaml")
_OLD_ABSOLUTE_BANS = (
    "fable5 = never a Building / workflow lane model",
    "fable5 = never a lane model",
    "fable5 = never a Building",
)
_REQUIRED_TEXT = (
    "Smith, 0702; reconciled\n0705/0706",
    "codex = default implementation, finishing, and code QA lane",
    "claude sonnet (xhigh effort) = default investigation, axis analysis, and evidence QA lane",
    "gemini = default low-risk review lens; never assign heavy work by default",
    "claude-fable-5 = admitted design-lead default for design/synthesis depth, not an absolute lane-model ban",
    "codex-fugu-local / model:sakana:fugu-ultra = admitted high-depth work/design tier when explicitly cast",
    "Code-attack-QA and closure may escalate by declared, risk-proportional casting",
    "work and code QA start on Codex",
    "investigation/evidence QA start on Claude Sonnet",
    "broad low-risk review\nstays Gemini-shaped",
    "explicit\ncode-attack-QA / closure elevation",
    # 0707 tier reconciliation rows (walk-results-adopted-0707 K/G/I).
    "codex excluded from development; opus-4.8 xhigh for simple-to-medium work",
    "codex leaves the work and repair lanes only and finishes walking its current building",
    "engine-side or very-important claude QA on claude-fable-5 xhigh",
    "other claude QA on model:claude:claude-opus-4-8 xhigh, replacing the prior sonnet QA default",
    "claude-local concurrency 1 is the safe line",
    "attach-QA recovery is the standard salvage",
)
_PROOF_LIMIT = (
    "proof limit: model-lane matching checker support evidence only; it proves "
    "discipline text and design-lead default consistency, not provider behavior, "
    "source truth, success judgment, quality judgment, or Movement authority."
)


class ModelLaneMatchingDisciplineError(ValueError):
    """Raised when the model-lane discipline drifts from the reconciled policy."""


def _resolve_path(repo: Path, value: str | None) -> Path:
    if value is None:
        return repo / _DISCIPLINE_REL
    path = Path(value)
    return path if path.is_absolute() else repo / path


def _read_design_lead(repo: Path) -> dict[str, object]:
    try:
        data = json.loads((repo / _DESIGN_LEAD_REL).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ModelLaneMatchingDisciplineError(f"could not read {_DESIGN_LEAD_REL}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ModelLaneMatchingDisciplineError(f"{_DESIGN_LEAD_REL} is not JSON-compatible YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelLaneMatchingDisciplineError(f"{_DESIGN_LEAD_REL} must contain an object")
    return data


def _check_text(text: str) -> list[str]:
    violations: list[str] = []
    for banned in _OLD_ABSOLUTE_BANS:
        if banned in text:
            violations.append(f"stale absolute fable-class ban remains: {banned!r}")
    for required in _REQUIRED_TEXT:
        if required not in text:
            violations.append(f"missing reconciled model-lane clause: {required!r}")
    return violations


def _check_design_lead_default(repo: Path) -> list[str]:
    design_lead = _read_design_lead(repo)
    violations: list[str] = []
    if design_lead.get("preferred_adapter_ref") != "adapter:claude-local":
        violations.append(
            "design-lead preferred_adapter_ref must remain adapter:claude-local "
            "for the admitted fable-class default"
        )
    if design_lead.get("preferred_model_ref") != "model:claude:claude-fable-5":
        violations.append(
            "design-lead preferred_model_ref must remain model:claude:claude-fable-5 "
            "for the admitted design/synthesis default"
        )
    return violations


def _mutation_red_probe(text: str) -> str:
    missing_allowance = text.replace(
        "claude-fable-5 = admitted design-lead default for design/synthesis depth, not an absolute lane-model ban",
        "",
    )
    old_ban = text.replace(
        "claude-fable-5 = admitted design-lead default for design/synthesis depth, not an absolute lane-model ban",
        "fable5 = never a Building / workflow lane model (operator orchestration only)",
    )
    missing_allowance_red = bool(_check_text(missing_allowance))
    old_ban_red = bool(_check_text(old_ban))
    if not (missing_allowance_red and old_ban_red):
        raise ModelLaneMatchingDisciplineError(
            "mutation RED failed: "
            f"missing_allowance_red={missing_allowance_red}, old_ban_red={old_ban_red}"
        )
    return (
        "mutation RED observed: removing the fable-class allowance and "
        "reintroducing the old absolute fable5 ban both reject."
    )


def check(repo: Path, discipline_path: Path) -> list[str]:
    try:
        text = discipline_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelLaneMatchingDisciplineError(f"could not read {discipline_path}: {exc}") from exc
    violations = _check_text(text)
    if discipline_path.resolve() == (repo / _DISCIPLINE_REL).resolve():
        violations.extend(_check_design_lead_default(repo))
    if violations:
        raise ModelLaneMatchingDisciplineError("\n- ".join(violations))
    return [
        "model-lane matching discipline green: reconciled 0705/0706 clauses observed.",
        _mutation_red_probe(text),
        _PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker for Agent model-lane matching discipline text."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument("--discipline-path", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    discipline_path = _resolve_path(repo, args.discipline_path)
    try:
        outputs = check(repo, discipline_path)
    except ModelLaneMatchingDisciplineError as exc:
        print("model-lane matching discipline rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(_PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
