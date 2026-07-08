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
     recording writer (brick_protocol/support/recording/step_outputs.py) does NOT carry usage,
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
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
# MODULE-SEP god-module split: the codex local-CLI invoke path (_invoke_local_cli,
# _invoke_local_cli_adapter, and the codex_assistant_text_from_json_stdout empty-file
# fallback) relocated verbatim from agent_adapter.py into the adapter_local_cli.py
# sibling (re-exported by the agent_adapter facade). The AST-scan + mutation pins
# follow the moved symbols to their new home. (The in-process behavioral probes
# below still import via the agent_adapter facade, whose public surface is preserved.)
_ADAPTER_REL = Path("brick_protocol/support/connection/adapter_local_cli.py")
_STEP_OUTPUTS_REL = Path("brick_protocol/support/recording/step_outputs.py")
_METER_REL = Path("brick_protocol/support/recording/adapter_usage_meter.py")
_RUN_REL = Path("brick_protocol/support/operator/run.py")
_WALKER_KERNEL_REL = Path("brick_protocol/support/operator/walker_kernel.py")

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


def _build_claude_alias_record() -> Mapping[str, object]:
    from brick_protocol.support.recording.adapter_usage_meter import (
        build_adapter_usage_record,
    )

    return build_adapter_usage_record(
        building_id="building-meter-fixture",
        step_ref="step:meter-fixture",
        adapter_ref="adapter:claude-local",
        selected_model_ref="model:claude:sonnet",
        attempt_index=1,
        adapter_usage={"input_tokens": 1, "output_tokens": 1},
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
    if record.get("dispatched_model") != "declared-default":
        raise AdapterUsageMeterError(
            "present default-model usage record did not record dispatched_model=declared-default"
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


def _assert_dispatched_model_alias_record() -> str:
    record = _build_claude_alias_record()
    if record.get("dispatched_model") != "claude-sonnet-5":
        raise AdapterUsageMeterError(
            "Claude alias usage record did not resolve dispatched_model to claude-sonnet-5"
        )
    return "dispatched-model: usage row records the concrete CLI model for Claude aliases"


def _assert_usage_record_timestamp_and_alias_resolution() -> str:
    record = _build_claude_alias_record()
    recorded_at = record.get("recorded_at")
    adapter_usage_recorded_at = record.get("adapter_usage_recorded_at")
    if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
        raise AdapterUsageMeterError(
            "usage row recorded_at is not an explicit UTC ISO timestamp"
        )
    if adapter_usage_recorded_at != recorded_at:
        raise AdapterUsageMeterError(
            "usage row adapter_usage_recorded_at does not match graph-ready recorded_at"
        )
    try:
        datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterUsageMeterError(
            f"usage row recorded_at is not parseable ISO text: {recorded_at!r}"
        ) from exc
    alias_resolution = record.get("model_alias_resolution")
    if not isinstance(alias_resolution, Mapping):
        raise AdapterUsageMeterError("usage row lacks model_alias_resolution mapping")
    expected = {
        "adapter_ref": "adapter:claude-local",
        "selected_model_ref": "model:claude:sonnet",
        "dispatched_model": "claude-sonnet-5",
    }
    for key, value in expected.items():
        if alias_resolution.get(key) != value:
            raise AdapterUsageMeterError(
                f"usage row model_alias_resolution[{key!r}]={alias_resolution.get(key)!r}, "
                f"expected {value!r}"
            )
    return (
        "timestamp+alias: usage row carries explicit ISO recorded_at/"
        "adapter_usage_recorded_at plus selected_model_ref -> dispatched_model "
        "alias-resolution evidence"
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


def _assert_mutation_red_missing_usage_timestamp_alias() -> str:
    record = dict(_build_claude_alias_record())
    record.pop("adapter_usage_recorded_at", None)
    record.pop("model_alias_resolution", None)
    if "adapter_usage_recorded_at" in record or "model_alias_resolution" in record:
        raise AdapterUsageMeterError(
            "mutation RED failed: timestamp/alias fields were not removed from fixture"
        )
    try:
        _assert_usage_record_timestamp_alias_on(record)
    except AdapterUsageMeterError:
        return (
            "mutation RED observed: a usage row missing adapter_usage_recorded_at "
            "and model_alias_resolution is rejected"
        )
    raise AdapterUsageMeterError(
        "mutation RED failed: a usage row missing timestamp/alias fields was accepted"
    )


def _assert_usage_record_timestamp_alias_on(record: Mapping[str, object]) -> None:
    if not isinstance(record.get("adapter_usage_recorded_at"), str):
        raise AdapterUsageMeterError("record missing adapter_usage_recorded_at")
    if not isinstance(record.get("model_alias_resolution"), Mapping):
        raise AdapterUsageMeterError("record missing model_alias_resolution")


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
    from brick_protocol.support.connection.adapter_subprocess import (
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


def _assert_local_cli_nonzero_classification() -> str:
    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants
    from brick_protocol.support.connection import adapter_local_cli

    cases = (
        ("spend_limit", "429 billing hard limit: spend limit reached"),
        ("auth", "401 authentication failed: login required"),
        ("transport", "503 service unavailable: connection reset"),
        ("unknown", "provider exited with code 1"),
    )
    for expected, stderr in cases:
        completed = adapter.LocalCliCompleted(
            ("codex", "exec"),
            1,
            "",
            stderr,
        )
        observed = adapter_local_cli._local_cli_nonzero_classification(completed)
        if observed != expected:
            raise AdapterUsageMeterError(
                f"nonzero classification for {stderr!r} was {observed!r}, expected {expected!r}"
            )

    request = adapter.AgentAdapterRequest(
        building_id="adapter-error-classification-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-probe",
        next_brick_instance_ref="brick-closure",
        casting={"selected_model_ref": "model:claude:sonnet"},
    )
    spec = adapter._local_cli_spec(adapter_constants.ADAPTER_CLAUDE_LOCAL)
    message = adapter_local_cli._local_cli_nonzero_error_message(
        request,
        spec,
        adapter.LocalCliCompleted(
            ("claude", "-p"),
            1,
            "",
            "401 authentication failed: login required",
        ),
    )
    required = (
        "adapter_error_classification=auth",
        "adapter_error_recorded_at=",
        "selected_model_ref=model:claude:sonnet",
        "dispatched_model=claude-sonnet-5",
        "return_code=1",
    )
    missing = [marker for marker in required if marker not in message]
    if missing:
        raise AdapterUsageMeterError(
            "nonzero error message lacks required safe evidence marker(s) "
            f"{missing!r}: {message!r}"
        )
    timestamp = message.split("adapter_error_recorded_at=", 1)[1].split(";", 1)[0]
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterUsageMeterError(
            f"adapter_error_recorded_at is not parseable ISO text: {timestamp!r}"
        ) from exc
    forbidden = ("sk-", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    leaked = [marker for marker in forbidden if marker in message]
    if leaked:
        raise AdapterUsageMeterError(
            f"nonzero error message leaked credential-looking marker(s) {leaked!r}"
        )
    return (
        "adapter-error classification: local CLI nonzero evidence carries "
        "spend_limit/auth/transport/unknown labels, ISO timestamp, return_code, "
        "selected_model_ref, and dispatched_model without credential markers"
    )


def _assert_mutation_red_missing_error_classification() -> str:
    message = (
        "local CLI adapter command returned non-zero; adapter_ref=adapter:claude-local; "
        "selected_model_ref=model:claude:sonnet; dispatched_model=claude-sonnet-5; "
        "return_code=1"
    )
    required = ("adapter_error_classification=", "adapter_error_recorded_at=")
    missing = [marker for marker in required if marker not in message]
    if missing:
        return (
            "mutation RED observed: nonzero CLI evidence without classification/"
            "timestamp markers is rejected"
        )
    raise AdapterUsageMeterError(
        "mutation RED failed: a nonzero CLI message lacking classification/timestamp "
        "markers was accepted"
    )


_CLAUDE_OBITUARY_PROVIDER_SENTENCE = "Claude usage limit reached; try again later"


def _claude_obituary_error_stdout() -> str:
    """A claude ``--output-format json`` result object reporting its own failure.

    Claude flags a failed run with ``is_error`` + an ``error*`` subtype (not a
    top-level ``error`` key), and carries the free-text reason in ``result``. The
    ``session_id`` is present precisely so the excerpt path is proven NOT to lift
    it (the obituary carries the error text only)."""

    return json.dumps(
        {
            "type": "result",
            "subtype": "error_during_execution",
            "is_error": True,
            "result": _CLAUDE_OBITUARY_PROVIDER_SENTENCE,
            "session_id": "claude-obituary-probe-session-id",
        }
    )


def _assert_claude_obituary_stdout_excerpt() -> str:
    """CLAUDE OBITUARY (R4 follow-up): a claude-local nonzero death records its
    provider stdout error excerpt + classification in the adapter-error message,
    same shape as the codex JSONL obituary, with the secret scrub boundary and the
    session-id non-leak preserved (0707 pre-dawn line deaths were obituary-less)."""

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants
    from brick_protocol.support.connection import adapter_local_cli

    error_stdout = _claude_obituary_error_stdout()
    noisy_stderr = "warning: unrelated client noise before useful provider JSON"

    excerpt = adapter_local_cli._stdout_error_excerpt(error_stdout)
    if _CLAUDE_OBITUARY_PROVIDER_SENTENCE not in excerpt:
        raise AdapterUsageMeterError(
            "claude obituary: claude result-JSON stdout error text was not preserved "
            f"in the stdout excerpt (got {excerpt!r})"
        )

    completed = adapter.LocalCliCompleted(("claude", "-p"), 1, error_stdout, noisy_stderr)
    if adapter_local_cli._local_cli_nonzero_classification(completed) != "spend_limit":
        raise AdapterUsageMeterError(
            "claude obituary: a claude usage-limit death did not classify as spend_limit"
        )

    request = adapter.AgentAdapterRequest(
        building_id="claude-obituary-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        casting={"selected_model_ref": "model:claude:sonnet"},
    )
    spec = adapter._local_cli_spec(adapter_constants.ADAPTER_CLAUDE_LOCAL)
    message = adapter_local_cli._local_cli_nonzero_error_message(request, spec, completed)
    stdout_at = message.find("stdout_error_excerpt=")
    stderr_at = message.find("stderr_excerpt=")
    if stdout_at < 0 or _CLAUDE_OBITUARY_PROVIDER_SENTENCE not in message:
        raise AdapterUsageMeterError(
            "claude obituary: adapter-error message carried no provider stdout error "
            f"excerpt for a claude result-JSON death: {message!r}"
        )
    if stderr_at >= 0 and stdout_at > stderr_at:
        raise AdapterUsageMeterError(
            "claude obituary: provider stdout error did not precede noisy stderr in "
            "the message_excerpt source text"
        )
    if "claude-obituary-probe-session-id" in message:
        raise AdapterUsageMeterError(
            "claude obituary: the claude session id leaked into the obituary message"
        )

    # HONEST-UNKNOWN: a claude success/no-signal result must not fabricate an excerpt.
    success_stdout = json.dumps(
        {"type": "result", "subtype": "success", "is_error": False, "result": "done"}
    )
    if adapter_local_cli._stdout_error_excerpt(success_stdout) != "":
        raise AdapterUsageMeterError(
            "claude obituary: a successful claude result fabricated a stdout excerpt"
        )

    # SCRUB boundary: a credential-looking token in the provider text is redacted,
    # never emitted verbatim into the excerpt.
    secret_token = "sk-ant-api03-" + "A" * 40
    secret_stdout = json.dumps(
        {"subtype": "error", "is_error": True, "result": f"auth failed {secret_token}"}
    )
    if secret_token in adapter_local_cli._stdout_error_excerpt(secret_stdout):
        raise AdapterUsageMeterError(
            "claude obituary: a credential-looking token leaked through the stdout "
            "excerpt scrub"
        )

    return (
        "claude obituary: a claude-local nonzero death records its provider stdout "
        "error excerpt (ahead of noisy stderr, session id + secrets scrubbed) with a "
        "spend_limit classification, and a successful result fabricates no excerpt"
    )


def _assert_mutation_red_claude_obituary_excerpt_dropped() -> str:
    """Mutation RED: neutering the claude result-error detector drops the claude
    obituary stdout excerpt (proves the detector is load-bearing, not decorative)."""

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants
    from brick_protocol.support.connection import adapter_local_cli

    error_stdout = _claude_obituary_error_stdout()
    completed = adapter.LocalCliCompleted(
        ("claude", "-p"), 1, error_stdout, "noisy client stderr only"
    )
    request = adapter.AgentAdapterRequest(
        building_id="claude-obituary-mutation-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        casting={"selected_model_ref": "model:claude:sonnet"},
    )
    spec = adapter._local_cli_spec(adapter_constants.ADAPTER_CLAUDE_LOCAL)
    original = adapter_local_cli._claude_result_error_present
    try:
        adapter_local_cli._claude_result_error_present = lambda _payload: False
        mutated_excerpt = adapter_local_cli._stdout_error_excerpt(error_stdout)
        mutated_message = adapter_local_cli._local_cli_nonzero_error_message(
            request, spec, completed
        )
    finally:
        adapter_local_cli._claude_result_error_present = original
    if _CLAUDE_OBITUARY_PROVIDER_SENTENCE in mutated_excerpt or (
        _CLAUDE_OBITUARY_PROVIDER_SENTENCE in mutated_message
    ):
        raise AdapterUsageMeterError(
            "mutation RED failed: removing the claude result-error detector still "
            "produced a claude stdout error excerpt"
        )
    return (
        "mutation RED observed: neutering the claude result-error detector drops the "
        "claude obituary stdout excerpt (the detector is load-bearing)"
    )


_CLAUDE_OBITUARY_UUID_SESSION = "550e8400-e29b-41d4-a716-446655440000"


def _assert_claude_obituary_edge_cases() -> str:
    """CLAUDE OBITUARY edge cases (closure QA follow-up): the obituary excerpt path
    survives the four false-fire / miss classes the first landing left open --
    P2b (a null top-level ``error`` shadowing the claude result branch), P4 (a
    mapping-valued error carrying a UUID session id), P5 (a claude result printed
    behind noisy stdout lines), and R4 (a cross-field space-join manufacturing a
    spend_limit marker neither field carried)."""

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_local_cli

    # P2b: a claude result flagging its own failure with an EXPLICIT ``"error": null``
    # alongside ``is_error: true`` must still record the result's free-text reason,
    # not fall to an empty excerpt because ``"error" in payload`` was truthy-by-key.
    null_error_stdout = json.dumps(
        {
            "type": "result",
            "subtype": "error_during_execution",
            "is_error": True,
            "error": None,
            "result": "claude run failed after a tool error",
        }
    )
    null_excerpt = adapter_local_cli._stdout_error_excerpt(null_error_stdout)
    if "claude run failed after a tool error" not in null_excerpt:
        raise AdapterUsageMeterError(
            "P2b: an explicit error:null shadowed the claude result branch and dropped "
            f"the obituary excerpt (got {null_excerpt!r})"
        )

    # P4: a mapping-valued error object carrying a bare-UUID session id (under a
    # session key AND under a benign key) must be scrubbed of the UUID while keeping
    # the real error message. The shared redactor does NOT match a bare hyphenated
    # UUID, so this proves the dedicated session-identifier scrub.
    mapping_error_stdout = json.dumps(
        {
            "is_error": True,
            "subtype": "error_during_execution",
            "error": {
                "message": "upstream provider failure while writing",
                "session_id": _CLAUDE_OBITUARY_UUID_SESSION,
                "detail": _CLAUDE_OBITUARY_UUID_SESSION,
            },
        }
    )
    mapping_excerpt = adapter_local_cli._stdout_error_excerpt(mapping_error_stdout)
    if _CLAUDE_OBITUARY_UUID_SESSION in mapping_excerpt:
        raise AdapterUsageMeterError(
            "P4: a UUID session id from a mapping-valued claude error rode into the "
            f"obituary excerpt (got {mapping_excerpt!r})"
        )
    if "upstream provider failure while writing" not in mapping_excerpt:
        raise AdapterUsageMeterError(
            "P4: scrubbing the session id also dropped the real provider error message "
            f"(got {mapping_excerpt!r})"
        )

    # P5: a claude obituary printed BEHIND a line of client noise (so the whole stdout
    # is not a single JSON object) is still recovered by the per-line scan.
    noisy_stdout = (
        "warning: unrelated client noise before the provider JSON\n"
        + _claude_obituary_error_stdout()
    )
    noisy_excerpt = adapter_local_cli._stdout_error_excerpt(noisy_stdout)
    if _CLAUDE_OBITUARY_PROVIDER_SENTENCE not in noisy_excerpt:
        raise AdapterUsageMeterError(
            "P5: a claude obituary behind a noise-prefixed stdout line yielded an empty "
            f"excerpt (got {noisy_excerpt!r})"
        )

    # R4: the classifier must NOT manufacture a spend_limit marker by space-joining a
    # "rate"-tailed stderr with a "limit"-led stdout. Neither field carries a full
    # spend marker on its own, so the honest label is unknown.
    cross_field = adapter.LocalCliCompleted(
        ("claude", "-p"), 1, "limit exceeded downstream", "provider error: rate"
    )
    cross_field_label = adapter_local_cli._local_cli_nonzero_classification(cross_field)
    if cross_field_label != "unknown":
        raise AdapterUsageMeterError(
            "R4: a cross-field space-join manufactured a "
            f"{cross_field_label!r} classification neither field carried"
        )

    return (
        "claude obituary edge cases: null-error no longer shadows the claude branch "
        "(P2b), a mapping-valued UUID session id is scrubbed while the message is kept "
        "(P4), a noise-prefixed obituary is still recovered (P5), and a cross-field "
        "join no longer fabricates a spend_limit label (R4)"
    )


# A NON-UUID provider session marker: it is dropped ONLY by the key-drop scrub
# (_scrub_session_identifiers), never by the embedded-UUID mask or the shared
# session-redaction patterns -- so it isolates the key-drop scrub as load-bearing.
_CLAUDE_OBITUARY_PLAIN_SESSION = "claude-obituary-plain-session-marker"


def _assert_mutation_red_session_identifier_scrub_dropped() -> str:
    """Mutation RED: neutering the session-identifier KEY-DROP scrub leaks a NON-UUID
    session id into the obituary excerpt (proves the P4 key-drop scrub is load-bearing
    for session-named keys whose value is NOT a bare UUID -- the shared redaction
    patterns AND the embedded-UUID mask both miss such a value, so only the key-drop
    scrub removes it). A UUID value is used elsewhere (the embedded-UUID mask test);
    here the value is deliberately non-UUID to isolate the key-drop path."""

    from brick_protocol.support.connection import adapter_local_cli

    mapping_error_stdout = json.dumps(
        {
            "is_error": True,
            "subtype": "error_during_execution",
            "error": {
                "message": "upstream provider failure",
                "session_id": _CLAUDE_OBITUARY_PLAIN_SESSION,
            },
        }
    )
    original = adapter_local_cli._scrub_session_identifiers
    try:
        adapter_local_cli._scrub_session_identifiers = lambda value, **_kw: value
        mutated_excerpt = adapter_local_cli._stdout_error_excerpt(mapping_error_stdout)
    finally:
        adapter_local_cli._scrub_session_identifiers = original
    if _CLAUDE_OBITUARY_PLAIN_SESSION not in mutated_excerpt:
        raise AdapterUsageMeterError(
            "mutation RED failed: neutering _scrub_session_identifiers did NOT leak the "
            "non-UUID session id -- the key-drop scrub is not load-bearing for "
            f"session-named keys (got {mutated_excerpt!r})"
        )
    # SANITY: the non-mutated path must still scrub the non-UUID session marker (the
    # key-drop scrub removes it), so the mutation above proves a real load-bearing gap.
    clean_excerpt = adapter_local_cli._stdout_error_excerpt(mapping_error_stdout)
    if _CLAUDE_OBITUARY_PLAIN_SESSION in clean_excerpt:
        raise AdapterUsageMeterError(
            "session scrub: the non-mutated obituary excerpt still leaked the non-UUID "
            f"session marker (got {clean_excerpt!r})"
        )
    return (
        "mutation RED observed: neutering _scrub_session_identifiers leaks a non-UUID "
        "session id into the obituary excerpt (the P4 key-drop scrub is load-bearing)"
    )


def _assert_string_error_uuid_scrubbed() -> str:
    """P-QA8: a STRING-typed provider error carrying an EMBEDDED bare UUID must have
    the UUID masked in the obituary excerpt while the real error text is preserved.

    The first landing scrubbed only mapping-valued errors (key drop + whole-string
    UUID value). A string-typed claude ``result`` free-text -- and a UUID embedded
    inside a mapping error's own message string -- still rode a bare session/request
    UUID into the excerpt (0707 scroll-window line deaths). This pins the embedded-UUID
    mask over BOTH branches; the shared session-redaction patterns do NOT cover a bare
    hyphenated UUID, so the mask is required."""

    from brick_protocol.support.connection import adapter_local_cli

    # (a) STRING-typed claude result error with an embedded UUID.
    string_error_stdout = json.dumps(
        {
            "type": "result",
            "subtype": "error_during_execution",
            "is_error": True,
            "result": (
                f"run failed in session {_CLAUDE_OBITUARY_UUID_SESSION} while writing"
            ),
        }
    )
    string_excerpt = adapter_local_cli._stdout_error_excerpt(string_error_stdout)
    if _CLAUDE_OBITUARY_UUID_SESSION in string_excerpt:
        raise AdapterUsageMeterError(
            "P-QA8: a string-typed claude error leaked its embedded UUID session id "
            f"into the obituary excerpt (got {string_excerpt!r})"
        )
    if "run failed" not in string_excerpt or "while writing" not in string_excerpt:
        raise AdapterUsageMeterError(
            "P-QA8: masking the embedded UUID also dropped the real string-error text "
            f"(got {string_excerpt!r})"
        )

    # (b) mapping-valued error whose own MESSAGE string embeds a UUID (not a whole-
    # string value, so the anchored value-scrub cannot reach it).
    embedded_mapping_stdout = json.dumps(
        {
            "is_error": True,
            "subtype": "error",
            "error": {
                "message": (
                    f"upstream failure for session {_CLAUDE_OBITUARY_UUID_SESSION} "
                    "downstream"
                ),
            },
        }
    )
    embedded_excerpt = adapter_local_cli._stdout_error_excerpt(embedded_mapping_stdout)
    if _CLAUDE_OBITUARY_UUID_SESSION in embedded_excerpt:
        raise AdapterUsageMeterError(
            "P-QA8: a UUID embedded inside a mapping error's message string leaked into "
            f"the obituary excerpt (got {embedded_excerpt!r})"
        )
    if "upstream failure" not in embedded_excerpt:
        raise AdapterUsageMeterError(
            "P-QA8: masking the embedded UUID also dropped the mapping error message "
            f"(got {embedded_excerpt!r})"
        )
    return (
        "P-QA8: a string-typed provider error and a UUID embedded inside a mapping "
        "error message are both masked in the obituary excerpt while the real error "
        "text is preserved"
    )


def _assert_mutation_red_embedded_uuid_mask_dropped() -> str:
    """Mutation RED: neutering the embedded-UUID mask leaks a string-typed error's
    embedded UUID into the obituary excerpt (proves the P-QA8 mask is load-bearing --
    the key-drop scrub does NOT run on a string error and the shared redaction
    patterns do NOT cover a bare hyphenated UUID)."""

    from brick_protocol.support.connection import adapter_local_cli

    string_error_stdout = json.dumps(
        {
            "type": "result",
            "subtype": "error_during_execution",
            "is_error": True,
            "result": (
                f"run failed in session {_CLAUDE_OBITUARY_UUID_SESSION} while writing"
            ),
        }
    )
    original = adapter_local_cli._mask_embedded_session_uuids
    try:
        adapter_local_cli._mask_embedded_session_uuids = lambda text: text
        mutated_excerpt = adapter_local_cli._stdout_error_excerpt(string_error_stdout)
    finally:
        adapter_local_cli._mask_embedded_session_uuids = original
    if _CLAUDE_OBITUARY_UUID_SESSION not in mutated_excerpt:
        raise AdapterUsageMeterError(
            "mutation RED failed: neutering _mask_embedded_session_uuids did NOT leak "
            "the embedded UUID from a string-typed error -- the mask is not load-bearing "
            f"or a wider redactor already covers bare embedded UUIDs (got {mutated_excerpt!r})"
        )
    return (
        "mutation RED observed: neutering _mask_embedded_session_uuids leaks a string-"
        "typed error's embedded UUID into the obituary excerpt (the P-QA8 mask is "
        "load-bearing)"
    )


def _assert_numeric_status_code_boundary() -> str:
    """Numeric-substring false-fire follow-up: an HTTP status code EMBEDDED inside a
    larger number must NOT fire a limit/transport/auth/content_policy label, while a
    genuine STANDALONE status code still classifies correctly.

    The first landing matched "429"/"529"/"503"-style codes as BARE SUBSTRINGS, so a
    token count ("11429 tokens"), a byte offset ("4529"), or a request id ("15039")
    manufactured a spend_limit/transport label the field never carried. This pins the
    standalone-status-code matching (delimited 3-digit tokens only)."""

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_local_cli

    def _cls(stderr: str) -> str:
        return adapter_local_cli._local_cli_nonzero_classification(
            adapter.LocalCliCompleted(("x",), 1, "", stderr)
        )

    # (a) embedded status codes must NOT false-fire -- honest unknown.
    false_fire_cases = (
        ("produced 11429 tokens then exited", "429->spend_limit"),
        ("write failed at byte offset 4529", "529->transport"),
        ("request id 15039 aborted", "503->transport"),
        ("trace 34519 recorded", "451->content_policy"),
        ("counter 24011 rolled", "401->auth"),
    )
    for stderr, why in false_fire_cases:
        observed = _cls(stderr)
        if observed != "unknown":
            raise AdapterUsageMeterError(
                f"numeric-status false-fire: {stderr!r} classified as {observed!r} "
                f"(embedded {why} substring); expected honest unknown"
            )

    # (b) genuine standalone status codes still classify to their label.
    genuine_cases = (
        ("HTTP 429 Too Many Requests", "spend_limit"),
        ("HTTP 401 Unauthorized", "auth"),
        ("HTTP 403 Forbidden", "auth"),
        ("HTTP 503 Service Unavailable", "transport"),
        ("HTTP 529 overloaded upstream", "transport"),
        ("HTTP 451 Unavailable For Legal Reasons", "content_policy"),
    )
    for stderr, expected in genuine_cases:
        observed = _cls(stderr)
        if observed != expected:
            raise AdapterUsageMeterError(
                f"numeric-status miss: genuine {stderr!r} classified as {observed!r}, "
                f"expected {expected!r}"
            )
    return (
        "numeric-status boundary: an HTTP status code embedded inside a larger number "
        "(token count / byte offset / request id) no longer false-fires a "
        "limit/transport/auth/content_policy label, while a genuine standalone "
        "429/401/403/503/529/451 still classifies correctly"
    )


def _assert_claude_throttle_marker_labels() -> str:
    """Pin each claude throttle/limit/overload TEXT marker to its classification label.

    The R4 follow-up added claude-specific text signatures (rate_limit / usage_limit /
    "usage limit" / "too many requests" for spend_limit; overloaded / overloaded_error
    for transport). Removing any of them would silently drop a real throttled/overloaded
    claude death to unknown -- this per-marker fixture makes that removal turn the
    checker RED. Absent any signal the classifier stays honestly unknown."""

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_local_cli

    def _cls(stderr: str) -> str:
        return adapter_local_cli._local_cli_nonzero_classification(
            adapter.LocalCliCompleted(("claude", "-p"), 1, "", stderr)
        )

    cases = (
        ("provider rate_limit hit", "spend_limit"),
        ("usage_limit exhausted for this key", "spend_limit"),
        ("Claude usage limit reached; try again later", "spend_limit"),
        ("too many requests, slow down", "spend_limit"),
        ("the server is overloaded right now", "transport"),
        ("overloaded_error from upstream", "transport"),
    )
    for stderr, expected in cases:
        observed = _cls(stderr)
        if observed != expected:
            raise AdapterUsageMeterError(
                f"claude-marker: {stderr!r} classified as {observed!r}, expected "
                f"{expected!r} (a throttle/overload marker was dropped from the "
                "decision table)"
            )
    # HONEST-UNKNOWN: a death with no throttle/transport/auth/policy signal stays
    # unknown (never a fabricated label).
    if _cls("the operation could not be completed") != "unknown":
        raise AdapterUsageMeterError(
            "claude-marker: a no-signal death was labelled instead of honest unknown"
        )
    return (
        "claude-marker: each claude throttle/limit marker (rate_limit / usage_limit / "
        "usage limit / too many requests -> spend_limit) and overload marker "
        "(overloaded / overloaded_error -> transport) classifies to its label; a "
        "no-signal death stays honestly unknown"
    )


def _assert_mutation_red_numeric_substring_false_fire() -> str:
    """Mutation RED: the OLD bare-substring status matcher WOULD false-fire on a status
    code embedded in a larger number (proves _assert_numeric_status_code_boundary is
    not vacuously green). Reconstructs the old ``"429" in field`` shape and confirms it
    misclassifies a token-count field the standalone matcher now leaves unknown."""

    embedded_field = "produced 11429 tokens then exited"

    # OLD shape: bare-substring membership (what the fix replaced).
    old_bare_substring_fires = "429" in embedded_field
    # NEW shape: standalone 3-digit tokens only.
    from brick_protocol.support.connection import adapter_local_cli

    standalone_tokens = set(
        adapter_local_cli._STANDALONE_STATUS_CODE_RE.findall(embedded_field)
    )
    new_boundary_fires = "429" in standalone_tokens
    if not old_bare_substring_fires:
        raise AdapterUsageMeterError(
            "mutation RED failed: the old bare-substring matcher did NOT fire on the "
            "embedded '429' -- the false-fire it models is not reproduced"
        )
    if new_boundary_fires:
        raise AdapterUsageMeterError(
            "mutation RED failed: the standalone-status matcher STILL matched the "
            "embedded '429' inside '11429' -- the boundary fix is not effective"
        )
    return (
        "mutation RED observed: the old bare-substring matcher fires on an embedded "
        "'429' inside '11429' (a false-fire) while the standalone-status matcher does "
        "not -- the numeric-boundary fix is load-bearing"
    )


def test_behavioral_probe_usage_only_stdout() -> str:
    """Drive the REAL codex invoke path end-to-end and prove usage cannot leak.

    AST pins (test_invoke_local_cli_uses_helper_not_raw_stdout) prove the SHAPE of
    the empty-file fallback. This probe proves the BEHAVIOR: it actually runs the
    codex-exec-readonly branch of ``_invoke_local_cli`` via _invoke_local_cli_adapter
    with a fake command_runner -- NO live codex, NO subprocess -- in the exact
    leak-prone situation:

      * the --output-last-message FILE is left EMPTY (the runner writes nothing);
      * the ``--json`` stdout is USAGE-ONLY: a single turn.completed.usage event
        with NO assistant-message event;
      * the Brick's required_return_shape DECLARES usage-shaped fields
        (input_tokens / usage), so if usage text ever reached the structured
        extractor it WOULD be lifted into AgentFact.returned.

    It then asserts, on the real path's output, that (a) the recovered output text
    is "" (empty file + no message event -> empty, never the raw JSONL), and
    (b) the ``returned`` dict the codex adapter builds (the AgentFact.returned
    source) carries NO usage key -- usage stayed on the adapter_usage side-channel.
    """

    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants
    from brick_protocol.support.connection import adapter_local_cli

    usage_only_stdout = (
        '{"type":"turn.completed","usage":{"input_tokens":4242,'
        '"cached_input_tokens":7,"output_tokens":9,"reasoning_output_tokens":5}}\n'
    )

    def _fake_codex_runner(
        args, cwd, timeout_seconds, *, env=None
    ):  # type: ignore[no-untyped-def]
        del cwd, timeout_seconds, env
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "codex 0.0.0-probe", "")
        # The real exec invocation. REGRESSION GUARD: the meter depends on codex
        # being invoked WITH ``--json`` (so stdout is the JSONL we parse usage from)
        # AND ``--output-last-message <path>`` (so the assistant TEXT comes from the
        # file, not the raw JSONL stdout). If a future refactor drops either flag,
        # the usage-leak protection this probe asserts becomes vacuous -- so fail
        # HERE, at the argv, if the real path stops passing them.
        if "--json" not in call:
            raise AdapterUsageMeterError(
                "behavioral probe: the real codex exec invocation did NOT include "
                f"--json (argv={call!r}); usage parsing depends on --json JSONL stdout"
            )
        if "--output-last-message" not in call:
            raise AdapterUsageMeterError(
                "behavioral probe: the real codex exec invocation did NOT include "
                f"--output-last-message (argv={call!r}); assistant TEXT must come from "
                "the output file, never the raw --json stdout"
            )
        _olm_index = call.index("--output-last-message")
        if _olm_index + 1 >= len(call) or not call[_olm_index + 1].strip():
            raise AdapterUsageMeterError(
                "behavioral probe: --output-last-message was passed with no output "
                f"path argument following it (argv={call!r})"
            )
        # Return rc=0 with USAGE-ONLY JSONL on stdout and DO NOT write the
        # --output-last-message file (it stays empty), reproducing the empty-file +
        # --json situation. (codex still passes --json + the temp output path; we
        # simply never touch that path.)
        return adapter.LocalCliCompleted(call, 0, usage_only_stdout, "")

    request = adapter.AgentAdapterRequest(
        building_id="adapter-usage-behavioral-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-probe",
        next_brick_instance_ref="brick-closure",
        # Declare usage-shaped return fields: if usage text reached the structured
        # extractor it would be lifted into returned. It must NOT be, because the
        # output text is empty.
        required_return_shape="returned_summary, input_tokens, usage",
    )

    # REDO (Smith 0623 struct-surgery): _invoke_local_cli_adapter returns raw
    # side-channel elements alongside the existing 4-tuple; the codex path
    # observes no non-granted gemini tools here.
    (
        returned,
        _proof_limits,
        _not_proven,
        adapter_usage,
        _observed_non_granted_gemini_tools,
        _adapter_raw_observations,
        _adapter_output_text,
    ) = adapter_local_cli._invoke_local_cli_adapter(
        request,
        cwd=_REPO_ROOT,
        timeout_seconds=5,
        command_runner=_fake_codex_runner,
    )

    if not isinstance(returned, Mapping):
        raise AdapterUsageMeterError(
            "behavioral probe: codex adapter did not return a mapping"
        )
    # (a) the real path recovered EMPTY output text from the empty file + usage-only
    # JSONL (no message event) -- never the raw JSONL.
    excerpt = returned.get("output_excerpt")
    if excerpt not in ("", None):
        raise AdapterUsageMeterError(
            "behavioral probe: empty output file + usage-only --json stdout did NOT "
            f"yield empty output text (output_excerpt={excerpt!r}); raw JSONL may be "
            "leaking through the assistant-text fallback"
        )
    for marker in ("turn.completed", '"usage"', "input_tokens", "4242"):
        if isinstance(excerpt, str) and marker in excerpt:
            raise AdapterUsageMeterError(
                f"behavioral probe: output_excerpt leaks raw JSONL marker {marker!r}"
            )
    # (b) NO token-usage key reached AgentFact.returned via structured extraction,
    # even though required_return_shape declared input_tokens / usage.
    leaked = sorted(_FORBIDDEN_RETURNED_USAGE_KEYS & set(returned)) + (
        ["usage"] if "usage" in returned else []
    )
    if leaked:
        raise AdapterUsageMeterError(
            "behavioral probe: token-usage key(s) "
            f"{leaked!r} reached AgentFact.returned via the real codex invoke path "
            "(usage must never leave the adapter_usage side-channel)"
        )
    # The usage MUST still be observed on the side-channel (proves the probe drove a
    # path where usage WAS present -- so the empty-returned result is meaningful, not
    # vacuous because no usage existed).
    if not isinstance(adapter_usage, Mapping) or adapter_usage.get("input_tokens") != 4242:
        raise AdapterUsageMeterError(
            "behavioral probe: the usage-only --json stdout was not surfaced on the "
            "adapter_usage side-channel (input_tokens=4242 expected); the probe did "
            "not actually exercise a usage-present path"
        )
    return (
        "behavioral probe: the REAL codex invoke path (empty output file + usage-"
        "only --json stdout) recovers empty output text and lifts NO usage key into "
        "AgentFact.returned, while usage IS present on the adapter_usage side-channel"
    )


def _assert_mutation_red_behavioral_probe_leak() -> str:
    """Mutation RED: simulate the leak the behavioral probe guards against.

    Reconstructs what the codex adapter ``returned`` dict WOULD contain if the raw
    JSONL stdout were handed to the structured extractor (the OLD raw-stdout
    fallback): the usage-only JSONL parses as a JSON object whose ``input_tokens``
    is a declared return field, so _extract_required_return_fields lifts it INTO
    returned. Confirms the behavioral probe's leak assertion catches that, so the
    probe is not vacuously green.
    """

    from brick_protocol.support.connection import adapter_grant_policy

    leaking_stdout = (
        '{"input_tokens": 4242, "usage": {"input_tokens": 4242}, '
        '"returned_summary": "leaked"}'
    )
    # The OLD bug shape: raw stdout flows into the structured extractor.
    extracted = adapter_grant_policy._extract_required_return_fields(
        leaking_stdout,
        "returned_summary, input_tokens, usage",
    )
    leaked = sorted(_FORBIDDEN_RETURNED_USAGE_KEYS & set(extracted)) + (
        ["usage"] if "usage" in extracted else []
    )
    if not leaked:
        raise AdapterUsageMeterError(
            "mutation RED failed: a raw-stdout structured extraction that lifts "
            "input_tokens/usage into returned was not detected as a leak"
        )
    return (
        "mutation RED observed: when raw --json stdout reaches the structured "
        "extractor, declared usage fields (input_tokens/usage) ARE lifted into "
        "returned -- exactly the leak the behavioral probe rejects"
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


def _assert_dynamic_walker_dispatch_timing_persisted(repo: Path) -> str:
    """Fan-out latency evidence must come from live node dispatch, not drain time.

    The dynamic walker defers fan-out step-output writes, so recorded_at can only
    describe the later drain/write moment. This static probe pins the support-only
    repair: the walker captures a live dispatch timing side-channel and persists
    it to both raw/adapter-usage.jsonl and the step-output projection after the
    deferred write closes. The timing must stay outside AgentFact.returned.
    """

    path = repo / _WALKER_KERNEL_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterUsageMeterError(f"could not read {_WALKER_KERNEL_REL}: {exc}") from exc
    required = (
        "adapter_dispatch_timing",
        "_adapter_dispatch_timing_record",
        "_record_adapter_dispatch_timing_evidence",
        "time.perf_counter",
        "raw/adapter-usage.jsonl",
        "adapter-dispatch-timing",
        "_step_output_manifest_ref",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise AdapterUsageMeterError(
            f"{_WALKER_KERNEL_REL}: dynamic fan-out dispatch timing is not persisted; "
            f"missing marker(s) {missing!r}. Deferred fan-out step-output recorded_at "
            "would still reflect drain/write time rather than the live adapter call."
        )
    if '"adapter_dispatch_timing"' not in text:
        raise AdapterUsageMeterError(
            f"{_WALKER_KERNEL_REL}: step-output enrichment does not carry an "
            "adapter_dispatch_timing object"
        )
    return (
        f"{_WALKER_KERNEL_REL}: dynamic walker records live adapter dispatch timing "
        "as support evidence in raw/adapter-usage.jsonl and step-output projection"
    )


# --------------------------------------------------------------------------- #
# Behavioral: the meter journal is PURE APPEND-ONLY raw evidence.              #
# --------------------------------------------------------------------------- #

# A seed journal mixing well-formed records and a MALFORMED (truncated JSON) line.
# The pure-append writer must leave ALL of these BYTE-FOR-BYTE and in-order; only
# a new line may be added at the very end.
_SEED_JOURNAL_BYTES = b'{"a":1}\n{ broken json with no closing brace\n{"b":2}\n'

# A TRUNCATED-TAIL seed: a journal whose last line was cut off WITHOUT a trailing
# newline. A naive ``open(path,"a")`` write would FUSE the new record onto this
# broken tail (same physical line). The writer must insert a single ``\n``
# separator first so the new record lands on its own line -- still append-only,
# since the separator is an ADDITION and no pre-existing byte is touched.
_SEED_JOURNAL_TRUNCATED_TAIL_BYTES = b"{ broken json with no newline"


def _run_writer_on_seeded_journal(tmp_root: Path, seed: bytes = _SEED_JOURNAL_BYTES) -> bytes:
    from brick_protocol.support.recording.adapter_usage_meter import (
        write_adapter_usage_meter,
    )

    journal = tmp_root / "raw" / "adapter-usage.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_bytes(seed)
    write_adapter_usage_meter(
        tmp_root,
        "building-append-probe",
        step_ref="step:append-probe",
        adapter_ref="adapter:codex-local",
        selected_model_ref="model:codex-fixture",
        attempt_index=1,
        adapter_usage={"input_tokens": 11, "output_tokens": 3},
    )
    return journal.read_bytes()


def _assert_pure_append_preserves_existing_lines() -> str:
    """The writer must APPEND ONE line and leave all prior bytes/order untouched.

    Seeds a journal with two well-formed records and one MALFORMED line, runs the
    real writer, and asserts the result is EXACTLY the original bytes followed by a
    single new JSON-object line. If the writer ever read+separated+re-serialized the
    existing lines (the old rewrite path), the malformed line would move to the
    front and the well-formed lines would be re-emitted in canonical byte form --
    both detected here.
    """

    with tempfile.TemporaryDirectory(prefix="bp-adapter-usage-append-") as tmpdir:
        result = _run_writer_on_seeded_journal(Path(tmpdir))
    if not result.startswith(_SEED_JOURNAL_BYTES):
        raise AdapterUsageMeterError(
            "pure-append violated: the original journal bytes are no longer the "
            "verbatim prefix of the file (existing lines were reordered or "
            "re-serialized instead of left untouched)"
        )
    tail = result[len(_SEED_JOURNAL_BYTES):]
    if not tail.endswith(b"\n"):
        raise AdapterUsageMeterError(
            "pure-append: the appended record line is not newline-terminated"
        )
    tail_text = tail.decode("utf-8").strip()
    if "\n" in tail_text:
        raise AdapterUsageMeterError(
            "pure-append: more than one line was appended"
        )
    import json as _json

    try:
        appended = _json.loads(tail_text)
    except ValueError as exc:
        raise AdapterUsageMeterError(
            f"pure-append: the appended line is not a JSON object: {exc}"
        ) from exc
    if not isinstance(appended, Mapping):
        raise AdapterUsageMeterError(
            "pure-append: the appended line is not a JSON object"
        )
    # TRUNCATED-TAIL case: a seed whose last byte is NOT a newline. The writer must
    # insert a single separator newline so the new record does NOT fuse onto the
    # broken tail -- while still preserving the original bytes verbatim as a prefix.
    with tempfile.TemporaryDirectory(prefix="bp-adapter-usage-append-tt-") as tmpdir:
        tt_result = _run_writer_on_seeded_journal(
            Path(tmpdir), seed=_SEED_JOURNAL_TRUNCATED_TAIL_BYTES
        )
    if not tt_result.startswith(_SEED_JOURNAL_TRUNCATED_TAIL_BYTES):
        raise AdapterUsageMeterError(
            "pure-append (truncated tail): the original (newline-less) journal bytes "
            "are no longer the verbatim prefix of the file"
        )
    tt_lines = [ln for ln in tt_result.split(b"\n") if ln.strip()]
    if len(tt_lines) != 2:
        raise AdapterUsageMeterError(
            "pure-append (truncated tail): expected 2 lines (the broken tail kept on "
            f"its own line + the new record on its own line) but found {len(tt_lines)} "
            "-- the new record FUSED onto the newline-less tail (missing separator)"
        )
    if tt_lines[0] != _SEED_JOURNAL_TRUNCATED_TAIL_BYTES:
        raise AdapterUsageMeterError(
            "pure-append (truncated tail): the original broken tail line was altered "
            f"({tt_lines[0]!r}); existing bytes must be preserved verbatim"
        )
    import json as _json_tt

    try:
        tt_appended = _json_tt.loads(tt_lines[1].decode("utf-8"))
    except ValueError as exc:
        raise AdapterUsageMeterError(
            f"pure-append (truncated tail): the appended line is not valid JSON: {exc}"
        ) from exc
    if not isinstance(tt_appended, Mapping):
        raise AdapterUsageMeterError(
            "pure-append (truncated tail): the appended line is not a JSON object"
        )
    return (
        "pure-append: the writer appends exactly ONE new record line to the END of "
        "the journal; the two well-formed records AND the malformed line keep their "
        "original bytes and order (append-only raw evidence preserved). A truncated "
        "tail (no trailing newline) gets a single separator newline so the new record "
        "lands on its own line (2 lines), still byte-preserving the original tail."
    )


def _assert_mutation_red_pure_append_rewrite() -> str:
    """Mutation RED: a writer that re-serializes/reorders existing lines must fail.

    Simulates the OLD rewrite path (read the journal, split malformed lines to the
    FRONT, re-serialize the parsed records in canonical form) and confirms the
    pure-append byte-preservation assertion above REJECTS it -- so that assertion is
    not vacuously green if the rewrite logic is ever reinstated.
    """

    import json as _json

    def _rewriting_writer(seed: bytes) -> bytes:
        records: list[Mapping[str, object]] = []
        raw_lines: list[str] = []
        for line in seed.decode("utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                value = _json.loads(text)
            except ValueError:
                raw_lines.append(text)
                continue
            if isinstance(value, Mapping):
                records.append(value)
            else:
                raw_lines.append(text)
        # The OLD shape: malformed lines first, then re-serialized records, plus the
        # new record -- i.e. the existing lines are reordered AND rewritten.
        out = "".join(rl + "\n" for rl in raw_lines)
        out += "".join(
            _json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
            for r in (*records, {"new": True})
        )
        return out.encode("utf-8")

    rewritten = _rewriting_writer(_SEED_JOURNAL_BYTES)
    if rewritten.startswith(_SEED_JOURNAL_BYTES):
        raise AdapterUsageMeterError(
            "mutation RED failed: a rewrite that reorders/re-serializes existing "
            "lines was NOT detected (it preserved the original byte prefix by "
            "accident, so the byte-preservation guard is vacuous)"
        )
    return (
        "mutation RED observed: a writer that reads + reorders (malformed-first) + "
        "re-serializes the existing journal lines breaks the verbatim byte prefix "
        "and is rejected by the pure-append guard"
    )


def _assert_mutation_red_truncated_tail_fusion() -> str:
    """Mutation RED: a writer that SKIPS the truncated-tail separator must fail.

    Simulates the naive ``open(path,"a")`` writer (no last-byte check), so a new
    record fuses onto a newline-less tail (yielding ONE physical line). Confirms the
    truncated-tail self-test would REJECT that -- the separator logic is not
    vacuously green.
    """

    import json as _json

    def _no_separator_writer(seed: bytes) -> bytes:
        # Append directly, never inserting a separator -- the bug this guards against.
        new_line = _json.dumps({"new": True}, separators=(",", ":")) + "\n"
        return seed + new_line.encode("utf-8")

    fused = _no_separator_writer(_SEED_JOURNAL_TRUNCATED_TAIL_BYTES)
    fused_lines = [ln for ln in fused.split(b"\n") if ln.strip()]
    if len(fused_lines) != 1:
        raise AdapterUsageMeterError(
            "mutation RED failed: a separator-less append onto a newline-less tail "
            f"did NOT fuse into a single line (found {len(fused_lines)} lines) -- the "
            "truncated-tail self-test would be vacuous"
        )
    return (
        "mutation RED observed: a separator-less append onto a truncated (newline-"
        "less) tail FUSES the new record onto the broken line (1 line), which the "
        "truncated-tail self-test rejects (it requires 2 lines)"
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
        temp_repo = Path(tmpdir) / "repo"
        copied_adapter_path = temp_repo / _ADAPTER_REL
        copied_adapter_path.parent.mkdir(parents=True)
        shutil.copy2(adapter_path, copied_adapter_path)
        source = copied_adapter_path.read_text(encoding="utf-8")
        if target not in source:
            raise AdapterUsageMeterError(
                f"{_ADAPTER_REL}: mutation target helper call is missing; "
                "cannot run mutation-RED probe"
            )
        copied_adapter_path.write_text(
            source.replace(target, replacement, 1),
            encoding="utf-8",
        )
        env = os.environ.copy()
        import_root = str(repo / "brick_protocol/support/import_identity")
        env["PYTHONPATH"] = (
            import_root
            if not env.get("PYTHONPATH")
            else f"{import_root}{os.pathsep}{env['PYTHONPATH']}"
        )
        completed = subprocess.run(
            (
                sys.executable,
                str(repo / "brick_protocol/support/checkers/check_adapter_usage_meter.py"),
                "--repo",
                str(temp_repo),
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
    return (
        "mutation RED observed: replacing the json_active helper fallback with "
        "bare completed.stdout in a temp adapter_local_cli.py copy makes "
        "check_adapter_usage_meter.py exit 1"
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
        _assert_dispatched_model_alias_record(),
        _assert_usage_record_timestamp_and_alias_resolution(),
        _assert_absent_usage_record(),
        _assert_no_forbidden_keys_in_record(),
        _assert_no_usage_in_codex_returned(repo),
        test_invoke_local_cli_uses_helper_not_raw_stdout(repo),
        _assert_step_output_carries_no_usage(repo),
        _assert_dynamic_walker_dispatch_timing_persisted(repo),
        _assert_jsonl_never_becomes_text(),
        _assert_local_cli_nonzero_classification(),
        _assert_claude_obituary_stdout_excerpt(),
        _assert_claude_obituary_edge_cases(),
        _assert_string_error_uuid_scrubbed(),
        _assert_numeric_status_code_boundary(),
        _assert_claude_throttle_marker_labels(),
        test_behavioral_probe_usage_only_stdout(),
        _assert_meter_write_guarded_by_usage_present(repo),
        _assert_pure_append_preserves_existing_lines(),
        _assert_mutation_red_dropped_key(),
        _assert_mutation_red_missing_usage_timestamp_alias(),
        _assert_mutation_red_usage_into_returned(),
        _assert_mutation_red_missing_error_classification(),
        _assert_mutation_red_claude_obituary_excerpt_dropped(),
        _assert_mutation_red_session_identifier_scrub_dropped(),
        _assert_mutation_red_embedded_uuid_mask_dropped(),
        _assert_mutation_red_numeric_substring_false_fire(),
        _assert_mutation_red_behavioral_probe_leak(),
        _assert_mutation_red_jsonl_text_fallback(),
        _assert_mutation_red_pure_append_rewrite(),
        _assert_mutation_red_truncated_tail_fusion(),
        _assert_mutation_red_unguarded_meter_write(),
        PROOF_LIMIT,
    ]
    return [
        "adapter-usage meter green: per-step codex token usage is recorded as a "
        "support fact in raw/adapter-usage.jsonl with allowlisted keys (an absent "
        "individual counter is null WITHIN a row); a step with absent/empty usage "
        "writes NO meter row at all (the meter only records steps that emitted "
        "usage), and usage never leaks into AgentFact.returned or any Link field.",
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
            "temporarily mutate a temp adapter_local_cli.py copy to the raw stdout "
            "fallback and assert this checker exits RED"
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
