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
from brick_protocol.brick.spec import WriteScope, WriteScopeContext


# adapter_constants is a PURE constant leaf (no intra-package imports) that
# agent_resources and agent/spec top-import at load. agent_adapter STAYS A
# FACADE for these symbols: checkers and other code reach them late-bound as
# agent_adapter.<sym>, so every moved name (public AND underscore-private) is
# re-exported explicitly here.
from .adapter_constants import (
    ADAPTER_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_GEMINI_API,
    ADAPTER_CHAT_SESSION,
    READ_WRITE_TOOL_POLICY_REF,
    REVIEWER_READONLY_TOOL_POLICY_REF,
    LEADER_COORDINATION_TOOL_POLICY_REF,
    WEB_CAPABLE_TOOL_POLICY_REF,
    READ_ONLY_TOOL_POLICY_REFS,
    READ_TIER_TOOL_POLICY_REFS,
    KNOWN_TOOL_POLICY_REFS,
    ADAPTER_CAPABILITY_READ,
    ADAPTER_CAPABILITY_WRITE,
    ADAPTER_CAPABILITY_REVIEW,
    ADAPTER_CAPABILITY_WEB,
    ADAPTER_CAPABILITY_LITERALS,
    MODEL_REF_DEFAULT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_GEMINI_DEFAULT,
    MODEL_REF_GEMINI_FLASH,
    MODEL_REF_GEMINI_LOCAL_FLASH,
    MODEL_PROVIDER_BY_ADAPTER,
    _RETIRED_WRITE_ADAPTER_REFS,
    _OBSERVED_WRITE_ADAPTER_REFS,
    ALLOWED_ADAPTER_REFS,
    _ADAPTER_CAPABILITIES,
    _REPO_ROOT,
)

_EFFECTIVE_WRITE_OBSERVATION_MARKER_ATTR = "_brick_protocol_effective_write_observed_cwd"
ALLOWED_SESSION_CONTINUITY_MODES = frozenset(
    {
        "none",
        "continue_if_available",
        "start_or_continue",
        "fork_from_available",
    }
)

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
# adapter_validation cluster (E2 split, extraction 2/7): Secret/text/JSON
# cleaning + payload guard relocated VERBATIM to support/connection/
# adapter_validation.py. EXPLICIT facade re-exports for EVERY moved symbol
# (public AND underscore-private) so late-bound agent_adapter.<sym> never breaks.
# _RAW_SESSION_PATTERNS + _SOURCE_FACT_BODY_LIMIT are still used by surviving
# agent_adapter helpers (_redacted_diagnostic_excerpt / _source_fact_bodies_for_prompt).
from .adapter_validation import (
    _RAW_SESSION_PATTERNS,
    _SOURCE_FACT_BODY_LIMIT,
    _clean_agent_instruction_packet,
    _clean_instruction_json_value,
    _clean_json_value,
    _clean_link_handoff_refs,
    _clean_optional_text,
    _clean_source_fact_bodies,
    _normalize,
    _reject_forbidden_text,
    _reject_secret_text,
    _safe_excerpt,
    _validate_returned_payload,
    safe_source_fact_body,
)

