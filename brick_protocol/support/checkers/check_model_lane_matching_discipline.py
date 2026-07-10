#!/usr/bin/env python3
"""Pin the Smith 0710 PM/development model-lane recast.

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


_REPO_ROOT = Path(__file__).resolve().parents[3]
_DISCIPLINE_REL = Path("brick_protocol/agent/disciplines/model-lane-matching.md")
_PM_LEAD_REL = Path("brick_protocol/agent/objects/pm-lead.yaml")
_DEV_REL = Path("brick_protocol/agent/objects/dev.yaml")
_OLD_ABSOLUTE_BANS = (
    "fable5 = never a Building / workflow lane model",
    "fable5 = never a lane model",
    "fable5 = never a Building",
    "claude-fable-5 = retired from active Building dispatch",
    "model:claude:claude-fable-5 is retired",
    "codex excluded from development",
    "codex leaves the work and repair lanes only",
)
_REQUIRED_TEXT = (
    "Smith, 0702; reconciled\n0705/0706",
    "Smith 0710 direct recast",
    "pm-lead planning/synthesis = adapter:claude-local / model:claude:claude-fable-5 / effort:xhigh",
    "development work/repair = adapter:codex-local / model:codex:gpt-5.6-sol / effort:xhigh",
    "claude sonnet (xhigh effort) = default investigation, axis analysis, and evidence QA lane",
    "gemini = default low-risk review lens; never assign heavy work by default",
    "codex-fugu-local / model:sakana:fugu-ultra = admitted high-depth work/design tier when explicitly cast",
    "Code-attack-QA and closure may escalate by declared, risk-proportional casting",
    "investigation/evidence QA start on Claude Sonnet",
    "broad low-risk review\nstays Gemini-shaped",
    "Fable5 is active only as the pm-lead",
    "GPT-5.6-sol xhigh is the active dev work/repair default",
    "supersedes the 0708 Fable5 active-dispatch",
    "supersedes the 0707 Codex development-retirement row",
    "engine-side or very-important claude QA on model:claude:claude-opus-4-8 xhigh",
    "Fable5 remains excluded from work and QA promotion",
    "claude-local concurrency 1 is the safe line",
    "attach-QA recovery is the standard salvage",
)
_PROOF_LIMIT = (
    "proof limit: model-lane matching checker support evidence only; it proves "
    "discipline text and pm-lead/dev default consistency, not provider behavior, "
    "source truth, success judgment, quality judgment, or Movement authority."
)


class ModelLaneMatchingDisciplineError(ValueError):
    """Raised when the model-lane discipline drifts from the reconciled policy."""


def _resolve_path(repo: Path, value: str | None) -> Path:
    if value is None:
        return repo / _DISCIPLINE_REL
    path = Path(value)
    return path if path.is_absolute() else repo / path


def _read_agent_object(repo: Path, relative: Path) -> dict[str, object]:
    try:
        data = json.loads((repo / relative).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ModelLaneMatchingDisciplineError(f"could not read {relative}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ModelLaneMatchingDisciplineError(
            f"{relative} is not JSON-compatible YAML: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ModelLaneMatchingDisciplineError(f"{relative} must contain an object")
    return data


def _check_text(text: str) -> list[str]:
    violations: list[str] = []
    for banned in _OLD_ABSOLUTE_BANS:
        if banned in text:
            violations.append(f"superseded model-lane clause remains active: {banned!r}")
    for required in _REQUIRED_TEXT:
        if required not in text:
            violations.append(f"missing reconciled model-lane clause: {required!r}")
    return violations


def _check_agent_default_values(
    pm_lead: dict[str, object], dev: dict[str, object]
) -> list[str]:
    violations: list[str] = []
    if pm_lead.get("preferred_adapter_ref") != "adapter:claude-local":
        violations.append(
            "pm-lead preferred_adapter_ref must be adapter:claude-local"
        )
    if pm_lead.get("preferred_model_ref") != "model:claude:claude-fable-5":
        violations.append(
            "pm-lead preferred_model_ref must be model:claude:claude-fable-5"
        )
    if pm_lead.get("preferred_reasoning_effort_ref") != "effort:xhigh":
        violations.append("pm-lead preferred_reasoning_effort_ref must be effort:xhigh")
    if dev.get("preferred_adapter_ref") != "adapter:codex-local":
        violations.append("dev preferred_adapter_ref must be adapter:codex-local")
    if dev.get("preferred_model_ref") != "model:codex:gpt-5.6-sol":
        violations.append("dev preferred_model_ref must be model:codex:gpt-5.6-sol")
    if dev.get("preferred_reasoning_effort_ref") != "effort:xhigh":
        violations.append("dev preferred_reasoning_effort_ref must be effort:xhigh")
    return violations


def _check_agent_defaults(repo: Path) -> list[str]:
    return _check_agent_default_values(
        _read_agent_object(repo, _PM_LEAD_REL),
        _read_agent_object(repo, _DEV_REL),
    )


def _mutation_red_probe(text: str, repo: Path) -> str:
    missing_fable = text.replace(
        "pm-lead planning/synthesis = adapter:claude-local / model:claude:claude-fable-5 / effort:xhigh",
        "",
    )
    missing_dev = text.replace(
        "development work/repair = adapter:codex-local / model:codex:gpt-5.6-sol / effort:xhigh",
        "",
    )
    pm_lead = _read_agent_object(repo, _PM_LEAD_REL)
    dev = _read_agent_object(repo, _DEV_REL)
    wrong_pm = dict(pm_lead)
    wrong_pm["preferred_model_ref"] = "model:claude:claude-opus-4-8"
    wrong_pm_effort = dict(pm_lead)
    wrong_pm_effort["preferred_reasoning_effort_ref"] = "effort:high"
    wrong_dev_model = dict(dev)
    wrong_dev_model["preferred_model_ref"] = "model:codex:default"
    wrong_dev = dict(dev)
    wrong_dev["preferred_reasoning_effort_ref"] = "effort:high"
    observations = (
        bool(_check_text(missing_fable)),
        bool(_check_text(missing_dev)),
        bool(_check_agent_default_values(wrong_pm, dev)),
        bool(_check_agent_default_values(wrong_pm_effort, dev)),
        bool(_check_agent_default_values(pm_lead, wrong_dev_model)),
        bool(_check_agent_default_values(pm_lead, wrong_dev)),
    )
    if not all(observations):
        raise ModelLaneMatchingDisciplineError(
            "mutation RED failed: " + repr(observations)
        )
    return (
        "mutation RED observed: missing Fable5/GPT-5.6-sol clauses and "
        "wrong PM/dev model-effort defaults all reject."
    )


def check(repo: Path, discipline_path: Path) -> list[str]:
    try:
        text = discipline_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelLaneMatchingDisciplineError(f"could not read {discipline_path}: {exc}") from exc
    violations = _check_text(text)
    if discipline_path.resolve() == (repo / _DISCIPLINE_REL).resolve():
        violations.extend(_check_agent_defaults(repo))
    if violations:
        raise ModelLaneMatchingDisciplineError("\n- ".join(violations))
    return [
        "model-lane matching discipline green: Fable5 xhigh PM and GPT-5.6-sol xhigh dev defaults observed.",
        _mutation_red_probe(text, repo),
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
