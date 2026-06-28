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
  ``_gemini_client_error_excerpt``, ``_GEMINI_CLIENT_ERROR_PATH_RE``, ``_extract_output_text``,
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
import tomllib
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
    _request_allows_source_mutation,
    _request_blocks_source_mutation,
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


# ISOLATION (Smith 0623/0624 operator decision): a dispatched build CLI must run in
# a SCRUBBED room, not the user's own ~/.claude / ~/.codex with their skills, hooks,
# and MCP servers bleeding in. The allowlist below is the ONLY env the child
# inherits by default; HOME + the provider config-dir + carried auth keys are
# layered on per provider. This is a clean-env allowlist (NOT dict(os.environ)),
# so a stray user env var (an unrelated API key, a hook toggle) never reaches the
# dispatched provider. Support mechanics only: it carries env, it judges nothing.
#
# AUTH-VS-SKILLS asymmetry (0624, OPERATOR-VERIFIED by real dispatch). The two
# providers store auth in DIFFERENT places, so the room is built differently:
#   * codex auth = a FILE (~/.codex/auth.json), but codex ALSO reads its personal
#     skills from CODEX_HOME/skills. --ignore-user-config governs config.toml ONLY,
#     NOT the skills dir -- with the REAL CODEX_HOME the user's ~/.codex/skills/*
#     (e.g. brick-protocol-migration-operator) STILL load (verified). So the room is
#     a TEMP CODEX_HOME whose empty skills/ blocks the personal skills, and auth.json
#     is COPIED into it so the door key still works. (--ignore-user-config then keeps
#     the user's config.toml out; only brick's MCP block is written into the temp.)
#   * claude auth = the macOS KEYCHAIN, pinned to the REAL HOME. A temp HOME cannot
#     reach the keychain -> auth fails. So the room keeps the REAL HOME and blocks the
#     personal stuff with FLAGS instead: --setting-sources excludes the `user` source
#     (drops ~/.claude skills/settings), disableAllHooks turns user hooks off, and
#     --strict-mcp-config + inline --mcp-config make brick's the ONLY MCP.
_ISOLATED_ENV_ALLOWLIST_KEYS: tuple[str, ...] = (
    "PATH",
    "HOME",  # set per provider (codex=temp HOME, claude=real HOME); never inherited raw
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "SHELL",
    "USER",
    "LOGNAME",
)
# Auth env that is CARRIED THROUGH the scrub so an API-KEY-authed user can still
# reach the backend (the door key). These are credential-bearing, so they are the
# ONLY user-env values forwarded; everything else is dropped. Per-provider, narrow.
# NOTE (0624): these are the API-KEY fallback path. The PRIMARY auth on this machine
# is non-env -- codex via a copied ~/.codex/auth.json, claude via the macOS keychain
# (real HOME) -- so carrying these keys is belt-and-suspenders, never the sole door.
_CLAUDE_AUTH_CARRY_ENV_KEYS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
)
_CODEX_AUTH_CARRY_ENV_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
)
_GEMINI_AUTH_CARRY_ENV_KEYS: tuple[str, ...] = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)
# LOCKED (0624 확정): the claude --setting-sources value that drops the user's
# personal source (~/.claude skills + settings) while KEEPING project-level
# settings. Excluding `user` is what makes claude not load the personal skills in
# the real-HOME room (operator-verified: with this value a "Brick Protocol skills?"
# prompt answers NO; the personal ~/.claude/skills are not visible).
_CLAUDE_ISOLATION_SETTING_SOURCES = "project"
# The codex credential files copied into the temp CODEX_HOME so the door key survives
# the skills-isolating temp home: auth.json (OpenAI/ChatGPT auth) and .env (the
# SAKANA_API_KEY etc. a custom provider's auth command reads). No path assumption
# beyond ~/.codex; a missing file is skipped.
_CODEX_CREDENTIAL_FILE_NAMES: tuple[str, ...] = ("auth.json", ".env")
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