# FACADE re-export: the subprocess runner + codex connect-stall watchdog + spawn
# journal + token/text meter + provider preflight cluster now lives in
# adapter_subprocess. agent_adapter STAYS A FACADE for these symbols -- checkers,
# run.py, onboard.py and other call sites reach them late-bound as
# agent_adapter.<sym> (and via `from agent_adapter import <sym>`), so EVERY moved
# name (public AND underscore-private) is re-exported explicitly here. The
# stay-behind symbols those functions need at runtime (LocalCliCompleted, the
# preflight specs/hints, _reject_secret_text) are pulled by adapter_subprocess via
# direct-sibling / lazy-in-function imports, so there is no import cycle.
from .adapter_subprocess import (
    CODEX_TURN_COMPLETED_USAGE_KEYS,
    codex_assistant_text_from_json_stdout,
    codex_usage_from_json_stdout,
    preflight_provider,
    _ADAPTER_SPAWN_JOURNAL_DEFAULT_PATH,
    _CODEX_ASSISTANT_MESSAGE_EVENT_TYPES,
    _CODEX_ASSISTANT_MESSAGE_ITEM_TYPES,
    _CODEX_ASSISTANT_TEXT_KEYS,
    _CODEX_JSON_UNSUPPORTED_MARKERS,
    _CODEX_STALL_WATCHDOG_DEFAULT_POLL_SECONDS,
    _CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS,
    _CODEX_STALL_WATCHDOG_POLL_ENV,
    _CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS,
    _CODEX_STALL_WATCHDOG_SIGTERM_GRACE_SECONDS,
    _CODEX_STALL_WATCHDOG_THRESHOLD_ENV,
    _CodexCliHealth,
    _CodexStallWatchdogConfig,
    _ProcessSnapshotRow,
    _STALL_DEAD_SIGNATURE_ATTR,
    _TIMEOUT_REAP_REASON_ATTR,
    _adapter_spawn_journal_path,
    _codex_cli_health_sample,
    _codex_cli_watchdog_applies,
    _codex_dead_connection_signature,
    _codex_event_assistant_text,
    _codex_json_unsupported,
    _codex_stall_watchdog_config,
    _codex_text_from_keys,
    _command_runner_accepts_env,
    _communicate_with_optional_codex_stall_watchdog,
    _established_tcp_socket_count,
    _float_env_or_default,
    _journal_reap,
    _journal_spawn,
    _journal_write,
    _parse_ps_cpu_seconds,
    _process_snapshot_rows,
    _reap_timeout_process_group,
    _related_process_ids,
    _run_command,
    _run_or_delegate,
    _run_text_cli_command,
    _safe_timeout_cmd,
    _signal_process_group,
    _stall_dead_signature_facts,
    _timeout_expired_reap_reason,
    _timeout_expired_stall_dead_signature,
    _validate_command_args,
)
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
_GEMINI_WEB_TOOL_NAMES = frozenset({"google_web_search", "web_fetch"})
_CANONICAL_TOOL_UNIVERSE_GEMINI = (
    "exit_plan_mode",
    "glob",
    "google_web_search",
    "grep_search",
    "list_directory",
    "read_file",
    "read_many_files",
    "replace",
    "run_shell_command",
    "search_file_content",
    "update_topic",
    "web_fetch",
    "write_file",
)
_GEMINI_TOOLS_BY_NATIVE_CAPABILITY = {
    ADAPTER_CAPABILITY_READ: _GEMINI_READ_TOOL_NAMES,
    ADAPTER_CAPABILITY_WEB: _GEMINI_WEB_TOOL_NAMES,
    ADAPTER_CAPABILITY_WRITE: frozenset(),
}


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
            ADAPTER_CAPABILITY_WEB,
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


# Lazy CASTING_FIELDS / NODE_CASTING_FIELDS access (E2/S6★). ``agent.spec``
# re-exports THIS module's brain catalog, so a top-level import of the casting
# field-set here would be circular. The request's generic per-dial casting
# accessor + normalize LOOP read the field-set through these cached lazy getters
# so the dataclass names no individual dial.
_CASTING_FIELDS_CACHE: tuple[Any, ...] | None = None
_NODE_CASTING_FIELDS_CACHE: frozenset[str] | None = None


def _casting_fields() -> tuple[Any, ...]:
    global _CASTING_FIELDS_CACHE
    if _CASTING_FIELDS_CACHE is None:
        from brick_protocol.agent.spec import CASTING_FIELDS

        _CASTING_FIELDS_CACHE = CASTING_FIELDS
    return _CASTING_FIELDS_CACHE


def _node_casting_fields() -> frozenset[str]:
    global _NODE_CASTING_FIELDS_CACHE
    if _NODE_CASTING_FIELDS_CACHE is None:
        from brick_protocol.agent.spec import NODE_CASTING_FIELDS

        _NODE_CASTING_FIELDS_CACHE = frozenset(NODE_CASTING_FIELDS)
    return _NODE_CASTING_FIELDS_CACHE


