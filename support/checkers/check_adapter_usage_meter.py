#!/usr/bin/env python3
"""Pin the per-step adapter token-usage METER to support-fact-only discipline.

TrackA-A1 (INSTRUMENT FIRST 0619). BRICK now records the per-step codex token
usage parsed from ``codex exec --json`` (the ``turn.completed.usage`` block) into
a SUPPORT meter journal at ``raw/adapter-usage.jsonl``. This checker pins the two
invariants that make that a clean Brick-axis SUPPORT FACT rather than a leak:

  1. KEY DISCIPLINE: the meter record carries only the allowlisted token-counter
     keys (the canonical WORKFLOW_IMPORT_USAGE_METRIC_KEYS subset), every key is
     always present, and absent usage is recorded as ``null`` (never fabricated,
     never dropped). usage_present flips False on the graceful-fallback path.

  2. GATE-NO-MEASURE / TRUTH-BEFORE-QUALITY: the token counts NEVER appear in
     AgentFact.returned or any Link field. The adapter surfaces usage on a
     SIDE-CHANNEL (AgentAdapterResult.adapter_usage), the per-step return
     recording writer (support/recording/step_outputs.py) does NOT carry usage,
     and the codex adapter does NOT inject usage into the ``returned`` dict it
     builds (which becomes AgentFact.returned).

It runs the meter writer IN-PROCESS with fabricated usage fixtures (NO live codex,
NO subprocess) and AST-scans the two real source modules. It FAILS CLOSED. It does
NOT call providers, choose Movement, judge source truth, judge success or quality,
or apply any token cap (a cap is TrackA-A2; this step is measurement only).
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADAPTER_REL = Path("support/connection/agent_adapter.py")
_STEP_OUTPUTS_REL = Path("support/recording/step_outputs.py")
_METER_REL = Path("support/recording/adapter_usage_meter.py")
_RUN_REL = Path("support/operator/run.py")

# A realistic codex ``exec --json`` JSONL stdout: one assistant-message event plus
# a terminal turn.completed carrying a usage block. Used to pin that, when the
# --output-last-message file is EMPTY, the assistant TEXT is recovered from the
# message event ONLY -- the raw JSONL (and any embedded usage) is never returned.
_CODEX_JSONL_STDOUT = (
    '{"type":"item.completed","item":{"type":"agent_message",'
    '"text":"the real assistant answer"}}\n'
    '{"type":"turn.completed","usage":{"input_tokens":11,"cached_input_tokens":2,'
    '"output_tokens":3,"reasoning_output_tokens":4}}\n'
)

# The allowlisted token-counter keys the meter record MUST carry (always present;
# null when absent). These are the only token-quantity keys admitted into the
# support meter journal.
_EXPECTED_USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens")

# Token-usage key NAMES that must NEVER appear in an AgentFact.returned payload or
# any Link field. If any of these literals is assigned INTO the ``returned`` dict
# the codex adapter builds (the AgentFact.returned source), usage has leaked off
# its support-only channel.
_FORBIDDEN_RETURNED_USAGE_KEYS = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "reasoning_output_tokens",
        "total_tokens",
        "adapter_usage",
    }
)

PROOF_LIMIT = (
    "proof limit: adapter-usage meter checker support evidence only; it does not "
    "prove source truth, success judgment, quality judgment, Movement authority, "
    "provider behavior, or any cumulative token budget. It applies NO cap "
    "(measurement only; a cap is TrackA-A2)."
)


class AdapterUsageMeterError(ValueError):
    """Raised when the adapter-usage meter violates support-fact-only discipline."""


# --------------------------------------------------------------------------- #
# Behavioral (in-process) checks: run the meter writer with usage fixtures.    #
# --------------------------------------------------------------------------- #


def _build_record(adapter_usage: Mapping[str, object] | None) -> Mapping[str, object]:
    from brick_protocol.support.recording.adapter_usage_meter import (
        build_adapter_usage_record,
    )

    return build_adapter_usage_record(
        building_id="building-meter-fixture",
        step_ref="step:meter-fixture",
        adapter_ref="adapter:codex-local",
        selected_model_ref="model:codex-fixture",
        attempt_index=1,
        adapter_usage=adapter_usage,
    )


def _assert_present_usage_record() -> str:
    fixture = {
        "input_tokens": 1234,
        "cached_input_tokens": 56,
        "output_tokens": 78,
        "reasoning_output_tokens": 90,
    }
    record = _build_record(fixture)
    if record.get("usage_present") is not True:
        raise AdapterUsageMeterError(
            "present-usage record did not set usage_present=True"
        )
    usage = record.get("usage")
    if not isinstance(usage, Mapping):
        raise AdapterUsageMeterError("meter record has no usage mapping")
    for key in _EXPECTED_USAGE_KEYS:
        if key not in usage:
            raise AdapterUsageMeterError(
                f"meter usage mapping is missing required allowlisted key {key!r}"
            )
    extra = set(usage) - set(_EXPECTED_USAGE_KEYS)
    if extra:
        raise AdapterUsageMeterError(
            f"meter usage mapping carries non-allowlisted key(s) {sorted(extra)!r}"
        )
    if usage["input_tokens"] != 1234:
        raise AdapterUsageMeterError("input_tokens was not carried through")
    if usage["output_tokens"] != 78:
        raise AdapterUsageMeterError("output_tokens was not carried through")
    # codex cached_input_tokens must map onto the allowlisted cache_read slot.
    if usage["cache_read_input_tokens"] != 56:
        raise AdapterUsageMeterError(
            "codex cached_input_tokens was not mapped to cache_read_input_tokens"
        )
    if record.get("reasoning_output_tokens") != 90:
        raise AdapterUsageMeterError(
            "codex reasoning_output_tokens provenance was not recorded"
        )
    return (
        "present-usage: allowlisted counters carried (input/output + codex "
        "cached->cache_read), reasoning provenance recorded, usage_present=True"
    )


def _assert_absent_usage_record() -> str:
    record = _build_record(None)
    if record.get("usage_present") is not False:
        raise AdapterUsageMeterError(
            "absent-usage record did not set usage_present=False"
        )
    usage = record.get("usage")
    if not isinstance(usage, Mapping):
        raise AdapterUsageMeterError("absent-usage record has no usage mapping")
    for key in _EXPECTED_USAGE_KEYS:
        if key not in usage:
            raise AdapterUsageMeterError(
                f"absent-usage mapping is missing key {key!r} (must be present-as-null)"
            )
        if usage[key] is not None:
            raise AdapterUsageMeterError(
                f"absent-usage key {key!r} was fabricated to {usage[key]!r} "
                "(absent must be null)"
            )
    if record.get("reasoning_output_tokens") is not None:
        raise AdapterUsageMeterError(
            "absent-usage reasoning_output_tokens must be null, not fabricated"
        )
    return "absent-usage: all counters present-as-null, usage_present=False (graceful)"


def _assert_no_forbidden_keys_in_record() -> str:
    """The meter record itself must not be a verdict: it must carry no Link/verdict
    keys (no route/transition/binding/movement). Confirms the meter is a Brick-axis
    support fact, not a Link field."""
    record = _build_record({"input_tokens": 1, "output_tokens": 2})
    forbidden_in_record = {
        "route_request",
        "transition_concern_evidence",
        "binding",
        "movement",
        "target_ref",
        "verdict",
        "success",
        "quality",
        "fault",
    }
    present = sorted(forbidden_in_record & set(record))
    if present:
        raise AdapterUsageMeterError(
            f"meter record carries forbidden Link/verdict key(s) {present!r}"
        )
    return "meter record carries no Link/verdict key (support fact only)"


def _assert_mutation_red_dropped_key() -> str:
    """A meter usage projection that DROPS an allowlisted key must be rejected.

    Mirrors the writer's own allowlist projection then strips one key and confirms
    the present-usage assertion REJECTS the truncated mapping -- so the checker is
    not vacuously green if the writer ever drops a counter key."""
    fixture = {
        "input_tokens": 1234,
        "cached_input_tokens": 56,
        "output_tokens": 78,
        "reasoning_output_tokens": 90,
    }
    record = dict(_build_record(fixture))
    usage = dict(record["usage"])  # type: ignore[arg-type]
    usage.pop("output_tokens", None)
    record["usage"] = usage
    try:
        _assert_present_usage_record_on(record)
    except AdapterUsageMeterError:
        return "mutation RED observed: a meter usage mapping with a dropped key is rejected"
    raise AdapterUsageMeterError(
        "mutation RED failed: a usage mapping missing output_tokens was still accepted"
    )


def _assert_present_usage_record_on(record: Mapping[str, object]) -> None:
    usage = record.get("usage")
    if not isinstance(usage, Mapping):
        raise AdapterUsageMeterError("record has no usage mapping")
    for key in _EXPECTED_USAGE_KEYS:
        if key not in usage:
            raise AdapterUsageMeterError(f"missing required allowlisted key {key!r}")


def _assert_mutation_red_usage_into_returned() -> str:
    """If usage is placed INTO an AgentFact.returned payload, the gate-no-measure
    AST guard must reject it. Builds a synthetic ``returned``-shaped function that
    assigns a usage key into the returned dict and confirms the leak detector
    flags it -- so the static guard is not vacuously green."""
    leaking_source = (
        "def _invoke_local_cli_adapter():\n"
        "    returned = {}\n"
        "    returned['input_tokens'] = completed.adapter_usage\n"
        "    return returned\n"
    )
    module = ast.parse(leaking_source)
    leaks = _returned_usage_leak_keys(module, "_invoke_local_cli_adapter")
    if not leaks:
        raise AdapterUsageMeterError(
            "mutation RED failed: a usage key assigned into returned was not detected"
        )
    return (
        "mutation RED observed: a usage key written into AgentFact.returned is "
        "detected by the gate-no-measure AST guard"
    )


# --------------------------------------------------------------------------- #
# Behavioral: --json JSONL stdout NEVER becomes assistant text (text safety).  #
# --------------------------------------------------------------------------- #


def _assert_jsonl_never_becomes_text() -> str:
    """Under --json, an EMPTY output file must NOT fall back to raw JSONL as text.

    Pins the ROOT fix: codex_assistant_text_from_json_stdout recovers ONLY the real
    assistant message text from the JSONL events, never the raw JSONL stdout. This
    is what stops the event structure (and any embedded ``usage`` key) from leaking
    into output_excerpt / AgentFact.returned when the file is empty + return_code 0.
    """
    from brick_protocol.support.connection.agent_adapter import (
        codex_assistant_text_from_json_stdout,
    )

    recovered = codex_assistant_text_from_json_stdout(_CODEX_JSONL_STDOUT)
    if recovered != "the real assistant answer":
        raise AdapterUsageMeterError(
            "assistant-text recovery did not return the message text "
            f"(got {recovered!r})"
        )
    # The recovered text must be the message ONLY -- never the raw JSONL structure.
    for marker in ('"type"', "turn.completed", '"usage"', "input_tokens"):
        if marker in recovered:
            raise AdapterUsageMeterError(
                f"recovered assistant text leaks raw JSONL marker {marker!r}"
            )
    # No assistant-message event at all -> empty string, never the raw JSONL.
    usage_only = (
        '{"type":"turn.completed","usage":{"input_tokens":7,'
        '"cached_input_tokens":1,"output_tokens":2,"reasoning_output_tokens":3}}\n'
    )
    if codex_assistant_text_from_json_stdout(usage_only) != "":
        raise AdapterUsageMeterError(
            "usage-only JSONL (no message event) must recover empty text, not JSONL"
        )
    return (
        "text-safety: codex_assistant_text_from_json_stdout recovers ONLY the "
        "assistant message text from --json JSONL (raw JSONL/usage never returned; "
        "no message event -> empty text)"
    )


def _assert_mutation_red_jsonl_text_fallback() -> str:
    """Mutation RED: a recovery that returns the raw JSONL stdout must be rejected.

    Simulates the OLD vulnerable fallback (return the raw JSONL as the assistant
    text) and confirms the text-safety assertion above catches it -- so the guard
    is not vacuously green if someone reinstates the raw-stdout fallback."""

    def _leaking_recovery(stdout: str) -> str:
        return stdout  # the OLD bug: raw JSONL handed back as assistant text

    recovered = _leaking_recovery(_CODEX_JSONL_STDOUT)
    leaks = any(
        marker in recovered
        for marker in ('"type"', "turn.completed", '"usage"', "input_tokens")
    )
    if not leaks:
        raise AdapterUsageMeterError(
            "mutation RED failed: a raw-JSONL text fallback was not detected as a leak"
        )
    return (
        "mutation RED observed: a raw-JSONL assistant-text fallback is detected as "
        "a text-safety/gate-no-measure leak"
    )


# --------------------------------------------------------------------------- #
# Static (AST): meter is written ONLY when usage is present (no null-row noise).#
# --------------------------------------------------------------------------- #


def _assert_meter_write_guarded_by_usage_present(repo: Path) -> str:
    """The step-close meter writer must SKIP when usage is absent/empty.

    Pins the regression fix: _write_adapter_usage_meter_on_step_close must early-
    return when adapter_usage is not a non-empty Mapping, so claude/gemini/local
    (and older-codex no-usage) steps write NO adapter-usage row. We confirm a
    guarded early return GATES the write_adapter_usage_meter call: the call must be
    dominated by a `return` that triggers when adapter_usage is None / not a Mapping
    / empty."""
    module = _parse(repo, _RUN_REL)
    func = _function_node(module, "_write_adapter_usage_meter_on_step_close")
    has_guard_return = False
    write_call_present = False
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name) and target.id == "write_adapter_usage_meter":
                write_call_present = True
        # An `if <cond>: return` with no value, where cond references adapter_usage.
        if isinstance(node, ast.If):
            returns_in_body = any(
                isinstance(inner, ast.Return) and inner.value is None
                for inner in node.body
            )
            cond_text = ast.dump(node.test)
            if returns_in_body and "adapter_usage" in cond_text and (
                "Mapping" in cond_text or "isinstance" in cond_text
            ):
                has_guard_return = True
    if not write_call_present:
        raise AdapterUsageMeterError(
            f"{_RUN_REL}: _write_adapter_usage_meter_on_step_close no longer calls "
            "write_adapter_usage_meter"
        )
    if not has_guard_return:
        raise AdapterUsageMeterError(
            f"{_RUN_REL}: _write_adapter_usage_meter_on_step_close does not guard the "
            "meter write with an early `return` when adapter_usage is absent/empty -- "
            "non-usage adapters would write null-usage noise rows."
        )
    return (
        f"{_RUN_REL}: the per-step meter write is guarded by an early return when "
        "adapter_usage is absent/empty (only usage-present steps write a row)"
    )


def _assert_mutation_red_unguarded_meter_write() -> str:
    """Mutation RED: an UNGUARDED step-close writer (no usage-present return) must
    be detected. Builds a synthetic function that calls write_adapter_usage_meter
    with no adapter_usage guard and confirms the guard detector flags it."""
    unguarded_source = (
        "def _write_adapter_usage_meter_on_step_close():\n"
        "    adapter_usage = adapter_result.adapter_usage\n"
        "    write_adapter_usage_meter(adapter_usage=adapter_usage)\n"
    )
    module = ast.parse(unguarded_source)
    func = _function_node(module, "_write_adapter_usage_meter_on_step_close")
    has_guard_return = False
    for node in ast.walk(func):
        if isinstance(node, ast.If):
            returns_in_body = any(
                isinstance(inner, ast.Return) and inner.value is None
                for inner in node.body
            )
            cond_text = ast.dump(node.test)
            if returns_in_body and "adapter_usage" in cond_text and (
                "Mapping" in cond_text or "isinstance" in cond_text
            ):
                has_guard_return = True
    if has_guard_return:
        raise AdapterUsageMeterError(
            "mutation RED failed: an unguarded meter writer was reported as guarded"
        )
    return (
        "mutation RED observed: an unguarded step-close meter writer (no usage-"
        "present early return) is detected"
    )


# --------------------------------------------------------------------------- #
# Static (AST) gate-no-measure guard over the real source modules.            #
# --------------------------------------------------------------------------- #


def _parse(repo: Path, rel: Path) -> ast.Module:
    path = repo / rel
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
    except OSError as exc:
        raise AdapterUsageMeterError(f"could not read {rel}: {exc}") from exc
    except SyntaxError as exc:
        raise AdapterUsageMeterError(f"{rel} is not valid Python: {exc}") from exc


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AdapterUsageMeterError(f"missing required function {name}")


def _returned_usage_leak_keys(module: ast.Module, func_name: str) -> list[str]:
    """Return forbidden usage-key literals assigned INTO a ``returned`` dict.

    Scans the function body for ``returned[<literal>] = ...`` and
    ``returned = {..., <literal>: ...}`` where <literal> is a forbidden token-usage
    key. This is the leak shape: usage written into the AgentFact.returned source.
    """
    func = _function_node(module, func_name)
    leaks: list[str] = []
    for node in ast.walk(func):
        # returned[<key>] = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "returned"
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                    and target.slice.value in _FORBIDDEN_RETURNED_USAGE_KEYS
                ):
                    leaks.append(target.slice.value)
            # returned = { "<key>": ... }
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "returned"
                and isinstance(node.value, ast.Dict)
            ):
                for dkey in node.value.keys:
                    if (
                        isinstance(dkey, ast.Constant)
                        and isinstance(dkey.value, str)
                        and dkey.value in _FORBIDDEN_RETURNED_USAGE_KEYS
                    ):
                        leaks.append(dkey.value)
    return sorted(set(leaks))


def _expr_references_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _call_references_name(node: ast.Call, name: str) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == name
    if isinstance(func, ast.Attribute):
        return func.attr == name
    return False


def _is_completed_stdout(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "stdout"
        and isinstance(node.value, ast.Name)
        and node.value.id == "completed"
    )


def _targets_text_stdout(targets: Sequence[ast.expr]) -> bool:
    return any(isinstance(target, ast.Name) and target.id == "text_stdout" for target in targets)


def _branch_assigns_text_stdout(statements: Sequence[ast.stmt]) -> bool:
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, ast.Assign) and _targets_text_stdout(node.targets):
                return True
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "text_stdout"
            ):
                return True
    return False


def _branch_helper_call_lines(statements: Sequence[ast.stmt]) -> list[int]:
    lines: list[int] = []
    for statement in statements:
        for node in ast.walk(statement):
            if (
                isinstance(node, ast.Call)
                and _call_references_name(node, "codex_assistant_text_from_json_stdout")
            ):
                lines.append(node.lineno)
    return lines


def _branch_raw_stdout_assignment_lines(statements: Sequence[ast.stmt]) -> list[int]:
    lines: list[int] = []
    for statement in statements:
        for node in ast.walk(statement):
            if (
                isinstance(node, ast.Assign)
                and _targets_text_stdout(node.targets)
                and _is_completed_stdout(node.value)
            ):
                lines.append(node.lineno)
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "text_stdout"
                and node.value is not None
                and _is_completed_stdout(node.value)
            ):
                lines.append(node.lineno)
    return lines


def test_invoke_local_cli_uses_helper_not_raw_stdout(repo: Path) -> str:
    """Pin the --json empty-file fallback to assistant-text recovery, not raw stdout."""

    module = _parse(repo, _ADAPTER_REL)
    func = _function_node(module, "_invoke_local_cli")
    candidate_lines: list[int] = []
    helper_lines: list[int] = []
    raw_stdout_lines: list[int] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        if not _expr_references_name(node.test, "json_active"):
            continue
        if not _branch_assigns_text_stdout(node.body):
            continue
        candidate_lines.append(node.lineno)
        helper_lines.extend(_branch_helper_call_lines(node.body))
        raw_stdout_lines.extend(_branch_raw_stdout_assignment_lines(node.body))
    if not candidate_lines:
        raise AdapterUsageMeterError(
            f"{_ADAPTER_REL}: _invoke_local_cli no longer has a json_active "
            "text_stdout fallback branch for the empty output-file path"
        )
    if raw_stdout_lines:
        raise AdapterUsageMeterError(
            f"{_ADAPTER_REL}: _invoke_local_cli assigns bare completed.stdout to "
            f"text_stdout inside the json_active fallback branch at line(s) "
            f"{raw_stdout_lines!r}; --json stdout must pass through "
            "codex_assistant_text_from_json_stdout"
        )
    if not helper_lines:
        raise AdapterUsageMeterError(
            f"{_ADAPTER_REL}: _invoke_local_cli json_active fallback branch at "
            f"line(s) {candidate_lines!r} does not call "
            "codex_assistant_text_from_json_stdout"
        )
    return (
        f"{_ADAPTER_REL}: _invoke_local_cli json_active empty-file fallback calls "
        "codex_assistant_text_from_json_stdout and does not assign raw "
        "completed.stdout to text_stdout"
    )


def probe_mutation_red(repo: Path) -> str:
    """Temporarily reopen the raw-stdout gap and require this checker to fail RED."""

    adapter_path = repo / _ADAPTER_REL
    target = "text_stdout = codex_assistant_text_from_json_stdout(completed.stdout)"
    replacement = "text_stdout = completed.stdout"
    with tempfile.TemporaryDirectory(prefix="bp-adapter-usage-meter-") as tmpdir:
        backup_path = Path(tmpdir) / "agent_adapter.py.bak"
        subprocess.run(("cp", str(adapter_path), str(backup_path)), check=True, cwd=repo)
        try:
            source = adapter_path.read_text(encoding="utf-8")
            if target not in source:
                raise AdapterUsageMeterError(
                    f"{_ADAPTER_REL}: mutation target helper call is missing; "
                    "cannot run mutation-RED probe"
                )
            adapter_path.write_text(source.replace(target, replacement, 1), encoding="utf-8")
            env = os.environ.copy()
            import_root = str(repo / "support/import_identity")
            env["PYTHONPATH"] = (
                import_root
                if not env.get("PYTHONPATH")
                else f"{import_root}{os.pathsep}{env['PYTHONPATH']}"
            )
            completed = subprocess.run(
                (
                    sys.executable,
                    str(repo / "support/checkers/check_adapter_usage_meter.py"),
                    "--repo",
                    str(repo),
                ),
                cwd=repo,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if completed.returncode != 1:
                raise AdapterUsageMeterError(
                    "mutation RED failed: raw completed.stdout fallback produced "
                    f"checker exit {completed.returncode}, expected 1"
                )
        finally:
            subprocess.run(("cp", str(backup_path), str(adapter_path)), check=True, cwd=repo)
    return (
        "mutation RED observed: replacing the json_active helper fallback with "
        "bare completed.stdout makes check_adapter_usage_meter.py exit 1, then "
        "agent_adapter.py is restored with cp"
    )


def _assert_no_usage_in_codex_returned(repo: Path) -> str:
    module = _parse(repo, _ADAPTER_REL)
    leaks = _returned_usage_leak_keys(module, "_invoke_local_cli_adapter")
    if leaks:
        raise AdapterUsageMeterError(
            f"{_ADAPTER_REL}: token-usage key(s) {leaks!r} are written into the "
            "AgentFact.returned payload -- usage must stay on the adapter_usage "
            "side-channel, never inside AgentFact.returned (gate-no-measure)."
        )
    return (
        f"{_ADAPTER_REL}: codex adapter builds AgentFact.returned with NO token-usage "
        "key (usage rides the adapter_usage side-channel only)"
    )


def _assert_step_output_carries_no_usage(repo: Path) -> str:
    """The per-step return recording writer must not carry any token-usage key.

    Reads step_outputs.py and asserts no forbidden usage key literal appears in the
    output_packet construction path. Text-level guard (the output_packet is built
    from many helpers) -- it rejects any usage-key literal anywhere in the module
    that records AgentFact.returned-derived step output."""
    path = repo / _STEP_OUTPUTS_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterUsageMeterError(f"could not read {_STEP_OUTPUTS_REL}: {exc}") from exc
    offending = sorted(
        key
        for key in _FORBIDDEN_RETURNED_USAGE_KEYS
        if f'"{key}"' in text or f"'{key}'" in text
    )
    if offending:
        raise AdapterUsageMeterError(
            f"{_STEP_OUTPUTS_REL}: token-usage key literal(s) {offending!r} appear in "
            "the per-step return recording writer -- step output must not carry usage "
            "(usage lives only in the raw/adapter-usage.jsonl meter)."
        )
    return (
        f"{_STEP_OUTPUTS_REL}: per-step return recording writer carries no token-usage "
        "key (usage confined to the meter journal)"
    )


def check(repo: Path) -> list[str]:
    lines = [
        _assert_present_usage_record(),
        _assert_absent_usage_record(),
        _assert_no_forbidden_keys_in_record(),
        _assert_no_usage_in_codex_returned(repo),
        test_invoke_local_cli_uses_helper_not_raw_stdout(repo),
        _assert_step_output_carries_no_usage(repo),
        _assert_jsonl_never_becomes_text(),
        _assert_meter_write_guarded_by_usage_present(repo),
        _assert_mutation_red_dropped_key(),
        _assert_mutation_red_usage_into_returned(),
        _assert_mutation_red_jsonl_text_fallback(),
        _assert_mutation_red_unguarded_meter_write(),
        PROOF_LIMIT,
    ]
    return [
        "adapter-usage meter green: per-step codex token usage is recorded as a "
        "support fact in raw/adapter-usage.jsonl with allowlisted keys (absent=null) "
        "and never leaks into AgentFact.returned or any Link field.",
        *lines,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the per-step adapter token-usage meter "
            "records allowlisted counters (absent=null) and never leaks usage into "
            "AgentFact.returned or any Link field (TrackA-A1 INSTRUMENT FIRST)."
        )
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily mutate agent_adapter.py to the raw stdout fallback, assert "
            "this checker exits RED, and restore with cp"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = [probe_mutation_red(repo)] if args.probe_mutation_red else check(repo)
    except AdapterUsageMeterError as exc:
        print("adapter-usage meter rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