def _claude_disable_hooks_settings_json() -> str:
    """Inline --settings JSON that turns the user's hooks off for a claude dispatch.

    ``disableAllHooks`` is the claude settings key that disables ALL hooks while
    leaving auth + MCP intact (operator-verified 0624: a real-HOME dispatch with this
    settings JSON authenticates and runs). This is the FLAG-based replacement for the
    old temp-HOME ``settings.json`` hooks scrub -- it disables the user's hooks without
    relocating HOME (which would break keychain auth)."""

    return json.dumps({"disableAllHooks": True}, sort_keys=True)


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

    The room is a TEMP CODEX_HOME whose EMPTY ``skills/`` blocks the user's personal
    ``~/.codex/skills/*`` (operator-verified 0624: --ignore-user-config alone does NOT
    block skills with the real CODEX_HOME; only a temp CODEX_HOME does). ``codex exec
    --ignore-user-config`` at the call site does NOT load ``$CODEX_HOME/config.toml``
    (per codex's own help) -- so the MCP + any custom provider definitions are wired by
    ``-c`` overrides at the call site, NOT by a config.toml file. AUTH "still uses
    CODEX_HOME" (codex help), so the real credential files are COPIED into the temp
    room: ``auth.json`` (the OpenAI/ChatGPT door key) and ``.env`` (carries
    provider-auth-command secrets such as the Sakana key the codex-fugu auth command
    reads). HOME + CODEX_HOME point at the temp room and the codex API-key env
    (fallback) is carried through the scrub. ``repo_root`` is unused here (the MCP is
    wired by -c at the call site) and kept for call-site signature stability. Support
    mechanics only: it relocates the user's OWN credential files into a throwaway room,
    it judges nothing and stores no credential of its own."""

    del repo_root
    if not _build_isolation_enabled():
        return None
    env = _scrubbed_base_env()
    env["HOME"] = str(codex_home)
    codex_config_dir = codex_home / ".codex"
    codex_config_dir.mkdir(parents=True, exist_ok=True)
    env["CODEX_HOME"] = str(codex_config_dir)
    # Copy the real codex credential files (the door keys) into the temp room so auth
    # works there. The temp home is what blocks the personal skills; the copied files
    # are what keep the dispatch logged in. NEVER raises: a user authed only by API key
    # (no auth.json / no .env) just has nothing to copy and falls back to the carried
    # env keys below.
    _copy_codex_credentials_into_home(codex_config_dir)
    _carry_auth_env(env, _CODEX_AUTH_CARRY_ENV_KEYS)
    return env


def _copy_codex_credentials_into_home(codex_config_dir: Path) -> None:
    """Copy the real codex credential files into the temp CODEX_HOME (best-effort).

    The temp CODEX_HOME isolates skills but starts with no credential; codex auth is
    file-based, so the credential files are copied in: ``auth.json`` (the door key) and
    ``.env`` (the SAKANA_API_KEY etc. that a custom provider's auth command reads).
    Support mechanics only -- it relocates the user's own credential files into the
    throwaway room and stores nothing of its own. NEVER raises: a missing file (e.g.
    the user authed by API key, so there is no auth.json/.env) is simply skipped."""

    real_codex = Path(os.path.expanduser("~")) / ".codex"
    for name in _CODEX_CREDENTIAL_FILE_NAMES:
        source = real_codex / name
        try:
            if source.is_file():
                shutil.copyfile(source, codex_config_dir / name)
        except OSError:
            continue


def _codex_user_provider_config_cli_args() -> list[str]:
    """Re-emit the user's ``[model_providers.*]`` config as ``-c`` overrides.

    WHY (0624, operator-verified): the codex dispatch runs with ``--ignore-user-config``
    (so the user's ~/.codex/config.toml -- with its skills-trust, hooks, user MCP --
    is NOT loaded) inside a TEMP CODEX_HOME (so the personal skills dir is empty). But a
    PROVIDER-ROUTED adapter (codex-fugu-local routes ``model_provider="sakana"``) needs
    the matching ``[model_providers.sakana]`` DEFINITION (base_url, wire_api, the
    auth.command), which lived in that now-ignored config.toml. We therefore read ONLY
    the ``model_providers`` table from the real config and flatten it back to dotted
    ``-c key=<toml-value>`` overrides -- restoring the provider DEFINITIONS without
    re-admitting the user's MCP/hooks/skills. Hardcodes NOTHING (reads the user's own
    config). Returns [] when isolation is off, the config is absent/unreadable, or it
    declares no model_providers (plain codex-local needs none). Support mechanics only:
    it relays the user's own provider config as data, it makes no provider decision."""

    if not _build_isolation_enabled():
        return []
    config_path = Path(os.path.expanduser("~")) / ".codex" / "config.toml"
    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    providers = data.get("model_providers")
    if not isinstance(providers, Mapping):
        return []
    args: list[str] = []
    _flatten_toml_to_cli_overrides("model_providers", providers, args)
    return args


def _flatten_toml_to_cli_overrides(prefix: str, node: Any, out: list[str]) -> None:
    """Flatten a parsed-TOML subtree into ``-c dotted.key=<toml-value>`` pairs.

    Scalars become a single ``-c`` pair whose value is rendered back as TOML (strings
    quoted via json.dumps -- valid TOML basic-string syntax -- bools lowercased, numbers
    repr'd). Nested tables recurse with a dotted prefix. Lists/other are rendered as a
    JSON array literal (valid TOML inline array for scalars), which is sufficient for
    the model_providers tables in practice. Pure data shaping, no judgment."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            _flatten_toml_to_cli_overrides(f"{prefix}.{key}", value, out)
        return
    if isinstance(node, bool):
        rendered = "true" if node else "false"
    elif isinstance(node, (int, float)):
        rendered = repr(node)
    elif isinstance(node, str):
        rendered = json.dumps(node)
    else:
        rendered = json.dumps(node)
    out.extend(("-c", f"{prefix}={rendered}"))


def _claude_isolated_run_env() -> dict[str, str] | None:
    """Build the scrubbed run env for a claude dispatch (None when isolation is off).

    KEEPS THE REAL HOME (0624, operator-verified): claude authenticates via the macOS
    KEYCHAIN, which is pinned to the real HOME -- a temp HOME cannot reach it and auth
    fails. So the room does NOT relocate HOME; it isolates the personal stuff with
    FLAGS at the call site instead (``--setting-sources project`` drops the user's
    skills/settings, ``disableAllHooks`` turns user hooks off, ``--strict-mcp-config``
    + inline ``--mcp-config`` make brick's the ONLY MCP). This function therefore only
    builds the env from a clean allowlist (no stray user vars) WITHOUT overriding HOME,
    and carries the claude API-key env (fallback) through the scrub. Support mechanics
    only: it carries env, it judges nothing and stores no credential of its own."""

    if not _build_isolation_enabled():
        return None
    # Start from the clean allowlist, then layer the REAL HOME back on (keychain auth
    # is pinned to it). We deliberately do NOT inherit the full user env -- only the
    # allowlisted keys plus the real HOME -- so a stray user var still cannot leak,
    # while the keychain (addressed by HOME) stays reachable.
    env = _scrubbed_base_env()
    real_home = os.environ.get("HOME")
    if real_home:
        env["HOME"] = real_home
    _carry_auth_env(env, _CLAUDE_AUTH_CARRY_ENV_KEYS)
    return env


def _gemini_api_key_run_env(gemini_home: Path) -> dict[str, str]:
    """Build the Gemini CLI room that forces API-key auth without touching user HOME."""

    env = _scrubbed_base_env()
    env["HOME"] = str(gemini_home)
    env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
    _carry_auth_env(env, _GEMINI_AUTH_CARRY_ENV_KEYS)
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
        agent_request_effective_write,
        agent_request_read_tier,
    )

    if (
        spec.invocation_args_kind == "gemini-p-json-flash"
        and command_runner is None
        and os.environ.get("BRICK_CHECKER_PROFILE_SWEEP") == "1"
    ):
        raise ValueError(
            "checker profile sweep must not invoke live gemini-local CLI; "
            "use an injected command_runner fixture"
        )

    executable_path = spec.executable_name if command_runner is not None else shutil.which(spec.executable_name)
    if not executable_path:
        raise FileNotFoundError(f"local CLI executable not found for {spec.adapter_ref}")
    if spec.invocation_args_kind == "codex-exec-readonly":
        sandbox = _codex_sandbox_for_request(request)
        repo_root = _repo_root_for_request(spec)
        # ISOLATION (Smith 0624): the codex dispatch runs in a TEMP CODEX_HOME whose
        # empty skills/ blocks the user's personal ~/.codex/skills/* (operator-verified:
        # --ignore-user-config alone does NOT block skills with the real CODEX_HOME).
        # --ignore-user-config makes codex skip the user's own config.toml entirely, so
        # the brick MCP + any custom provider DEFINITIONS are re-supplied by -c overrides
        # (NOT a config.toml file, which would be ignored). AUTH still uses CODEX_HOME, so
        # the real auth.json + .env are COPIED into the temp room by the env builder.
        # When isolation is opted out (BRICK_BUILD_ISOLATION=0) run_env stays None
        # (byte-identical inherited-env behavior) and the flags are omitted.
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
            # registration shape connect.py renders). Restore ONLY the user's custom
            # [model_providers.*] DEFINITIONS as -c overrides (so a provider-routed
            # adapter like codex-fugu-local resolves model_provider="sakana"), WITHOUT
            # re-admitting the user's MCP/hooks/skills. Provider defs go BEFORE the
            # spec's routing overrides below so the routing references a defined
            # provider. All only when isolation is on.
            if run_env is not None:
                args_list.append("--ignore-user-config")
                args_list.extend(_codex_mcp_config_cli_args(repo_root))
                args_list.extend(_codex_user_provider_config_cli_args())
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
        # ISOLATION (Smith 0624): the claude dispatch keeps the REAL HOME (claude auths
        # via the macOS keychain, pinned to the real HOME -- a temp HOME breaks auth)
        # and isolates the personal stuff with FLAGS:
        #   * --mcp-config (inline brick MCP) + --strict-mcp-config: brick's is the ONLY
        #     MCP; the user's ~/.claude MCP servers are suppressed (lever #1);
        #   * --settings disableAllHooks: the user's hooks are off in the build room
        #     without a temp-HOME settings.json (which would break keychain auth);
        #   * --setting-sources project: the user `user` source (personal skills +
        #     settings) is dropped; only project-level settings load.
        # Opt out (BRICK_BUILD_ISOLATION=0) -> run_env None (real inherited env, no HOME
        # override) and all four isolation flags omitted (byte-identical legacy shape).
        run_env = _claude_isolated_run_env()
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
        allowed_tools = knobs.get("allowed_tools", "")
        if allowed_tools:
            args_list.extend(["--allowedTools", allowed_tools])
        # ISOLATION levers + MCP wire: attach ONLY the brick-protocol MCP, suppress the
        # user's ~/.claude MCP servers, turn user hooks off, and drop the user setting
        # source (personal skills/settings). Only when isolation is on.
        if run_env is not None:
            args_list.extend(
                [
                    "--mcp-config",
                    _claude_mcp_config_json(repo_root),
                    "--strict-mcp-config",
                    "--settings",
                    _claude_disable_hooks_settings_json(),
                    "--setting-sources",
                    _CLAUDE_ISOLATION_SETTING_SOURCES,
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
            write_tier = agent_request_effective_write(request)
            allowed_gemini_tools = _gemini_allowed_tool_names_for_request(request)
            native_tool_tier = bool(allowed_gemini_tools)
            policy_path = temp_root / (
                "native-grant-policy.toml" if native_tool_tier else "no-tools-policy.toml"
            )
            policy_path.write_text(
                _gemini_admin_policy_for_request(request),
                encoding="utf-8",
            )
            run_cwd = cwd if read_tier or write_tier else temp_root
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
            run_env = _gemini_api_key_run_env(gemini_home)
            if not _gemini_api_key_env_present(run_env):
                raise FileNotFoundError(
                    "gemini-local requires an API key in env "
                    + " or ".join(_GEMINI_API_KEY_ENV_VARS)
                    + " (none set)"
                )
            model_arg = _model_cli_arg(request, spec) or "gemini-3.5-flash"
            args = (
                executable_path,
                "-p",
                prompt,
                "--output-format",
                "json",
                "--model",
                model_arg,
                "--yolo",
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
    if _request_blocks_source_mutation(request):
        return _merge_texts(
            spec.proof_limits,
            "Agent hook:reviewer-no-mutation blocks provider-projected source mutation",
        )
    return _merge_texts(
        spec.proof_limits,
        "workspace write is limited by Brick-declared write_scope",
    )


def _not_proven_for_request(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> tuple[str, ...]:
    from .agent_adapter import _merge_texts, agent_request_effective_write

    if not agent_request_effective_write(request) or _request_blocks_source_mutation(request):
        return spec.not_proven
    return _merge_texts(
        spec.not_proven,
        "semantic correctness of file edits",
    )


def _codex_sandbox_for_request(request: AgentAdapterRequest) -> str:
    from .agent_adapter import agent_request_effective_write

    if not agent_request_effective_write(request) or not _request_allows_source_mutation(request):
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
    tool policy) + acceptEdits + a write-aware system prompt. When the request
    qualifies for the read tier, it also uses the normal claude invocation plane
    (acceptEdits) but projects ONLY the read-only browse tool list from YAML
    policy (Read/Grep/Glob). The old plan-mode read tier made Claude refuse Read;
    BRICK's control boundary is the declared tool list, not provider plan mode.
    Ambiguous no-tier requests still fail closed to plan + no tools. Unlike codex
    there is NO OS sandbox here -- and NONE of the claude-side knobs is a verified
    write boundary: the tools allowlist, acceptEdits, claude's own provider-side
    protected-path prompts, cwd, and the injected prompt rules are all
    advisory/provider-state, not enforced by this code. The ONLY enforcement
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

    if agent_request_effective_write(request) and _request_allows_source_mutation(request):
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
                "allowed_tools": tools,
                "system_prompt": _CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT,
            }
    if agent_request_effective_write(request) and _request_blocks_source_mutation(request):
        from .agent_resources import claude_tools_for_tool_policies

        mapping = claude_tools_for_tool_policies(
            list(request.tool_policy_refs),
            write_need=False,
            native_grant_resources=request.agent_instruction_packet.get("tool_policy_resources", []),
        )
        return {
            "permission_mode": "acceptEdits",
            "tools": ",".join(mapping["tools"]),
            "allowed_tools": ",".join(mapping["tools"]),
            "system_prompt": _CLAUDE_READ_ONLY_SYSTEM_PROMPT,
        }
    if agent_request_read_tier(request):
        from .agent_resources import claude_tools_for_tool_policies

        mapping = claude_tools_for_tool_policies(
            list(request.tool_policy_refs),
            write_need=False,
            native_grant_resources=request.agent_instruction_packet.get("tool_policy_resources", []),
        )
        return {
            "permission_mode": "acceptEdits",
            "tools": ",".join(mapping["tools"]),
            "allowed_tools": ",".join(mapping["tools"]),
            "system_prompt": _CLAUDE_READ_ONLY_SYSTEM_PROMPT,
        }
    return {
        "permission_mode": "plan",
        "tools": "",
        "allowed_tools": "",
        "system_prompt": _CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT,
    }


_GEMINI_CLIENT_ERROR_PATH_RE = re.compile(
    r"""[^\s'"`<>]*gemini-client-error-[^\s'"`<>]*\.json"""
)
_GEMINI_CLIENT_ERROR_MAX_BYTES = 64 * 1024


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
    gemini_error_excerpt = _gemini_client_error_excerpt(completed.stderr)
    if gemini_error_excerpt:
        parts.append(f"gemini_client_error_excerpt={gemini_error_excerpt}")
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

    raw_path = _stderr_gemini_client_error_path_raw(stderr)
    if not raw_path:
        return ""
    return _redacted_diagnostic_excerpt(raw_path, limit=240)


def _stderr_gemini_client_error_path_raw(stderr: str) -> str:
    match = _GEMINI_CLIENT_ERROR_PATH_RE.search(stderr)
    return match.group(0) if match else ""


def _gemini_client_error_excerpt(stderr: str) -> str:
    raw_path = _stderr_gemini_client_error_path_raw(stderr)
    if not raw_path:
        return ""
    # The Gemini CLI may print a diagnostic file path to stderr. Treat that path
    # as a redacted address only; do not read provider-selected files into
    # adapter error evidence.
    return ""


def _gemini_client_error_summary(payload: Mapping[str, Any]) -> str:
    from .agent_adapter import _try_json_value

    observed: list[str] = []

    def _add(label: str, value: Any) -> None:
        if value in (None, ""):
            return
        rendered = f"{label}={value}"
        if rendered not in observed:
            observed.append(rendered)

    def _visit(value: Any, *, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(value, Mapping):
            for key in ("code", "status", "reason", "domain", "message", "service"):
                if key in value:
                    _add(key, value.get(key))
            metadata = value.get("metadata")
            if isinstance(metadata, Mapping):
                for key in ("service", "reason", "domain"):
                    if key in metadata:
                        _add(key, metadata.get(key))
            for child in value.values():
                _visit(child, depth=depth + 1)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for child in value:
                _visit(child, depth=depth + 1)
            return
        if isinstance(value, str):
            nested = _try_json_value(value)
            if isinstance(nested, (Mapping, list, tuple)):
                _visit(nested, depth=depth + 1)

    _visit(payload)
    return "; ".join(observed)


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
