"""Single Agent brain connection support surface for SIMPLE-RUN-0.

Agent Adapter connects an Agent Object to an admitted brain surface. It is
support mechanics only: it does not own Agent meaning, choose Link Movement,
create default GateFacts, judge success or quality, store credentials, or run
tools/hooks.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import ALWAYS_SECRET_KEYS as _ALWAYS_SECRET_KEYS
from brick_protocol.agent.return_fact import TOP_LEVEL_VERDICT_KEYS as _TOP_LEVEL_VERDICT_KEYS
from brick_protocol.agent.return_fact import TRANSITION_CONCERN_ALLOWED_KEYS as _TRANSITION_CONCERN_ALLOWED_KEYS
from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS as _TRANSITION_CONCERN_KINDS
from brick_protocol.brick.work import parse_required_return_shape


ADAPTER_LOCAL = "adapter:local"
ADAPTER_CODEX_LOCAL = "adapter:codex-local"
ADAPTER_CLAUDE_LOCAL = "adapter:claude-local"
ADAPTER_GEMINI_LOCAL = "adapter:gemini-local"
ADAPTER_GEMINI_API = "adapter:gemini-api"
ADAPTER_CHAT_SESSION = "adapter:chat-session"
READ_WRITE_TOOL_POLICY_REF = "tool-policy:read-write-scoped"
REVIEWER_READONLY_TOOL_POLICY_REF = "tool-policy:reviewer-readonly"
LEADER_COORDINATION_TOOL_POLICY_REF = "tool-policy:leader-coordination"
READ_ONLY_TOOL_POLICY_REFS = frozenset(
    {
        REVIEWER_READONLY_TOOL_POLICY_REF,
        LEADER_COORDINATION_TOOL_POLICY_REF,
    }
)
KNOWN_TOOL_POLICY_REFS = READ_ONLY_TOOL_POLICY_REFS | frozenset({READ_WRITE_TOOL_POLICY_REF})
ADAPTER_CAPABILITY_READ = "read"
ADAPTER_CAPABILITY_WRITE = "write"
ADAPTER_CAPABILITY_REVIEW = "review"
ADAPTER_CAPABILITY_LITERALS = frozenset(
    {
        ADAPTER_CAPABILITY_READ,
        ADAPTER_CAPABILITY_WRITE,
        ADAPTER_CAPABILITY_REVIEW,
    }
)
MODEL_REF_DEFAULT = "model:default"
MODEL_REF_CODEX_DEFAULT = "model:codex:default"
MODEL_REF_CLAUDE_INHERIT = "model:claude:inherit"
MODEL_REF_GEMINI_DEFAULT = "model:gemini:default"
MODEL_REF_GEMINI_FLASH = "model:gemini:gemini-2.5-flash"
MODEL_REF_GEMINI_LOCAL_FLASH = "model:gemini:gemini-3.5-flash"
MODEL_PROVIDER_BY_ADAPTER = {
    ADAPTER_CODEX_LOCAL: "codex",
    ADAPTER_CLAUDE_LOCAL: "claude",
    ADAPTER_GEMINI_LOCAL: "gemini",
    ADAPTER_GEMINI_API: "gemini",
}
_RETIRED_WRITE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
    }
)
_OBSERVED_WRITE_ADAPTER_REFS = frozenset({ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL})
_EFFECTIVE_WRITE_OBSERVATION_MARKER_ATTR = "_brick_protocol_effective_write_observed_cwd"
ALLOWED_SESSION_CONTINUITY_MODES = frozenset(
    {
        "none",
        "continue_if_available",
        "start_or_continue",
        "fork_from_available",
    }
)

ALLOWED_ADAPTER_REFS = frozenset(
    {
        ADAPTER_LOCAL,
        ADAPTER_CODEX_LOCAL,
        ADAPTER_CLAUDE_LOCAL,
        ADAPTER_GEMINI_LOCAL,
        ADAPTER_GEMINI_API,
        ADAPTER_CHAT_SESSION,
    }
)
_ADAPTER_CAPABILITIES = {
    ADAPTER_LOCAL: frozenset({ADAPTER_CAPABILITY_READ}),
    ADAPTER_CODEX_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    ADAPTER_CLAUDE_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    ADAPTER_GEMINI_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_REVIEW}),
    # gemini-api is the direct-HTTP sibling of gemini-local: same READ+REVIEW
    # brain capability (review/read, not write). It calls the Gemini HTTP API
    # directly (stdlib urllib, API key from env) and spawns NO subprocess.
    ADAPTER_GEMINI_API: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_REVIEW}),
    ADAPTER_CHAT_SESSION: frozenset({ADAPTER_CAPABILITY_READ}),
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROOF_LIMITS = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_DEFAULT_NOT_PROVEN = (
    "brain surface behavior",
    "credential validity",
    "tool or hook execution",
    "runtime or scheduler behavior",
    "quality of returned work",
)
_CODEX_STALL_WATCHDOG_THRESHOLD_ENV = "BRICK_CODEX_STALL_THRESHOLD_SECONDS"
_CODEX_STALL_WATCHDOG_POLL_ENV = "BRICK_CODEX_STALL_POLL_SECONDS"
# CONNECT-STALL FAST-FAIL (TrackB 0619): a dead-connection codex worker (process
# alive, 0 children, 0 established sockets, cpu_seconds frozen) must be reaped and
# surfaced to a human within the 90-180s band, not after ~20 minutes. The 150s
# default sits inside that band, but the EFFECTIVE threshold is clamped to
# (adapter timeout - 2*poll) so it always fires BEFORE the subprocess deadline with
# room for the 2-sample dead-signature (codex-review F1): at the 120s production
# default the effective threshold is 60s (fires at ~90s, before the 120s deadline).
# BRICK_CODEX_STALL_THRESHOLD_SECONDS still overrides the default but is clamped the
# same way and must be > 0 (NaN/inf/negative/ZERO all rejected -> default; F2). This
# is the DEAD-worker (connect-stall) watchdog ONLY -- it never touches a live worker.
_CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS = 150
_CODEX_STALL_WATCHDOG_DEFAULT_POLL_SECONDS = 30
_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS = 2
_CODEX_STALL_WATCHDOG_SIGTERM_GRACE_SECONDS = 5
_TIMEOUT_REAP_REASON_ATTR = "_brick_protocol_reap_reason"
# SUPPORT FACTS ONLY: raw dead-connection observation carried on a stall
# TimeoutExpired so the reap journal can record the last health-sample triple +
# how long the dead signature persisted. Never an Agent-fault label or a Link
# decision -- just the numbers the watchdog saw at reap time.
_STALL_DEAD_SIGNATURE_ATTR = "_brick_protocol_stall_dead_signature"
_RETURN_LABEL_FIELDS = frozenset(
    {
        "blocked_or_missing_evidence",
        "integration_risks",
        "made_changes",
        "narrowly_proven",
        "no_changes_reason",
        "not_proven",
        "observed_evidence",
        "open_questions",
        "proof_limits",
        "remaining_delta",
        "required_outputs",
        "review_needed",
        "risks",
        "transition_concern_evidence",
        "worker_assignments",
    }
)
_RETURN_LIST_FIELDS = frozenset(
    {
        "blocked_or_missing_evidence",
        "integration_risks",
        "made_changes",
        "narrowly_proven",
        "not_proven",
        "observed_evidence",
        "open_questions",
        "proof_limits",
        "remaining_delta",
        "required_outputs",
        "review_needed",
        "risks",
        "worker_assignments",
    }
)
_RETURN_JSON_FIELDS = frozenset({"transition_concern_evidence"})
_RETURN_WAIVER_FIELDS_BY_REQUIRED = {
    "made_changes": ("no_changes_reason",),
}
from brick_protocol.support.connection.secret_text import (
    RAW_SECRET_PATTERNS as _RAW_SECRET_PATTERNS,
)
_RAW_SESSION_PATTERNS = (
    re.compile(r"\bsess[_-][A-Za-z0-9_-]{12,}\b"),  # sess_ and sess- (OpenAI)
    re.compile(r"\bprovider-session-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bresume-token-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bchatcmpl-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bya29\.[A-Za-z0-9._-]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),
    re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b"),  # Crockford base32 ULID session id
)
_SOURCE_FACT_BODY_LIMIT = 12000
_GEMINI_SOURCE_FACT_BODY_LIMIT = 4000
_CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT = (
    "You are a non-interactive Brick Protocol support evidence reviewer. "
    "Do not use tools, do not call hooks, do not enter or discuss plan-mode "
    "actions such as ExitPlanMode, and do not ask follow-up questions. "
    "Return concise text matching the requested return shape. "
    "Do not claim source truth, success judgment, quality judgment, or Movement authority."
)
_CLAUDE_READ_ONLY_SYSTEM_PROMPT = (
    "You are a non-interactive Brick Protocol support evidence reviewer. "
    "You MAY use only read-only repository tools (Read, Grep, Glob) to inspect "
    "files, diffs, and declared evidence. Do not edit or write files, do not run "
    "git mutations, do not call hooks or provider SDKs, do not use network beyond "
    "the provider itself, do not enter or discuss plan-mode actions such as "
    "ExitPlanMode, and do not ask follow-up questions. Return concise text matching "
    "the requested return shape. Do not claim source truth, success judgment, "
    "quality judgment, or Movement authority."
)
_CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT = (
    "You are a non-interactive Brick Protocol worker agent. "
    "You MAY use only the tools allowed for this run (Read, Grep, Glob, Edit, Write, Bash). "
    "Run Bash only from the adapter cwd for commands that stay inside the Brick-declared "
    "write_scope and local checker/test surface. "
    "Edit files ONLY inside the Brick-declared write_scope.allowed_paths; never edit "
    "write_scope.forbidden_paths, the .git directory, or credential/config files. "
    "Do not call hooks or provider SDKs, do not run git commit or git push, do not access "
    "or print setup tokens, auth bodies, credentials, or raw provider sessions, do not enter "
    "or discuss plan-mode actions, and do not ask follow-up questions. "
    "Return concise text matching the requested return shape. "
    "Do not claim source truth, success judgment, quality judgment, or Movement authority."
)
_GEMINI_NO_TOOL_POLICY = """[[rule]]
toolName = [
  "glob",
  "grep_search",
  "list_directory",
  "read_file",
  "read_many_files",
  "replace",
  "run_shell_command",
  "search_file_content",
  "update_topic",
  "write_file",
  "exit_plan_mode",
]
decision = "deny"
priority = 999
"""

_GEMINI_READ_TOOL_NAMES = frozenset(
    {
        "glob",
        "grep_search",
        "list_directory",
        "read_file",
        "read_many_files",
        "search_file_content",
    }
)
_GEMINI_READONLY_POLICY = """[[rule]]
toolName = [
  "glob",
  "grep_search",
  "list_directory",
  "read_file",
  "read_many_files",
  "search_file_content",
]
decision = "allow"
priority = 998