_NODE_CASTING_FIELDS_ORDERED_CACHE: tuple[str, ...] | None = None


def _node_casting_fields_ordered() -> tuple[str, ...]:
    """The ordered node-layer ``selected_<base>`` keys (load-bearing dial order).

    Used where the casting dials are SERIALIZED into a stable-order mapping (the
    work-envelope / prompt / returned-evidence) so a NEW dial joins the serialized
    bag with no edit at each seam."""

    global _NODE_CASTING_FIELDS_ORDERED_CACHE
    if _NODE_CASTING_FIELDS_ORDERED_CACHE is None:
        from brick_protocol.agent.spec import NODE_CASTING_FIELDS

        _NODE_CASTING_FIELDS_ORDERED_CACHE = tuple(NODE_CASTING_FIELDS)
    return _NODE_CASTING_FIELDS_ORDERED_CACHE


@dataclass(frozen=True)
class AgentAdapterRequest:
    """Input passed to one Agent brain adapter without secret/session bodies."""

    building_id: str
    agent_object_ref: str
    adapter_ref: str
    brick_instance_ref: str
    next_brick_instance_ref: str
    # E2/S7 (mirror M2): the per-dial casting scalar (``selected_model_ref``) that
    # used to be a NAMED field here is replaced by ONE opaque ``casting`` bag keyed
    # by the node-level ``selected_*`` casting names. A ``@dataclass`` cannot splice
    # a tuple into named fields, so a new casting dial would otherwise cost a new
    # hand-typed scalar; the bag carries them all. The bag is built ONCE at the
    # ``run._adapter_request_from_prepared`` seam and threaded verbatim. The
    # ``selected_model_ref`` accessor below reads the bag, so every existing reader
    # (and the per-adapter __post_init__ normalize) is byte-identical; the dial's
    # NORMALIZED value is written back INTO the bag so the on-disk work-envelope
    # carries the same resolved model the named scalar carried.
    casting: Mapping[str, str] = field(default_factory=dict)
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

    def __getattr__(self, name: str) -> str:
        """Generic per-dial casting accessor (E2/S7 -> S6★ generalization).

        REPLACES the single ``selected_model_ref`` @property: any node-layer
        ``selected_<base>`` casting key (the ``selected_*`` twin of a
        ``CASTING_FIELDS`` descriptor) resolves out of the opaque ``casting`` bag,
        so ``getattr(request, selected_key(descriptor))`` works for ALL dials —
        model (byte-identical to the prior property), effort, and any new dial —
        with no per-dial property. Absent from the bag -> empty string (the prior
        scalar default). Non-casting names raise AttributeError as usual.

        ``__getattr__`` runs only when normal attribute lookup fails, so the real
        ``casting`` field (and every other dataclass field) is unaffected; reading
        ``self.casting`` here cannot recurse."""

        if name in _node_casting_fields():
            return self.casting.get(name, "")
        raise AttributeError(name)

    def __post_init__(self) -> None:
        adapter_ref = _validate_adapter_ref(self.adapter_ref)
        object.__setattr__(self, "adapter_ref", adapter_ref)
        mode = _clean_optional_text("session_continuity_mode", self.session_continuity_mode)
        mode = mode or "none"
        if mode not in ALLOWED_SESSION_CONTINUITY_MODES:
            raise ValueError("session_continuity_mode is not admitted for SESSION-CONTINUITY-0")
        object.__setattr__(self, "session_continuity_mode", mode)
        # E2/S6★ (was S7/M2): normalize EVERY casting dial INSIDE the bag by
        # LOOPING the single-source CASTING_FIELDS rather than hand-naming the model
        # dial. Each carried ``selected_<base>`` value is cleaned text; the MODEL
        # dial additionally runs ``_normalize_selected_model_ref`` (validate +
        # default-fill) exactly as the prior named scalar did — identified by its
        # ``default_ref == MODEL_REF_DEFAULT`` sentinel (data, not a dial-name
        # literal). Other dials (effort) get clean/identity. The resolved values are
        # written back into a fresh bag, so the work-envelope serialization and every
        # reader see byte-identical model values; a NEW dial flows through with no edit.
        casting = dict(self.casting)
        for descriptor in _casting_fields():
            key = "selected_" + descriptor.field_name.removeprefix("preferred_")
            value = _clean_optional_text(key, casting.get(key, ""))
            if descriptor.default_ref == MODEL_REF_DEFAULT:
                value = _normalize_selected_model_ref(adapter_ref, value)
            casting[key] = value
        object.__setattr__(self, "casting", casting)

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
        cleaned_write_scope = WriteScope.clean(self.write_scope, _WRITE_SCOPE_CONTEXT)
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
    if not tool_policy_refs.intersection(READ_TIER_TOOL_POLICY_REFS):
        return False
    return request.adapter_ref in {ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL, ADAPTER_GEMINI_LOCAL}


