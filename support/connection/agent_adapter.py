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
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import RETURNED_FORBIDDEN_KEYS as _RETURN_FORBIDDEN_KEYS
from brick_protocol.agent.return_fact import TRANSITION_CONCERN_ALLOWED_KEYS as _TRANSITION_CONCERN_ALLOWED_KEYS
from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS as _TRANSITION_CONCERN_KINDS
from brick_protocol.brick.work import parse_required_return_shape


ADAPTER_LOCAL = "adapter:local"
ADAPTER_CODEX_LOCAL = "adapter:codex-local"
ADAPTER_CLAUDE_LOCAL = "adapter:claude-local"
ADAPTER_GEMINI_LOCAL = "adapter:gemini-local"
READ_WRITE_TOOL_POLICY_REF = "tool-policy:read-write-scoped"
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
MODEL_PROVIDER_BY_ADAPTER = {
    ADAPTER_CODEX_LOCAL: "codex",
    ADAPTER_CLAUDE_LOCAL: "claude",
    ADAPTER_GEMINI_LOCAL: "gemini",
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
    }
)
_ADAPTER_CAPABILITIES = {
    ADAPTER_LOCAL: frozenset({ADAPTER_CAPABILITY_READ}),
    ADAPTER_CODEX_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    ADAPTER_CLAUDE_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    ADAPTER_GEMINI_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_REVIEW}),
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
_RAW_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bxoxb-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bghp_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bgho_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
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
_CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT = (
    "You are a non-interactive Brick Protocol worker agent. "
    "You MAY use only the file tools allowed for this run (Read, Grep, Glob, Edit, Write). "
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


AgentBrainCallable = Callable[[AgentAdapterRequest], Any]
CommandRunner = Callable[[Sequence[str], Path, int], LocalCliCompleted]

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
        default_model_ref=MODEL_REF_GEMINI_FLASH,
    ),
}


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
    dispatch_cwd = Path(cwd) if cwd is not None else _REPO_ROOT
    _consume_effective_write_observation_path(request, cwd=dispatch_cwd)
    if request.adapter_ref == ADAPTER_LOCAL:
        returned_value = _invoke_local_callable(request, local_callables)
        proof_limits = _merge_texts(_DEFAULT_PROOF_LIMITS, request.proof_limits)
        not_proven = _merge_texts(_DEFAULT_NOT_PROVEN, request.not_proven)
    else:
        returned_value, proof_limits, not_proven = _invoke_local_cli_adapter(
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
            MODEL_REF_GEMINI_FLASH,
            "model:gemini:<gemini-model-id>",
        )
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


def project_model_ref_to_cli_arg(adapter_ref: str, selected_model_ref: str = "") -> str:
    """Project a selected_model_ref to the local CLI model argument.

    This is support projection only. It does not prove provider availability or
    model quality.
    """

    if adapter_ref == ADAPTER_LOCAL:
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
                "adapter:codex-local, adapter:claude-local, adapter:gemini-local"
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
) -> tuple[Mapping[str, Any], tuple[str, ...], tuple[str, ...]]:
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
        raise ValueError("local CLI adapter command returned non-zero")
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
    return returned, _merge_texts(proof_limits, request.proof_limits), _merge_texts(
        not_proven,
        request.not_proven,
    )


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
            if request.session_continuity_mode == "none":
                args_list.append("--ephemeral")
            args_list.extend(("--output-last-message", output_file.name, prompt))
            args = tuple(args_list)
            completed = _run_or_delegate(args, cwd, timeout_seconds, command_runner)
            if not completed.stdout:
                output_file.seek(0)
                file_text = output_file.read().decode("utf-8", errors="replace")
                if file_text.strip():
                    completed = LocalCliCompleted(
                        args=completed.args,
                        return_code=completed.return_code,
                        stdout=file_text,
                        stderr=completed.stderr,
                    )
            return completed
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
            policy_path = temp_root / "no-tools-policy.toml"
            policy_path.write_text(_GEMINI_NO_TOOL_POLICY, encoding="utf-8")
            args = (
                executable_path,
                "-p",
                prompt,
                "--output-format",
                "json",
                "--model",
                _model_cli_arg(request, spec) or "gemini-2.5-flash",
                "--approval-mode",
                "plan",
                "--extensions",
                "",
                "--admin-policy",
                str(policy_path),
                "--skip-trust",
            )
            return _run_or_delegate(args, temp_root, timeout_seconds, command_runner)
    raise ValueError("unsupported local CLI adapter kind")