[[rule]]
toolName = [
  "exit_plan_mode",
  "google_web_search",
  "replace",
  "run_shell_command",
  "update_topic",
  "web_fetch",
  "write_file",
]
decision = "deny"
priority = 999
"""


def adapter_capabilities(adapter_ref: str) -> tuple[str, ...]:
    """Return v1 technical capabilities for an admitted adapter ref."""

    ref = _clean_optional_text("adapter_ref", adapter_ref)
    try:
        capabilities = _ADAPTER_CAPABILITIES[ref]
    except KeyError as exc:
        raise ValueError("adapter_ref is not admitted for ADAPTER-CAPABILITY-REHOME-0") from exc
    return tuple(
        capability
        for capability in (
            ADAPTER_CAPABILITY_READ,
            ADAPTER_CAPABILITY_WRITE,
            ADAPTER_CAPABILITY_REVIEW,
        )
        if capability in capabilities
    )


def adapter_has_capability(adapter_ref: str, capability: str) -> bool:
    """Check support-side technical capability only; this grants no authority."""

    checked_capability = _clean_optional_text("adapter_capability", capability)
    if checked_capability not in ADAPTER_CAPABILITY_LITERALS:
        raise ValueError("adapter_capability is not admitted for ADAPTER-CAPABILITY-REHOME-0")
    return checked_capability in adapter_capabilities(adapter_ref)


def adapter_is_write_capable(adapter_ref: str) -> bool:
    """Return whether the adapter can technically attempt writes."""

    return adapter_has_capability(adapter_ref, ADAPTER_CAPABILITY_WRITE)


@dataclass(frozen=True)
class AgentAdapterRequest:
    """Input passed to one Agent brain adapter without secret/session bodies."""

    building_id: str
    agent_object_ref: str
    adapter_ref: str
    brick_instance_ref: str
    next_brick_instance_ref: str
    selected_model_ref: str = ""
    callable_ref: str = ""
    prompt_refs: tuple[str, ...] = ()
    skill_refs: tuple[str, ...] = ()
    hook_refs: tuple[str, ...] = ()
    tool_policy_refs: tuple[str, ...] = ()
    discipline_refs: tuple[str, ...] = ()
    input_packet_ref: str = ""
    output_packet_ref: str = ""
    work_statement: str = ""
    comparison_rule: str = ""
    required_return_shape: str = ""
    source_fact_bodies: Mapping[str, str] = field(default_factory=dict)
    link_handoff_refs: Mapping[str, Any] = field(default_factory=dict)
    agent_instruction_packet: Mapping[str, Any] = field(default_factory=dict)
    write_scope: Mapping[str, Any] = field(default_factory=dict)
    building_session_ref: str = ""
    session_scope_ref: str = ""
    session_continuity_mode: str = "none"
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        adapter_ref = _validate_adapter_ref(self.adapter_ref)
        object.__setattr__(self, "adapter_ref", adapter_ref)
        mode = _clean_optional_text("session_continuity_mode", self.session_continuity_mode)
        mode = mode or "none"
        if mode not in ALLOWED_SESSION_CONTINUITY_MODES:
            raise ValueError("session_continuity_mode is not admitted for SESSION-CONTINUITY-0")
        object.__setattr__(self, "session_continuity_mode", mode)
        selected_model_ref = _clean_optional_text("selected_model_ref", self.selected_model_ref)
        selected_model_ref = _normalize_selected_model_ref(adapter_ref, selected_model_ref)
        object.__setattr__(self, "selected_model_ref", selected_model_ref)

        for field_name in (
            "work_statement",
            "comparison_rule",
            "required_return_shape",
            "building_session_ref",
            "session_scope_ref",
        ):
            value = _clean_optional_text(field_name, getattr(self, field_name))
            object.__setattr__(self, field_name, value)
            _reject_forbidden_text(field_name, value)

        if mode != "none" and (not self.building_session_ref or not self.session_scope_ref):
            raise ValueError(
                "continuity modes require provider-neutral building_session_ref and session_scope_ref"
            )

        object.__setattr__(
            self,
            "source_fact_bodies",
            _clean_source_fact_bodies(self.source_fact_bodies),
        )
        object.__setattr__(
            self,
            "link_handoff_refs",
            _clean_link_handoff_refs(self.link_handoff_refs),
        )
        object.__setattr__(
            self,
            "agent_instruction_packet",
            _clean_agent_instruction_packet(
                self.agent_instruction_packet,
                agent_object_ref=self.agent_object_ref,
            ),
        )
        cleaned_write_scope = _clean_write_scope(self.write_scope)
        object.__setattr__(self, "write_scope", cleaned_write_scope)
        if cleaned_write_scope:
            _validate_effective_write_request(self, cleaned_write_scope)


@dataclass(frozen=True)
class AgentAdapterResult:
    """Returned payload from one adapter, before AgentFact collection."""

    request: AgentAdapterRequest
    returned_value: Any
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)
    # TrackA-A1 METER side-channel (SUPPORT FACT only): per-step codex token usage
    # parsed from `codex exec --json`. This rides ALONGSIDE returned_value, never
    # INSIDE it -- the adapter meter writer reads this; AgentFact.returned and the
    # Link facts never see it. None when the adapter emitted no usage. NO quality
    # or fault label is attached.
    adapter_usage: Mapping[str, Any] | None = None


class AgentAdapterParked(RuntimeError):
    """Typed support signal: chat-session work is parked, not invoked."""

    def __init__(self, request: AgentAdapterRequest) -> None:
        super().__init__("chat-session adapter parked work envelope before provider invocation")
        self.request = request
        self.parked_kind = "chat_session_parked"
        self.proof_limits = (
            "chat-session adapter park signal only",
            "no CLI or provider invocation attempted",
            "not Agent returned payload",
            "not AgentFact",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        )
        self.not_proven = (
            "chat session pickup behavior",
            "future submit or resume behavior",
            "semantic correctness of parked work",
            "caller/COO disposition after parked frontier observation",
        )


@dataclass(frozen=True)
class LocalCliSpec:
    """Allowlisted local CLI command shape behind an adapter ref."""

    adapter_ref: str
    brain_surface_ref: str
    executable_name: str
    version_args: tuple[str, ...]
    invocation_args_kind: str
    default_model_ref: str = MODEL_REF_DEFAULT
    proof_limits: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_PROOF_LIMITS)
    not_proven: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_NOT_PROVEN)


@dataclass(frozen=True)
class LocalCliProbe:
    """Redacted local CLI availability evidence."""

    adapter_ref: str
    brain_surface_ref: str
    executable_name: str
    executable_path: str
    version_text: str
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LocalCliCompleted:
    """Small command completion record used before AgentFact collection."""

    args: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    # TrackA-A1 METER (SUPPORT FACT only): per-turn codex token usage parsed from
    # the `codex exec --json` JSONL stdout (last turn.completed.usage), already
    # mapped onto the allowlisted token-counter key names. None means "no usage
    # observed" -- older codex without --json, or no turn.completed event. This
    # field NEVER flows into AgentFact.returned or any Link field; it is a Brick-
    # axis meter input carrying NO quality/fault label.
    adapter_usage: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _CodexStallWatchdogConfig:
    threshold_seconds: float
    poll_seconds: float


@dataclass(frozen=True)
class _CodexCliHealth:
    process_running: bool
    child_count: int
    established_socket_count: int
    cpu_seconds: float


@dataclass(frozen=True)
class _ProcessSnapshotRow:
    ppid: int
    pgid: int
    cpu_seconds: float


AgentBrainCallable = Callable[[AgentAdapterRequest], Any]
CommandRunner = Callable[..., LocalCliCompleted]

_LOCAL_CLI_SPECS: Mapping[str, LocalCliSpec] = {
    ADAPTER_CODEX_LOCAL: LocalCliSpec(
        adapter_ref=ADAPTER_CODEX_LOCAL,
        brain_surface_ref="brain-surface:codex-local-cli",
        executable_name="codex",
        version_args=("--version",),
        invocation_args_kind="codex-exec-readonly",
        default_model_ref=MODEL_REF_CODEX_DEFAULT,
    ),
    ADAPTER_CLAUDE_LOCAL: LocalCliSpec(
        adapter_ref=ADAPTER_CLAUDE_LOCAL,
        brain_surface_ref="brain-surface:claude-code-local-cli",
        executable_name="claude",
        version_args=("--version",),
        invocation_args_kind="claude-plan-json",
        default_model_ref=MODEL_REF_CLAUDE_INHERIT,
    ),
    ADAPTER_GEMINI_LOCAL: LocalCliSpec(
        adapter_ref=ADAPTER_GEMINI_LOCAL,
        brain_surface_ref="brain-surface:gemini-local-cli",
        executable_name="gemini",
        version_args=("--version",),
        invocation_args_kind="gemini-p-json-flash",
        default_model_ref=MODEL_REF_GEMINI_LOCAL_FLASH,
    ),
}

# Gemini HTTP API adapter (gemini-api) — ADDITIVE sibling of the gemini-local
# CLI. It is DELIBERATELY NOT a member of _LOCAL_CLI_SPECS: there is no CLI, no
# subprocess, no executable. We reuse the LocalCliSpec dataclass purely as an
# inert carrier of the same descriptive fields (adapter_ref, brain_surface_ref,
# default_model_ref, proof_limits, not_proven) so the prompt builder and the
# returned-evidence shape mirror the CLI path exactly — keeping the engine
# adapter-agnostic. executable_name/version_args/invocation_args_kind are unused
# on this path (the HTTP call is made directly via stdlib urllib).
_GEMINI_API_SPEC = LocalCliSpec(
    adapter_ref=ADAPTER_GEMINI_API,
    brain_surface_ref="brain-surface:gemini-http-api",
    executable_name="",
    version_args=(),
    invocation_args_kind="gemini-http-generate-content",
    default_model_ref=MODEL_REF_GEMINI_FLASH,
)

# Gemini Generative Language HTTP API (grounded, not guessed):
#   POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent
#   header  x-goog-api-key: <API_KEY>   (key from env, never committed)
#   body    {"contents":[{"parts":[{"text": <prompt>}]}]}
#   text    candidates[0].content.parts[0].text
_GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_API_MODEL_FALLBACK = "gemini-2.5-flash"
# Env var names checked in order (decision 1): GEMINI_API_KEY then GOOGLE_API_KEY.
_GEMINI_API_KEY_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def connect_agent_brain(
    request: AgentAdapterRequest,
    *,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    cwd: Path | str | None = None,
    timeout_seconds: int = 120,
) -> AgentAdapterResult:
    """Connect one Agent Object request to its selected brain adapter."""

    if not isinstance(request, AgentAdapterRequest):
        raise TypeError("request must be AgentAdapterRequest")
    if request.adapter_ref not in ALLOWED_ADAPTER_REFS:
        raise ValueError("adapter_ref is not admitted for SIMPLE-RUN-0")
    if request.adapter_ref == ADAPTER_CHAT_SESSION:
        raise AgentAdapterParked(request)
    dispatch_cwd = Path(cwd) if cwd is not None else _REPO_ROOT
    _consume_effective_write_observation_path(request, cwd=dispatch_cwd)
    # TrackA-A1 METER: only the local-CLI codex path emits token usage today. The
    # local-callable and gemini-api paths carry no per-turn usage, so it stays None.
    adapter_usage: Mapping[str, Any] | None = None
    if request.adapter_ref == ADAPTER_LOCAL:
        returned_value = _invoke_local_callable(request, local_callables)
        proof_limits = _merge_texts(_DEFAULT_PROOF_LIMITS, request.proof_limits)
        not_proven = _merge_texts(_DEFAULT_NOT_PROVEN, request.not_proven)
    elif request.adapter_ref == ADAPTER_GEMINI_API:
        returned_value, proof_limits, not_proven = _invoke_gemini_api(
            request,
            timeout_seconds=timeout_seconds,
        )
    else:
        returned_value, proof_limits, not_proven, adapter_usage = _invoke_local_cli_adapter(
            request,
            cwd=dispatch_cwd,
            timeout_seconds=timeout_seconds,
            command_runner=command_runner,
        )
    _validate_returned_payload("returned_value", returned_value)
    return AgentAdapterResult(
        request=request,
        returned_value=returned_value,
        proof_limits=proof_limits,
        not_proven=not_proven,
        adapter_usage=adapter_usage,
    )


def local_cli_adapter_refs() -> tuple[str, ...]:
    """Return the allowlisted local CLI adapter refs."""

    return tuple(_LOCAL_CLI_SPECS)


def supported_model_ref_examples(adapter_ref: str) -> tuple[str, ...]:
    """Return documented model ref examples for an adapter.

    Model availability is provider/local-app state. These refs describe the
    admitted selection grammar only and are not availability proof.
    """

    if adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError("adapter_ref is retired and not admitted as an active adapter")
    if adapter_ref == ADAPTER_CODEX_LOCAL:
        return (
            MODEL_REF_CODEX_DEFAULT,
            "model:codex:<codex-cli-model-name>",
        )
    if adapter_ref == ADAPTER_CLAUDE_LOCAL:
        return (
            MODEL_REF_CLAUDE_INHERIT,
            "model:claude:sonnet",
            "model:claude:opus",
            "model:claude:haiku",
            "model:claude:<claude-model-id>",
        )
    if adapter_ref == ADAPTER_GEMINI_LOCAL:
        return (
            MODEL_REF_GEMINI_DEFAULT,
            MODEL_REF_GEMINI_LOCAL_FLASH,
            "model:gemini:<gemini-model-id>",
        )
    if adapter_ref == ADAPTER_GEMINI_API:
        return (
            MODEL_REF_GEMINI_DEFAULT,
            MODEL_REF_GEMINI_FLASH,
            "model:gemini:<gemini-model-id>",
        )
    if adapter_ref == ADAPTER_CHAT_SESSION:
        return (MODEL_REF_DEFAULT,)
    return (MODEL_REF_DEFAULT,)


def agent_request_effective_write(request: AgentAdapterRequest) -> bool:
    """Return whether this adapter request opens observed workspace write."""

    if not isinstance(request, AgentAdapterRequest):
        raise TypeError("request must be AgentAdapterRequest")
    return (
        bool(request.write_scope)
        and READ_WRITE_TOOL_POLICY_REF in request.tool_policy_refs
        and _adapter_ref_supports_observed_write(request.adapter_ref)
    )


def agent_request_read_tier(request: AgentAdapterRequest) -> bool:
    """Return whether this non-write request admits read-only repo inspection.

    Read/write tier is NOT a support-side authority over the tool-policy label.
    The uniform rule across codex-local/claude-local/gemini-local is: if the
    request does not open observed workspace write AND it carries a known,
    tool-bearing Agent policy (every ref in KNOWN_TOOL_POLICY_REFS, at least
    one present), the adapter opens the read-only browse tier -- regardless of
    which read/write policy label it is. A read-only Brick paired with a
    tool-capable Agent therefore browses read-only. Effective-write requests
    still take the write path (early return). Ambiguous requests -- no tool
    policy, or any unknown policy ref -- fail closed to the none tier. Only
    codex/claude/gemini local adapters can reach the read tier.
    """

    if not isinstance(request, AgentAdapterRequest):
        raise TypeError("request must be AgentAdapterRequest")
    if agent_request_effective_write(request):
        return False
    tool_policy_refs = set(request.tool_policy_refs)
    if not tool_policy_refs:
        return False
    if any(ref not in KNOWN_TOOL_POLICY_REFS for ref in tool_policy_refs):
        return False
    return request.adapter_ref in {ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL, ADAPTER_GEMINI_LOCAL}


def _read_tier_policy_refs_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    if request.adapter_ref == ADAPTER_GEMINI_LOCAL:
        return KNOWN_TOOL_POLICY_REFS
    return READ_ONLY_TOOL_POLICY_REFS


def project_model_ref_to_cli_arg(adapter_ref: str, selected_model_ref: str = "") -> str:
    """Project a selected_model_ref to the local CLI model argument.

    This is support projection only. It does not prove provider availability or
    model quality.
    """

    if adapter_ref == ADAPTER_LOCAL:
        _normalize_selected_model_ref(adapter_ref, selected_model_ref)
        return ""
    if adapter_ref == ADAPTER_CHAT_SESSION:
        _normalize_selected_model_ref(adapter_ref, selected_model_ref)
        return ""
    spec = _local_cli_spec(adapter_ref)
    normalized = _normalize_selected_model_ref(adapter_ref, selected_model_ref)
    return _model_cli_arg_from_ref(normalized, spec)


def probe_local_cli_adapter(
    adapter_ref: str,
    *,
    timeout_seconds: int = 10,
    command_runner: CommandRunner | None = None,
) -> LocalCliProbe:
    """Detect a local CLI and collect redacted version evidence."""

    spec = _local_cli_spec(adapter_ref)
    executable_path = spec.executable_name if command_runner is not None else shutil.which(spec.executable_name)
    if not executable_path:
        raise FileNotFoundError(f"local CLI executable not found for {adapter_ref}")
    completed = _run_or_delegate(
        (executable_path, *spec.version_args),
        _REPO_ROOT,
        timeout_seconds,
        command_runner,
    )
    if completed.return_code != 0:
        raise ValueError(f"local CLI version probe failed for {adapter_ref}")
    version_text = _safe_excerpt(completed.stdout or completed.stderr)
    _reject_secret_text("version_text", version_text)
    return LocalCliProbe(
        adapter_ref=spec.adapter_ref,
        brain_surface_ref=spec.brain_surface_ref,
        executable_name=spec.executable_name,
        executable_path=executable_path,
        version_text=version_text,
        proof_limits=spec.proof_limits,
        not_proven=spec.not_proven,
    )


# ONBOARDING-PROVIDER-PREFLIGHT-0: friendly install hints per local CLI.
# Plain Korean, no jargon, no stack-trace. message_ko tells the beginner WHAT is
# wrong and the ONE line to fix it. These are support-side onboarding hints only;
# they prove no provider availability and choose no Movement.
_PROVIDER_INSTALL_HINT_KO: Mapping[str, str] = {
    ADAPTER_CODEX_LOCAL: (
        "codex가 설치돼 있지 않아요. 터미널에 이걸 붙여넣어 설치하세요: "
        "npm install -g @openai/codex"
    ),
    ADAPTER_CLAUDE_LOCAL: (
        "claude가 설치돼 있지 않아요. 터미널에 이걸 붙여넣어 설치하세요: "
        "npm install -g @anthropic-ai/claude-code"
    ),
    ADAPTER_GEMINI_LOCAL: (
        "gemini가 설치돼 있지 않아요. 터미널에 이걸 붙여넣어 설치하세요: "
        "npm install -g @google/gemini-cli"
    ),
}
_PROVIDER_LOGIN_HINT_KO: Mapping[str, str] = {
    ADAPTER_CODEX_LOCAL: "codex login",
    ADAPTER_CLAUDE_LOCAL: "claude (실행 후 안내에 따라 로그인)",
    ADAPTER_GEMINI_LOCAL: "gemini (실행 후 안내에 따라 로그인)",
}


def preflight_provider(adapter_ref: str) -> dict[str, Any]:
    """Friendly, never-raising provider readiness preflight (onboarding "login").

    Returns a structured status dict and NEVER raises. A missing or unauthed
    provider CLI becomes a plain-Korean message (message_ko), not a stack-trace,
    so an AI-never-used beginner can self-fix. This is support mechanics only: it
    proves no provider availability, judges no success/quality, and chooses no
    Movement. It never runs a real (cost-incurring) provider call -- only a cheap
    --version probe with a short timeout.

    Status shape:
      adapter_ref, cli, installed (bool), authed ("yes"|"no"|"unknown"),
      ok (bool), message_ko (non-empty plain Korean).
    """

    ref = adapter_ref.strip() if isinstance(adapter_ref, str) else ""

    # adapter:local is in-process: no CLI, always ready.
    if ref == ADAPTER_LOCAL:
        return {
            "adapter_ref": ADAPTER_LOCAL,
            "cli": "",
            "installed": True,
            "authed": "yes",
            "ok": True,
            "message_ko": "준비 완료 ✅ (별도 설치/로그인이 필요 없어요)",
        }
    if ref == ADAPTER_CHAT_SESSION:
        return {
            "adapter_ref": ADAPTER_CHAT_SESSION,
            "cli": "",
            "installed": True,
            "authed": "unknown",
            "ok": True,
            "message_ko": "chat-session은 CLI를 실행하지 않고 작업 봉투를 parked로 기록해요.",
        }
    # gemini-api is HTTP-direct: no CLI to install, readiness == API key in env.
    # We only check key PRESENCE (never the key value, never a live API call).
    if ref == ADAPTER_GEMINI_API:
        has_key = any(
            (os.environ.get(env_var) or "").strip() for env_var in _GEMINI_API_KEY_ENV_VARS
        )
        return {
            "adapter_ref": ADAPTER_GEMINI_API,
            "cli": "",
            "installed": True,
            "authed": "yes" if has_key else "no",
            "ok": has_key,
            "message_ko": (
                "준비 완료 ✅ (Gemini API 키가 환경변수에 있어요)"
                if has_key
                else "Gemini API 키가 필요해요 → 환경변수 GEMINI_API_KEY (또는 GOOGLE_API_KEY)를 설정하세요."
            ),
        }

    # Retired or unknown adapter refs: clear message, no raise.
    spec = _LOCAL_CLI_SPECS.get(ref)
    if spec is None:
        return {
            "adapter_ref": ref,
            "cli": "",
            "installed": False,
            "authed": "unknown",
            "ok": False,
            "message_ko": (
                "알 수 없는 provider예요. 지원하는 것: adapter:local, "
                "adapter:codex-local, adapter:claude-local, adapter:gemini-local, "
                "adapter:gemini-api, adapter:chat-session"
            ),
        }

    cli = spec.executable_name
    installed = shutil.which(cli) is not None
    if not installed:
        return {
            "adapter_ref": ref,
            "cli": cli,
            "installed": False,
            "authed": "unknown",
            "ok": False,
            "message_ko": _PROVIDER_INSTALL_HINT_KO.get(
                ref, f"{cli}가 설치돼 있지 않아요. {cli}를 먼저 설치하세요."
            ),
        }

    # Installed: run only the cheap --version probe (short timeout). This proves
    # the CLI runs but NOT that it is logged in, so authed stays best-effort.
    # We never run a real provider/building call here.
    authed = "unknown"
    version_ok = False
    try:
        probe_local_cli_adapter(ref, timeout_seconds=8)
        version_ok = True
    except Exception:
        # Any failure (CLI errored, timed out, redaction tripped) -> stay
        # best-effort. We do NOT raise; missing/broken auth must never crash.
        version_ok = False

    if version_ok:
        return {
            "adapter_ref": ref,
            "cli": cli,
            "installed": True,
            "authed": authed,
            "ok": True,
            "message_ko": (
                f"준비 완료 ✅ ({cli} 설치됨). 로그인이 안 돼 있으면 → "
                f"{_PROVIDER_LOGIN_HINT_KO.get(ref, cli + ' login')}"
            ),
        }

    # Installed but the cheap probe did not succeed: most often a login is
    # needed. Give the friendly login line, never a stack-trace.
    return {
        "adapter_ref": ref,
        "cli": cli,
        "installed": True,
        "authed": "unknown",
        "ok": False,
        "message_ko": (
            f"{cli} 로그인이 필요해요 → "
            f"{_PROVIDER_LOGIN_HINT_KO.get(ref, cli + ' login')}"
        ),
    }


def _invoke_local_callable(
    request: AgentAdapterRequest,
    local_callables: Mapping[str, AgentBrainCallable] | None,
) -> Any:
    if not request.callable_ref:
        raise ValueError("adapter:local requires callable_ref")
    registry = dict(_BUILTIN_LOCAL_CALLABLES)
    if local_callables:
        registry.update(local_callables)
    local_callable = registry.get(request.callable_ref)
    if local_callable is None:
        raise ValueError("local callable ref is not registered")
    return local_callable(request)


def _local_callable_smoke(request: AgentAdapterRequest) -> Mapping[str, Any]:
    return {
        "returned_summary": "local Agent Adapter callable returned support evidence",
        "adapter_ref": request.adapter_ref,
        "agent_object_ref": request.agent_object_ref,
        "callable_ref": request.callable_ref,
        "prompt_refs": list(request.prompt_refs),
        "skill_refs": list(request.skill_refs),
        "hook_refs": list(request.hook_refs),
        "tool_policy_refs": list(request.tool_policy_refs),
        "discipline_refs": list(request.discipline_refs),
        "evidence_refs": [request.output_packet_ref or "support-ref:agent-adapter-output"],
    }


_BUILTIN_LOCAL_CALLABLES: Mapping[str, AgentBrainCallable] = {
    "callable:local:agent-invoke0-smoke": _local_callable_smoke,
}


def _invoke_local_cli_adapter(
    request: AgentAdapterRequest,
    *,
    cwd: Path,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
) -> tuple[Mapping[str, Any], tuple[str, ...], tuple[str, ...], Mapping[str, Any] | None]:
    spec = _local_cli_spec(request.adapter_ref)
    probe = probe_local_cli_adapter(
        spec.adapter_ref,
        command_runner=command_runner,
    )
    proof_limits = _proof_limits_for_request(request, spec)
    not_proven = _not_proven_for_request(request, spec)
    prompt = _build_prompt(request, spec)
    completed = _invoke_local_cli(
        spec,
        request,
        prompt,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        command_runner=command_runner,
    )
    if completed.return_code != 0:
        raise ValueError(_local_cli_nonzero_error_message(spec, completed))
    output_text = _extract_output_text(spec, completed)
    _reject_secret_text("local_cli_output", output_text)
    returned = {
        "returned_summary": "local CLI Agent Adapter returned support evidence",
        "adapter_ref": spec.adapter_ref,
        "selected_model_ref": request.selected_model_ref,
        "agent_object_ref": request.agent_object_ref,
        "brain_surface_ref": spec.brain_surface_ref,
        "cli_version_text": probe.version_text,
        # F7 proof-limit (codex review 2, operator decision B 0601): cli_call_ref
        # is BUILDING-scoped (adapter + building_id), so multiple steps of one
        # Building share it. _invoke_local_cli DOES spawn a fresh subprocess per
        # step (each step is a real independent process), but the returned
        # evidence does NOT carry per-step identifiers (call_index / args /
        # return_code / cwd). So this evidence proves "a real codex CLI of this
        # version returned this content" but NOT, by itself, "each step ran as a
        # distinct OS process". That per-step process-identity is NOT-PROVEN.
        # HONESTY CORRECTION (codex review 2): this NOT-PROVEN phrase is recorded
        # in the engine BLUEPRINT §9, NOT in spec.not_proven / the returned
        # evidence (an earlier comment here overclaimed that). _DEFAULT_NOT_PROVEN
        # does NOT carry it. Adding it to every returned record would change the
        # AgentFact returned-evidence shape and require migrating every existing
        # real-codex building (FQ-2-class) — disproportionate to a P3 labelling
        # gap where behavior is already correct; left as a blueprint-level limit.
        "cli_call_ref": f"support-cli-call:{spec.adapter_ref}:{request.building_id}",
        "output_excerpt": _safe_excerpt(output_text),
        "evidence_refs": [
            request.output_packet_ref or f"support-ref:{spec.adapter_ref}:local-cli-output"
        ],
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    _merge_structured_return_fields(
        returned,
        _extract_required_return_fields(
            output_text,
            request.required_return_shape,
        ),
    )
    # TrackA-A1 METER: the codex token usage rides back as a SEPARATE 4th element,
    # NOT inside `returned` (which becomes AgentFact.returned). Support fact only.
    return (
        returned,
        _merge_texts(proof_limits, request.proof_limits),
        _merge_texts(not_proven, request.not_proven),
        completed.adapter_usage,
    )


def _gemini_api_key_from_env() -> str:
    """Return the Gemini API key from env, or raise FileNotFoundError (no-key).

    Decision 1 (locked): key from GEMINI_API_KEY else GOOGLE_API_KEY; absent key
    is a CLEAN typed adapter-error that MIRRORS the local_cli_missing shape. We
    raise FileNotFoundError so it flows the EXACT B2-hardened adapter-error/hold
    path in run.py (_adapter_error_kind -> 'local_cli_missing'), never a crash and
    never a subprocess. The key value is NEVER returned in evidence or logged.
    """
    for env_var in _GEMINI_API_KEY_ENV_VARS:
        value = os.environ.get(env_var)
        if value and value.strip():
            return value.strip()
    raise FileNotFoundError(
        "gemini-api adapter requires an API key in env "
        + " or ".join(_GEMINI_API_KEY_ENV_VARS)
        + " (none set)"
    )


def _gemini_api_model_name(request: AgentAdapterRequest) -> str:
    """Resolve the bare Gemini model name for the HTTP path (no provider state)."""
    model_id = _model_cli_arg_from_ref(
        request.selected_model_ref or _GEMINI_API_SPEC.default_model_ref,
        _GEMINI_API_SPEC,
    )
    # _model_cli_arg_from_ref returns "" for the gemini default sentinel; the HTTP
    # endpoint always needs a concrete model, so fall back to flash.
    return model_id or _GEMINI_API_MODEL_FALLBACK


def _build_gemini_api_request(
    api_key: str,
    model_name: str,
    prompt: str,
) -> "urllib.request.Request":
    """Build the signed Gemini generateContent POST request (pure, no network)."""
    url = f"{_GEMINI_API_BASE_URL}/{model_name}:generateContent"
    body = json.dumps(
        {"contents": [{"parts": [{"text": prompt}]}]},
        ensure_ascii=True,
    ).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    # Auth header (preferred over ?key=): keeps the key out of the URL/logs.
    request.add_header("x-goog-api-key", api_key)
    request.add_header("Content-Type", "application/json")
    return request


def _parse_gemini_api_response(raw_body: bytes) -> str:
    """Parse candidates[0].content.parts[0].text from a Gemini API response body.

    Any malformed/missing shape raises a CLEAN ValueError (flows the B2 hold path,
    never a raw KeyError/IndexError crash).
    """
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("gemini-api response was not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("gemini-api response must be a JSON object")
    candidates = payload.get("candidates")
    if not isinstance(candidates, Sequence) or not candidates:
        raise ValueError("gemini-api response missing candidates")
    first = candidates[0]
    if not isinstance(first, Mapping):
        raise ValueError("gemini-api candidate must be an object")
    content = first.get("content")
    if not isinstance(content, Mapping):
        raise ValueError("gemini-api candidate missing content")
    parts = content.get("parts")
    if not isinstance(parts, Sequence) or not parts:
        raise ValueError("gemini-api content missing parts")
    texts = [
        part["text"]
        for part in parts
        if isinstance(part, Mapping) and isinstance(part.get("text"), str)
    ]
    if not texts:
        raise ValueError("gemini-api response missing parts[].text")
    text = "".join(texts)
    if not text.strip():
        raise ValueError("gemini-api response text was empty")
    return text


def _gemini_api_urlopen(
    request: "urllib.request.Request",
    *,
    timeout_seconds: int,
) -> bytes:
    """Perform the HTTP call via stdlib urllib, converting failures to clean errors.

    Timeout / non-200 / transport failure all become a clean typed ValueError that
    flows the B2 hold path (never a raw urllib traceback crash). NO subprocess is
    spawned anywhere on this path.
    """
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if status != 200:
                raise ValueError(f"gemini-api HTTP status {status} (non-200)")
            return response.read()
    except urllib.error.HTTPError as exc:
        # Non-2xx surfaced as an exception by urllib. Read+discard the body to
        # avoid leaking a provider error body (may echo prompt/credentials).
        raise ValueError(f"gemini-api HTTP error status {exc.code}") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise ValueError("gemini-api request timed out") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise ValueError("gemini-api request timed out") from exc
        raise ValueError("gemini-api request failed (transport error)") from exc


def _invoke_gemini_api(
    request: AgentAdapterRequest,
    *,
    timeout_seconds: int,
    urlopen: Callable[["urllib.request.Request", int], bytes] | None = None,
) -> tuple[Mapping[str, Any], tuple[str, ...], tuple[str, ...]]:
    """Direct Gemini HTTP API adapter (stdlib urllib, env key, NO subprocess).

    Mirrors _invoke_local_cli_adapter's return triple exactly so the engine stays
    adapter-agnostic. The optional urlopen seam exists ONLY so a checker FIRE can
    capture/mocks the request without a network/credential; live calls leave it
    None (the default stdlib path). Absent key / HTTP error / timeout / malformed
    response all become CLEAN typed adapter-errors (never a crash, never a spawn).
    """
    spec = _GEMINI_API_SPEC
    proof_limits = _proof_limits_for_request(request, spec)
    not_proven = _not_proven_for_request(request, spec)
    prompt = _build_prompt(request, spec)
    api_key = _gemini_api_key_from_env()  # no-key -> FileNotFoundError (hold path)
    model_name = _gemini_api_model_name(request)
    http_request = _build_gemini_api_request(api_key, model_name, prompt)
    if urlopen is not None:
        raw_body = urlopen(http_request, timeout_seconds)
    else:
        raw_body = _gemini_api_urlopen(http_request, timeout_seconds=timeout_seconds)
    output_text = _parse_gemini_api_response(raw_body)
    _reject_secret_text("gemini_api_output", output_text)
    returned = {
        "returned_summary": "Gemini HTTP API Agent Adapter returned support evidence",
        "adapter_ref": spec.adapter_ref,
        "selected_model_ref": request.selected_model_ref,
        "agent_object_ref": request.agent_object_ref,
        "brain_surface_ref": spec.brain_surface_ref,
        # No CLI version on the HTTP path; record the resolved endpoint model name
        # (NOT the key, NOT the URL with any secret) as the provider identity.
        "api_model_name": model_name,
        "api_call_ref": f"support-api-call:{spec.adapter_ref}:{request.building_id}",
        "output_excerpt": _safe_excerpt(output_text),
        "evidence_refs": [
            request.output_packet_ref or f"support-ref:{spec.adapter_ref}:http-api-output"
        ],
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    _merge_structured_return_fields(
        returned,
        _extract_required_return_fields(
            output_text,
            request.required_return_shape,
        ),
    )
    return returned, _merge_texts(proof_limits, request.proof_limits), _merge_texts(
        not_proven,
        request.not_proven,
    )


def invoke_gemini_text(
    prompt: str,
    *,
    model_name: str = "gemini-2.5-flash",
    timeout_seconds: int = 90,
    urlopen: Callable[..., bytes] | None = None,
) -> str:
    """PUBLIC prompt -> text seam over the Gemini HTTP API (H3b customer entry).

    This is an ADDITIVE thin wrapper composing the EXISTING private helpers --
    ``_gemini_api_key_from_env`` (env key, never logged), ``_build_gemini_api_request``
    (pure request build), ``_gemini_api_urlopen`` (stdlib urllib, clean typed
    errors), ``_parse_gemini_api_response`` (candidates[0]...text) -- plus the
    output secret-scrub. It exists so a caller (the H3b ``ai_invoke`` default)
    can turn a bare design prompt into bare text WITHOUT building an
    ``AgentAdapterRequest`` (the per-Brick dispatch path stays untouched).

    Key handling mirrors decision 1 (locked): the key is read from
    ``GEMINI_API_KEY`` else ``GOOGLE_API_KEY``; an ABSENT key raises the SAME
    ``FileNotFoundError`` the per-Brick path raises (mirrors the B2-hardened
    ``local_cli_missing`` adapter-error shape) -- a CLEAN typed error, NEVER a
    crash and NEVER a subprocess. HTTP error / timeout / malformed response all
    surface as the helpers' clean ``ValueError`` (no raw traceback). The key is
    never returned in the result and never logged.

    The optional ``urlopen`` seam exists ONLY so a checker FIRE can mock the HTTP
    call (capture the request, return a canned body) with NO network / credential;
    a live caller leaves it None (the default stdlib ``_gemini_api_urlopen`` path).
    It is called as ``urlopen(request, timeout_seconds=...)`` -- the same keyword
    shape as ``_gemini_api_urlopen``.
    """

    if not isinstance(prompt, str):
        raise TypeError("invoke_gemini_text requires a str prompt")
    api_key = _gemini_api_key_from_env()  # no-key -> FileNotFoundError (clean, no spawn)
    bare_model = str(model_name).strip() or _GEMINI_API_MODEL_FALLBACK
    http_request = _build_gemini_api_request(api_key, bare_model, prompt)
    if urlopen is not None:
        raw_body = urlopen(http_request, timeout_seconds=timeout_seconds)
    else:
        raw_body = _gemini_api_urlopen(http_request, timeout_seconds=timeout_seconds)
    output_text = _parse_gemini_api_response(raw_body)
    _reject_secret_text("gemini_api_text_output", output_text)
    return output_text


def invoke_claude_text(
    prompt: str,
    *,
    model_name: str = "",
    timeout_seconds: int = 120,
    command_runner: CommandRunner | None = None,
) -> str:
    """PUBLIC prompt -> text seam over the local Claude CLI.

    This additive design-AI seam mirrors ``invoke_gemini_text``'s narrow
    contract: caller supplies a prompt, the provider returns raw text, and the
    output must be non-empty and secret-free. It does not build or return an
    AgentFact and does not touch the Building adapter path.
    """

    if not isinstance(prompt, str):
        raise TypeError("invoke_claude_text requires a str prompt")
    executable_path = _text_cli_executable("claude", command_runner)
    args_list = [executable_path, "-p", prompt, "--output-format", "text"]
    bare_model = _clean_text_cli_option("claude model_name", model_name)
    if bare_model:
        args_list.extend(("--model", bare_model))
    completed = _run_text_cli(
        tuple(args_list),
        timeout_seconds=timeout_seconds,
        command_runner=command_runner,
    )
    return _raw_text_from_completed("claude_text_output", completed.stdout, completed)


def invoke_codex_text(
    prompt: str,
    *,
    model_name: str = "",
    timeout_seconds: int = 180,
    command_runner: CommandRunner | None = None,
) -> str:
    """PUBLIC prompt -> text seam over ``codex exec --output-last-message``.

    The Codex CLI writes the last assistant message to a temp file; this wrapper
    returns that file's raw text after the same empty-output and secret-output
    guards used by the Gemini text seam.
    """

    if not isinstance(prompt, str):
        raise TypeError("invoke_codex_text requires a str prompt")
    executable_path = _text_cli_executable("codex", command_runner)
    bare_model = _clean_text_cli_option("codex model_name", model_name)
    with tempfile.TemporaryDirectory(prefix="bp-codex-text-") as tmpdir:
        output_path = Path(tmpdir) / "last-message.txt"
        args_list = [
            executable_path,
            "exec",
            "--sandbox",
            "read-only",
        ]
        if bare_model:
            args_list.extend(("-m", bare_model))
        args_list.extend(("--output-last-message", str(output_path), prompt))
        completed = _run_text_cli(
            tuple(args_list),
            timeout_seconds=timeout_seconds,
            command_runner=command_runner,
        )
        try:
            output_text = output_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError("codex text output file was not written") from exc
    return _raw_text_from_completed("codex_text_output", output_text, completed)


def _local_cli_spec(adapter_ref: str) -> LocalCliSpec:
    if adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError("adapter_ref is retired and not admitted as an active adapter")
    try:
        return _LOCAL_CLI_SPECS[adapter_ref]
    except KeyError as exc:
        raise ValueError("adapter_ref is not a local CLI adapter") from exc


# TrackA-A1 METER (codex token usage): `codex exec --json` emits one JSONL event
# per line on stdout, ending each turn with
#   {"type":"turn.completed","usage":{"input_tokens","cached_input_tokens",
#    "output_tokens","reasoning_output_tokens"}}
# We parse the LAST turn.completed.usage and expose the four counters under a
# STABLE codex-vocabulary key set. These are SUPPORT FACTS only -- the meter
# writer (support/recording/adapter_usage_meter.py) maps the subset that overlaps
# the WORKFLOW_IMPORT_USAGE_METRIC_KEYS allowlist; nothing here is a verdict.
CODEX_TURN_COMPLETED_USAGE_KEYS: tuple[str, ...] = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


def codex_usage_from_json_stdout(stdout: str) -> Mapping[str, Any] | None:
    """Parse the LAST ``turn.completed`` usage from ``codex exec --json`` stdout.

    Returns a mapping carrying ONLY the codex usage counter keys, or ``None`` when
    the stdout is empty / not JSONL / has no ``turn.completed`` with a ``usage``
    block (older codex without ``--json``). Per the graceful-fallback contract,
    absent is ``None`` and a missing individual counter is recorded as ``None``;
    this function NEVER fabricates a count and NEVER raises on malformed input.
    """

    if not isinstance(stdout, str) or not stdout.strip():
        return None
    last_usage: Mapping[str, Any] | None = None
    for line in stdout.splitlines():
        text = line.strip()
        if not text or text[0] != "{":
            continue
        try:
            event = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if isinstance(usage, Mapping):
            last_usage = usage
    if last_usage is None:
        return None
    parsed: dict[str, Any] = {}
    for key in CODEX_TURN_COMPLETED_USAGE_KEYS:
        value = last_usage.get(key)
        parsed[key] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return parsed


# TrackA-A1 ROOT FIX (TEXT SAFETY + GATE-NO-MEASURE): the assistant message TEXT
# keys codex emits inside its `--json` JSONL events. When the --output-last-message
# file is empty/unwritten under --json, we recover the assistant text from THESE
# event fields ONLY -- never by handing raw JSONL back as the assistant text. The
# raw JSONL must never become output_text (it would leak the event structure into
# output_excerpt and, worse, let a JSONL "usage" key be lifted into
# AgentFact.returned via _extract_required_return_fields -- a gate-no-measure
# violation). Tolerant of the known codex item/message event shapes; on no match
# returns "" (treated as no-text), NEVER the raw JSONL stdout.
_CODEX_ASSISTANT_MESSAGE_EVENT_TYPES: frozenset[str] = frozenset(
    {"item.completed", "agent_message", "assistant_message", "response.completed"}
)
_CODEX_ASSISTANT_MESSAGE_ITEM_TYPES: frozenset[str] = frozenset(
    {"agent_message", "assistant_message", "message"}
)
_CODEX_ASSISTANT_TEXT_KEYS: tuple[str, ...] = ("text", "message", "content")


def codex_assistant_text_from_json_stdout(stdout: str) -> str:
    """Recover the LAST assistant message TEXT from ``codex exec --json`` stdout.

    Returns the assistant's text content drawn from the JSONL event fields, or the
    empty string when no assistant-message event/text is present. It NEVER returns
    the raw JSONL and NEVER raises on malformed input. This is the safe replacement
    for the old ``completed.stdout`` fallback: under ``--json`` the stdout is raw
    JSONL events, so the previous fallback leaked event structure (and any embedded
    ``usage`` key) into the assistant-text path. Here only real message text is ever
    returned; absence is the empty string, treated downstream as no-text.
    """

    if not isinstance(stdout, str) or not stdout.strip():
        return ""
    last_text = ""
    for line in stdout.splitlines():
        text = line.strip()
        if not text or text[0] != "{":
            continue
        try:
            event = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("type") not in _CODEX_ASSISTANT_MESSAGE_EVENT_TYPES:
            continue
        candidate = _codex_event_assistant_text(event)
        if candidate:
            last_text = candidate
    return last_text


def _codex_event_assistant_text(event: Mapping[str, Any]) -> str:
    """Pull assistant text out of one codex JSONL event mapping (best-effort)."""

    # Newer codex nests the message under an "item" with its own type/text.
    item = event.get("item")
    if isinstance(item, Mapping):
        item_type = item.get("type")
        if item_type is None or item_type in _CODEX_ASSISTANT_MESSAGE_ITEM_TYPES:
            nested = _codex_text_from_keys(item)
            if nested:
                return nested
    return _codex_text_from_keys(event)


def _codex_text_from_keys(source: Mapping[str, Any]) -> str:
    for key in _CODEX_ASSISTANT_TEXT_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
        # codex content can be a list of {type:"text"/"output_text", text:...} parts.
        if isinstance(value, list):
            joined = "".join(
                part.get("text", "")
                for part in value
                if isinstance(part, Mapping) and isinstance(part.get("text"), str)
            )
            if joined.strip():
                return joined
    return ""


# TrackA-A1 MAJOR FIX (graceful older-codex --json): a codex binary that does not
# understand ``--json`` exits NONZERO with an "unrecognized/unknown --json"-shaped
# diagnostic. The meter is INSTRUMENTATION; it must NEVER break a build. So when a
# ``--json`` invocation fails with this signature we retry ONCE without ``--json``
# (the meter just records absent usage). Any OTHER nonzero failure is a real build
# error and is returned untouched for the normal nonzero path.
_CODEX_JSON_UNSUPPORTED_MARKERS: tuple[str, ...] = (
    "unrecognized",
    "unknown option",
    "unexpected argument",
    "no such option",
    "invalid option",
    "unknown flag",
    "unknown argument",
)


def _codex_json_unsupported(completed: LocalCliCompleted) -> bool:
    """True when a nonzero codex result looks like ``--json`` is unsupported."""

    if completed.return_code == 0:
        return False
    haystack = f"{completed.stderr}\n{completed.stdout}".lower()
    if "--json" not in haystack and "json" not in haystack:
        return False
    return any(marker in haystack for marker in _CODEX_JSON_UNSUPPORTED_MARKERS)


def _invoke_local_cli(
    spec: LocalCliSpec,
    request: AgentAdapterRequest,
    prompt: str,
    *,
    cwd: Path,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
) -> LocalCliCompleted:
    executable_path = spec.executable_name if command_runner is not None else shutil.which(spec.executable_name)
    if not executable_path:
        raise FileNotFoundError(f"local CLI executable not found for {spec.adapter_ref}")
    if spec.invocation_args_kind == "codex-exec-readonly":
        sandbox = _codex_sandbox_for_request(request)
        with tempfile.NamedTemporaryFile(prefix="bp-codex-cli-", suffix=".txt") as output_file:
            args_list = [
                executable_path,
                "exec",
                "--skip-git-repo-check",
                "--cd",
                str(cwd),
                "--sandbox",
                sandbox,
                "-c",
                'approval_policy="never"',
            ]
            # OPT-IN ONLY (default invocation byte-identical when the env var is
            # unset/not "1"): codex's non-managed hooks (e.g. the .codex/hooks
            # native-dispatch recording pair) require a one-time interactive
            # TRUST review; `codex exec` cannot show that prompt and silently
            # skips untrusted hooks (empirically observed 0610: a registered
            # SessionStart canary did not fire under this exact invocation).
            # Setting BRICK_CODEX_HOOK_TRUST_BYPASS=1 appends codex's own
            # automation escape hatch so already-vetted repo hooks run. This
            # bypasses HOOK TRUST only -- not approvals, not the sandbox.
            if os.environ.get("BRICK_CODEX_HOOK_TRUST_BYPASS") == "1":
                args_list.append("--dangerously-bypass-hook-trust")
            model_arg = _model_cli_arg(request, spec)
            if model_arg:
                args_list.extend(("-m", model_arg))
            # Ephemeral by DEFAULT: a non-ephemeral `codex exec` persists its
            # session to the shared ~/.codex SQLite state (state/logs/goals/
            # memories), which is single-writer locked. Two concurrent codex
            # builds therefore deadlock the second on that write lock -- it
            # spawns but never connects (0 CPU, 0 sockets) and hangs to the full
            # adapter timeout. --ephemeral skips SESSION persistence only (the
            # workspace code write is governed by --sandbox, untouched), so
            # concurrent codex builds stop contending. BRICK keeps its own
            # evidence ledger and never reads codex's session, so nothing is
            # lost. Opt out (rare, e.g. inspecting codex sessions) with
            # BRICK_CODEX_EPHEMERAL=0.
            if os.environ.get("BRICK_CODEX_EPHEMERAL") != "0":
                args_list.append("--ephemeral")
            # TrackA-A1 METER: `--json` turns codex's stdout into per-event JSONL so
            # we can read the turn.completed token usage. It does NOT change where
            # the TEXT response lives: codex still writes the last assistant message
            # to the --output-last-message FILE regardless of --json. So below we
            # read the TEXT from that FILE ALWAYS (the JSONL stdout is NOT text), and
            # parse the JSONL stdout ONLY for the usage meter. stdin=DEVNULL (the
            # connect-stall cure) and --output-last-message are untouched.
            #
            # GRACEFUL OLDER-CODEX (the meter is instrumentation, never break a
            # build): we try WITH --json first; if that exact invocation fails with
            # an "unrecognized --json"-shaped diagnostic (older codex), we retry ONCE
            # WITHOUT --json. The meter then records absent usage (None) and the build
            # proceeds. Any OTHER nonzero is a real build error, returned untouched.
            tail_args = ("--output-last-message", output_file.name, prompt)
            json_args = tuple((*args_list, "--json", *tail_args))
            completed = _run_or_delegate(json_args, cwd, timeout_seconds, command_runner)
            json_active = True
            if _codex_json_unsupported(completed):
                # Older codex: re-run WITHOUT --json so the build still completes.
                # The file may have been left empty by the rejected first attempt;
                # re-running with a fresh seek keeps the text path identical.
                plain_args = tuple((*args_list, *tail_args))
                completed = _run_or_delegate(
                    plain_args, cwd, timeout_seconds, command_runner
                )
                json_active = False
            # SUPPORT meter input (Brick-axis fact, no verdict): the LAST
            # turn.completed.usage from the JSONL stdout. None when --json is
            # unavailable (older codex) or no turn.completed/usage is present.
            adapter_usage = (
                codex_usage_from_json_stdout(completed.stdout) if json_active else None
            )
            # TEXT response ALWAYS from the --output-last-message file. When the file
            # is empty/unwritten we must NOT fall back to raw stdout under --json --
            # that stdout is JSONL events, and feeding it to the assistant-text path
            # leaks the event structure into output_excerpt AND can let a JSONL
            # "usage" key be lifted into AgentFact.returned (gate-no-measure). So with
            # --json on we recover the assistant message TEXT from the JSONL events
            # (codex_assistant_text_from_json_stdout), which returns "" when no
            # message text is present -- never the raw JSONL. Without --json (older
            # codex), the stdout is plain text and the original fallback is restored.
            output_file.seek(0)
            file_text = output_file.read().decode("utf-8", errors="replace")
            if file_text.strip():
                text_stdout = file_text
            elif json_active:
                text_stdout = codex_assistant_text_from_json_stdout(completed.stdout)
            else:
                text_stdout = completed.stdout
            return LocalCliCompleted(
                args=completed.args,
                return_code=completed.return_code,
                stdout=text_stdout,
                stderr=completed.stderr,
                adapter_usage=adapter_usage,
            )
    if spec.invocation_args_kind == "claude-plan-json":
        knobs = _claude_cli_invocation(request)
        args_list = [
            executable_path,
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            knobs["permission_mode"],
            "--system-prompt",
            knobs["system_prompt"],
            "--tools",
            knobs["tools"],
        ]
        model_arg = _model_cli_arg(request, spec)
        if model_arg:
            args_list.extend(("--model", model_arg))
        if request.session_continuity_mode == "none":
            args_list.append("--no-session-persistence")
        args_list.append(prompt)
        args = tuple(args_list)
        return _run_or_delegate(args, cwd, timeout_seconds, command_runner)
    if spec.invocation_args_kind == "gemini-p-json-flash":
        with tempfile.TemporaryDirectory(prefix="bp-gemini-cli-") as tmpdir:
            temp_root = Path(tmpdir)
            read_tier = agent_request_read_tier(request)
            policy_path = temp_root / ("readonly-policy.toml" if read_tier else "no-tools-policy.toml")
            policy_path.write_text(
                _GEMINI_READONLY_POLICY if read_tier else _GEMINI_NO_TOOL_POLICY,
                encoding="utf-8",
            )
            run_cwd = cwd if read_tier else temp_root
            run_env = None
            approval_mode = "plan"
            model_arg = _model_cli_arg(request, spec) or "gemini-2.5-flash"
            if read_tier:
                run_env = dict(os.environ)
                if not _gemini_api_key_env_present(run_env):
                    raise FileNotFoundError(
                        "gemini-local read tier requires an API key in env "
                        + " or ".join(_GEMINI_API_KEY_ENV_VARS)
                        + " (none set)"
                    )
                gemini_home = temp_root / "home"
                gemini_settings_dir = gemini_home / ".gemini"
                gemini_settings_dir.mkdir(parents=True)
                (gemini_settings_dir / "settings.json").write_text(
                    json.dumps(
                        {"security": {"auth": {"selectedType": "gemini-api-key"}}},
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                run_env["HOME"] = str(gemini_home)
                approval_mode = "default"
                model_arg = _model_cli_arg(request, spec) or "gemini-3.5-flash"
            args = (
                executable_path,
                "-p",
                prompt,
                "--output-format",
                "json",
                "--model",
                model_arg,
                "--approval-mode",
                approval_mode,
                "--extensions",
                "",
                "--admin-policy",
                str(policy_path),
                "--skip-trust",
            )
            return _run_or_delegate(
                args,
                run_cwd,
                timeout_seconds,
                command_runner,
                env=run_env,
            )
    raise ValueError("unsupported local CLI adapter kind")


def _adapter_model_spec(adapter_ref: str) -> LocalCliSpec:
    """Return the model-selection spec carrier for an adapter ref.

    gemini-api is NOT a CLI (not in _LOCAL_CLI_SPECS), but it shares the gemini
    model grammar; route it to its inert _GEMINI_API_SPEC carrier so model-ref
    normalization mirrors the CLI adapters without polluting _LOCAL_CLI_SPECS.
    """
    if adapter_ref == ADAPTER_GEMINI_API:
        return _GEMINI_API_SPEC
    return _local_cli_spec(adapter_ref)


def _normalize_selected_model_ref(adapter_ref: str, selected_model_ref: str) -> str:
    if adapter_ref in {ADAPTER_LOCAL, ADAPTER_CHAT_SESSION}:
        if selected_model_ref and selected_model_ref != MODEL_REF_DEFAULT:
            raise ValueError(f"{adapter_ref} accepts only model:default")
        return MODEL_REF_DEFAULT
    spec = _adapter_model_spec(adapter_ref)
    if not selected_model_ref:
        return spec.default_model_ref
    if selected_model_ref == MODEL_REF_DEFAULT:
        return spec.default_model_ref
    _validate_model_ref_for_adapter(adapter_ref, selected_model_ref)
    return selected_model_ref


def _validate_model_ref_for_adapter(adapter_ref: str, model_ref: str) -> None:
    provider = MODEL_PROVIDER_BY_ADAPTER.get(adapter_ref)
    if provider is None:
        raise ValueError("selected_model_ref is supported only for admitted local CLI adapters")
    expected_prefix = f"model:{provider}:"
    if not model_ref.startswith(expected_prefix):
        raise ValueError("selected_model_ref provider must match selected adapter")
    model_id = model_ref.removeprefix(expected_prefix)
    if not model_id:
        raise ValueError("selected_model_ref must include a model id")
    _reject_secret_text("selected_model_ref", model_ref)
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", model_id):
        raise ValueError("selected_model_ref model id contains unsupported characters")


def _model_cli_arg(request: AgentAdapterRequest, spec: LocalCliSpec) -> str:
    return _model_cli_arg_from_ref(request.selected_model_ref or spec.default_model_ref, spec)


def _proof_limits_for_request(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> tuple[str, ...]:
    if not agent_request_effective_write(request):
        return spec.proof_limits
    return _merge_texts(
        spec.proof_limits,
        "workspace write is limited by Brick-declared write_scope",
    )


def _not_proven_for_request(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> tuple[str, ...]:
    if not agent_request_effective_write(request):
        return spec.not_proven
    return _merge_texts(
        spec.not_proven,
        "semantic correctness of file edits",
    )


def _codex_sandbox_for_request(request: AgentAdapterRequest) -> str:
    return "workspace-write" if agent_request_effective_write(request) else "read-only"


def _claude_cli_invocation(request: AgentAdapterRequest) -> dict[str, str]:
    """Pure projection of the claude-local CLI knobs for a request.

    Mirrors _codex_sandbox_for_request: the SINGLE place that decides whether a
    claude-local invocation opens scoped write. When agent_request_effective_write
    is True the run uses the scoped write tool set (from the Agent's read-write
    tool policy) + acceptEdits + a write-aware system prompt; otherwise it keeps
    the unchanged read-only shape (plan + no tools + the non-interactive reviewer
    prompt). Unlike codex there is NO OS sandbox here -- and NONE of the claude-side
    knobs is a verified write boundary: the tools allowlist, acceptEdits, claude's
    own provider-side protected-path prompts, cwd, and the injected prompt rules are
    all advisory/provider-state, not enforced by this code. The ONLY enforcement
    this layer owns is the 3-gate effective_write decision + post-hoc write
    observation; a live in-scope/out-of-scope claude write is NOT-PROVEN.
    """
    if agent_request_effective_write(request):
        # Lazy import: agent_resources imports FROM this module, so a top-level
        # import would be circular.
        from .agent_resources import claude_tools_for_tool_policies

        # tool_policy_refs is a tuple on the request; claude_tools_for_tool_policies'
        # _string_list helper accepts only a list, so pass a list copy. This is the
        # RUN-TIME provider invocation FOR A STEP, so the step's actual write NEED
        # (a non-empty Brick write_scope) gates the physical tool set -- matching
        # the agent_request_effective_write gate this branch already passed, never
        # the agent's bare capability.
        tools = ",".join(
            claude_tools_for_tool_policies(
                list(request.tool_policy_refs),
                write_need=bool(request.write_scope),
            )["tools"]
        )
        return {
            "permission_mode": "acceptEdits",
            "tools": tools,
            "system_prompt": _CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT,
        }
    if agent_request_read_tier(request):
        return {
            "permission_mode": "plan",
            "tools": "Read,Grep,Glob",
            "system_prompt": _CLAUDE_READ_ONLY_SYSTEM_PROMPT,
        }
    return {
        "permission_mode": "plan",
        "tools": "",
        "system_prompt": _CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT,
    }


def _model_cli_arg_from_ref(model_ref: str, spec: LocalCliSpec) -> str:
    if model_ref in {MODEL_REF_DEFAULT, spec.default_model_ref}:
        if model_ref in {MODEL_REF_CODEX_DEFAULT, MODEL_REF_CLAUDE_INHERIT, MODEL_REF_DEFAULT}:
            return ""
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL and model_ref == MODEL_REF_GEMINI_DEFAULT:
        return ""
    provider = MODEL_PROVIDER_BY_ADAPTER.get(spec.adapter_ref)
    if provider is None:
        return ""
    expected_prefix = f"model:{provider}:"
    if not model_ref.startswith(expected_prefix):
        raise ValueError("selected_model_ref provider must match selected adapter")
    model_id = model_ref.removeprefix(expected_prefix)
    if model_id in {"default", "inherit"}:
        return ""
    return model_id


def _run_or_delegate(
    args: Sequence[str],
    cwd: Path,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
    *,
    env: Mapping[str, str] | None = None,
) -> LocalCliCompleted:
    if command_runner is not None:
        if env is not None and _command_runner_accepts_env(command_runner):
            return command_runner(args, cwd, timeout_seconds, env=env)
        return command_runner(args, cwd, timeout_seconds)
    return _run_command(args, cwd=cwd, timeout_seconds=timeout_seconds, env=env)


def _command_runner_accepts_env(command_runner: CommandRunner) -> bool:
    call = getattr(command_runner, "__call__", None)
    candidates = (command_runner, call) if call is not None else (command_runner,)
    for candidate in candidates:
        code = getattr(candidate, "__code__", None)
        if code is None:
            continue
        arg_names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
        if "env" in arg_names:
            return True
    return False


def _text_cli_executable(executable_name: str, command_runner: CommandRunner | None) -> str:
    executable_path = executable_name if command_runner is not None else shutil.which(executable_name)
    if not executable_path:
        raise FileNotFoundError(f"{executable_name} CLI executable not found")
    return executable_path


def _clean_text_cli_option(label: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    text = value.strip()
    if "\x00" in text or "\n" in text:
        raise ValueError(f"{label} contains unsupported control text")
    if text:
        _reject_secret_text(label, text)
    return text


def _run_text_cli(
    args: Sequence[str],
    *,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
) -> LocalCliCompleted:
    if not args:
        raise ValueError("text CLI args must not be empty")
    executable = Path(str(args[0])).name
    if executable not in {"codex", "claude"}:
        raise ValueError("text CLI executable is not allowlisted")
    for index, item in enumerate(args):
        text = str(item)
        if "\x00" in text:
            raise ValueError("text CLI arg contains unsupported control text")
        if index != len(args) - 1:
            _reject_secret_text("text_cli_arg", text)
    if command_runner is not None:
        return command_runner(args, _REPO_ROOT, timeout_seconds)
    return _run_text_cli_command(args, cwd=_REPO_ROOT, timeout_seconds=timeout_seconds)


def _codex_stall_watchdog_config(timeout_seconds: int | float) -> _CodexStallWatchdogConfig | None:
    # CONNECT-STALL THRESHOLD COUPLING (TrackB 0619, codex-review F1/F2): the
    # watchdog threshold is COUPLED to the adapter timeout. The subprocess
    # communicate(timeout=timeout_seconds) raises a PLAIN (untagged) TimeoutExpired
    # at the adapter deadline; if the dead-signature threshold is >= that deadline
    # the watchdog can NEVER fire and a connect-stall is mislabeled
    # local_cli_timeout. At the production default (adapter_timeout_seconds=120 in
    # driver.py / run.py) the unclamped 150s default was pure dead code. So the
    # EFFECTIVE threshold is clamped to (timeout_seconds - 2*poll): the dead-signature
    # needs TWO samples to confirm (it anchors at the FIRST dead poll, ~poll seconds
    # in), so the watchdog can only confirm-and-fire before the adapter deadline when
    # it has two polls of room (timeout-poll alone fires AT the deadline = still dead
    # code, proven by execution). The env override is clamped the SAME way so an
    # operator-set env can never reintroduce the inversion.
    # Reject non-finite timeouts (NaN/inf) as well as <= 0 (codex re-review): a NaN
    # timeout slips past a bare <=0 check (nan comparisons are False) and would yield
    # an unclamped active watchdog. Same idiom as _float_env_or_default below.
    if (
        timeout_seconds != timeout_seconds
        or timeout_seconds in {float("inf"), float("-inf")}
        or timeout_seconds <= 0
    ):
        return None
    poll = _float_env_or_default(
        _CODEX_STALL_WATCHDOG_POLL_ENV,
        float(_CODEX_STALL_WATCHDOG_DEFAULT_POLL_SECONDS),
    )
    if poll is None or poll <= 0:
        return None
    # F2: reject env values <= 0 (and NaN/inf via _float_env_or_default) -> fall
    # back to the 150 default. The chosen threshold is then F1-clamped below.
    env_threshold = _float_env_or_default(_CODEX_STALL_WATCHDOG_THRESHOLD_ENV, None)
    if env_threshold is not None and env_threshold > 0:
        chosen_threshold = env_threshold
    else:
        chosen_threshold = float(_CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS)
    # F1: cap the chosen threshold so it fires BEFORE the adapter deadline. Two polls
    # of room (not one): the dead-signature needs 2 samples, anchored at the first
    # dead poll, so timeout-poll would only confirm AT the deadline (dead code).
    effective_threshold = min(chosen_threshold, float(timeout_seconds) - 2 * poll)
    # Require room for at least 2 health samples before the deadline; otherwise the
    # run is too short to sample a dead-signature, so the adapter timeout is itself
    # the fast-fail -> watchdog OFF.
    if effective_threshold < 2 * poll:
        return None
    return _CodexStallWatchdogConfig(threshold_seconds=effective_threshold, poll_seconds=poll)


def _float_env_or_default(name: str, default: float | None) -> float | None:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def _codex_cli_watchdog_applies(args: Sequence[str]) -> bool:
    return bool(args) and Path(str(args[0])).name == "codex"


def _communicate_with_optional_codex_stall_watchdog(
    proc: "subprocess.Popen[str]",
    args: Sequence[str],
    *,
    timeout_seconds: int | float,
    watchdog_config: _CodexStallWatchdogConfig | None = None,
    health_probe: Callable[["subprocess.Popen[str]"], _CodexCliHealth | None] | None = None,
    clock: Callable[[], float] | None = None,
) -> tuple[str | None, str | None]:
    if not _codex_cli_watchdog_applies(args):
        return proc.communicate(timeout=timeout_seconds)
    config = watchdog_config
    if config is None:
        config = _codex_stall_watchdog_config(timeout_seconds)
    if config is None:
        return proc.communicate(timeout=timeout_seconds)

    health = health_probe or _codex_cli_health_sample
    monotonic = clock or time.monotonic
    deadline = monotonic() + float(timeout_seconds)
    previous_sample = health(proc)
    dead_signature_since: float | None = None

    while True:
        now = monotonic()
        remaining = deadline - now
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd=tuple(str(part) for part in args), timeout=timeout_seconds)
        try:
            return proc.communicate(timeout=min(config.poll_seconds, remaining))
        except subprocess.TimeoutExpired as exc:
            now = monotonic()
            if now >= deadline:
                raise
            current_sample = health(proc)
            if _codex_dead_connection_signature(previous_sample, current_sample):
                if dead_signature_since is None:
                    dead_signature_since = now
                if now - dead_signature_since >= config.threshold_seconds:
                    stall_exc = subprocess.TimeoutExpired(
                        cmd=_safe_timeout_cmd(args),
                        timeout=config.threshold_seconds,
                    )
                    setattr(stall_exc, _TIMEOUT_REAP_REASON_ATTR, "stall")
                    # SUPPORT FACTS ONLY (TrackB 0619 step E): carry the last
                    # health-sample triple + how long the dead-connection signature
                    # persisted so the reap journal can record WHY this was reaped as
                    # a connect-stall. No Agent-fault label, no Link decision -- these
                    # are raw observations of the dead worker at reap time.
                    setattr(
                        stall_exc,
                        _STALL_DEAD_SIGNATURE_ATTR,
                        _stall_dead_signature_facts(current_sample, now - dead_signature_since),
                    )
                    raise stall_exc from exc
            else:
                dead_signature_since = None
            previous_sample = current_sample


def _safe_timeout_cmd(args: Sequence[str]) -> tuple[str, ...]:
    executable = Path(str(args[0])).name if args else "codex"
    if executable == "codex":
        return ("codex", "exec")
    return (executable,)


def _codex_dead_connection_signature(
    previous_sample: _CodexCliHealth | None,
    current_sample: _CodexCliHealth | None,
) -> bool:
    if previous_sample is None or current_sample is None:
        return False
    if not previous_sample.process_running or not current_sample.process_running:
        return False
    if previous_sample.child_count != 0 or current_sample.child_count != 0:
        return False
    if previous_sample.established_socket_count != 0 or current_sample.established_socket_count != 0:
        return False
    if current_sample.cpu_seconds != previous_sample.cpu_seconds:
        return False
    return True


def _codex_cli_health_sample(proc: "subprocess.Popen[str]") -> _CodexCliHealth | None:
    if proc.poll() is not None:
        return _CodexCliHealth(
            process_running=False,
            child_count=0,
            established_socket_count=0,
            cpu_seconds=0.0,
        )
    rows = _process_snapshot_rows()
    if rows is None:
        return None
    root_pid = int(proc.pid)
    root_row = rows.get(root_pid)
    if root_row is None:
        return None
    related_pids = _related_process_ids(root_pid, root_row.pgid, rows)
    if not related_pids:
        return None
    established_sockets = _established_tcp_socket_count(related_pids)
    if established_sockets is None:
        return None
    cpu_seconds = sum(rows[pid].cpu_seconds for pid in related_pids if pid in rows)
    return _CodexCliHealth(
        process_running=True,
        child_count=len(related_pids - {root_pid}),
        established_socket_count=established_sockets,
        cpu_seconds=cpu_seconds,
    )


def _process_snapshot_rows() -> dict[int, _ProcessSnapshotRow] | None:
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,pgid=,time="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    rows: dict[int, _ProcessSnapshotRow] = {}
    for line in completed.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) != 4:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            pgid = int(parts[2])
        except ValueError:
            continue
        cpu_seconds = _parse_ps_cpu_seconds(parts[3])
        if cpu_seconds is None:
            continue
        rows[pid] = _ProcessSnapshotRow(ppid=ppid, pgid=pgid, cpu_seconds=cpu_seconds)
    return rows


def _parse_ps_cpu_seconds(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    days = 0
    if "-" in text:
        day_text, text = text.split("-", 1)
        try:
            days = int(day_text)
        except ValueError:
            return None
    parts = text.split(":")
    try:
        if len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            seconds = float(parts[1])
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
        else:
            return None
    except ValueError:
        return None
    return float((days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60)) + seconds


def _related_process_ids(
    root_pid: int,
    root_pgid: int,
    rows: Mapping[int, _ProcessSnapshotRow],
) -> set[int]:
    related = {pid for pid, row in rows.items() if row.pgid == root_pgid}
    related.add(root_pid)
    frontier = [root_pid]
    while frontier:
        parent = frontier.pop()
        for pid, row in rows.items():
            if row.ppid == parent and pid not in related:
                related.add(pid)
                frontier.append(pid)
    return {pid for pid in related if pid in rows}


def _established_tcp_socket_count(pids: set[int]) -> int | None:
    if not pids:
        return None
    try:
        completed = subprocess.run(
            [
                "lsof",
                "-nP",
                "-a",
                "-p",
                ",".join(str(pid) for pid in sorted(pids)),
                "-iTCP",
                "-sTCP:ESTABLISHED",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode not in {0, 1}:
        return None
    if not completed.stdout.strip():
        if completed.stderr.strip():
            return None
        return 0
    return sum(
        1
        for line in completed.stdout.splitlines()[1:]
        if "TCP" in line and "ESTABLISHED" in line
    )


def _timeout_expired_reap_reason(exc: subprocess.TimeoutExpired) -> str:
    reason = getattr(exc, _TIMEOUT_REAP_REASON_ATTR, "")
    return reason if reason == "stall" else "timeout"


def _stall_dead_signature_facts(
    last_sample: _CodexCliHealth | None,
    dead_signature_seconds: float,
) -> dict[str, Any]:
    """Raw dead-connection observation for the reap journal (SUPPORT FACTS ONLY).

    Records the last health-sample triple (child_count, established_socket_count,
    cpu_seconds) the watchdog saw plus how long the dead-connection signature
    persisted before the threshold tripped. No fault attribution, no Movement
    decision -- only the numbers, so an operator can see the dead worker forensics.
    """

    facts: dict[str, Any] = {
        "dead_signature_seconds": round(float(dead_signature_seconds), 3),
    }
    if last_sample is not None:
        facts["child_count"] = last_sample.child_count
        facts["established_socket_count"] = last_sample.established_socket_count
        facts["cpu_seconds"] = last_sample.cpu_seconds
    return facts


def _timeout_expired_stall_dead_signature(
    exc: subprocess.TimeoutExpired,
) -> Mapping[str, Any] | None:
    facts = getattr(exc, _STALL_DEAD_SIGNATURE_ATTR, None)
    if isinstance(facts, Mapping):
        return facts
    return None


def _reap_timeout_process_group(proc: "subprocess.Popen[str]", *, reason: str) -> None:
    if reason == "stall":
        _signal_process_group(proc, signal.SIGTERM)
        try:
            proc.wait(timeout=_CODEX_STALL_WATCHDOG_SIGTERM_GRACE_SECONDS)
            return
        except subprocess.TimeoutExpired:
            pass
    _signal_process_group(proc, signal.SIGKILL)
    proc.wait()


def _signal_process_group(proc: "subprocess.Popen[str]", sig: signal.Signals) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def _run_text_cli_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> LocalCliCompleted:
    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd),
        text=True,
        # stdin=DEVNULL gives the child an IMMEDIATE EOF on fd 0. codex/claude/gemini
        # `exec` unconditionally read() stdin at startup; if BRICK inherited a pipe/FIFO
        # whose write-end is held open with no data and no EOF, that startup read blocks
        # FOREVER (0 CPU, 0 sockets) to the adapter timeout -- the "connect-stall". BRICK
        # passes the prompt as a positional/flag argv item (never via stdin), so DEVNULL
        # cannot break any input path. This is the PRIMARY structural cure; the watchdog
        # stays as defense-in-depth for genuine network hangs.
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    _journal_spawn(proc, args, cwd)
    try:
        stdout, stderr = _communicate_with_optional_codex_stall_watchdog(
            proc,
            args,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        reason = _timeout_expired_reap_reason(exc)
        _reap_timeout_process_group(proc, reason=reason)
        _journal_reap(
            proc,
            reason=reason,
            dead_signature=_timeout_expired_stall_dead_signature(exc),
        )
        raise
    _journal_reap(proc, reason="exit")
    return LocalCliCompleted(
        args=tuple(str(part) for part in args),
        return_code=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
    )


def _raw_text_from_completed(
    label: str,
    output_text: str,
    completed: LocalCliCompleted,
) -> str:
    if completed.return_code != 0:
        raise ValueError(f"{label} command returned non-zero")
    if not output_text.strip():
        raise ValueError(f"{label} was empty")
    _reject_secret_text(label, output_text)
    return output_text


# Fixed path for the append-only adapter spawn journal. The env override exists
# ONLY so a test/probe can redirect it off the shared default; live use leaves it
# unset. Mirrors the native-dispatch context-path seam (single fixed /tmp default
# + BRICK_*_PATH override). RECORD-ONLY: this is a forensic trace of spawn/reap so
# an orphaned provider grandchild is traceable -- it is NOT a reaper.
_ADAPTER_SPAWN_JOURNAL_DEFAULT_PATH = os.path.join("/tmp", "brick-adapter-spawn-journal.jsonl")


def _adapter_spawn_journal_path() -> str:
    """Resolve the adapter spawn-journal file path (env-overridable seam)."""
    override = os.environ.get("BRICK_ADAPTER_SPAWN_JOURNAL_PATH")
    return override if override else _ADAPTER_SPAWN_JOURNAL_DEFAULT_PATH


def _journal_write(record: Mapping[str, Any]) -> None:
    """Append one JSONL record. Best-effort: NEVER raises into the adapter path."""
    try:
        line = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        path = _adapter_spawn_journal_path()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except Exception:
        # Forensic journal only -- a journal IO failure must not break a spawn.
        return


def _journal_spawn(proc: "subprocess.Popen[str]", args: Sequence[str], cwd: Path) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = -1
    _journal_write(
        {
            "event": "spawn",
            "pid": proc.pid,
            "pgid": pgid,
            "argv0": Path(str(args[0])).name if args else "",
            "cwd": str(cwd),
            "started_at": time.time(),
        }
    )


def _journal_reap(
    proc: "subprocess.Popen[str]",
    *,
    reason: str,
    dead_signature: Mapping[str, Any] | None = None,
) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = -1
    record: dict[str, Any] = {
        "event": "reap",
        "pid": proc.pid,
        "pgid": pgid,
        "reason": reason,
        "return_code": proc.returncode,
        "reaped_at": time.time(),
    }
    if dead_signature is not None:
        # SUPPORT FACTS ONLY: last health triple + dead-signature duration the
        # connect-stall watchdog observed. Forensic trace, not a fault label.
        record["dead_signature"] = dict(dead_signature)
    _journal_write(record)


def _run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    env: Mapping[str, str] | None = None,
) -> LocalCliCompleted:
    _validate_command_args(args)
    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        text=True,
        # stdin=DEVNULL gives the child an IMMEDIATE EOF on fd 0. codex/claude/gemini
        # `exec` unconditionally read() stdin at startup; if BRICK inherited a pipe/FIFO
        # whose write-end is held open with no data and no EOF, that startup read blocks
        # FOREVER (0 CPU, 0 sockets) to the adapter timeout -- the "connect-stall". BRICK
        # passes the prompt as a positional/flag argv item (never via stdin), so DEVNULL
        # cannot break any input path. This is the PRIMARY structural cure; the watchdog
        # stays as defense-in-depth for genuine network hangs.
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,  # proc becomes its own process-group leader (setsid)
    )
    _journal_spawn(proc, args, cwd)  # best-effort; never raises
    try:
        stdout, stderr = _communicate_with_optional_codex_stall_watchdog(
            proc,
            args,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        reason = _timeout_expired_reap_reason(exc)
        _reap_timeout_process_group(proc, reason=reason)
        _journal_reap(
            proc,
            reason=reason,
            dead_signature=_timeout_expired_stall_dead_signature(exc),
        )
        # SAME TimeoutExpired re-raised. run.py _adapter_error_kind reads the
        # reap_reason tag: a 'stall' reap -> 'local_cli_connect_stall', a plain
        # timeout -> 'local_cli_timeout' (both route to the same adapter-error HOLD).
        raise
    _journal_reap(proc, reason="exit")
    return LocalCliCompleted(
        args=tuple(str(part) for part in args),
        return_code=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
    )


def _validate_command_args(args: Sequence[str]) -> None:
    if not args:
        raise ValueError("local CLI args must not be empty")
    executable = Path(str(args[0])).name
    if executable not in {"codex", "claude", "gemini"}:
        raise ValueError("local CLI executable is not allowlisted")
    for item in args:
        text = str(item)
        if "\x00" in text or "\n" in text:
            raise ValueError("local CLI arg contains unsupported control text")
        _reject_secret_text("local_cli_arg", text)


def _build_prompt(request: AgentAdapterRequest, spec: LocalCliSpec) -> str:
    required_labels = _required_return_shape_fields(request.required_return_shape)
    waiver_labels = _return_field_waivers(required_labels)
    reserved_top_level_return_keys = ", ".join(sorted(_TOP_LEVEL_VERDICT_KEYS))
    rules = [
        "Do not claim source truth.",
        "Do not judge success or quality.",
        "Do not choose Link Movement.",
        "Do not run git commit or git push.",
        "Do not access or print setup tokens, auth bodies, credentials, or raw provider sessions.",
        "Return concise text only.",
        "Return one JSON object. The object may include only required_return_shape fields and listed return_field_waivers.",
        "Do not use these reserved keys at the top level of the returned JSON object: "
        + reserved_top_level_return_keys
        + ".",
        "If evidence is missing, put it under blocked_or_missing_evidence or not_proven inside that JSON object; do not invent fields.",
    ]
    if "transition_concern_evidence" in required_labels:
        rules.extend(_transition_concern_schema_rules())
    if agent_request_effective_write(request):
        rules.extend(
            (
                "You may edit files only inside the Brick-declared write_scope.allowed_paths.",
                "Do not edit files matching write_scope.forbidden_paths.",
                "Do not execute hooks or provider SDKs.",
                "Return non-judgmental support evidence only.",
            )
        )
    elif agent_request_read_tier(request):
        admitted = ", ".join(sorted(_read_tier_policy_refs_for_request(request)))
        rules.extend(
            (
                "You may use read-only repository inspection tools only: read files, inspect diffs, search with grep/glob, and run checker commands.",
                f"Read tier is admitted for this adapter only by these Agent tool policies: {admitted}.",
                "Do not edit, create, delete, or write files.",
                "Do not run git mutations, including commit, push, checkout, reset, merge, rebase, or stash.",
                "Do not execute hooks or provider SDKs.",
                "Do not use network beyond the selected provider itself.",
                "Return non-judgmental support evidence only.",
            )
        )
    else:
        rules.append("Do not use tools or hooks.")
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        if agent_request_read_tier(request):
            rules.append(
                "Gemini local read tier may use only read_file, glob, grep_search, search_file_content, list_directory, and read_many_files through the read-only admin policy; write and shell tools remain blocked."
            )
        rules.extend(
            (
                "Do not call exit_plan_mode or any plan-finalization tool.",
                "Do not write output_packet_ref; it is an evidence label, not a file path.",
                "Return the requested evidence in the CLI response text only.",
            )
        )
    prompt = {
        "task": "Return provider-neutral Brick Protocol support evidence only.",
        "rules": rules,
        "building_id": request.building_id,
        "agent_object_ref": request.agent_object_ref,
        "adapter_ref": spec.adapter_ref,
        "selected_model_ref": request.selected_model_ref,
        "prompt_refs": list(request.prompt_refs),
        "skill_refs": list(request.skill_refs),
        "hook_refs": list(request.hook_refs),
        "tool_policy_refs": list(request.tool_policy_refs),
        "discipline_refs": list(request.discipline_refs),
        "input_packet_ref": request.input_packet_ref,
        "output_packet_ref": request.output_packet_ref,
        "work_statement": request.work_statement,
        "comparison_rule": request.comparison_rule,
        "required_return_shape": request.required_return_shape,
        "required_return_labels": list(required_labels),
        "return_field_waivers": list(waiver_labels),
        "source_fact_bodies": _source_fact_bodies_for_prompt(request, spec),
        "link_handoff_refs": dict(request.link_handoff_refs),
        "agent_instruction_packet": _instruction_packet_for_prompt(request, spec),
        "write_scope": dict(request.write_scope),
        "building_session_ref": request.building_session_ref,
        "session_scope_ref": request.session_scope_ref,
        "session_continuity_mode": request.session_continuity_mode,
    }
    return json.dumps(prompt, ensure_ascii=True, sort_keys=True)


def _instruction_packet_for_prompt(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> Mapping[str, Any]:
    if not request.agent_instruction_packet:
        return {}
    return dict(request.agent_instruction_packet)


def _transition_concern_schema_rules() -> tuple[str, ...]:
    allowed_keys = ", ".join(sorted(_TRANSITION_CONCERN_ALLOWED_KEYS))
    allowed_kinds = ", ".join(sorted(_TRANSITION_CONCERN_KINDS))
    return (
        "If you return transition_concern_evidence, it must be one JSON object using only these keys: "
        + allowed_keys
        + ".",
        "transition_concern_evidence.concern_ref must start with 'transition-concern:'.",
        "transition_concern_evidence.concern_kind must be one of: " + allowed_kinds + ".",
        "transition_concern_evidence.binding must be the JSON literal false.",
        "transition_concern_evidence.reason_refs must be a non-empty list of strings.",
        "transition_concern_evidence.related_boundary_refs may name only Brick boundaries such as brick-..., brick:..., brick-boundary:..., brick-instance:..., or building-boundary:....",
        "For a reproduced defect, set related_boundary_refs to the upstream work node (not yourself/sentinel); put env/runtime constraints in not_proven, not a concern; reason_refs must not be /tmp filesystem paths.",
        "Do not put observation, disposition_note, candidate_pending_target_ref, secondary_concern_kind, route_target, target_ref, or movement inside transition_concern_evidence.",
    )


def _extract_required_return_fields(
    output_text: str,
    required_return_shape: Any,
) -> Mapping[str, Any]:
    """Lift strictly structured Agent return fields from local CLI text.

    This is a mechanical adapter normalization step. It only accepts a JSON
    object returned by the Agent and only copies keys requested by
    Brick.required_return_shape. It never infers Movement, target, success,
    failure, approval, or quality fields from unstructured prose.
    """

    # Every declared, forbidden-filtered field (U2-3 richer kind shapes). The
    # earlier `if field in _RETURN_LABEL_FIELDS` clause dropped fields the kind's
    # required_return_shape declares but the label set never enumerated (e.g.
    # work: received_work_ref / changed_files / commands_run / handoff_refs), so a
    # model that DID return them lost them from AgentFact.returned and the gate
    # reported them missing. This is safe: forbidden keys are stripped upstream
    # (_required_return_shape_fields) AND re-checked downstream
    # (_validate_returned_payload); an unknown declared field passes through
    # _clean_return_field_value's else-branch verbatim; the JSON-shape guard
    # (_structured_return_payload) is unchanged.
    fields = _allowed_return_fields(required_return_shape)
    if not fields:
        return {}
    payload = _structured_return_payload(output_text)
    if payload is None:
        return {}
    extracted: dict[str, Any] = {}
    for field in fields:
        if field not in payload:
            continue
        extracted[field] = _clean_return_field_value(field, payload[field])
    return extracted


def _merge_structured_return_fields(
    returned: dict[str, Any],
    extracted: Mapping[str, Any],
) -> None:
    for key, value in extracted.items():
        if key in {"evidence_refs", "not_proven", "proof_limits"} and key in returned:
            returned[key] = list(_merge_texts(returned[key], value))
            continue
        if key not in returned:
            returned[key] = value


def _required_return_shape_fields(value: Any) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            field
            for field in parse_required_return_shape(value)
            if field not in _ALWAYS_SECRET_KEYS
            and field not in _TOP_LEVEL_VERDICT_KEYS
        )
    )


def _return_field_waivers(required_fields: Iterable[str]) -> tuple[str, ...]:
    waiver_fields: list[str] = []
    for field in required_fields:
        waiver_fields.extend(_RETURN_WAIVER_FIELDS_BY_REQUIRED.get(field, ()))
    return tuple(dict.fromkeys(waiver_fields))


def _allowed_return_fields(value: Any) -> tuple[str, ...]:
    required = _required_return_shape_fields(value)
    return tuple(dict.fromkeys((*required, *_return_field_waivers(required))))


def _structured_return_payload(output_text: str) -> Mapping[str, Any] | None:
    text = output_text.strip()
    parsed = _try_json_value(_strip_code_fence(text))
    if isinstance(parsed, Mapping):
        return parsed
    for match in re.finditer(r"(?s)```(?:json)?\s*(.*?)```", output_text):
        parsed = _try_json_value(match.group(1).strip())
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _clean_return_field_value(field: str, value: Any) -> Any:
    if field in _RETURN_JSON_FIELDS:
        return value
    if field in _RETURN_LIST_FIELDS:
        if isinstance(value, list):
            return value
        if isinstance(value, Mapping):
            return [dict(value)]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return value
    return value


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text


_GEMINI_CLIENT_ERROR_PATH_RE = re.compile(
    r"""[^\s'"`<>]*gemini-client-error-[^\s'"`<>]*\.json"""
)


