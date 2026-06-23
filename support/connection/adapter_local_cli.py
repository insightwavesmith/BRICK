"""Local-CLI invocation cluster for the Agent Adapter.

Extracted VERBATIM from ``support/connection/agent_adapter.py`` (E2 split,
extraction 7/7). PURE relocation -- no logic/name/signature change. This module
owns the local-CLI invocation surface:

* argv assembly + per-adapter CLI knobs: ``_invoke_local_cli`` (codex-exec /
  claude-plan-json / gemini-p-json-flash branches), ``_codex_sandbox_for_request``,
  ``_claude_cli_invocation``, ``_proof_limits_for_request``,
  ``_not_proven_for_request``;
* the local-callable stub path: ``_invoke_local_callable``,
  ``_local_callable_smoke``, ``_BUILTIN_LOCAL_CALLABLES``;
* the local-CLI dispatch + output/nonzero-error extraction:
  ``_invoke_local_cli_adapter``, ``_local_cli_nonzero_error_message``,
  ``_stdout_error_excerpt``, ``_stderr_gemini_client_error_path``,
  ``_GEMINI_CLIENT_ERROR_PATH_RE``, ``_extract_output_text``,
  ``_extract_gemini_response``, ``_gemini_nonread_tool_names``.

The ``agent_adapter`` facade re-exports every symbol here (public AND
underscore-private) so late-bound ``agent_adapter.<sym>`` access never breaks.

This module imports siblings DIRECTLY (adapter_constants, adapter_validation,
adapter_subprocess, adapter_model_casting, adapter_grant_policy,
adapter_gemini_http) and NEVER ``from support.connection.agent_adapter import
...`` at top level (cycle). The stay-behind carriers, constants, and helper
functions that still live in ``agent_adapter`` (the ``LocalCliSpec`` /
``LocalCliCompleted`` / ``AgentBrainCallable`` carriers, ``_local_cli_spec``,
``probe_local_cli_adapter``, ``agent_request_effective_write`` /
``agent_request_read_tier``, ``_merge_texts``, ``_redacted_diagnostic_excerpt``,
``_try_json_value``, the ``_CLAUDE_*_SYSTEM_PROMPT`` constants,
``_DEFAULT_PROOF_LIMITS`` / ``_DEFAULT_NOT_PROVEN``, ``_GEMINI_API_KEY_ENV_VARS``,
``_GEMINI_READ_TOOL_NAMES``, ``_BUILTIN_LOCAL_CALLABLES`` consumers) are reached
LAZILY in-function (the ``from .agent_adapter import ...`` back-edge runs only at
call time, after both modules are fully loaded) so there is no import cycle and
the moved bodies keep their exact statements. ``AgentAdapterRequest`` /
``LocalCliSpec`` / ``LocalCliCompleted`` / ``AgentBrainCallable`` /
``CommandRunner`` are annotation-only here (``from __future__ import
annotations`` keeps them strings).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_GEMINI_LOCAL,
)
from .adapter_gemini_http import _gemini_api_key_env_present
from .adapter_grant_policy import (
    _build_prompt,
    _extract_required_return_fields,
    _gemini_admin_policy_for_request,
    _gemini_allowed_tool_names_for_request,
    _merge_structured_return_fields,
)
from .adapter_model_casting import (
    _casting_cli_args,
    _model_cli_arg,
    _node_casting_fields_ordered,
)
from .adapter_subprocess import (
    codex_assistant_text_from_json_stdout,
    codex_usage_from_json_stdout,
    _codex_json_unsupported,
    _run_or_delegate,
)
from .adapter_validation import _reject_secret_text, _safe_excerpt

if TYPE_CHECKING:
    from .agent_adapter import (
        AgentAdapterRequest,
        AgentBrainCallable,
        CommandRunner,
        LocalCliCompleted,
        LocalCliSpec,
    )


# ISOLATION (Smith 0623 operator decision): a dispatched build CLI must run in a
# SCRUBBED room, not the user's own ~/.claude / ~/.codex with their skills, hooks,
# and MCP servers bleeding in. The allowlist below is the ONLY env the child
# inherits by default; HOME + the provider config-dir + carried auth keys are
# layered on per provider. This is a clean-env allowlist (NOT dict(os.environ)),
# so a stray user env var (an unrelated API key, a hook toggle) never reaches the
# dispatched provider. Support mechanics only: it carries env, it judges nothing.
_ISOLATED_ENV_ALLOWLIST_KEYS: tuple[str, ...] = (
    "PATH",
    "HOME",  # replaced below with the temp HOME; listed so a missing key is explicit
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "SHELL",
    "USER",
    "LOGNAME",
)
# Auth env that must be CARRIED THROUGH the scrub so the provider can still talk to
# its backend (the door key). These are credential-bearing, so they are the ONLY
# user-env values forwarded; everything else is dropped. Per-provider, narrow.
_CLAUDE_AUTH_CARRY_ENV_KEYS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
)
_CODEX_AUTH_CARRY_ENV_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
)
# Opt OUT of isolation (default ON): a stray legacy caller that genuinely needs the
# user's own config can set BRICK_BUILD_ISOLATION=0. Default/unset/any-other-value
# keeps isolation ON (fail-safe toward the clean room).
_BUILD_ISOLATION_ENV = "BRICK_BUILD_ISOLATION"


def _build_isolation_enabled() -> bool:
    return os.environ.get(_BUILD_ISOLATION_ENV) != "0"


def _scrubbed_base_env() -> dict[str, str]:
    """The clean allowlist env (no user ~/.* config leakage, no stray user vars)."""

    base: dict[str, str] = {}
    for key in _ISOLATED_ENV_ALLOWLIST_KEYS:
        if key == "HOME":
            continue  # HOME is set to the temp room by the caller, never inherited
        value = os.environ.get(key)
        if value is not None:
            base[key] = value
    return base


def _carry_auth_env(base: dict[str, str], carry_keys: tuple[str, ...]) -> None:
    for key in carry_keys:
        value = os.environ.get(key)
        if value:
            base[key] = value


def _brick_mcp_server_argv(repo_root: Path) -> list[str]:
    """Single-source the brick-protocol MCP server command + args.

    Reuses connect.py's derivation (the same ``parents[2]`` repo-root + server
    script path it already renders for the hand-paste connect docs), so the
    DISPATCH-time wiring and the connect docs register byte-identically -- one
    registration shape, no second copy of the path."""

    from . import connect

    script = connect._server_script(repo_root)
    return ["python3", str(script), "--repo", str(repo_root)]


_BRICK_MCP_SERVER_NAME = "brick-protocol"


def _claude_mcp_config_json(repo_root: Path) -> str:
    """Inline --mcp-config JSON wiring the brick-protocol MCP for a claude dispatch."""

    command, *args = _brick_mcp_server_argv(repo_root)
    return json.dumps(
        {
            "mcpServers": {
                _BRICK_MCP_SERVER_NAME: {"command": command, "args": args},
            }
        },
        sort_keys=True,
    )


def _codex_mcp_config_cli_args(repo_root: Path) -> list[str]:
    """`-c mcp_servers.brick-protocol.*` overrides wiring the MCP for a codex dispatch."""

    command, *args = _brick_mcp_server_argv(repo_root)
    return [
        "-c",
        f"mcp_servers.{_BRICK_MCP_SERVER_NAME}.command={json.dumps(command)}",
        "-c",
        f"mcp_servers.{_BRICK_MCP_SERVER_NAME}.args={json.dumps(args)}",
    ]


def _repo_root_for_request(spec: LocalCliSpec) -> Path:
    """The BRICK repo root whose mcp_projection.py the dispatch wires as the MCP.

    Single-sourced from connect.py's own ``parents[2]`` derivation (the same path
    the connect docs render) so the dispatch-time MCP and the connect docs always
    agree. ``spec`` is unused today but kept in the signature so a future
    per-adapter override has a seam without a call-site change."""

    del spec
    from . import connect

    return connect.repo_root_from_here()


def _codex_isolated_run_env(codex_home: Path, repo_root: Path) -> dict[str, str] | None:
    """Build the scrubbed run env for a codex dispatch (None when isolation is off).

    Writes a clean ``<home>/.codex/config.toml`` carrying ONLY brick's MCP server
    (no user MCP/hooks), sets HOME + CODEX_HOME to the temp room, carries the codex
    auth keys through the scrub, and returns the env. Support mechanics only: it
    carries config + env, it judges nothing and stores no credential of its own."""

    if not _build_isolation_enabled():
        return None
    env = _scrubbed_base_env()
    env["HOME"] = str(codex_home)
    codex_config_dir = codex_home / ".codex"
    codex_config_dir.mkdir(parents=True, exist_ok=True)
    env["CODEX_HOME"] = str(codex_config_dir)
    from . import connect

    (codex_config_dir / "config.toml").write_text(
        connect.render_codex_mcp_config(repo_root),
        encoding="utf-8",
    )
    _carry_auth_env(env, _CODEX_AUTH_CARRY_ENV_KEYS)
    return env


def _project_brick_skills_into_home(claude_config_dir: Path, repo_root: Path) -> None:
    """Project the Agent-axis skills into the dispatch room's ~/.claude/skills/.

    H2 (INSTALL-WIZARD-0623): the claude dispatch runs in a SCRUBBED temp HOME, so
    the user's real ~/.claude/skills (where ``run_skills_place_step`` installs the
    brick skills) is NOT visible. The skill manifest the runtime packet ships uses a
    repo-relative path -- codex/gemini read it from cwd=repo, but claude's NATIVE
    description-triggered fetch looks in ~/.claude/skills. So we render the same
    Agent-Skills projection ``run_skills_place_step`` uses straight into the room's
    HOME, byte-identical to the operator install. Read-only support projection:
    renders declared skill bodies, judges nothing, NEVER raises (a skill that fails
    to render is skipped so a single bad skill never breaks the build dispatch)."""

    from .agent_resources import (
        AgentResourceError,
        list_agent_object_refs,
        render_skill_md,
        resolve_agent_object,
    )

    skills_root = claude_config_dir / "skills"
    seen: set[str] = set()
    try:
        object_refs = list_agent_object_refs(repo_root)
    except (AgentResourceError, OSError, ValueError):
        return
    for object_ref in object_refs:
        try:
            resolution = resolve_agent_object(object_ref, repo_root=repo_root)
        except (AgentResourceError, OSError, ValueError):
            continue
        for skill in resolution.get("skill_resources", []):
            ref = str(skill.get("ref") or "")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            name = (ref.removeprefix("skill:") if ref.startswith("skill:") else ref).replace("_", "-")
            body = str(skill.get("body") or "")
            front = _skill_front_matter_from_body(body)
            try:
                rendered = render_skill_md(
                    name,
                    front.get("description") or f"Brick Protocol skill {name}",
                    _skill_body_without_front_matter(body),
                )
            except (AgentResourceError, ValueError):
                continue
            target = skills_root / name / "SKILL.md"
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered, encoding="utf-8")
            except OSError:
                continue


def _skill_front_matter_from_body(body: str) -> dict[str, str]:
    name = ""
    description = ""
    lines = body.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            stripped = line.strip()
            if stripped == "---":
                break
            if stripped.startswith("name:"):
                name = stripped[len("name:") :].strip()
            elif stripped.startswith("description:"):
                description = stripped[len("description:") :].strip()
    return {"name": name, "description": description}


def _skill_body_without_front_matter(body: str) -> str:
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return body.strip()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return body.strip()


def _claude_isolated_run_env(claude_home: Path, repo_root: Path) -> dict[str, str] | None:
    """Build the scrubbed run env for a claude dispatch (None when isolation is off).

    Sets HOME to the temp room with a minimal ``<home>/.claude/settings.json`` that
    disables the user's hooks (the inline --strict-mcp-config handles MCP), projects
    the brick Agent-axis skills into ``<home>/.claude/skills/`` so claude's NATIVE
    description-triggered fetch resolves them inside the scrubbed room (H2), carries
    the claude auth keys through the scrub, and returns the env. ``repo_root`` is the
    BRICK repo whose declared skills are projected (it also feeds the inline
    --mcp-config at the call site). Support mechanics only."""

    if not _build_isolation_enabled():
        return None
    env = _scrubbed_base_env()
    env["HOME"] = str(claude_home)
    claude_config_dir = claude_home / ".claude"
    claude_config_dir.mkdir(parents=True, exist_ok=True)
    # Minimal settings: empty hooks so the user's global hooks never fire in the
    # build room. MCP is governed by the inline --strict-mcp-config at the call
    # site, so it is intentionally not duplicated here.
    (claude_config_dir / "settings.json").write_text(
        json.dumps({"hooks": {}}, sort_keys=True),
        encoding="utf-8",
    )
    # H2: project the brick skills into the room HOME so claude's native skills
    # trigger path (~/.claude/skills) is not dead inside the scrubbed room.
    _project_brick_skills_into_home(claude_config_dir, repo_root)
    _carry_auth_env(env, _CLAUDE_AUTH_CARRY_ENV_KEYS)
    return env


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
) -> tuple[
    Mapping[str, Any],
    tuple[str, ...],
    tuple[str, ...],
    Mapping[str, Any] | None,
    tuple[str, ...],
]:
    from .agent_adapter import _local_cli_spec, _merge_texts, probe_local_cli_adapter

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
    output_text, observed_non_granted_gemini_tools = _extract_output_text(
        spec, completed, request=request
    )
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
    # REDO (Smith 0623 struct-surgery): the adapter EXPOSES the raw it already saw;
    # it RECORDS NOTHING. A non-granted gemini tool call is no longer attached to the
    # returned payload here -- the observed tool names ride back as RAW on the 5th
    # side-channel element so support/recording can record the
    # ``observed_non_granted_gemini_tools`` fact. The real answer is already in
    # output_excerpt (the adapter returns the ANSWER, not a fact).
    _merge_structured_return_fields(
        returned,
        _extract_required_return_fields(
            output_text,
            request.required_return_shape,
        ),
    )
    # TrackA-A1 METER: the codex token usage rides back as a SEPARATE 4th element,
    # NOT inside `returned` (which becomes AgentFact.returned). Support fact only.
    # REDO (Smith 0623): the observed non-granted gemini tool names ride back as RAW
    # on a SEPARATE 5th element -- never inside `returned`. support/recording records
    # the fact; the adapter only exposes the raw it saw.
    return (
        returned,
        _merge_texts(proof_limits, request.proof_limits),
        _merge_texts(not_proven, request.not_proven),
        completed.adapter_usage,
        tuple(observed_non_granted_gemini_tools),
    )


def _invoke_local_cli(
    spec: LocalCliSpec,
    request: AgentAdapterRequest,
    prompt: str,
    *,
    cwd: Path,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
) -> LocalCliCompleted:
    from .agent_adapter import (
        LocalCliCompleted,
        _GEMINI_API_KEY_ENV_VARS,
        agent_request_read_tier,
    )

    executable_path = spec.executable_name if command_runner is not None else shutil.which(spec.executable_name)
    if not executable_path:
        raise FileNotFoundError(f"local CLI executable not found for {spec.adapter_ref}")
    if spec.invocation_args_kind == "codex-exec-readonly":
        sandbox = _codex_sandbox_for_request(request)
        repo_root = _repo_root_for_request(spec)
        # ISOLATION (Smith 0623): the codex dispatch runs in a SCRUBBED room. A temp
        # HOME holds a clean ~/.codex/config.toml carrying ONLY brick's MCP (no user
        # MCP/hooks), --ignore-user-config makes codex skip the user's own
        # ~/.codex/config.toml, and the auth keys are carried through the scrub so
        # the provider can still reach its backend. When isolation is opted out
        # (BRICK_BUILD_ISOLATION=0) run_env stays None (byte-identical inherited-env
        # behavior) and the user-config flag is omitted.
        with tempfile.TemporaryDirectory(prefix="bp-codex-home-") as codex_home_dir, \
                tempfile.NamedTemporaryFile(prefix="bp-codex-cli-", suffix=".txt") as output_file:
            run_env = _codex_isolated_run_env(Path(codex_home_dir), repo_root)
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
            # ISOLATION lever #2 + MCP wire: ignore the user's ~/.codex config and
            # attach the brick-protocol MCP server via -c overrides (the same
            # registration shape connect.py renders). Only when isolation is on.
            if run_env is not None:
                args_list.append("--ignore-user-config")
                args_list.extend(_codex_mcp_config_cli_args(repo_root))
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
            # PROVIDER-ROUTING -c OVERRIDES (DATA, no judgment). Each spec carries
            # extra ``-c key=value`` pairs as DATA; support only concatenates them
            # into argv -- it makes no provider decision. EMPTY for every existing
            # adapter (codex-local etc.), so their argv is BYTE-IDENTICAL; the sakana
            # variant (codex-fugu-local) flattens its (model_provider + catalog) pairs
            # here, AFTER the approval-policy -c knob and BEFORE the casting model/
            # effort args.
            for _override_flag, _override_value in spec.extra_config_overrides:
                args_list.extend((_override_flag, _override_value))
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
            completed = _run_or_delegate(
                json_args, cwd, timeout_seconds, command_runner, env=run_env
            )
            json_active = True
            if _codex_json_unsupported(completed):
                # Older codex: re-run WITHOUT --json so the build still completes.
                # The file may have been left empty by the rejected first attempt;
                # re-running with a fresh seek keeps the text path identical.
                plain_args = tuple((*args_list, *tail_args))
                completed = _run_or_delegate(
                    plain_args, cwd, timeout_seconds, command_runner, env=run_env
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
        repo_root = _repo_root_for_request(spec)
        # ISOLATION (Smith 0623): the claude dispatch runs in a SCRUBBED room. A temp
        # HOME with a minimal ~/.claude/settings.json disabling user hooks, plus
        # --strict-mcp-config so the inline --mcp-config (the brick-protocol MCP) is
        # the ONLY MCP set (the user's ~/.claude MCP servers are suppressed), plus
        # the auth keys carried through the scrub. Opt out -> run_env None
        # (byte-identical inherited-env behavior) and the strict/mcp flags omitted.
        with tempfile.TemporaryDirectory(prefix="bp-claude-home-") as claude_home_dir:
            run_env = _claude_isolated_run_env(Path(claude_home_dir), repo_root)
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
            # ISOLATION lever #1 + MCP wire: attach ONLY the brick-protocol MCP and
            # suppress the user's ~/.claude MCP servers. Only when isolation is on.
            if run_env is not None:
                args_list.extend(
                    [
                        "--mcp-config",
                        _claude_mcp_config_json(repo_root),
                        "--strict-mcp-config",
                    ]
                )
            # E2/S6 (mirror M6): the claude ``--model`` model flag is now DATA on the
            # casting model dial's cli_emit; the spawn path loops CASTING_FIELDS.
            # Byte-identical to the deleted inline ``("--model", model_arg)`` literal.
            args_list.extend(_casting_cli_args(request, spec))
            if request.session_continuity_mode == "none":
                args_list.append("--no-session-persistence")
            args_list.append(prompt)
            args = tuple(args_list)
            return _run_or_delegate(args, cwd, timeout_seconds, command_runner, env=run_env)
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


def _proof_limits_for_request(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> tuple[str, ...]:
    from .agent_adapter import _merge_texts, agent_request_effective_write

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
    from .agent_adapter import _merge_texts, agent_request_effective_write

    if not agent_request_effective_write(request):
        return spec.not_proven
    return _merge_texts(
        spec.not_proven,
        "semantic correctness of file edits",
    )


def _codex_sandbox_for_request(request: AgentAdapterRequest) -> str:
    from .agent_adapter import agent_request_effective_write

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
    from .agent_adapter import (
        _CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT,
        _CLAUDE_READ_ONLY_SYSTEM_PROMPT,
        _CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT,
        agent_request_effective_write,
        agent_request_read_tier,
    )

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


_GEMINI_CLIENT_ERROR_PATH_RE = re.compile(
    r"""[^\s'"`<>]*gemini-client-error-[^\s'"`<>]*\.json"""
)


