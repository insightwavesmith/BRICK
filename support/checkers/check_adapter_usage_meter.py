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
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-probe",
        next_brick_instance_ref="brick-closure",
        # Declare usage-shaped return fields: if usage text reached the structured
        # extractor it would be lifted into returned. It must NOT be, because the
        # output text is empty.
        required_return_shape="returned_summary, input_tokens, usage",
    )

    returned, _proof_limits, _not_proven, adapter_usage = adapter._invoke_local_cli_adapter(
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

    from brick_protocol.support.connection import agent_adapter as adapter

    leaking_stdout = (
        '{"input_tokens": 4242, "usage": {"input_tokens": 4242}, '
        '"returned_summary": "leaked"}'
    )
    # The OLD bug shape: raw stdout flows into the structured extractor.
    extracted = adapter._extract_required_return_fields(
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
        test_behavioral_probe_usage_only_stdout(),
        _assert_meter_write_guarded_by_usage_present(repo),
        _assert_pure_append_preserves_existing_lines(),
        _assert_mutation_red_dropped_key(),
        _assert_mutation_red_usage_into_returned(),
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