def _local_cli_nonzero_error_message(spec: LocalCliSpec, completed: LocalCliCompleted) -> str:
    parts = [
        "local CLI adapter command returned non-zero",
        f"adapter_ref={spec.adapter_ref}",
        f"return_code={completed.return_code}",
    ]
    stderr_excerpt = _redacted_diagnostic_excerpt(completed.stderr, limit=420)
    if stderr_excerpt:
        parts.append(f"stderr_excerpt={stderr_excerpt}")
    stdout_error_excerpt = _stdout_error_excerpt(completed.stdout)
    if stdout_error_excerpt:
        parts.append(f"stdout_error_excerpt={stdout_error_excerpt}")
    stderr_error_path = _stderr_gemini_client_error_path(completed.stderr)
    if stderr_error_path:
        parts.append(f"stderr_error_path={stderr_error_path}")
    return "; ".join(parts)


def _stdout_error_excerpt(stdout: str) -> str:
    payload = _try_json_value(stdout)
    if not isinstance(payload, Mapping) or "error" not in payload:
        return ""
    error = payload["error"]
    if isinstance(error, str):
        text = error
    else:
        text = json.dumps(error, ensure_ascii=True, sort_keys=True)
    return _redacted_diagnostic_excerpt(text, limit=360)


def _stderr_gemini_client_error_path(stderr: str) -> str:
    match = _GEMINI_CLIENT_ERROR_PATH_RE.search(stderr)
    if not match:
        return ""
    return _redacted_diagnostic_excerpt(match.group(0), limit=240)


