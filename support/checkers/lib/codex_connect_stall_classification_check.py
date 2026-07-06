"""codex_connect_stall_classification checker-lib leaf.

Support checker mechanics only. This module observes mocked Codex stall
classification; it authors no axis crossing and decides no Movement, success,
or quality.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


def run_codex_connect_stall_classification(repo: Path) -> KernelResult:
    """CONNECT-STALL CLASSIFICATION (TrackB 0619): pin the dead-worker label split.

    Two diseases are never conflated. This checker pins ONLY the connect-stall
    (DEAD worker: process alive, 0 children, 0 established sockets, cpu_seconds
    frozen) path -- NOT token-amplification (a LIVE worker re-reading a transcript).

    FIREs, IN-PROCESS with mock fixtures only (NO live provider CLI, NO 20-min wait):
      (A) the stall watchdog DEFAULT threshold sits inside the 90-180s fast-fail
          band, the BRICK_CODEX_STALL_THRESHOLD_SECONDS env override still wins, and
          the NaN / negative / zero guards still reject bad env values.
      (B) a dead-connection signature classifies as a stall WITHIN the threshold (a
          fast clock + fast watchdog config, no real sleep): the raised
          TimeoutExpired is tagged reap_reason == "stall" and
          run._adapter_error_kind maps it to the DISTINCT 'local_cli_connect_stall'.
      (C) a PLAIN TimeoutExpired (no stall tag) still maps to 'local_cli_timeout'.
      (D) BOTH kinds route to the SAME adapter-error HOLD seam (label split, not a
          new lifecycle) and there is NO auto-retry / scheduler surface.
      (E) the reap journal carries the last health-sample triple (child_count,
          established_socket_count, cpu_seconds) + dead_signature_seconds as SUPPORT
          FACTS ONLY (no fault label, no Movement decision).

    Mutation-RED: re-flatten run._adapter_error_kind so a stall maps back to
    'local_cli_timeout' (or restore the ~20-min default threshold) and this check
    goes RED without invoking any live provider CLI.
    """
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    adapter_local_cli = importlib.import_module("brick_protocol.support.connection.adapter_local_cli")
    adapter_subprocess = importlib.import_module("brick_protocol.support.connection.adapter_subprocess")
    run_module = importlib.import_module("brick_protocol.support.operator.run")
    walker_resume = importlib.import_module("brick_protocol.support.operator.walker_resume")
    inspected = 0

    # (A) DEFAULT threshold inside the 90-180s connect-stall fast-fail band.
    default_threshold = adapter_subprocess._CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS
    if not (90 <= default_threshold <= 180):
        raise ProfileError(
            "codex_connect_stall_classification A: default stall threshold "
            f"{default_threshold!r} is outside the 90-180s fast-fail band"
        )
    # env override still wins (a parseable value replaces the default).
    override_seconds = 137.0
    prior_env = os.environ.get(adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV)
    try:
        os.environ[adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV] = str(override_seconds)
        override_config = adapter_subprocess._codex_stall_watchdog_config(timeout_seconds=600)
        if override_config is None or override_config.threshold_seconds != override_seconds:
            raise ProfileError(
                "codex_connect_stall_classification A: env override did not replace "
                "the default stall threshold"
            )
        # NaN / inf / negative / ZERO guards reject bad env values. A bad env value
        # must NOT yield the env number itself; it falls back to the (clamped)
        # default. At timeout=600 the default clamps to 150, so a rejected env still
        # yields the 150 default -- never (0.0, 30.0) or a negative band. F2: 0 is in
        # this set (the <= 0 guard, not a strict < 0 guard, is what rejects it).
        for bad_value in ("nan", "inf", "-5", "0"):
            os.environ[adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV] = bad_value
            bad_config = adapter_subprocess._codex_stall_watchdog_config(timeout_seconds=600)
            if bad_config is None or bad_config.threshold_seconds != float(
                adapter_subprocess._CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS
            ):
                raise ProfileError(
                    "codex_connect_stall_classification A: stall watchdog guard did "
                    f"not fall back to the 150s default for bad env threshold {bad_value!r} "
                    f"(got {bad_config!r})"
                )
    finally:
        if prior_env is None:
            os.environ.pop(adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV, None)
        else:
            os.environ[adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV] = prior_env
    inspected += 1

    class _DeadCodexProc:
        pid = 982451653
        returncode: int | None = None

        def __init__(self, clock_state: dict[str, float]) -> None:
            self.clock_state = clock_state
            self.communicate_timeouts: list[float] = []

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, *, timeout: float) -> tuple[str, str]:
            self.communicate_timeouts.append(float(timeout))
            self.clock_state["now"] += float(timeout)
            raise subprocess.TimeoutExpired(cmd=("codex", "exec"), timeout=timeout)

    # (A2) PRODUCTION DEFAULT (codex-review F3): the real blocker is the 120s default
    # adapter_timeout_seconds (driver.py / run.py), NOT the 3600 used below. At 3600
    # the 150s threshold trivially fits, hiding the inversion. Here we pin the default
    # timeout directly. NO live CLI / NO real wait -- the watchdog runs on an injected
    # fast clock; the mock proc advances that clock instead of sleeping.
    prod_env = os.environ.get(adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV)
    prod_poll_env = os.environ.get(adapter_subprocess._CODEX_STALL_WATCHDOG_POLL_ENV)
    os.environ.pop(adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV, None)
    os.environ.pop(adapter_subprocess._CODEX_STALL_WATCHDOG_POLL_ENV, None)
    try:
        # (a) the EFFECTIVE threshold at the 120s default is STRICTLY LESS THAN 120,
        # so the watchdog fires BEFORE the adapter deadline (no plain untagged
        # TimeoutExpired beats it to the punch).
        prod_default_timeout = 120
        prod_config = adapter_subprocess._codex_stall_watchdog_config(timeout_seconds=prod_default_timeout)
        if prod_config is None:
            raise ProfileError(
                "codex_connect_stall_classification A2: watchdog is OFF at the 120s "
                "production default timeout (dead code -- a connect-stall mislabels)"
            )
        if not (prod_config.threshold_seconds < prod_default_timeout):
            raise ProfileError(
                "codex_connect_stall_classification A2: effective stall threshold "
                f"{prod_config.threshold_seconds!r} is NOT strictly less than the 120s "
                "adapter deadline -- the watchdog can never fire before the plain timeout"
            )
        # non-finite timeouts (NaN/inf) must be REJECTED, not silently activated
        # (codex re-review): a bare <=0 timeout guard lets NaN through.
        for bad_timeout in (float("nan"), float("inf")):
            if adapter_subprocess._codex_stall_watchdog_config(timeout_seconds=bad_timeout) is not None:
                raise ProfileError(
                    "codex_connect_stall_classification A2: non-finite timeout "
                    f"{bad_timeout!r} was not rejected by the watchdog config"
                )
        # (b) a dead-connection signature AT the 120s default still classifies as a
        # stall and run._adapter_error_kind maps it to local_cli_connect_stall.
        prod_clock = {"now": 0.0}
        prod_proc = _DeadCodexProc(prod_clock)
        prod_health = adapter_subprocess._CodexCliHealth(
            process_running=True,
            child_count=0,
            established_socket_count=0,
            cpu_seconds=7.0,
        )
        prod_stall_exc: subprocess.TimeoutExpired | None = None
        try:
            adapter_subprocess._communicate_with_optional_codex_stall_watchdog(
                prod_proc,
                ("codex", "exec", "--output-last-message", "/tmp/ignored", "prompt"),
                timeout_seconds=prod_default_timeout,
                # NO watchdog_config injection (codex re-review): exercise the exact
                # production path where _communicate computes the config INTERNALLY
                # from timeout_seconds=120 -- proving the real wiring, not just the
                # arithmetic already pinned in (a) above.
                health_probe=lambda proc: prod_health,
                clock=lambda: prod_clock["now"],
            )
        except subprocess.TimeoutExpired as exc:
            prod_stall_exc = exc
        if prod_stall_exc is None:
            raise ProfileError(
                "codex_connect_stall_classification A2: dead-connection watchdog did "
                "not fire at the 120s production default timeout"
            )
        if prod_clock["now"] >= prod_default_timeout:
            raise ProfileError(
                "codex_connect_stall_classification A2: dead-connection did not "
                "fast-fail BEFORE the 120s adapter deadline (it ran to the full timeout)"
            )
        if adapter_subprocess._timeout_expired_reap_reason(prod_stall_exc) != "stall":
            raise ProfileError(
                "codex_connect_stall_classification A2: dead-connection timeout at the "
                "120s default was not tagged reap_reason == 'stall'"
            )
        if run_module._adapter_error_kind(prod_stall_exc) != "local_cli_connect_stall":
            raise ProfileError(
                "codex_connect_stall_classification A2: a dead-connection at the 120s "
                "production default did NOT map to local_cli_connect_stall"
            )
    finally:
        if prod_env is None:
            os.environ.pop(adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV, None)
        else:
            os.environ[adapter_subprocess._CODEX_STALL_WATCHDOG_THRESHOLD_ENV] = prod_env
        if prod_poll_env is None:
            os.environ.pop(adapter_subprocess._CODEX_STALL_WATCHDOG_POLL_ENV, None)
        else:
            os.environ[adapter_subprocess._CODEX_STALL_WATCHDOG_POLL_ENV] = prod_poll_env
    inspected += 1

    # (B) a dead-connection signature classifies WITHIN the threshold (fast clock +
    # fast watchdog config: no real 20-min sleep). The watchdog raises a stall-tagged
    # TimeoutExpired and run._adapter_error_kind maps it to local_cli_connect_stall.
    fast_config = adapter_subprocess._CodexStallWatchdogConfig(threshold_seconds=0.2, poll_seconds=0.1)
    dead_clock = {"now": 0.0}
    dead_proc = _DeadCodexProc(dead_clock)
    dead_health = adapter_subprocess._CodexCliHealth(
        process_running=True,
        child_count=0,
        established_socket_count=0,
        cpu_seconds=42.0,
    )

    stall_exc: subprocess.TimeoutExpired | None = None
    try:
        adapter_subprocess._communicate_with_optional_codex_stall_watchdog(
            dead_proc,
            ("codex", "exec", "--output-last-message", "/tmp/ignored", "prompt"),
            timeout_seconds=3600,
            watchdog_config=fast_config,
            health_probe=lambda proc: dead_health,
            clock=lambda: dead_clock["now"],
        )
    except subprocess.TimeoutExpired as exc:
        stall_exc = exc
    if stall_exc is None:
        raise ProfileError(
            "codex_connect_stall_classification B: dead-connection watchdog did not fire"
        )
    if dead_clock["now"] >= 3600:
        raise ProfileError(
            "codex_connect_stall_classification B: dead-connection did not fast-fail "
            "WITHIN the threshold (it waited until the full adapter timeout)"
        )
    if adapter_subprocess._timeout_expired_reap_reason(stall_exc) != "stall":
        raise ProfileError(
            "codex_connect_stall_classification B: dead-connection timeout was not "
            "tagged reap_reason == 'stall'"
        )
    if run_module._adapter_error_kind(stall_exc) != "local_cli_connect_stall":
        raise ProfileError(
            "codex_connect_stall_classification B: a stall-tagged timeout did NOT map "
            "to the distinct 'local_cli_connect_stall' kind (the un-flatten regressed)"
        )
    inspected += 1

    # (C) a PLAIN TimeoutExpired (no stall tag) still maps to local_cli_timeout.
    plain_exc = subprocess.TimeoutExpired(cmd=("codex", "exec"), timeout=5)
    if adapter_subprocess._timeout_expired_reap_reason(plain_exc) != "timeout":
        raise ProfileError(
            "codex_connect_stall_classification C: an untagged timeout was mis-read "
            "as a stall"
        )
    if run_module._adapter_error_kind(plain_exc) != "local_cli_timeout":
        raise ProfileError(
            "codex_connect_stall_classification C: a plain timeout no longer maps to "
            "'local_cli_timeout'"
        )
    inspected += 1

    # (D) BOTH kinds route to the SAME adapter-error HOLD seam (label split, not a new
    # lifecycle). The error_kind only labels the carried mapping; the hold_reason is
    # identical, so the resume HOLD seam recognizes the frontier for both.
    stall_mapping = run_module._adapter_error_mapping(stall_exc)
    timeout_mapping = run_module._adapter_error_mapping(plain_exc)
    if stall_mapping.get("error_kind") != "local_cli_connect_stall":
        raise ProfileError(
            "codex_connect_stall_classification D: stall mapping lost its connect-stall label"
        )
    if timeout_mapping.get("error_kind") != "local_cli_timeout":
        raise ProfileError(
            "codex_connect_stall_classification D: timeout mapping lost its timeout label"
        )
    hold_record = {"hold_reason": "adapter_error_frontier"}
    if not walker_resume._adapter_error_hold_without_return(hold_record):
        raise ProfileError(
            "codex_connect_stall_classification D: adapter-error HOLD seam no longer "
            "recognizes the frontier both kinds route to"
        )
    # NO auto-retry / queue / scheduler surface in either mapping.
    for mapping in (stall_mapping, timeout_mapping):
        flat = json.dumps(mapping).lower()
        for forbidden in ("retry", "schedule", "requeue", "re-fire", "refire"):
            if forbidden in flat:
                raise ProfileError(
                    "codex_connect_stall_classification D: adapter-error mapping leaked "
                    f"an auto-retry/scheduler token {forbidden!r} (no-scheduler invariant)"
                )
    inspected += 1

    # (E) reap journal carries the last health triple + dead_signature_seconds as
    # SUPPORT FACTS ONLY. Drive the live journal seam (_journal_reap) with the facts a
    # stall reap carries, redirect the journal to a temp file, and read it back.
    signature_facts = adapter_subprocess._timeout_expired_stall_dead_signature(stall_exc)
    if not isinstance(signature_facts, Mapping):
        raise ProfileError(
            "codex_connect_stall_classification E: stall exception did not carry the "
            "dead-signature support facts"
        )
    for key in ("child_count", "established_socket_count", "cpu_seconds", "dead_signature_seconds"):
        if key not in signature_facts:
            raise ProfileError(
                f"codex_connect_stall_classification E: dead-signature facts missing {key!r}"
            )
    if (
        signature_facts["child_count"] != 0
        or signature_facts["established_socket_count"] != 0
        or signature_facts["cpu_seconds"] != 42.0
    ):
        raise ProfileError(
            "codex_connect_stall_classification E: dead-signature triple did not mirror "
            f"the observed health sample: {dict(signature_facts)!r}"
        )

    class _ReapProc:
        pid = 982451653
        returncode = -15

        def poll(self) -> int | None:
            return self.returncode

    with tempfile.TemporaryDirectory(prefix="bp-connect-stall-journal-") as tmp:
        journal_path = Path(tmp) / "adapter-spawn-journal.jsonl"
        prior_journal = os.environ.get("BRICK_ADAPTER_SPAWN_JOURNAL_PATH")
        os.environ["BRICK_ADAPTER_SPAWN_JOURNAL_PATH"] = str(journal_path)
        try:
            adapter_subprocess._journal_reap(_ReapProc(), reason="stall", dead_signature=signature_facts)
        finally:
            if prior_journal is None:
                os.environ.pop("BRICK_ADAPTER_SPAWN_JOURNAL_PATH", None)
            else:
                os.environ["BRICK_ADAPTER_SPAWN_JOURNAL_PATH"] = prior_journal
        if not journal_path.is_file():
            raise ProfileError(
                "codex_connect_stall_classification E: reap journal was not written"
            )
        records = [
            json.loads(line)
            for line in journal_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    reap_records = [r for r in records if r.get("event") == "reap" and r.get("reason") == "stall"]
    if not reap_records:
        raise ProfileError(
            "codex_connect_stall_classification E: no stall reap record in the journal"
        )
    journaled = reap_records[-1].get("dead_signature")
    if not isinstance(journaled, Mapping):
        raise ProfileError(
            "codex_connect_stall_classification E: stall reap record carried no "
            "dead_signature support facts"
        )
    if (
        journaled.get("child_count") != 0
        or journaled.get("established_socket_count") != 0
        or journaled.get("cpu_seconds") != 42.0
        or "dead_signature_seconds" not in journaled
    ):
        raise ProfileError(
            "codex_connect_stall_classification E: journaled dead_signature did not "
            f"carry the health triple + duration: {dict(journaled)!r}"
        )
    inspected += 1

    # (F) content-policy exits are a distinct adapter-error label and preserve the
    # provider sentence from JSONL stdout even when stderr carries unrelated noise.
    content_policy_sentence = "Request blocked by content policy (451)."
    jsonl_stdout = "\n".join(
        (
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "error", "error": {"message": content_policy_sentence}}),
        )
    )
    turn_failed_stdout = json.dumps(
        {"type": "turn.failed", "error": {"message": content_policy_sentence}}
    )
    noisy_stderr = "warning: unrelated client noise before useful provider JSON"
    for label, stdout in (("error-event", jsonl_stdout), ("turn-failed", turn_failed_stdout)):
        completed = adapter.LocalCliCompleted(
            args=("codex", "exec", "--json"),
            return_code=1,
            stdout=stdout,
            stderr=noisy_stderr,
        )
        if adapter_local_cli._local_cli_nonzero_classification(completed) != "content_policy":
            raise ProfileError(
                "codex_connect_stall_classification F: "
                f"{label} stdout did not classify as content_policy"
            )
        excerpt = adapter_local_cli._stdout_error_excerpt(stdout)
        if content_policy_sentence not in excerpt:
            raise ProfileError(
                "codex_connect_stall_classification F: "
                f"{label} stdout did not preserve provider content-policy sentence"
            )
        request = adapter.AgentAdapterRequest(
            building_id="content-policy-classification-probe",
            agent_object_ref="agent-object:dev",
            adapter_ref="adapter:codex-local",
            brick_instance_ref="brick-work",
            next_brick_instance_ref="brick-closure",
            casting={"selected_model_ref": "model:codex:default"},
        )
        message = adapter_local_cli._local_cli_nonzero_error_message(
            request,
            adapter._LOCAL_CLI_SPECS["adapter:codex-local"],
            completed,
        )
        if message.find("stdout_error_excerpt=") < 0 or message.find(
            "stdout_error_excerpt="
        ) > message.find("stderr_excerpt="):
            raise ProfileError(
                "codex_connect_stall_classification F: provider stdout error did "
                "not precede noisy stderr in message_excerpt source text"
            )
        if run_module._adapter_error_kind(ValueError(message)) != "content_policy":
            raise ProfileError(
                "codex_connect_stall_classification F: adapter error kind did not "
                "map nonzero content-policy classification to content_policy"
            )
    removed_signature = adapter_local_cli._content_policy_signature_present
    try:
        adapter_local_cli._content_policy_signature_present = lambda _text: False
        mutated = adapter.LocalCliCompleted(
            args=("codex", "exec", "--json"),
            return_code=1,
            stdout=jsonl_stdout,
            stderr=noisy_stderr,
        )
        if adapter_local_cli._local_cli_nonzero_classification(mutated) == "content_policy":
            raise ProfileError(
                "codex_connect_stall_classification F mutation-RED: removing the "
                "content-policy signature detector did not change classification"
            )
    finally:
        adapter_local_cli._content_policy_signature_present = removed_signature
    inspected += 1

    return KernelResult(
        check_id="codex_connect_stall_classification",
        inspected=inspected,
        output=(
            "codex connect-stall classification passed: default stall threshold sits "
            f"in the 90-180s fast-fail band ({default_threshold}s), env override wins, "
            "NaN/negative/zero guards hold; a dead-connection signature fast-fails "
            "WITHIN the threshold and maps to the distinct local_cli_connect_stall "
            "kind while a plain timeout stays local_cli_timeout; both route to the same "
            "adapter_error_frontier HOLD with NO auto-retry/scheduler token; and the "
            "reap journal carries the last health triple + dead_signature_seconds as "
            "support facts only; content-policy JSONL stdout classifies as "
            "content_policy with the provider sentence ahead of noisy stderr and a "
            f"mutation-RED detector-removal probe fired -- NO live provider CLI ({inspected} group(s) inspected)."
        ),
    )