def _read_tier_policy_refs_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    if request.adapter_ref == ADAPTER_GEMINI_LOCAL:
        return KNOWN_TOOL_POLICY_REFS
    return READ_TIER_TOOL_POLICY_REFS


def _native_grant_resolution_for_request(
    request: AgentAdapterRequest,
    *,
    write_need: bool | None = None,
) -> Mapping[str, Any]:
    resources = request.agent_instruction_packet.get("tool_policy_resources")
    if resources is None:
        resources = []
    from .agent_resources import resolve_native_grant

    return resolve_native_grant(
        resources,
        tool_policy_refs=list(request.tool_policy_refs),
        write_need=bool(request.write_scope) if write_need is None else bool(write_need),
    )


def _native_capabilities_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    resolution = _native_grant_resolution_for_request(request)
    capabilities = resolution.get("capabilities", ())
    if not isinstance(capabilities, list):
        return frozenset()
    return frozenset(str(capability) for capability in capabilities)


def _native_web_requested_for_request(request: AgentAdapterRequest) -> bool:
    resolution = _native_grant_resolution_for_request(request)
    return bool(resolution.get("web_requested"))


def _adapter_projects_web_for_request(request: AgentAdapterRequest) -> bool:
    return (
        ADAPTER_CAPABILITY_WEB in _native_capabilities_for_request(request)
        and adapter_has_capability(request.adapter_ref, ADAPTER_CAPABILITY_WEB)
    )


def _gemini_allowed_tool_names_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    capabilities = _native_capabilities_for_request(request)
    allowed: set[str] = set()
    for capability in (ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WEB, ADAPTER_CAPABILITY_WRITE):
        if capability in capabilities:
            allowed.update(_GEMINI_TOOLS_BY_NATIVE_CAPABILITY.get(capability, frozenset()))
    return frozenset(allowed)