def _local_cli_nonzero_error_message(spec: LocalCliSpec, completed: LocalCliCompleted) -> str:
    from .agent_adapter import _redacted_diagnostic_excerpt

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
    from .agent_adapter import _redacted_diagnostic_excerpt, _try_json_value

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
    from .agent_adapter import _redacted_diagnostic_excerpt

    match = _GEMINI_CLIENT_ERROR_PATH_RE.search(stderr)
    if not match:
        return ""
    return _redacted_diagnostic_excerpt(match.group(0), limit=240)


def _extract_output_text(
    spec: LocalCliSpec,
    completed: LocalCliCompleted,
    *,
    request: AgentAdapterRequest,
) -> tuple[str, tuple[str, ...]]:
    """Return (output_text, observed_non_granted_gemini_tools).

    Only the gemini path can observe non-granted tools (move+record only); the
    other adapters always report an empty observed-tool tuple."""

    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        return _extract_gemini_response(
            completed.stdout,
            allowed_tool_names=_gemini_allowed_tool_names_for_request(request),
        )
    if spec.adapter_ref == ADAPTER_CLAUDE_LOCAL and completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return completed.stdout, ()
        if isinstance(payload, Mapping):
            for key in ("response", "text", "content", "message", "result"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value, ()
        return completed.stdout, ()
    return completed.stdout or completed.stderr, ()


def _extract_gemini_response(
    stdout: str,
    *,
    allowed_tool_names: Iterable[str] | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Smith 0623 LOCK (move+record only): return the real Gemini answer plus the
    observed NON-GRANTED tool names as RECORDED FACT.

    The shape/integrity raises (output not JSON, not an object, missing response
    text) STAY -- those are not policy stops, the support helper cannot carry a
    payload it failed to parse. But a non-granted tool call is a POLICY observation,
    not floor-ripping: it no longer refuses the payload. The response is returned and
    the observed non-read tool names ride back so the caller records them."""

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
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Gemini local CLI JSON output missing response text")
    return response, tuple(nonread_tool_names)


def _gemini_nonread_tool_names(
    stats: Any,
    *,
    allowed_tool_names: Iterable[str] | None = None,
) -> tuple[str, ...]:
    from .agent_adapter import (
        _GEMINI_BENIGN_CONTROL_TOOL_NAMES,
        _GEMINI_READ_TOOL_NAMES,
    )

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
    # PART 1 (faithful-to-grant): treat a reported tool as a violation ONLY if it is
    # NOT in the full GRANTED allowed set (read + web + write as actually granted,
    # produced by ``_gemini_allowed_tool_names_for_request`` and threaded in via
    # ``allowed_tool_names``) -- not merely the read set. A genuinely-granted web/write
    # tool that already passed the launch-time admin-policy must not be re-flagged here.
    # Fail-closed: when the granted set was NOT resolved (``allowed_tool_names is None``)
    # fall back to read-only -- do NOT widen.
    granted = set(_GEMINI_READ_TOOL_NAMES if allowed_tool_names is None else allowed_tool_names)
    # PART 2 (benign control plane): gemini's own completion/orchestration control
    # tools have no repo/external side effect and are NEVER a violation, independent of
    # what capability the Brick granted. Layered on top of the granted set, never inside
    # it (they are not a grantable capability).
    allowed = granted | set(_GEMINI_BENIGN_CONTROL_TOOL_NAMES)
    return tuple(sorted(name for name in names if name not in allowed))