def _redacted_diagnostic_excerpt(value: str, *, limit: int) -> str:
    text = value
    for pattern in (*_RAW_SECRET_PATTERNS, *_RAW_SESSION_PATTERNS):
        text = pattern.sub("[redacted]", text)
    return _safe_excerpt(text, limit=limit)


def _try_json_value(value: str) -> Any:
    text = value.strip()
    if not text or text[0] not in "[{":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_output_text(spec: LocalCliSpec, completed: LocalCliCompleted) -> str:
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        return _extract_gemini_response(completed.stdout)
    if spec.adapter_ref == ADAPTER_CLAUDE_LOCAL and completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return completed.stdout
        if isinstance(payload, Mapping):
            for key in ("response", "text", "content", "message", "result"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return completed.stdout
    return completed.stdout or completed.stderr


def _source_fact_bodies_for_prompt(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> Mapping[str, str]:
    limit = (
        _GEMINI_SOURCE_FACT_BODY_LIMIT
        if spec.adapter_ref == ADAPTER_GEMINI_LOCAL
        else _SOURCE_FACT_BODY_LIMIT
    )
    return {
        ref: safe_source_fact_body(body, limit=limit)
        for ref, body in request.source_fact_bodies.items()
    }


def _extract_gemini_response(stdout: str) -> str:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini local CLI output was not JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Gemini local CLI JSON output must be an object")
    stats = payload.get("stats")
    nonread_tool_names = _gemini_nonread_tool_names(stats)
    if nonread_tool_names:
        raise ValueError(
            "Gemini local CLI reported non-read tool calls; refusing support payload: "
            + ", ".join(nonread_tool_names)
        )
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Gemini local CLI JSON output missing response text")
    return response


def _gemini_api_key_env_present(env: Mapping[str, str]) -> bool:
    return any((env.get(env_var) or "").strip() for env_var in _GEMINI_API_KEY_ENV_VARS)


def _gemini_nonread_tool_names(stats: Any) -> tuple[str, ...]:
    if not isinstance(stats, Mapping):
        return ()
    tools = stats.get("tools")
    if not isinstance(tools, Mapping):
        return ()
    by_name = tools.get("byName")
    if by_name is None:
        return ()
    names: set[str] = set()
    if isinstance(by_name, Mapping):
        names.update(str(name) for name in by_name)
    elif isinstance(by_name, Sequence) and not isinstance(by_name, (str, bytes, bytearray)):
        for item in by_name:
            if isinstance(item, Mapping):
                raw_name = item.get("name") or item.get("toolName") or item.get("tool_name")
                if raw_name:
                    names.add(str(raw_name))
            elif item:
                names.add(str(item))
    else:
        raise ValueError("Gemini local CLI stats.tools.byName must be an object or list")
    return tuple(sorted(name for name in names if name not in _GEMINI_READ_TOOL_NAMES))


def _gemini_tool_call_count(payload: Mapping[str, Any]) -> int:
    stats = payload.get("stats")
    if not isinstance(stats, Mapping):
        return 0
    tools = stats.get("tools")
    if not isinstance(tools, Mapping):
        return 0
    total_calls = tools.get("totalCalls", 0)
    if isinstance(total_calls, bool):
        return int(total_calls)
    if isinstance(total_calls, int):
        return total_calls
    if isinstance(total_calls, float) and total_calls.is_integer():
        return int(total_calls)
    if isinstance(total_calls, str) and total_calls.strip().isdigit():
        return int(total_calls.strip())
    raise ValueError("Gemini local CLI tool-call count must be numeric")


def _validate_returned_payload(label: str, value: Any, *, depth: int = 0) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = _normalize(raw_key)
            # Secret/session-bearing key names stay recursive. A nested key can
            # still structure credential material even when it is not an
            # authority assertion.
            if key in _ALWAYS_SECRET_KEYS:
                raise ValueError(f"{label} contains forbidden return key {raw_key!r}")
            if depth == 0 and key in _TOP_LEVEL_VERDICT_KEYS:
                raise ValueError(f"{label} contains forbidden return key {raw_key!r}")
            _validate_returned_payload(f"{label}.{raw_key}", child, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_returned_payload(f"{label}[{index}]", child, depth=depth + 1)
    elif isinstance(value, str):
        _reject_secret_text(label, value)


def _safe_excerpt(value: str, *, limit: int = 600) -> str:
    text = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _reject_secret_text(label: str, value: str) -> None:
    if any(pattern.search(value) for pattern in _RAW_SECRET_PATTERNS):
        raise ValueError(f"{label} contains raw credential-looking text")
    if any(pattern.search(value) for pattern in _RAW_SESSION_PATTERNS):
        raise ValueError(f"{label} contains raw provider session-looking text")


def _reject_forbidden_text(label: str, value: str) -> None:
    if value:
        _reject_secret_text(label, value)


def _clean_optional_text(label: str, value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    return value.strip()


def _validate_adapter_ref(value: Any) -> str:
    adapter_ref = _clean_optional_text("adapter_ref", value)
    if not adapter_ref:
        raise ValueError("adapter_ref must not be blank")
    if adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError("adapter_ref is retired and not admitted as an active adapter")
    if adapter_ref not in ALLOWED_ADAPTER_REFS:
        raise ValueError("adapter_ref is not admitted for SIMPLE-RUN-0")
    return adapter_ref


def _clean_source_fact_bodies(value: Any) -> Mapping[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("source_fact_bodies must be a mapping")
    cleaned: dict[str, str] = {}
    for raw_ref, raw_body in value.items():
        ref = _clean_optional_text("source_fact_bodies ref", raw_ref)
        body = _clean_optional_text(f"source_fact_bodies.{ref}", raw_body)
        if not ref:
            raise ValueError("source_fact_bodies refs must not be blank")
        _reject_forbidden_text("source_fact_bodies ref", ref)
        cleaned[ref] = safe_source_fact_body(body)
    return cleaned


def _clean_link_handoff_refs(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("link_handoff_refs must be a mapping")
    cleaned = _clean_json_value("link_handoff_refs", value)
    if not isinstance(cleaned, Mapping):
        raise TypeError("link_handoff_refs must clean to a mapping")
    return cleaned


def _clean_agent_instruction_packet(
    value: Any,
    *,
    agent_object_ref: str,
) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("agent_instruction_packet must be a mapping")
    if not value:
        return {}
    cleaned = _clean_instruction_json_value("agent_instruction_packet", value)
    if not isinstance(cleaned, Mapping):
        raise TypeError("agent_instruction_packet must clean to a mapping")
    if cleaned.get("kind") != "agent-instruction-packet":
        raise ValueError("agent_instruction_packet.kind must be agent-instruction-packet")
    if cleaned.get("agent_object_ref") != agent_object_ref:
        raise ValueError(
            "agent_instruction_packet.agent_object_ref must match AgentAdapterRequest.agent_object_ref"
        )
    return cleaned


def _clean_write_scope(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("write_scope must be a mapping")
    cleaned = _clean_json_value("write_scope", value)
    if not isinstance(cleaned, Mapping):
        raise TypeError("write_scope must clean to a mapping")
    return cleaned


def _validate_effective_write_request(
    request: AgentAdapterRequest,
    write_scope: Mapping[str, Any],
) -> None:
    # UNION of two orthogonal write-hardening lines:
    #  - main (6/4): effective write requires Brick write_scope + read-write tool
    #    policy + observed-write adapter mapping + write observation; write authority
    #    is NOT owned by the adapter name or by `dev` alone (a non-dev Agent with the
    #    full intersection CAN write -- see kernel _agent_effective_write_probe).
    #  - branch (adapter-capability-rehome): emits the rehome reason tokens
    #    (missing_brick_write_scope / legacy_adapter_identity_only_not_authority /
    #    missing_agent_write_policy / missing_adapter_write_capability) that the
    #    surviving agent_axis_behavioral profile + case_runners assert.
    # The dev-name check is kept ONLY as a message discriminator for the
    # policy-missing path; it is NOT an authority gate (non-dev + full intersection
    # still passes), so main's "not by dev alone" hardening is preserved.
    if not write_scope:
        raise ValueError(
            "missing_brick_write_scope: Brick row write_scope is required for a "
            "write-capable selected adapter"
        )
    if READ_WRITE_TOOL_POLICY_REF not in request.tool_policy_refs:
        if request.agent_object_ref != "agent-object:dev":
            raise ValueError(
                "legacy_adapter_identity_only_not_authority: adapter_capabilities "
                "write does not authorize a non-dev Agent Object; "
                "write_scope requires tool-policy:read-write-scoped"
            )
        raise ValueError(
            "missing_agent_write_policy: Agent tool_policy_refs must include "
            "tool-policy:read-write-scoped for a write attempt; "
            "write_scope requires tool-policy:read-write-scoped"
        )
    if not _adapter_ref_supports_observed_write(request.adapter_ref):
        raise ValueError(
            "missing_adapter_write_capability: write_scope requires adapter mapping "
            "that supports observed workspace write"
        )
    _validate_write_scope("write_scope", write_scope)


def _adapter_ref_supports_observed_write(adapter_ref: str) -> bool:
    return adapter_ref in _OBSERVED_WRITE_ADAPTER_REFS


def _mark_effective_write_observation_path(request: AgentAdapterRequest, cwd: Path) -> None:
    if agent_request_effective_write(request):
        object.__setattr__(
            request,
            _EFFECTIVE_WRITE_OBSERVATION_MARKER_ATTR,
            cwd.resolve().as_posix(),
        )


def _consume_effective_write_observation_path(
    request: AgentAdapterRequest,
    *,
    cwd: Path,
) -> None:
    if not agent_request_effective_write(request):
        return
    observed_cwd = getattr(request, _EFFECTIVE_WRITE_OBSERVATION_MARKER_ATTR, "")
    if not observed_cwd:
        raise ValueError("effective write requires write observation before adapter execution")
    if observed_cwd != cwd.resolve().as_posix():
        raise ValueError("effective write observation cwd must match adapter execution cwd")
    object.__setattr__(request, _EFFECTIVE_WRITE_OBSERVATION_MARKER_ATTR, "")


def _validate_write_scope(label: str, value: Mapping[str, Any]) -> None:
    allowed = value.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed:
        raise ValueError(f"{label}.allowed_paths must be a non-empty list")
    for index, item in enumerate(allowed):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}.allowed_paths[{index}] must be non-empty text")
        _reject_forbidden_write_path(f"{label}.allowed_paths[{index}]", item)
        _reject_bare_dir_write_path(f"{label}.allowed_paths[{index}]", item)

    forbidden = value.get("forbidden_paths")
    if not isinstance(forbidden, list):
        raise TypeError(f"{label}.forbidden_paths must be a list")
    for index, item in enumerate(forbidden):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}.forbidden_paths[{index}] must be non-empty text")
        _reject_secret_text(f"{label}.forbidden_paths[{index}]", item)
        _reject_bare_dir_write_path(f"{label}.forbidden_paths[{index}]", item)

    for key in ("commit_allowed", "push_allowed"):
        if value.get(key) is True:
            raise ValueError(f"{label}.{key} must not be true")


def _reject_forbidden_write_path(label: str, value: str) -> None:
    text = value.strip().replace("\\", "/")
    lowered = text.lower()
    _reject_secret_text(label, text)
    if (
        lowered == ".git"
        or lowered.startswith(".git/")
        or lowered.startswith("/")
        or lowered.startswith("../")
        or "/../" in lowered
        or lowered in {".env", "env"}
        or lowered.endswith((".pem", ".key"))
        or _path_has_forbidden_write_segment(lowered)
    ):
        raise ValueError(f"{label} is not admitted for write_scope")


def _reject_bare_dir_write_path(label: str, value: str) -> None:
    """Fail closed on a bare-directory write_scope entry.

    ``support/operator/write_observation.py:_path_matches_scope`` matches a
    changed file against an entry via ``fnmatch`` OR exact-path equality
    (``path == pattern.rstrip("/")``). A bare directory with no glob char (e.g.
    ``"support/"``) therefore matches ONLY the literal directory entry, never
    any nested file: it passes construction here but then silently HOLDs every
    nested file at observation time (write_observation_out_of_scope). Reject it
    at construction so the author fixes the declaration instead of getting a
    silent stall. Exact-file entries (``AGENTS.md``, ``brick/work.py``) and
    glob entries (``support/*``, ``support/**``) are unaffected.
    """

    text = value.strip().replace("\\", "/")
    if text.endswith("/") and "*" not in text:
        raise ValueError(
            f"{label} is a bare directory ({value!r}) that matches no nested "
            f"files at write_observation time; use a glob such as "
            f"'{text.rstrip('/')}/*' or '{text.rstrip('/')}/**' instead"
        )


def _path_has_forbidden_write_segment(path: str) -> bool:
    segments = [
        segment
        for segment in path.replace("\\", "/").replace(".", "/").replace("-", "/").replace("_", "/").split("/")
        if segment
    ]
    for segment in segments:
        if segment in {"auth", "credential", "credentials", "secret", "secrets", "token", "tokens"}:
            return True
    return False


def _clean_json_value(label: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = _clean_optional_text(f"{label} key", raw_key)
            if not key:
                raise ValueError(f"{label} keys must not be blank")
            _reject_secret_text(f"{label} key", key)
            cleaned[key] = _clean_json_value(f"{label}.{key}", child)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(f"{label}[{index}]", item) for index, item in enumerate(value)]
    if isinstance(value, str):
        text = _clean_optional_text(label, value)
        _reject_secret_text(label, text)
        return text
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"{label} must be JSON-compatible")


def _clean_instruction_json_value(label: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = _clean_optional_text(f"{label} key", raw_key)
            if not key:
                raise ValueError(f"{label} keys must not be blank")
            _reject_secret_text(f"{label} key", key)
            cleaned[key] = _clean_instruction_json_value(f"{label}.{key}", child)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [
            _clean_instruction_json_value(f"{label}[{index}]", item)
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        return safe_source_fact_body(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"{label} must be JSON-compatible")


def safe_source_fact_body(value: str, *, limit: int = _SOURCE_FACT_BODY_LIMIT) -> str:
    """Redact/truncate source bodies before carrying them as work-packet support."""

    body = _clean_optional_text("source_fact_body", value)
    for pattern in _RAW_SECRET_PATTERNS:
        body = pattern.sub("[REDACTED_RAW_CREDENTIAL]", body)
    for pattern in _RAW_SESSION_PATTERNS:
        body = pattern.sub("[REDACTED_PROVIDER_SESSION_REF]", body)
    if len(body) > limit:
        body = body[:limit] + "\n[TRUNCATED_SOURCE_FACT_BODY]"
    return body


def _merge_texts(*values: Any) -> tuple[str, ...]:
    merged: list[str] = []
    for value in values:
        for item in _text_tuple(value):
            if item not in merged:
                merged.append(item)
    return tuple(merged)


def _text_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, (list, tuple)):
        raise TypeError("text value must be text or text sequence")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"text value {index} must be non-empty text")
        result.append(item.strip())
    return tuple(result)


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "ADAPTER_CAPABILITY_LITERALS",
    "ADAPTER_CAPABILITY_READ",
    "ADAPTER_CAPABILITY_REVIEW",
    "ADAPTER_CAPABILITY_WRITE",
    "ADAPTER_CLAUDE_LOCAL",
    "ADAPTER_CHAT_SESSION",
    "ADAPTER_CODEX_LOCAL",
    "ADAPTER_GEMINI_API",
    "ADAPTER_GEMINI_LOCAL",
    "ADAPTER_LOCAL",
    "ALLOWED_ADAPTER_REFS",
    "ALLOWED_SESSION_CONTINUITY_MODES",
    "AgentAdapterRequest",
    "AgentAdapterParked",
    "AgentAdapterResult",
    "AgentBrainCallable",
    "CommandRunner",
    "LocalCliCompleted",
    "LocalCliProbe",
    "LocalCliSpec",
    "KNOWN_TOOL_POLICY_REFS",
    "LEADER_COORDINATION_TOOL_POLICY_REF",
    "READ_ONLY_TOOL_POLICY_REFS",
    "READ_WRITE_TOOL_POLICY_REF",
    "REVIEWER_READONLY_TOOL_POLICY_REF",
    "adapter_capabilities",
    "adapter_has_capability",
    "adapter_is_write_capable",
    "agent_request_effective_write",
    "agent_request_read_tier",
    "connect_agent_brain",
    "invoke_claude_text",
    "invoke_codex_text",
    "invoke_gemini_text",
    "local_cli_adapter_refs",
    "preflight_provider",
    "probe_local_cli_adapter",
    "project_model_ref_to_cli_arg",
    "safe_source_fact_body",
    "supported_model_ref_examples",
]
