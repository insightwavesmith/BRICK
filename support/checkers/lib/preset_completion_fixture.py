"""Deterministic preset completion CLI fixture helpers."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


_PRESET_COMPLETION_LIST_RETURN_FIELDS = frozenset(
    {
        "agent_axis_findings",
        "attacked_scope",
        "attacked_work",
        "axis_responsibility",
        "blocked_or_missing_evidence",
        "boundary_findings",
        "boundary_violations",
        "brick_axis_findings",
        "candidate_file_changes",
        "changed_files",
        "checked_sources",
        "checker_or_verifier_plan",
        "checker_overclaim_risks",
        "commands_run",
        "deferred_smith_review_queue",
        "edge_cases",
        "evidence_refs",
        "evidence_scope",
        "evidence_used",
        "failing_or_missing_probes",
        "handoff_refs",
        "integration_risks",
        "invariants",
        "link_axis_findings",
        "made_changes",
        "matched_facts",
        "missing_evidence",
        "missing_facts",
        "missing_or_mismatched_facts",
        "mismatched_facts",
        "narrowly_proven",
        "negative_probe_observations",
        "next_target_candidates",
        "not_proven",
        "observed_evidence",
        "observed_matches",
        "open_questions",
        "persisted_evidence_roots",
        "projection_authority_findings",
        "proof_limit_findings",
        "proof_limits",
        "proposed_changes",
        "reading_scope_map",
        "regression_risks",
        "relevant_current_structure",
        "remaining_delta",
        "required_outputs",
        "review_needed",
        "risk_boundaries",
        "risks",
        "source_fact_bodies",
        "stale_source_risks",
        "support_leak_findings",
        "unchanged_surfaces",
        "worker_assignments",
    }
)

_PRESET_COMPLETION_REPO_ARTIFACT_FIELDS = frozenset(
    {
        "checked_sources",
        "evidence_refs",
        "evidence_used",
        "relevant_current_structure",
    }
)


def _preset_completion_command_runner(completed_cls: type[Any]) -> Callable[[Sequence[str], Path, int], Any]:
    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> Any:
        checked_args = tuple(str(arg) for arg in args)
        executable = Path(checked_args[0]).name if checked_args else ""
        if "--version" in checked_args:
            return completed_cls(
                args=checked_args,
                return_code=0,
                stdout=f"{executable or 'local-cli'} preset-completion-fixture 0.0\n",
                stderr="",
            )
        prompt = _preset_completion_prompt_from_cli_args(checked_args)
        labels = _return_labels_from_cli_prompt(prompt)
        returned: dict[str, Any] = {}
        for label in labels:
            if label == "transition_concern_evidence":
                returned[label] = {
                    "concern_ref": "transition-concern:preset-completion-no-reroute",
                    "concern_kind": "unknown",
                    "binding": False,
                    "reason_refs": ["observation:preset-completion-no-reroute"],
                    "related_boundary_refs": ["building-boundary:preset-completion-no-reroute"],
                    "proof_limits": ["support evidence only"],
                    "not_proven": ["semantic correctness"],
                }
            elif label in _PRESET_COMPLETION_LIST_RETURN_FIELDS:
                returned[label] = _deterministic_completion_list(label, "preset-completion")
            else:
                returned[label] = f"{label}: deterministic preset completion evidence"
        returned.setdefault("observed_evidence", ["deterministic preset completion evidence"])
        returned.setdefault(
            "not_proven",
            ["semantic correctness", "real Slack delivery", "real provider behavior"],
        )
        assistant_text = json.dumps(returned, sort_keys=True)
        # TrackA-A1 FIXTURE FAITHFULNESS: real `codex exec --json` writes the
        # assistant text to the --output-last-message FILE and emits JSONL events on
        # stdout (the assistant payload is NOT on raw stdout). Model that here when
        # the invocation carries --output-last-message (codex): write the text to
        # the file, and put a terminal turn.completed usage event on stdout so the
        # meter side-channel is exercised. The adapter reads text from the file (it
        # must NEVER treat the JSONL stdout as assistant text). Non-codex
        # invocations (no --output-last-message) keep the plain-text stdout shape.
        output_path = _output_last_message_path(checked_args)
        if output_path is not None:
            Path(output_path).write_text(assistant_text, encoding="utf-8")
            stdout = (
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 12,
                            "cached_input_tokens": 3,
                            "output_tokens": 4,
                            "reasoning_output_tokens": 5,
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        elif _is_gemini_json_invocation(checked_args):
            stdout = json.dumps(
                {
                    "response": assistant_text,
                    "stats": {"tools": {"byName": {}}},
                },
                sort_keys=True,
            )
        else:
            stdout = assistant_text
        return completed_cls(
            args=checked_args,
            return_code=0,
            stdout=stdout,
            stderr="",
        )

    return _runner


def _preset_completion_prompt_from_cli_args(args: Sequence[str]) -> str:
    """Return the prompt from fixture CLI args across codex/claude/gemini shapes."""
    args = tuple(str(arg) for arg in args)
    for index, value in enumerate(args):
        if (
            value == "-p"
            and index + 1 < len(args)
            and not args[index + 1].startswith("-")
        ):
            return args[index + 1]
    return args[-1] if args else ""


def _is_gemini_json_invocation(args: Sequence[str]) -> bool:
    args = tuple(str(arg) for arg in args)
    for index, value in enumerate(args):
        if value == "--output-format" and index + 1 < len(args):
            return args[index + 1] == "json" and "-p" in args
    return False


def _output_last_message_path(args: Sequence[str]) -> str | None:
    """Return the --output-last-message path from a codex invocation, else None."""
    args = list(args)
    for index, value in enumerate(args):
        if value == "--output-last-message" and index + 1 < len(args):
            return args[index + 1]
    return None


def _deterministic_completion_list(label: str, source: str) -> list[str]:
    if label in _PRESET_COMPLETION_REPO_ARTIFACT_FIELDS:
        return [
            f"{label}: {source} deterministic evidence from support/checkers/lib/case_runners.py"
        ]
    return [f"{label}: {source} deterministic evidence"]


def _return_labels_from_cli_prompt(prompt: str) -> tuple[str, ...]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, Mapping):
        return ()
    labels = payload.get("required_return_labels")
    if not isinstance(labels, Sequence) or isinstance(labels, (str, bytes)):
        return ()
    return tuple(str(label).strip() for label in labels if str(label).strip())