def _gemini_admin_policy_partition_for_request(
    request: AgentAdapterRequest,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    allowed_set = _gemini_allowed_tool_names_for_request(request)
    universe_set = set(_CANONICAL_TOOL_UNIVERSE_GEMINI)
    unknown_allowed = sorted(allowed_set - universe_set)
    if unknown_allowed:
        raise ValueError(
            "gemini native grant projected tools outside canonical universe: "
            + ", ".join(unknown_allowed)
        )
    allowed = tuple(tool for tool in _CANONICAL_TOOL_UNIVERSE_GEMINI if tool in allowed_set)
    denied = tuple(tool for tool in _CANONICAL_TOOL_UNIVERSE_GEMINI if tool not in allowed_set)
    if set(allowed).intersection(denied) or set(allowed).union(denied) != universe_set:
        raise ValueError("gemini native grant tool partition is not exhaustive")
    return allowed, denied


def _toml_tool_rule(tool_names: tuple[str, ...], *, decision: str, priority: int) -> str:
    lines = [
        "[[rule]]",
        "toolName = [",
        *[f'  "{tool_name}",' for tool_name in tool_names],
        "]",
        f'decision = "{decision}"',
        f"priority = {priority}",
    ]
    return "\n".join(lines)


def _gemini_admin_policy_for_request(request: AgentAdapterRequest) -> str:
    allowed, denied = _gemini_admin_policy_partition_for_request(request)
    blocks: list[str] = []
    if allowed:
        blocks.append(_toml_tool_rule(allowed, decision="allow", priority=998))
    if denied:
        blocks.append(_toml_tool_rule(denied, decision="deny", priority=999))
    return "\n\n".join(blocks) + "\n"


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
    output_text = _extract_output_text(spec, completed, request=request)
    _reject_secret_text("local_cli_output", output_text)
    returned = {
        "returned_summary": "local CLI Agent Adapter returned support evidence",
        "adapter_ref": spec.adapter_ref,
        # E2/S6★: serialize the casting dials by LOOPING the single-source
        # NODE_CASTING_FIELDS instead of naming the model dial. Each declared
        # (truthy) ``selected_<base>`` value joins the bag; an undeclared dial is
        # absent, so today this emits exactly ``selected_model_ref`` (byte-identical
        # to the prior single key) and a NEW dial (effort) rides along when declared.
        **{
            _ck: getattr(request, _ck)
            for _ck in _node_casting_fields_ordered()
            if getattr(request, _ck)
        },
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
        # E2/S6★: serialize the casting dials by LOOPING the single-source
        # NODE_CASTING_FIELDS instead of naming the model dial. Each declared
        # (truthy) ``selected_<base>`` value joins the bag; an undeclared dial is
        # absent, so today this emits exactly ``selected_model_ref`` (byte-identical
        # to the prior single key) and a NEW dial (effort) rides along when declared.
        **{
            _ck: getattr(request, _ck)
            for _ck in _node_casting_fields_ordered()
            if getattr(request, _ck)
        },
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
            # E2/S6 (mirror M6): the codex ``-m`` model flag is now DATA on the
            # casting model dial's cli_emit; the spawn path loops CASTING_FIELDS.
            # Byte-identical to the deleted inline ``("-m", model_arg)`` literal.
            args_list.extend(_casting_cli_args(request, spec))
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
        # E2/S6 (mirror M6): the claude ``--model`` model flag is now DATA on the
        # casting model dial's cli_emit; the spawn path loops CASTING_FIELDS.
        # Byte-identical to the deleted inline ``("--model", model_arg)`` literal.
        args_list.extend(_casting_cli_args(request, spec))
        if request.session_continuity_mode == "none":
            args_list.append("--no-session-persistence")
        args_list.append(prompt)
        args = tuple(args_list)
        return _run_or_delegate(args, cwd, timeout_seconds, command_runner)
    if spec.invocation_args_kind == "gemini-p-json-flash":
        with tempfile.TemporaryDirectory(prefix="bp-gemini-cli-") as tmpdir:
            temp_root = Path(tmpdir)
            read_tier = agent_request_read_tier(request)
            allowed_gemini_tools = _gemini_allowed_tool_names_for_request(request)
            native_tool_tier = bool(allowed_gemini_tools)
            policy_path = temp_root / (
                "native-grant-policy.toml" if native_tool_tier else "no-tools-policy.toml"
            )
            policy_path.write_text(
                _gemini_admin_policy_for_request(request),
                encoding="utf-8",
            )
            run_cwd = cwd if read_tier else temp_root
            run_env = None
            approval_mode = "plan"
            model_arg = _model_cli_arg(request, spec) or "gemini-2.5-flash"
            if native_tool_tier:
                run_env = dict(os.environ)
                if not _gemini_api_key_env_present(run_env):
                    raise FileNotFoundError(
                        "gemini-local native tool tier requires an API key in env "
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


def _casting_cli_args(request: AgentAdapterRequest, spec: LocalCliSpec) -> tuple[str, ...]:
    """Project the casting dials to their spawn-time CLI args via CASTING_FIELDS.

    E2/S6 (mirror M6): the per-adapter CLI flag knowledge that was inlined twice
    (the codex ``-m`` / claude ``--model`` literals) is now DATA on each
    ``CastingField.cli_emit``. The spawn path LOOPS the field-set and concatenates
    each dial's emit; the adapter dial contributes nothing (``_no_cli_emit``), the
    model dial contributes ``(flag, model_arg)`` exactly as the deleted literals
    did. BYTE-IDENTICAL to the inline path: the per-dial spawn VALUE is the
    declared ``selected_*`` on the request, else — for the deferrable model dial
    (``default_ref is not None``) — the spec's ``default_model_ref`` (the same
    ``request.selected_model_ref or spec.default_model_ref`` the inline
    ``_model_cli_arg`` fed its projector); the fail-closed adapter dial
    (``default_ref is None``) falls back to the already-chosen ``spec.adapter_ref``
    and emits nothing. A provider mismatch raises identically (the projector
    inside ``cli_emit`` raises just as the inline ``_model_cli_arg`` did).

    Imported lazily to avoid an import cycle: ``agent.spec`` re-exports this
    module's brain catalog, so a top-level import here would be circular.
    """

    from brick_protocol.agent.spec import CASTING_FIELDS, selected_key

    args: list[str] = []
    for descriptor in CASTING_FIELDS:
        declared = getattr(request, selected_key(descriptor), "")
        # The per-dial deferrable spawn default is descriptor DATA now (replaces the
        # 2-dial ternary): adapter => spec.adapter_ref, model => spec.default_model_ref,
        # effort => its own sentinel (which cli_emit suppresses to no-arg). A NEW dial
        # supplies its own spawn_default with no edit here. Byte-identical for the two
        # existing dials.
        value = declared or descriptor.spawn_default(spec)
        args.extend(descriptor.cli_emit(value, spec.adapter_ref))
    return tuple(args)


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
    if not agent_request_effective_write(request):
        return "read-only"
    from .agent_resources import codex_sandbox_mode_for_tool_policies

    projected = codex_sandbox_mode_for_tool_policies(
        list(request.tool_policy_refs),
        write_need=bool(request.write_scope),
        native_grant_resources=request.agent_instruction_packet.get("tool_policy_resources", []),
    )
    return "workspace-write" if projected == "workspace-write" else "read-only"


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
        mapping = claude_tools_for_tool_policies(
            list(request.tool_policy_refs),
            write_need=bool(request.write_scope),
            native_grant_resources=request.agent_instruction_packet.get("tool_policy_resources", []),
        )
        if mapping.get("write_capable") is True:
            tools = ",".join(mapping["tools"])
            return {
                "permission_mode": "acceptEdits",
                "tools": tools,
                "system_prompt": _CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT,
            }
    if agent_request_read_tier(request):
        from .agent_resources import claude_tools_for_tool_policies

        mapping = claude_tools_for_tool_policies(
            list(request.tool_policy_refs),
            write_need=False,
            native_grant_resources=request.agent_instruction_packet.get("tool_policy_resources", []),
        )
        return {
            "permission_mode": "plan",
            "tools": ",".join(mapping["tools"]),
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


def _build_prompt(request: AgentAdapterRequest, spec: LocalCliSpec) -> str:
    required_labels = _required_return_shape_fields(request.required_return_shape)
    waiver_labels = _return_field_waivers(required_labels)
    reserved_top_level_return_keys = ", ".join(sorted(_TOP_LEVEL_VERDICT_KEYS))
    native_grant = _native_grant_resolution_for_request(request)
    web_requested = bool(native_grant.get("web_requested"))
    web_projected = _adapter_projects_web_for_request(request)
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
    elif agent_request_read_tier(request) or web_projected or (
        web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL
    ):
        admitted = ", ".join(sorted(_read_tier_policy_refs_for_request(request)))
        if agent_request_read_tier(request):
            rules.extend(
                (
                    "You may use read-only repository inspection tools only: read files, inspect diffs, search with grep/glob, and run checker commands.",
                    f"Read tier is admitted for this adapter only by these Agent tool policies: {admitted}.",
                )
            )
        elif web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL:
            rules.append(
                "No adapter-native web tools are available on codex-local for this native_grant."
            )
        else:
            rules.append(
                "You may use only adapter-native web tools granted by native_grant; do not inspect repository files."
            )
        rules.extend(
            (
                "Do not edit, create, delete, or write files.",
                "Do not run git mutations, including commit, push, checkout, reset, merge, rebase, or stash.",
                "Do not execute hooks or provider SDKs.",
                "Return non-judgmental support evidence only.",
            )
        )
        if web_projected:
            rules.append(
                "Web access is adapter-projected from tool-policy:web-capable; use only the adapter-native web tools granted by native_grant."
            )
        elif web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL:
            rules.append("Web NOT available on this adapter; do not use network beyond the selected provider itself.")
        else:
            rules.append("Do not use network beyond the selected provider itself.")
    else:
        rules.append("Do not use tools or hooks.")
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        if agent_request_read_tier(request) or web_projected:
            rules.append(
                "Gemini local native grant may use only read_file, glob, grep_search, search_file_content, list_directory, read_many_files, and when web-capable is present google_web_search/web_fetch; write and shell tools remain blocked."
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
        # E2/S6★: serialize the casting dials by LOOPING the single-source
        # NODE_CASTING_FIELDS instead of naming the model dial. Each declared
        # (truthy) ``selected_<base>`` value joins the bag; an undeclared dial is
        # absent, so today this emits exactly ``selected_model_ref`` (byte-identical
        # to the prior single key) and a NEW dial (effort) rides along when declared.
        **{
            _ck: getattr(request, _ck)
            for _ck in _node_casting_fields_ordered()
            if getattr(request, _ck)
        },
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
        "native_grant": dict(native_grant),
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


def _extract_output_text(
    spec: LocalCliSpec,
    completed: LocalCliCompleted,
    *,
    request: AgentAdapterRequest,
) -> str:
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        return _extract_gemini_response(
            completed.stdout,
            allowed_tool_names=_gemini_allowed_tool_names_for_request(request),
        )
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


def _extract_gemini_response(
    stdout: str,
    *,
    allowed_tool_names: Iterable[str] | None = None,
) -> str:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini local CLI output was not JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Gemini local CLI JSON output must be an object")
    stats = payload.get("stats")
    nonread_tool_names = _gemini_nonread_tool_names(
        stats,
        allowed_tool_names=allowed_tool_names,
    )
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


def _gemini_nonread_tool_names(
    stats: Any,
    *,
    allowed_tool_names: Iterable[str] | None = None,
) -> tuple[str, ...]:
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
    allowed = set(_GEMINI_READ_TOOL_NAMES if allowed_tool_names is None else allowed_tool_names)
    return tuple(sorted(name for name in names if name not in allowed))


def _validate_adapter_ref(value: Any) -> str:
    adapter_ref = _clean_optional_text("adapter_ref", value)
    if not adapter_ref:
        raise ValueError("adapter_ref must not be blank")
    if adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError("adapter_ref is retired and not admitted as an active adapter")
    if adapter_ref not in ALLOWED_ADAPTER_REFS:
        raise ValueError("adapter_ref is not admitted for SIMPLE-RUN-0")
    return adapter_ref


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
    WriteScope.validate("write_scope", write_scope, _WRITE_SCOPE_CONTEXT)


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


# Brick WriteScope value-object discipline (E2/S9): the SHAPE + path-safety rules
# live on the BRICK axis (brick/spec.py). The two support-mechanic coercers it
# delegates to (deep JSON clean + raw credential/session rejection) are injected
# here so the axis never imports support; accept/reject + error text stay
# byte-identical to the prior agent_adapter-local helpers.
_WRITE_SCOPE_CONTEXT = WriteScopeContext(
    clean_json=_clean_json_value,
    reject_secret_text=_reject_secret_text,
)


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


__all__ = [
    "ADAPTER_CAPABILITY_LITERALS",
    "ADAPTER_CAPABILITY_READ",
    "ADAPTER_CAPABILITY_REVIEW",
    "ADAPTER_CAPABILITY_WEB",
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
    "READ_TIER_TOOL_POLICY_REFS",
    "READ_WRITE_TOOL_POLICY_REF",
    "REVIEWER_READONLY_TOOL_POLICY_REF",
    "WEB_CAPABLE_TOOL_POLICY_REF",
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
