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


# adapter_constants is a PURE constant leaf (no intra-package imports). The
# symbols below are the ones agent_adapter's OWN surviving body consumes at
# runtime (capability literals, adapter refs, model-ref defaults, the
# read-tier/read-write policy refs, the observed/retired write sets, the
# capability table, the repo root). Callers that need a moved constant import
# adapter_constants directly -- this is no longer a re-export facade.
from .adapter_constants import (
    ADAPTER_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_GEMINI_API,
    ADAPTER_CHAT_SESSION,
    READ_WRITE_TOOL_POLICY_REF,
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
# cleaning + payload guard live in support/connection/adapter_validation.py.
# The symbols below are the ones agent_adapter's own body consumes at runtime
# (_RAW_SESSION_PATTERNS + _SOURCE_FACT_BODY_LIMIT feed _redacted_diagnostic_excerpt
# / _source_fact_bodies_for_prompt; the cleaners + payload guard are called from
# connect_agent_brain and its helpers). Callers import adapter_validation directly.
from .adapter_validation import (
    _RAW_SESSION_PATTERNS,
    _SOURCE_FACT_BODY_LIMIT,
    _clean_agent_instruction_packet,
    _clean_json_value,
    _clean_link_handoff_refs,
    _clean_optional_text,
    _clean_source_fact_bodies,
    _reject_forbidden_text,
    _reject_secret_text,
    _safe_excerpt,
    _validate_returned_payload,
    safe_source_fact_body,
)

# The subprocess runner + codex connect-stall watchdog + spawn journal +
# token/text meter + provider preflight cluster lives in adapter_subprocess. The
# only two symbols agent_adapter's own body still calls at runtime are the
# command dispatchers (_run_or_delegate / _run_text_cli_command). Callers that
# need a moved subprocess symbol import adapter_subprocess directly.
from .adapter_subprocess import (
    _run_or_delegate,
    _run_text_cli_command,
)

# The model-ref normalization + casting->CLI-arg projection cluster lives in
# adapter_model_casting (E2 split, extraction 4/7). agent_adapter's own body
# calls only the casting-field accessors + the selected-model-ref normalizer.
# Callers that need a moved casting symbol import adapter_model_casting directly.
from .adapter_model_casting import (
    _normalize_selected_model_ref,
    _casting_fields,
    _node_casting_fields,
)

# The native-grant resolution + gemini admin-policy TOML + work-envelope prompt
# build + structured-return extraction cluster lives in adapter_grant_policy (E2
# split, extraction 5/7). agent_adapter's own body no longer calls any of these
# symbols directly (the work-envelope prompt + grant resolution flow runs inside
# adapter_grant_policy / adapter_local_cli now), so there is NO import of it here.
# Callers that need a grant-policy symbol import adapter_grant_policy directly.

# The Gemini HTTP API adapter (★S11 SEAM★) + the bare prompt ->
# text design-AI seams (invoke_gemini_text / invoke_claude_text / invoke_codex_text
# and their _text_cli_* helpers) live in adapter_gemini_http (E2 split, extraction
# 6/7). The S11 FIRE (urlopen patch + _gemini_api_urlopen) now targets
# adapter_gemini_http directly (which top-imports urllib.request), so agent_adapter
# no longer re-exports those seams. The only gemini-http symbol agent_adapter's own
# body still calls is _invoke_gemini_api (the gemini-api adapter dispatch inside
# connect_agent_brain). Callers import adapter_gemini_http directly.
from .adapter_gemini_http import (
    _invoke_gemini_api,
)

# The Local-CLI invocation cluster (argv assembly + local-callable stub +
# output/nonzero-error extraction) lives in adapter_local_cli (E2 split,
# extraction 7/7). agent_adapter's own connect_agent_brain dispatch calls the
# local-callable + local-cli adapter entry points; the rest of the cluster is
# reached by callers importing adapter_local_cli directly.
from .adapter_local_cli import (
    _invoke_local_callable,
    _invoke_local_cli_adapter,
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
# GEMINI-CONTROLPLANE-EXEMPT-0622: gemini's OWN orchestration/completion control
# plane. These names appear in stats.tools.byName when the gemini CLI finishes or
# fans out internally, but they touch NO repo file and reach NO external surface,
# so they are NEVER a read-tier violation and must not produce a false-positive HOLD.
# They are deliberately NOT in the granted/admin-policy set (they are not a
# capability the Brick grants) -- they are an always-benign exemption layered on top
# of the granted set in the post-hoc refusal check.
#   * complete_task  -- gemini signals task completion (control signal, no side effect)
#   * invoke_agent   -- gemini delegates to an internal sub-agent (orchestration, no
#                       repo/external write of its own)
# DELIBERATELY EXCLUDED (stay governed / denied -- do NOT add):
#   * exit_plan_mode -- the work-envelope prompt explicitly forbids it
#     (adapter_grant_policy.py "Do not call exit_plan_mode..."); exempting it here
#     would contradict that deny rule.
#   * update_topic   -- not demonstrably side-effect-free; never a measured false
#                       positive; stays a violation if reported.
#   * google_web_search / web_fetch -- read EXTERNAL state; stay governed by the
#                       granted set (web exempt ONLY when WEB capability is granted).
#   * write_file / run_shell_command / replace -- real writes; stay denied.
_GEMINI_BENIGN_CONTROL_TOOL_NAMES = frozenset({"complete_task", "invoke_agent"})
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


def _local_cli_spec(adapter_ref: str) -> LocalCliSpec:
    if adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError("adapter_ref is retired and not admitted as an active adapter")
    try:
        return _LOCAL_CLI_SPECS[adapter_ref]
    except KeyError as exc:
        raise ValueError("adapter_ref is not a local CLI adapter") from exc


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
    "READ_TIER_TOOL_POLICY_REFS",
    "READ_WRITE_TOOL_POLICY_REF",
    "adapter_capabilities",
    "adapter_has_capability",
    "adapter_is_write_capable",
    "agent_request_effective_write",
    "agent_request_read_tier",
    "connect_agent_brain",
    "local_cli_adapter_refs",
    "probe_local_cli_adapter",
    "safe_source_fact_body",
    "supported_model_ref_examples",
]