def _normalize_selected_model_ref(adapter_ref: str, selected_model_ref: str) -> str:
    if adapter_ref == ADAPTER_LOCAL:
        if selected_model_ref and selected_model_ref != MODEL_REF_DEFAULT:
            raise ValueError("adapter:local accepts only model:default")
        return MODEL_REF_DEFAULT
    spec = _local_cli_spec(adapter_ref)
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
) -> LocalCliCompleted:
    if command_runner is not None:
        return command_runner(args, cwd, timeout_seconds)
    return _run_command(args, cwd=cwd, timeout_seconds=timeout_seconds)


def _run_command(args: Sequence[str], *, cwd: Path, timeout_seconds: int) -> LocalCliCompleted:
    _validate_command_args(args)
    completed = subprocess.run(
        list(args),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return LocalCliCompleted(
        args=tuple(str(part) for part in args),
        return_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
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
    rules = [
        "Do not claim source truth.",
        "Do not judge success or quality.",
        "Do not choose Link Movement.",
        "Do not run git commit or git push.",
        "Do not access or print setup tokens, auth bodies, credentials, or raw provider sessions.",
        "Return concise text only.",
        "Return one JSON object. The object may include only required_return_shape fields and listed return_field_waivers.",
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
    else:
        rules.append("Do not use tools or hooks.")
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
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
        if key in {"not_proven", "proof_limits"} and key in returned:
            returned[key] = list(_merge_texts(returned[key], value))
            continue
        if key not in returned:
            returned[key] = value


def _required_return_shape_fields(value: Any) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            field
            for field in parse_required_return_shape(value)
            if field not in _RETURN_FORBIDDEN_KEYS
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
    total_calls = _gemini_tool_call_count(payload)
    if total_calls:
        raise ValueError("Gemini local CLI reported tool calls; refusing support payload")
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Gemini local CLI JSON output missing response text")
    return response


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


def _validate_returned_payload(label: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = _normalize(raw_key)
            if key in _RETURN_FORBIDDEN_KEYS:
                raise ValueError(f"{label} contains forbidden return key {raw_key!r}")
            _validate_returned_payload(f"{label}.{raw_key}", child)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_returned_payload(f"{label}[{index}]", child)
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

    forbidden = value.get("forbidden_paths")
    if not isinstance(forbidden, list):
        raise TypeError(f"{label}.forbidden_paths must be a list")
    for index, item in enumerate(forbidden):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}.forbidden_paths[{index}] must be non-empty text")
        _reject_secret_text(f"{label}.forbidden_paths[{index}]", item)

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
    "ADAPTER_CODEX_LOCAL",
    "ADAPTER_GEMINI_LOCAL",
    "ADAPTER_LOCAL",
    "ALLOWED_ADAPTER_REFS",
    "ALLOWED_SESSION_CONTINUITY_MODES",
    "AgentAdapterRequest",
    "AgentAdapterResult",
    "AgentBrainCallable",
    "CommandRunner",
    "LocalCliCompleted",
    "LocalCliProbe",
    "LocalCliSpec",
    "READ_WRITE_TOOL_POLICY_REF",
    "adapter_capabilities",
    "adapter_has_capability",
    "adapter_is_write_capable",
    "agent_request_effective_write",
    "connect_agent_brain",
    "local_cli_adapter_refs",
    "preflight_provider",
    "probe_local_cli_adapter",
    "project_model_ref_to_cli_arg",
    "safe_source_fact_body",
    "supported_model_ref_examples",
]
