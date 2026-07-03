"""Proof-command observation for declared Brick proof obligations.

Support records command rc/log excerpts only. It does not judge success,
quality, sufficiency, or Movement.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.connection.agent_adapter import AgentAdapterResult
from brick_protocol.support.operator.primitives import _REPO_ROOT, _mapping, _merge_texts


_PROOF_COMMAND_TIMEOUT_SECONDS = 120
_PROOF_LOG_TAIL_CHARS = 4000


def _proof_obligations_from_brick_row(
    row: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    value = row.get("proof_obligations")
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Brick row proof_obligations must be a list")
    obligations: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        obligations.append(_mapping(f"proof_obligations[{index}]", item))
    return tuple(obligations)


def _adapter_result_with_proof_observation(
    adapter_result: AgentAdapterResult,
    proof_obligations: Sequence[Mapping[str, Any]],
    *,
    adapter_cwd: Path | str | None,
) -> AgentAdapterResult:
    if not proof_obligations:
        return adapter_result
    observed = [
        _observe_proof_obligation(item, cwd=_adapter_cwd_path(adapter_cwd))
        for item in proof_obligations
        if str(item.get("kind") or "command").strip() != "mutation_red"
    ]
    returned_value = adapter_result.returned_value
    if isinstance(returned_value, Mapping):
        returned_mapping = dict(returned_value)
    else:
        returned_mapping = {"returned_excerpt": str(returned_value)}
    returned_mapping["observed_proof_runs"] = observed
    return AgentAdapterResult(
        request=adapter_result.request,
        returned_value=returned_mapping,
        proof_limits=_merge_texts(
            adapter_result.proof_limits,
            "proof observation support evidence only",
        ),
        not_proven=_merge_texts(
            adapter_result.not_proven,
            "semantic correctness of proof commands",
            "mutation_red proof obligations are not executed by support",
        ),
        adapter_usage=adapter_result.adapter_usage,
        adapter_raw_observations=adapter_result.adapter_raw_observations,
        adapter_output_text=adapter_result.adapter_output_text,
    )


def _observe_proof_obligation(
    obligation: Mapping[str, Any],
    *,
    cwd: Path,
) -> dict[str, Any]:
    command = str(obligation.get("command") or "").strip()
    if not command:
        return {
            "command": command,
            "kind": str(obligation.get("kind") or "command").strip() or "command",
            "expect_rc": obligation.get("expect_rc") if "expect_rc" in obligation else None,
            "rc": None,
            "log_tail": "",
            "observation_error": "blank command",
        }
    return _run_proof_obligation(obligation, cwd=cwd)


def _run_proof_obligation(
    obligation: Mapping[str, Any],
    *,
    cwd: Path,
) -> dict[str, Any]:
    command = str(obligation.get("command") or "").strip()
    record: dict[str, Any] = {
        "command": command,
        "kind": str(obligation.get("kind") or "command").strip() or "command",
    }
    if "expect_rc" in obligation:
        record["expect_rc"] = obligation.get("expect_rc")
    if not command:
        record.update({"rc": None, "log_tail": "", "observation_error": "blank command"})
        return record
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            capture_output=True,
            check=False,
            timeout=_PROOF_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        record.update(
            {
                "rc": None,
                "log_tail": _tail_text(
                    _output_text(exc.stdout)
                    + ("\n" if exc.stdout and exc.stderr else "")
                    + _output_text(exc.stderr)
                ),
                "observation_error": "timeout",
            }
        )
        return record
    except (OSError, subprocess.SubprocessError) as exc:
        record.update(
            {
                "rc": None,
                "log_tail": "",
                "observation_error": type(exc).__name__,
            }
        )
        return record
    record.update(
        {
            "rc": completed.returncode,
            "log_tail": _tail_text(completed.stdout + completed.stderr),
        }
    )
    return record


def _adapter_cwd_path(adapter_cwd: Path | str | None) -> Path:
    return Path(adapter_cwd) if adapter_cwd is not None else _REPO_ROOT


def _tail_text(value: str) -> str:
    text = str(value)
    return text[-_PROOF_LOG_TAIL_CHARS:]


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
