"""Friendly, never-raising onboarding flow (ONBOARDING-WIZARD-0).

This support surface ties the EXISTING onboarding pieces into one guided,
plain-Korean, beginner-safe experience:

  1. preflight  -> support.connection.agent_adapter.preflight_provider
  2. connect    -> support.connection.connect.render_connect
  3. example    -> support.operator.driver.run_building_intake (the PART-2
                   confirmed-task.md + selected-preset -> running-Building seam).
                   Driven on adapter:local (read-only, in-process) by default;
                   when preflight reports the real provider READY and the caller
                   opts in, the SAME seam runs the example on that provider's
                   observed-write adapter (codex/claude/gemini local).
  4. handoff    -> a plain-Korean closing line that NAMES the Phase-1 seam verb
                   (driver.run_building_intake) the beginner uses next.

WHY THIS EXISTS: an AI-never-used beginner needs ONE flow that, even when a
provider is missing/unauthed, NEVER throws a stack-trace. Every step is wrapped
so a failure becomes a friendly status field, not a raised traceback.
``run_onboard`` returns a structured dict and NEVER raises.

This is support mechanics ONLY. It reuses existing functions; it does not own
Agent / Brick / Link meaning, choose Movement, judge success or quality, store
credentials, auto-edit the user's config, or fabricate provider readiness.
(The OPT-IN ``--recording`` step is the one explicit exception on config: it
writes ONLY this checkout's gitignored .claude/.codex machine config, paths
computed from the actual repo root, idempotently, and never silently
overwrites a user-modified file -- compare + skip + warn.) The
real-vs-local example adapter is driven by the PREFLIGHT READINESS EVIDENCE
(recorded as a structured field), NOT by support guessing -- and the example
NEVER touches the repo working tree (evidence + any adapter cwd stay under a
TEMP output_root). The proceed/retry decision stays a human / Link concern;
onboarding only RECORDS what it observed.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.connection import connect
from brick_protocol.support.connection.adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_FUGU_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_LOCAL,
)
from brick_protocol.support.connection.adapter_model_casting import (
    _validate_model_ref_for_adapter,
)
from brick_protocol.support.connection.adapter_subprocess import (
    preflight_provider,
)
from brick_protocol.support.connection.agent_adapter import (
    adapter_is_write_capable,
)
from brick_protocol.support.operator.driver import run_building_intake
from brick_protocol.support.operator.frontier_observation import (
    observe_building_frontier,
)
from brick_protocol.support.operator.building_operation_common import (
    _jsonl_records,
    _read_json_mapping,
    _rel,
    _repo_path,
)
from brick_protocol.support.operator.provider_registry import (
    DEFAULT_MODEL_REF_BY_ADAPTER,
    LLM_ALIAS_DECLARATIONS,
    llm_alias_declaration,
    register_ready_provider,
)
from brick_protocol.support.operator.sink_registry import (
    SINK_REF_DASHBOARD,
    SINK_REF_SLACK,
    brick_home as sink_brick_home,
    record_sink_reachability,
)
from brick_protocol.support.operator.worktree_sandbox import reclaim_wip_anchor
from brick_protocol.link.transition import DISPOSITION_ACTIONS


_REPO_ROOT = Path(__file__).resolve().parents[2]

# The Phase-1 seam verb the example routes through and the handoff names. Kept as
# a constant so the checker can pin BOTH the routing and the handoff pointer.
SEAM_VERB = "support.operator.driver.run_building_intake"

# Legacy bundled example plan ref. The example no longer walks this hand-authored
# plan directly (it routes through the seam instead); the constant is retained so
# the existing path_exists pins and the bundled-plan boundary sweep stay honest.
EXAMPLE_PLAN_REL = "brick/building_plans/onboarding-example-0.yaml"

# The bundled task source the seam materializes (an already-present, repo-relative
# task.md template; onboarding authors no new task file). Its ## Objective /
# ## First-Line Contract / ## Desired Output headings feed the materializer's
# task summary.
EXAMPLE_TASK_SOURCE_REF = "brick/templates/tasks/source-template.md"

# The caller / COO declaration recorded on the confirmed intent. NOT support:.
EXAMPLE_DECLARED_BY = "coo"

# Preset for the FALLBACK (adapter:local) example: an all-read-only chain
# (design / review / closure -- NO write_need Brick), so it routes through the
# seam on the in-process read-only adapter:local with NO write_scope and never
# touches the repo. NOTE (gate wiring 0610): the example moved OFF
# governed-change-review when its gate_concept_profile became REAL wired gates
# -- that preset now legitimately HOLDs at the closure human gate until a
# human disposition exists, and onboarding must NOT auto-supply a fake human
# disposition just to make the example complete.
# GRAPH (G5 S4): the example now routes through an onboarding-only GRAPH variant
# of design-contract-only -- same design / review / closure forward, but carrying
# node_reroute_budgets so it materializes as a graph and the example walks the
# DYNAMIC walker (linear -> dynamic). The shared design-contract-only preset
# (checker profiles, quickstart, hardening tests depend on it) stays untouched.
EXAMPLE_LOCAL_PRESET_REF = "building-chain-preset:onboarding-example-graph"

# Preset for the REAL-PROVIDER example: a LINEAR chain that DOES include a
# write_need Brick (work). A write_need Brick requires an observed-write-capable
# adapter (the canonical set agent_adapter._OBSERVED_WRITE_ADAPTER_REFS, read via
# adapter_is_write_capable),
# so this preset is only routed when preflight reports an observed-write provider
# READY and the caller opts in.
EXAMPLE_REAL_PRESET_REF = "building-chain-preset:fast-fix"

# The write_scope declared for the real-provider example. It is confined to the
# example Building's own evidence area and forbids every repo surface, so even a
# real provider cannot write the working tree. (The example also runs with
# adapter_cwd under the TEMP output_root, a second containment layer.)
_EXAMPLE_WRITE_SCOPE: dict[str, Any] = {
    "allowed_paths": ["onboarding-example/**"],
    "forbidden_paths": [
        ".git/**",
        "AGENTS.md",
        "agent/**",
        "brick/**",
        "link/**",
        "support/**",
        "project/**",
        "**/*token*",
        "**/*credential*",
        "**/*secret*",
        "**/.env",
        "**/.env.*",
    ],
}

# Friendly host -> adapter ref map. ``local`` is the in-process smoke host (no
# CLI); codex/claude/gemini are the admitted local CLI providers.
_HOST_ADAPTER_REF = {
    "codex": ADAPTER_CODEX_LOCAL,
    "claude": ADAPTER_CLAUDE_LOCAL,
    "gemini": ADAPTER_GEMINI_LOCAL,
    "fugu": ADAPTER_CODEX_FUGU_LOCAL,
    "local": ADAPTER_LOCAL,
}
# ``connect`` only renders codex/claude config; other hosts get a friendly note.
_CONNECT_TARGETS = {"codex", "claude"}

SUPPORTED_HOSTS = tuple(_HOST_ADAPTER_REF)
INTERACTIVE_PROVIDER_ALIASES = tuple(LLM_ALIAS_DECLARATIONS)


def _safe_repo_root(repo_root: Path | str | None) -> Path:
    if repo_root is None:
        return _REPO_ROOT
    try:
        return Path(repo_root).resolve()
    except Exception:  # noqa: BLE001 -- never raise on a bad path
        return _REPO_ROOT


def _path_is_self_or_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _unsafe_live_repo_adapter_cwd(
    adapter_cwd: Path | str | None,
    *,
    repo_root: Path,
) -> dict[str, str] | None:
    if adapter_cwd is None:
        return None
    try:
        candidate = Path(adapter_cwd).resolve()
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        return {
            "error_kind": "invalid_adapter_cwd",
            "error_message": f"adapter_cwd could not be resolved: {type(exc).__name__}: {exc}",
            "message_ko": "adapter_cwd 경로를 확인할 수 없어요.",
        }
    if _path_is_self_or_child(candidate, repo_root):
        return {
            "error_kind": "adapter_cwd_refused_live_repo",
            "error_message": (
                "launch_assembled_building() refuses caller adapter_cwd inside "
                f"the live repo/customer tree: {candidate}"
            ),
            "message_ko": (
                "adapter_cwd가 라이브 repo/customer tree 안을 가리켜 거부했어요. "
                "엔진이 만든 sandbox_cwd를 사용해야 해요."
            ),
        }
    return None


def _building_root_signature(path: Path) -> bool:
    """True for a plausible recorded Building root, without judging its state."""

    return path.is_dir() and ((path / "raw").is_dir() or (path / "work").is_dir())


def _approval_building_root_candidates(
    building_ref: str,
    *,
    output_root: Path | str | None,
    repo_root: Path,
) -> list[Path]:
    building_path = Path(building_ref).expanduser()
    if building_path.is_absolute():
        return [building_path.resolve()]
    candidates: list[Path] = []
    if output_root is not None:
        candidates.append((Path(output_root).expanduser() / building_path).resolve())
    else:
        candidates.append((Path.home() / ".brick" / "goal-runs" / building_path).resolve())
    candidates.append((repo_root / building_path).resolve())
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _resolve_approval_building_root(
    building_ref: str,
    *,
    output_root: Path | str | None,
    repo_root: Path,
) -> tuple[Path | None, list[Path]]:
    """Resolve operator-entered building refs with repo-relative recovery.

    Existing goal-runs refs keep their historical precedence. Repo-relative refs
    are admitted when they point at a real Building vessel in this checkout.
    """

    candidates = _approval_building_root_candidates(
        building_ref,
        output_root=output_root,
        repo_root=repo_root,
    )
    for candidate in candidates:
        if _building_root_signature(candidate):
            return candidate, candidates
    return None, candidates


def _prepare_resume_adapter_cwd(
    *,
    repo_root: Path,
    building_id: str,
    adapter_cwd: Path | str | None,
) -> tuple[Path | None, dict[str, Any] | None]:
    if adapter_cwd is not None:
        adapter_cwd_refusal = _unsafe_live_repo_adapter_cwd(adapter_cwd, repo_root=repo_root)
        if adapter_cwd_refusal is not None:
            return None, adapter_cwd_refusal
        return Path(adapter_cwd).expanduser().resolve(), {
            "adapter_cwd_auto_created": False,
            "adapter_cwd_source": "caller",
        }
    try:
        from brick_protocol.support.operator.worktree_sandbox import (  # noqa: PLC0415
            WorktreeSandboxError,
            create_worktree_sandbox,
            probe_worktree_capable,
        )

        probe = probe_worktree_capable(repo_root)
        if not probe.ok:
            return None, {
                "error_kind": "resume_requires_isolated_adapter_cwd",
                "error_message": (
                    "onboard approve could not auto-create an isolated adapter_cwd "
                    f"because worktree probe failed: {probe.reason}"
                ),
                "message_ko": "resume adapter_cwd 자동 생성 조건을 만족하지 못했어요.",
                "adapter_cwd_auto_create_reason": probe.reason,
            }
        sandbox = create_worktree_sandbox(
            repo_root,
            building_id=building_id,
            base_sha=probe.base_sha,
        )
    except WorktreeSandboxError as exc:
        return None, {
            "error_kind": "resume_requires_isolated_adapter_cwd",
            "error_message": (
                "onboard approve could not auto-create an isolated git worktree "
                f"for resume: {type(exc).__name__}: {exc}"
            ),
            "message_ko": "resume adapter_cwd 자동 worktree 생성에 실패했어요.",
            "adapter_cwd_auto_create_reason": type(exc).__name__,
        }
    return sandbox.path, {
        "adapter_cwd_auto_created": True,
        "adapter_cwd_source": "engine_worktree",
        "adapter_cwd_base_sha": sandbox.base_sha,
        "worktree_path": str(sandbox.path),
    }


def _normalize_host(host: Any) -> str:
    return host.strip().lower() if isinstance(host, str) else ""


def _preflight_step(host: str, *, command_runner: Any | None = None) -> dict[str, Any]:
    """Step 1: friendly provider readiness. Never raises."""

    adapter_ref = _HOST_ADAPTER_REF.get(host, "")
    if not adapter_ref:
        return {
            "ok": False,
            "adapter_ref": "",
            "message_ko": (
                "알 수 없는 host예요. 지원하는 것: "
                + ", ".join(SUPPORTED_HOSTS)
            ),
        }
    try:
        status = preflight_provider(adapter_ref, command_runner=command_runner)
    except Exception as exc:  # noqa: BLE001 -- no-raise is the whole point
        # preflight_provider is designed to never raise; if it ever does, we
        # still surface a friendly field instead of a stack-trace.
        return {
            "ok": False,
            "adapter_ref": adapter_ref,
            "message_ko": (
                "provider 상태를 확인하는 중에 문제가 생겼어요. "
                "잠시 후 다시 시도해 주세요."
            ),
            "error_kind": type(exc).__name__,
        }
    return dict(status)


def _preflight_readiness(preflight: dict[str, Any]) -> str:
    """Classify the preflight result into a structured readiness token.

    Pure record of WHAT preflight observed -- it judges no success / quality and
    chooses no Movement. The proceed/retry decision stays a human / Link concern.

    Tokens:
      ready    -> the provider CLI is installed AND the cheap --version probe ran
                  (preflight ok True). NOT a login/auth proof -- authed may stay
                  "unknown" -- only that the CLI is runnable.
      unauthed -> the CLI is installed but the probe did not succeed (most often a
                  login is needed).
      missing  -> no CLI installed (or a retired / unknown adapter ref).
      unknown  -> preflight reported nothing classifiable (defensive).
    """

    if bool(preflight.get("ok")):
        return "ready"
    if bool(preflight.get("installed")):
        return "unauthed"
    if "installed" in preflight:
        return "missing"
    return "unknown"


def _model_ref_for_alias(alias: str) -> str:
    declaration = llm_alias_declaration(alias)
    adapter_ref = str(declaration["adapter_ref"])
    return str(
        declaration.get("model_ref")
        or DEFAULT_MODEL_REF_BY_ADAPTER.get(adapter_ref, "model:default")
    )


def _validated_model_ref_for_alias(alias: str, raw_model_ref: str) -> str:
    declaration = llm_alias_declaration(alias)
    adapter_ref = str(declaration["adapter_ref"])
    default_ref = _model_ref_for_alias(alias)
    requested = str(raw_model_ref or "").strip() or default_ref
    try:
        _validate_model_ref_for_adapter(adapter_ref, requested)
    except ValueError:
        return default_ref
    return requested


def run_interactive_provider_intake(
    *,
    prompt_func: Any,
    host_default: str = "codex",
    providers: Sequence[str] = INTERACTIVE_PROVIDER_ALIASES,
) -> dict[str, Any]:
    """Collect provider/model choices for an already-confirmed interactive TTY.

    This front-end collector does not preflight or persist. The caller owns the
    TTY gate and injects ``prompt_func`` so fixtures never read real stdin.
    """

    if not callable(prompt_func):
        raise TypeError("prompt_func must be callable")
    allowed = tuple(provider for provider in providers if provider in LLM_ALIAS_DECLARATIONS)
    if not allowed:
        raise ValueError("providers must include at least one admitted llm alias")
    default_alias = str(host_default or "codex").strip().lower()
    if default_alias not in allowed:
        default_alias = "codex" if "codex" in allowed else allowed[0]
    raw_alias = str(
        prompt_func(
            "Provider to register "
            f"({'/'.join(allowed)}/skip) [{default_alias}]: "
        )
        or ""
    ).strip().lower()
    if raw_alias == "skip":
        return {
            "kind": "interactive-provider-intake",
            "skipped": True,
            "host": "",
            "model_ref": "",
            "available_provider_aliases": list(allowed),
        }
    alias = raw_alias or default_alias
    try:
        declaration = llm_alias_declaration(alias)
    except ValueError:
        alias = default_alias
        declaration = llm_alias_declaration(alias)
    default_model_ref = _model_ref_for_alias(alias)
    raw_model_ref = str(
        prompt_func(f"Model ref for {alias} [{default_model_ref}]: ") or ""
    ).strip()
    model_ref = _validated_model_ref_for_alias(alias, raw_model_ref)
    return {
        "kind": "interactive-provider-intake",
        "skipped": False,
        "host": alias,
        "adapter_ref": str(declaration["adapter_ref"]),
        "model_ref": model_ref,
        "default_model_ref": default_model_ref,
        "model_ref_fell_back_to_default": bool(raw_model_ref and raw_model_ref != model_ref),
        "available_provider_aliases": list(allowed),
    }


def run_interactive_gemini_key_intake(
    *,
    prompt_func: Any,
    host: str,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """B4 (0703): if gemini was chosen and no key is in the environment, collect
    and persist one on the spot instead of only pointing at an env var to set
    by hand. Mirrors the existing Slack bot-token provisioning shape
    (``_append_report_env_values`` -> ``~/.brick/report.env``, 0600) rather
    than inventing a new persistence path. No-op (never prompts) for any
    other host, or when a key is already present. Never raises.
    """

    import os  # noqa: PLC0415

    from brick_protocol.support.connection.adapter_gemini_http import (  # noqa: PLC0415
        _gemini_api_key_env_present,
    )

    if not callable(prompt_func):
        raise TypeError("prompt_func must be callable")
    if str(host or "").strip().lower() != "gemini":
        return {"kind": "interactive-gemini-key-intake", "applicable": False, "provisioned": False}
    if _gemini_api_key_env_present(env if env is not None else os.environ):
        return {
            "kind": "interactive-gemini-key-intake",
            "applicable": True,
            "provisioned": False,
            "message_ko": "GEMINI_API_KEY(또는 GOOGLE_API_KEY)가 이미 있어요, 그대로 써요 ✅",
        }
    raw_key = str(
        prompt_func(
            "Gemini API key (GEMINI_API_KEY, 비워두면 나중에 직접 설정): "
        )
        or ""
    ).strip()
    if not raw_key:
        return {
            "kind": "interactive-gemini-key-intake",
            "applicable": True,
            "provisioned": False,
            "message_ko": (
                "그냥 넘어갔어요. 나중에 GEMINI_API_KEY 또는 GOOGLE_API_KEY 를 "
                "직접 설정하면 돼요."
            ),
        }
    target = _report_env_path()
    _append_report_env_values(target, {"GEMINI_API_KEY": raw_key})
    return {
        "kind": "interactive-gemini-key-intake",
        "applicable": True,
        "provisioned": True,
        "report_env_path": str(target),
        "message_ko": f"Gemini API 키를 {target}(0600)에 저장했어요 ✅",
    }


def _connect_step(host: str, repo_root: Path) -> dict[str, Any]:
    """Step 2: render the connect config text. Never raises. No auto-edit."""

    if host not in _CONNECT_TARGETS:
        return {
            "ok": True,
            "target": host,
            "config_text": "",
            "message_ko": (
                f"{host}는 자동 연결 설정이 따로 필요 없어요. "
                "(연결 설정은 codex / claude에만 해당돼요.)"
            ),
        }
    try:
        config_text = connect.render_connect(host, repo_root)
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        return {
            "ok": False,
            "target": host,
            "config_text": "",
            "message_ko": (
                "연결 설정 문구를 만드는 중에 문제가 생겼어요. "
                "잠시 후 다시 시도해 주세요."
            ),
            "error_kind": type(exc).__name__,
        }
    return {
        "ok": True,
        "target": host,
        "config_text": config_text,
        "message_ko": (
            "아래 연결 설정을 복사해서 안내대로 붙여넣으세요. "
            "(설정 파일은 자동으로 바꾸지 않아요.)"
        ),
    }


def run_provider_register_step(
    host: str,
    *,
    model_ref: str | None = None,
    command_runner: Any | None = None,
) -> dict[str, Any]:
    """Register the requested LLM provider only after ready preflight evidence."""

    normalized_host = _normalize_host(host)
    preflight = _preflight_step(normalized_host, command_runner=command_runner)
    readiness = _preflight_readiness(preflight)
    adapter_ref = str(preflight.get("adapter_ref") or "")
    if adapter_ref == ADAPTER_LOCAL:
        return {
            "ok": True,
            "action": "skipped_local",
            "adapter_ref": adapter_ref,
            "preflight_readiness": readiness,
            "message_ko": "local host는 provider 등록이 필요 없어요.",
        }
    if readiness != "ready" or not adapter_ref:
        return {
            "ok": True,
            "action": "skipped_not_ready",
            "adapter_ref": adapter_ref,
            "preflight_readiness": readiness,
            "message_ko": (
                "등록할 준비된 provider가 없어요. 나중에 provider 로그인을 마친 뒤 "
                "`brick init --host <host>`를 다시 실행하세요."
            ),
        }
    selected_model_ref = model_ref
    if selected_model_ref:
        try:
            _validate_model_ref_for_adapter(adapter_ref, selected_model_ref)
        except ValueError:
            selected_model_ref = DEFAULT_MODEL_REF_BY_ADAPTER.get(adapter_ref, "model:default")
    result = register_ready_provider(adapter_ref, preflight, model_ref=selected_model_ref)
    result["preflight_readiness"] = readiness
    result["message_ko"] = "준비된 provider를 ~/.brick/providers.yaml에 등록했어요."
    return result


def _choose_example_adapter(
    preflight: dict[str, Any],
    readiness: str,
    *,
    allow_real_provider: bool,
) -> dict[str, Any]:
    """Decide the example adapter FROM the preflight readiness evidence.

    Returns a plan dict {adapter_ref, chain_preset_ref, write_scope, real,
    adapter_choice_basis}. The choice is driven by recorded preflight evidence,
    NOT by support guessing or fabricating readiness:

    - REAL branch (observed-write adapter): only when the caller opted in AND
      preflight observed the real provider READY (readiness == "ready") AND that
      ready provider is in the canonical observed-write adapter set (read via
      ``adapter_is_write_capable`` -- never a hardcoded provider literal). Uses a preset
      with a write_need Brick (write_scope confined to the example area).
    - LOCAL fallback (adapter:local): every other case -- a missing / unauthed /
      unknown provider, or no opt-in. Uses an all-read-only preset (no
      write_scope), so it routes through the SAME seam in-process and never
      needs a provider CLI.

    This records evidence + routes accordingly; it does not claim success, judge
    quality, or choose Movement.
    """

    real_ref = str(preflight.get("adapter_ref") or "")
    real_ref_ready = readiness == "ready" and adapter_is_write_capable(real_ref)
    if allow_real_provider and real_ref_ready:
        return {
            "adapter_ref": real_ref,
            "chain_preset_ref": EXAMPLE_REAL_PRESET_REF,
            "write_scope": dict(_EXAMPLE_WRITE_SCOPE),
            "real": True,
            "adapter_choice_basis": (
                f"preflight readiness=ready for observed-write adapter {real_ref}"
                " + caller opt-in -> real-provider example"
            ),
        }
    if allow_real_provider and not real_ref_ready:
        basis = (
            "caller opted in but preflight readiness="
            f"{readiness} (not a ready observed-write provider) -> adapter:local fallback"
        )
    else:
        basis = "no real-provider opt-in -> adapter:local fallback"
    return {
        "adapter_ref": ADAPTER_LOCAL,
        "chain_preset_ref": EXAMPLE_LOCAL_PRESET_REF,
        "write_scope": None,
        "real": False,
        "adapter_choice_basis": basis,
    }


def _materialized_step_adapter_evidence(plan_path: Path) -> list[dict[str, str]]:
    """Return declared per-step Agent adapter evidence from a materialized plan."""

    try:
        packet = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    plan = packet.get("declared_plan_copy") if isinstance(packet, Mapping) else None
    if not isinstance(plan, Mapping):
        plan = packet if isinstance(packet, Mapping) else {}
    steps = plan.get("brick_steps")
    if not isinstance(steps, list):
        steps = plan.get("steps")
    if not isinstance(steps, list):
        return []
    evidence: list[dict[str, str]] = []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        row = {
            "step_ref": str(step.get("step_ref") or ""),
            "step_template_ref": str(step.get("step_template_ref") or ""),
            "selected_adapter_ref": str(step.get("selected_adapter_ref") or ""),
            "selected_model_ref": str(step.get("selected_model_ref") or ""),
        }
        if any(row.values()):
            evidence.append(row)
    return evidence


def _example_step(
    *,
    repo_root: Path,
    output_root: Path | str | None,
    preflight: dict[str, Any],
    readiness: str,
    allow_real_provider: bool,
    command_runner: Any | None = None,
) -> dict[str, Any]:
    """Step 3: route the first example through the PART-1 seam. Never raises.

    Builds a confirmed intent (bundled task.md + a registry preset + an adapter
    chosen FROM the preflight readiness evidence) and runs it through
    ``support.operator.driver.run_building_intake`` -- the confirmed-task.md ->
    running-Building verb the beginner uses next. Evidence (and any real-provider
    adapter cwd) lands under ``output_root`` (a TEMP dir by default), never the
    repo working tree.

    The adapter is the LOCAL in-process read-only ``adapter:local`` unless
    preflight observed the real provider READY and the caller opted in, in which
    case the SAME seam runs the example on that provider's observed-write adapter
    (codex/claude/gemini local). Which adapter ran, and WHY, is
    recorded as evidence.
    """

    choice = _choose_example_adapter(
        preflight, readiness, allow_real_provider=allow_real_provider
    )
    intent: dict[str, Any] = {
        "declared_by": EXAMPLE_DECLARED_BY,
        "task_source_ref": EXAMPLE_TASK_SOURCE_REF,
        "chain_preset_ref": choice["chain_preset_ref"],
        "selected_adapter_ref": choice["adapter_ref"],
        "building_id": "onboarding-example-0",
    }
    if choice["write_scope"] is not None:
        intent["write_scope"] = choice["write_scope"]

    # The common evidence fields recorded on EVERY outcome (ok or not): they make
    # the routing + the adapter choice auditable, not just a Korean string.
    base_evidence: dict[str, Any] = {
        "routed_through": SEAM_VERB,
        "task_source_ref": EXAMPLE_TASK_SOURCE_REF,
        "chain_preset_ref": choice["chain_preset_ref"],
        "adapter_ref": choice["adapter_ref"],
        "real_provider": bool(choice["real"]),
        "adapter_choice_basis": choice["adapter_choice_basis"],
        "preflight_readiness": readiness,
    }

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if output_root is None:
            temp_dir = tempfile.TemporaryDirectory(prefix="bp-onboard-example-")
            effective_root: Path | str = temp_dir.name
        else:
            effective_root = output_root
        # adapter_cwd is the TEMP root: even the real provider's own writes (when
        # the real branch runs) stay under the temp output_root, never the repo.
        result_obj = run_building_intake(
            intent,
            repo_root=repo_root,
            output_root=effective_root,
            overwrite_existing=True,
            adapter_cwd=effective_root if choice["real"] else None,
            command_runner=command_runner,
        )
        materialized_step_adapters = _materialized_step_adapter_evidence(result_obj.plan_path)
        run_result = result_obj.run_result
        frontier = observe_building_frontier(
            run_result.lifecycle_write.root, repo_root=repo_root
        )
        frontier_kind = str(frontier.get("frontier_kind") or "")
        returned_summary = ""
        if run_result.step_results:
            returned_value = run_result.step_results[0].adapter_result.returned_value
            if isinstance(returned_value, dict):
                returned_summary = str(returned_value.get("returned_summary") or "")
        if choice["real"]:
            # Name the ACTUAL ready provider (codex / claude / gemini -- observed-write
            # parity), never a hardcoded codex literal: reverse the friendly
            # host map for the adapter ref preflight reported READY.
            real_host = next(
                (
                    host
                    for host, ref in _HOST_ADAPTER_REF.items()
                    if ref == choice["adapter_ref"]
                ),
                str(choice["adapter_ref"]),
            )
            message_ko = (
                f"첫 예제 빌딩이 실제 provider({real_host})로 한 번 돌았어요 ✅ "
                "(결과는 아래 저장 위치에 그대로 남겨 뒀고, 작업 트리는 "
                "건드리지 않았어요. 직접 열어 보세요.)"
            )
        else:
            step_adapter_refs = {
                row.get("selected_adapter_ref", "")
                for row in materialized_step_adapters
                if row.get("selected_adapter_ref")
            }
            if step_adapter_refs - {ADAPTER_LOCAL}:
                message_ko = (
                    "첫 예제 빌딩이 adapter:local 진입점으로 한 번 돌았어요 ✅ "
                    "(role step은 선언된 Agent adapter로 실행됐고, step별 adapter는 "
                    "example_result.materialized_step_adapters에 기록됐어요. 결과는 아래 "
                    "저장 위치에 남겼고, 작업 트리는 건드리지 않았어요.)"
                )
            else:
                message_ko = (
                    "첫 예제 빌딩이 한 번 돌았어요 ✅ "
                    "(provider 없이 내부에서 실행됐고, 결과는 아래 저장 위치에 "
                    "그대로 남겨 뒀어요. 작업 트리는 건드리지 않았어요. 직접 열어 보세요.)"
                )
        return {
            "ok": True,
            "ran": True,
            "building_id": result_obj.building_id,
            "plan_ref": run_result.plan_ref,
            "plan_path": str(result_obj.plan_path),
            "plan_shape": result_obj.plan_shape,
            "walker_mode": result_obj.walker_mode,
            "evidence_root": str(run_result.lifecycle_write.root),
            "written_file_count": len(run_result.written_files),
            "frontier_kind": frontier_kind,
            "returned_summary": returned_summary,
            "message_ko": message_ko,
            "materialized_step_adapters": materialized_step_adapters,
            **base_evidence,
        }
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        return {
            "ok": False,
            "ran": False,
            "message_ko": (
                "예제 빌딩을 돌리는 중에 문제가 생겼어요. "
                "에이전트에게 'onboarding 예제가 안 돌아간다'고 알려 주세요."
            ),
            "error_kind": type(exc).__name__,
            # The FULL message, not just the class name: "split catalog
            # requires PyYAML" is diagnosable; bare "ValueError" is not.
            "error_message": str(exc),
            **base_evidence,
        }
    finally:
        if temp_dir is not None:
            try:
                temp_dir.cleanup()
            except Exception:  # noqa: BLE001 -- cleanup must never raise
                pass


# ---------------------------------------------------------------------------
# OPT-IN recording step (ONBOARDING-RECORDING-HOOKS, 0610)
#
# The AGENTS.md auto-record promise (Pre/PostToolUse + codex Subagent hooks)
# needs MACHINE CONFIG that a fresh clone does not have. This step copies the
# TRACKED machine-neutral templates (support/onboarding/{claude,codex}-hooks/)
# into THIS checkout's .claude/hooks/ + .codex/hooks/ and wires the hook
# commands (BRICK_REPO_ROOT + absolute paths computed from the ACTUAL repo
# root) into .claude/settings.local.json + .codex/hooks.json.
#
# Discipline: OPT-IN only (--recording flag), idempotent (re-run -> no-op),
# and NEVER silently overwrites a user-modified file (compare + skip + warn).
# It edits ONLY this checkout's gitignored .claude/.codex machine config --
# never the user's global config, never the repo's tracked surfaces.
# ---------------------------------------------------------------------------

RECORDING_HOOK_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("support/onboarding/claude-hooks/open-recording.py", ".claude/hooks/open-recording.py"),
    ("support/onboarding/claude-hooks/close-recording.py", ".claude/hooks/close-recording.py"),
    ("support/onboarding/codex-hooks/codex-open-recording.py", ".codex/hooks/codex-open-recording.py"),
    ("support/onboarding/codex-hooks/codex-close-recording.py", ".codex/hooks/codex-close-recording.py"),
)

CODEX_TRUST_INSTRUCTION_KO = (
    "codex 한 번만 신뢰 설정: 이 저장소에서 codex 를 처음 실행하면 "
    ".codex/hooks.json 을 신뢰할지 한 번 물어봐요. 그때 수락해야 codex 쪽 "
    "자동 기록이 켜집니다 (그 전까지는 아무 것도 기록되지 않아요)."
)


def _recording_hook_command(repo: Path, installed_rel: str) -> str:
    import shlex  # noqa: PLC0415

    repo_text = str(repo)
    return (
        f"BRICK_REPO_ROOT={shlex.quote(repo_text)} python3 "
        f"{shlex.quote(str(repo / installed_rel))}"
    )


def _recording_claude_hook_entries(repo: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        "PreToolUse": [
            {
                "matcher": "Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": _recording_hook_command(
                            repo, ".claude/hooks/open-recording.py"
                        ),
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": _recording_hook_command(
                            repo, ".claude/hooks/close-recording.py"
                        ),
                    }
                ],
            }
        ],
    }


def _recording_codex_hook_entries(repo: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        "SubagentStart": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": _recording_hook_command(
                            repo, ".codex/hooks/codex-open-recording.py"
                        ),
                        "timeout": 60,
                    }
                ],
            }
        ],
        "SubagentStop": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": _recording_hook_command(
                            repo, ".codex/hooks/codex-close-recording.py"
                        ),
                        "timeout": 60,
                    }
                ],
            }
        ],
    }


def _recording_copy_template(repo: Path, source_rel: str, target_rel: str) -> dict[str, Any]:
    """Copy ONE template (compare + skip + warn; never silently overwrite)."""

    import shutil  # noqa: PLC0415

    source = repo / source_rel
    target = repo / target_rel
    if not source.is_file():
        return {
            "path": target_rel,
            "action": "error",
            "note": f"template missing: {source_rel}",
        }
    if target.exists():
        try:
            if target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8"):
                return {"path": target_rel, "action": "unchanged", "note": ""}
        except Exception as exc:  # noqa: BLE001 -- unreadable target -> skip, warn
            return {
                "path": target_rel,
                "action": "skipped_modified",
                "note": f"existing file unreadable, NOT overwritten: {exc!r}",
            }
        return {
            "path": target_rel,
            "action": "skipped_modified",
            "note": "existing file differs from the template; NOT overwritten "
            "(remove or diff it yourself, then re-run)",
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return {"path": target_rel, "action": "installed", "note": ""}


def _recording_entry_commands(entry: Any) -> list[str]:
    if not isinstance(entry, dict):
        return []
    out: list[str] = []
    hooks = entry.get("hooks")
    if isinstance(hooks, list):
        for hook in hooks:
            if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                out.append(hook["command"])
    return out


def _recording_merge_hooks_file(
    repo: Path,
    target_rel: str,
    desired: dict[str, list[dict[str, Any]]],
    marker_filenames: tuple[str, ...],
) -> dict[str, Any]:
    """Merge desired hook entries into ONE {"hooks": {...}} JSON config file.

    Per event: an entry already carrying the EXACT desired command -> no-op; a
    DIFFERENT command that still references one of ``marker_filenames`` means
    the user wired/modified their own -> skip + warn (file untouched for that
    event); otherwise append the desired entry. Unknown keys and unrelated
    entries are preserved verbatim.
    """

    import json  # noqa: PLC0415

    target = repo / target_rel
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 -- bad JSON -> skip, never clobber
            return {
                "path": target_rel,
                "action": "skipped_modified",
                "note": f"existing file is not valid JSON, NOT touched: {exc!r}",
            }
        if not isinstance(data, dict):
            return {
                "path": target_rel,
                "action": "skipped_modified",
                "note": "existing file is not a JSON object, NOT touched",
            }
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return {
            "path": target_rel,
            "action": "skipped_modified",
            "note": "existing 'hooks' key is not an object, NOT touched",
        }

    changed = False
    warnings: list[str] = []
    for event, desired_entries in desired.items():
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            warnings.append(f"{event}: existing value is not a list, left as-is")
            continue
        existing_commands = [
            command
            for entry in existing
            for command in _recording_entry_commands(entry)
        ]
        for desired_entry in desired_entries:
            desired_commands = _recording_entry_commands(desired_entry)
            if all(command in existing_commands for command in desired_commands):
                continue  # already wired exactly -> idempotent no-op
            referencing = [
                command
                for command in existing_commands
                if any(marker in command for marker in marker_filenames)
            ]
            if referencing:
                warnings.append(
                    f"{event}: a different {marker_filenames} hook command is "
                    f"already wired ({referencing[0]!r}); NOT touched"
                )
                continue
            existing.append(desired_entry)
            changed = True

    if changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if warnings:
        return {
            "path": target_rel,
            "action": "skipped_modified" if not changed else "merged_with_warnings",
            "note": "; ".join(warnings),
        }
    return {
        "path": target_rel,
        "action": "merged" if changed else "unchanged",
        "note": "",
    }


def run_recording_setup(repo_root: Path | str | None = None) -> dict[str, Any]:
    """OPT-IN recording wiring for THIS checkout. NEVER raises.

    Copies the tracked machine-neutral hook templates into .claude/hooks/ +
    .codex/hooks/, merges the Pre/PostToolUse(Agent) entries into
    .claude/settings.local.json, writes/merges .codex/hooks.json (paths
    computed from the ACTUAL repo root), and returns a structured dict with
    per-file actions. Idempotent; a user-modified file is compared, skipped,
    and warned about -- never silently overwritten.
    """

    repo = _safe_repo_root(repo_root)
    actions: list[dict[str, Any]] = []
    try:
        for source_rel, target_rel in RECORDING_HOOK_TEMPLATES:
            actions.append(_recording_copy_template(repo, source_rel, target_rel))
        actions.append(
            _recording_merge_hooks_file(
                repo,
                ".claude/settings.local.json",
                _recording_claude_hook_entries(repo),
                ("open-recording.py", "close-recording.py"),
            )
        )
        actions.append(
            _recording_merge_hooks_file(
                repo,
                ".codex/hooks.json",
                _recording_codex_hook_entries(repo),
                ("codex-open-recording.py", "codex-close-recording.py"),
            )
        )
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        actions.append({"path": "", "action": "error", "note": repr(exc)})

    ok = all(action.get("action") != "error" for action in actions)
    skipped = [a for a in actions if a.get("action", "").startswith("skipped")]
    if ok and not skipped:
        message_ko = (
            "자동 기록 훅을 이 저장소에 연결했어요 ✅ "
            "(.claude/hooks + .codex/hooks, 경로는 이 컴퓨터 기준으로 계산)"
        )
    elif ok:
        message_ko = (
            "자동 기록 훅 연결을 끝냈지만, 이미 손대신 파일은 건드리지 않고 "
            "건너뛰었어요 (아래 안내를 확인해 주세요)."
        )
    else:
        message_ko = "자동 기록 훅 연결 중 문제가 있었어요 (아래 안내를 확인해 주세요)."
    return {
        "ok": ok,
        "repo_root": str(repo),
        "actions": actions,
        "codex_trust_instruction_ko": CODEX_TRUST_INSTRUCTION_KO,
        "message_ko": message_ko,
    }


def _render_recording_text(recording: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("R) 자동 기록(녹화) 훅 연결")
    lines.append(f"   {recording.get('message_ko', '')}")
    for action in recording.get("actions", []):
        note = action.get("note") or ""
        suffix = f" -- {note}" if note else ""
        lines.append(f"   - {action.get('path', '')}: {action.get('action', '')}{suffix}")
    lines.append(f"   {recording.get('codex_trust_instruction_ko', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# INSTALL WIZARD STEPS (INSTALL-WIZARD-0623)
#
# B2 plugin install (MCP register + skills place), B3 Slack provision. These are
# the steps `brick init` runs in order so a beginner gets ONE command that wires
# everything, idempotently, with friendly fallbacks (never a hard stop).
#
# These steps live in the OPERATOR layer (allowed to spawn subprocesses); the
# read-side connect.py / mcp_projection.py stay subprocess-free. Each step
# checks-then-acts (idempotent) and returns a friendly evidence packet -- never
# raises.
# ---------------------------------------------------------------------------


def _claude_cli_available() -> bool:
    import shutil  # noqa: PLC0415

    return shutil.which("claude") is not None


def run_mcp_register_step(repo_root: Path | str | None = None) -> dict[str, Any]:
    """B2a: REGISTER the brick-protocol MCP for the user's own interactive CLIs.

    For claude: runs the real ``claude mcp add`` (idempotent -- if the server is
    already registered, claude reports it and we record skipped). For codex: writes
    the ``[mcp_servers.brick-protocol]`` block connect.py renders into the user's
    ``~/.codex/config.toml`` (merge-aware: skip if a brick-protocol block already
    exists, never clobber a hand-edited file). NEVER raises.

    NOTE the split: this persists the MCP for the user's OWN interactive sessions.
    A DISPATCHED build CLI gets the MCP wired per-invocation by the adapter
    (A1, --mcp-config / -c overrides into the isolated room), independent of this
    persistence -- so a build agent sees the MCP even if the user skipped this step.
    """

    import subprocess  # noqa: PLC0415

    repo = _safe_repo_root(repo_root)
    actions: list[dict[str, Any]] = []

    # --- claude: real `claude mcp add` ---
    if _claude_cli_available():
        # M5: use connect's argv-LIST helper verbatim (single source). A
        # ``.split()`` of the one-liner would shred a repo path containing spaces,
        # so the actual registration must reuse the exact argv connect renders.
        argv = connect.render_claude_mcp_command_argv(repo)
        try:
            completed = subprocess.run(  # noqa: S603 -- fixed-shape connect argv
                argv,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            combined = f"{completed.stdout}\n{completed.stderr}".lower()
            if completed.returncode == 0:
                actions.append(
                    {"target": "claude", "action": "registered", "note": ""}
                )
            elif "already exists" in combined or "already configured" in combined:
                actions.append(
                    {"target": "claude", "action": "unchanged", "note": "already registered"}
                )
            else:
                actions.append(
                    {
                        "target": "claude",
                        "action": "error",
                        "note": (completed.stderr or completed.stdout or "").strip()[:200],
                    }
                )
        except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
            actions.append(
                {"target": "claude", "action": "error", "note": repr(exc)}
            )
    else:
        actions.append(
            {"target": "claude", "action": "skipped", "note": "claude CLI not installed"}
        )

    # --- codex: merge the rendered block into ~/.codex/config.toml ---
    actions.append(_codex_mcp_config_merge(repo))

    ok = all(action.get("action") != "error" for action in actions)
    message_ko = (
        "brick-protocol MCP 서버를 등록했어요 ✅ (codex/claude 내 세션에서 바로 보여요)"
        if ok
        else "MCP 등록 중 일부 문제가 있었어요 (아래 안내 확인)."
    )
    return {"ok": ok, "repo_root": str(repo), "actions": actions, "message_ko": message_ko}


def _codex_mcp_config_merge(repo: Path) -> dict[str, Any]:
    """Append connect.py's brick-protocol block to ~/.codex/config.toml (idempotent).

    Skip if a ``[mcp_servers.brick-protocol]`` block already exists (never clobber a
    user-edited config). Create the file 0600 if absent. NEVER raises."""

    block = connect.render_codex_mcp_config(repo)
    target = Path("~/.codex/config.toml").expanduser()
    marker = "[mcp_servers.brick-protocol]"
    try:
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if marker in existing:
                return {"target": "codex", "action": "unchanged", "note": "already in ~/.codex/config.toml"}
            sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
            target.write_text(existing + sep + block, encoding="utf-8")
            return {"target": "codex", "action": "merged", "note": "appended to ~/.codex/config.toml"}
        target.parent.mkdir(parents=True, exist_ok=True)
        import os  # noqa: PLC0415

        fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, block.encode("utf-8"))
        finally:
            os.close(fd)
        return {"target": "codex", "action": "installed", "note": "wrote ~/.codex/config.toml"}
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        return {"target": "codex", "action": "error", "note": repr(exc)}


def run_skills_place_step(repo_root: Path | str | None = None) -> dict[str, Any]:
    """B2b: PROJECT the Agent-axis skills into the user's ~/.claude/skills/ index.

    Customer deploy canonical is SKILLS_PLACE: render Agent Object skill
    resources into provider-native ``~/.claude/skills`` files. Any direct
    agent/skills -> live copy path is repo-internal development support, not the
    onboarding deploy path.

    Renders each admitted Agent Object's skills (via the read-only
    ``render_skill_md`` projection) into ``~/.claude/skills/<name>/SKILL.md`` so
    claude can NATIVELY trigger them on description (couples with the A2 manifest:
    the runtime packet ships the index, claude fetches the file). Idempotent
    (compare + skip), never clobbers a user-modified skill file, NEVER raises.
    """

    from brick_protocol.support.connection.agent_resources import (  # noqa: PLC0415
        AgentResourceError,
        list_agent_object_refs,
        resolve_agent_object,
    )
    from brick_protocol.support.connection.agent_resources import (  # noqa: PLC0415
        render_skill_md,
    )

    repo = _safe_repo_root(repo_root)
    skills_root = Path("~/.claude/skills").expanduser()
    actions: list[dict[str, Any]] = []
    seen_skill_refs: set[str] = set()
    try:
        for object_ref in list_agent_object_refs(repo):
            resolution = resolve_agent_object(object_ref, repo_root=repo)
            for skill in resolution.get("skill_resources", []):
                ref = str(skill.get("ref") or "")
                if ref in seen_skill_refs:
                    continue
                seen_skill_refs.add(ref)
                actions.append(_place_one_skill(repo, skills_root, skill, render_skill_md))
    except (AgentResourceError, OSError, ValueError) as exc:
        actions.append({"path": "", "action": "error", "note": repr(exc)})

    ok = all(action.get("action") != "error" for action in actions)
    # L1: _place_one_skill returns unchanged/skipped_modified/installed/error only --
    # there is no "updated" action, so it is not counted (dead vocab dropped).
    placed = sum(1 for a in actions if a.get("action") == "installed")
    message_ko = (
        f"브릭 스킬 {placed}개를 ~/.claude/skills/ 에 깔았어요 ✅ "
        "(claude가 설명을 보고 필요할 때 알아서 불러와요)"
        if ok
        else "스킬 설치 중 일부 문제가 있었어요 (아래 안내 확인)."
    )
    return {"ok": ok, "repo_root": str(repo), "skills_root": str(skills_root), "actions": actions, "message_ko": message_ko}


def _place_one_skill(
    repo: Path,
    skills_root: Path,
    skill: Mapping[str, Any],
    render_skill_md: Any,
) -> dict[str, Any]:
    """Render + place ONE skill (compare + skip + warn). Never raises."""

    ref = str(skill.get("ref") or "")
    # The directory name (the ref slug) is the canonical Agent-Skills name. Normalize
    # underscores to hyphens (the Agent-Skills standard render_skill_md enforces) so a
    # source SKILL.md whose front-matter name drifted to an underscore (e.g.
    # task_intake vs the task-intake dir) still projects cleanly instead of erroring.
    name = (ref.removeprefix("skill:") if ref.startswith("skill:") else ref).replace("_", "-")
    rel_path = str(skill.get("path") or "")
    try:
        body = str(skill.get("body") or "")
        # The projected SKILL.md needs a name + description front-matter. The source
        # SKILL.md already carries them; we use the hyphen-normalized DIR name (so it
        # matches the placed directory + the Agent-Skills standard) and the source
        # description, falling back to a generic description.
        front = _skill_front_matter_from_body(body)
        rendered = render_skill_md(
            name,
            front.get("description") or f"Brick Protocol skill {name}",
            _skill_body_without_front_matter(body),
        )
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        return {"path": f"~/.claude/skills/{name}/SKILL.md", "action": "error", "note": repr(exc)}

    target = skills_root / name / "SKILL.md"
    display = f"~/.claude/skills/{name}/SKILL.md"
    try:
        if target.exists():
            current = target.read_text(encoding="utf-8")
            if current == rendered:
                return {"path": display, "action": "unchanged", "note": "", "source": rel_path}
            return {
                "path": display,
                "action": "skipped_modified",
                "note": "existing skill file differs; NOT overwritten",
                "source": rel_path,
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        return {"path": display, "action": "installed", "note": "", "source": rel_path}
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        return {"path": display, "action": "error", "note": repr(exc)}


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


# B3 SLACK PROVISION: the report-delivery spine is COMPLETE (default policy fans
# out to local-inbox + slack + dashboard with allow_real=True; the auto-loader is
# wired at every report seam; pinned by check_report_env_autoload). The ONLY hole
# is that nothing CREATES/validates ~/.brick/report.env -- the loader silently
# no-ops on an absent file. This step provisions/validates that file (0600).
_SLACK_BOT_TOKEN_KEY = "BRICK_REPORT_SLACK_BOT_TOKEN"
_SLACK_CHANNEL_ID_KEY = "BRICK_REPORT_SLACK_CHANNEL_ID"
_DASHBOARD_INGEST_URL_KEY = "BRICK_DASHBOARD_INGEST_URL"
_DASHBOARD_SECRET_KEY = "BRICK_DASHBOARD_INGEST_SECRET"
_DASHBOARD_SA_KEY_PATH = "BRICK_DASHBOARD_SA_KEY_PATH"


def _report_env_path() -> Path:
    return sink_brick_home() / "report.env"


def _env_key_has_value(text: str, key: str) -> bool:
    """Shape check: a non-comment ``[export ]KEY=<non-empty>`` line exists for key.

    Presence/shape ONLY -- the value is never echoed, stored, or returned. A comment
    line (leading ``#``) and an empty RHS (``KEY=`` / ``KEY=   ``) are rejected so a
    placeholder never reports as configured. Whitespace/quotes are stripped before
    the emptiness test (``KEY=""`` is empty)."""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        body = line[len("export "):].strip() if line.startswith("export ") else line
        prefix = key + "="
        if not body.startswith(prefix):
            continue
        value = body[len(prefix):].strip().strip("\"'").strip()
        if value:
            return True
    return False


def _env_key_value(text: str, key: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        body = line[len("export "):].strip() if line.startswith("export ") else line
        prefix = key + "="
        if not body.startswith(prefix):
            continue
        return body[len(prefix):].strip().strip("\"'").strip()
    return ""


def _append_report_env_values(target: Path, values: Mapping[str, str]) -> None:
    import os  # noqa: PLC0415

    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"export {key}={value}\n" for key, value in values.items() if value)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(target), flags, 0o600)
    try:
        os.write(fd, body.encode("utf-8"))
    finally:
        os.close(fd)


def _default_slack_api_call(
    *,
    token: str,
    channel_id: str,
    text: str,
    timeout: float,
) -> dict[str, Any]:
    import json as json_mod  # noqa: PLC0415
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    payload = json_mod.dumps({"channel": channel_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status_code = int(getattr(response, "status", 0) or 0)
            body = response.read(65536).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status_code": int(exc.code), "error_kind": "HTTPError"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error_kind": type(exc).__name__}
    try:
        parsed = json_mod.loads(body) if body else {}
    except json_mod.JSONDecodeError:
        parsed = {}
    return {
        "ok": bool(parsed.get("ok")),
        "status_code": status_code,
        "slack_error": str(parsed.get("error") or "")[:80],
    }


def _default_dashboard_http_call(
    *,
    ingest_url: str,
    secret: str,
    timeout: float,
) -> dict[str, Any]:
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    request = urllib.request.Request(
        ingest_url,
        headers={
            "X-Brick-Dashboard-Secret": secret,
            "User-Agent": "brick-onboarding/1",
        },
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status_code = int(getattr(response, "status", 0) or 0)
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        return {
            "ok": 200 <= status_code < 500,
            "status_code": status_code,
            "error_kind": "HTTPError",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error_kind": type(exc).__name__}
    return {"ok": 200 <= status_code < 500, "status_code": status_code}


def run_slack_provision_step(
    *,
    slack_bot_token: str | None = None,
    slack_channel_id: str | None = None,
    slack_api_call: Any | None = None,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """B3: provision/validate ~/.brick/report.env (0600) with the two Slack keys.

    Friendly fallback: if no Slack credentials are supplied AND none already exist,
    this is a NON-FATAL advisory (local-inbox delivery still works) -- it never
    hard-stops the wizard. When credentials ARE supplied it writes them 0600; when
    the file already exists it VALIDATES (presence of both keys + 0600 perms) and
    never overwrites. Reads the values only from the explicit args (never echoes a
    secret value back). NEVER raises.
    """

    import stat as stat_mod  # noqa: PLC0415

    target = _report_env_path()
    result: dict[str, Any] = {
        "ok": True,
        "path": str(target),
        "action": "",
        "slack_configured": False,
        "slack_ready": False,
        "perms_ok": None,
        "message_ko": "",
    }
    try:
        token = (slack_bot_token or "").strip()
        channel = (slack_channel_id or "").strip()
        if target.exists():
            mode = stat_mod.S_IMODE(target.stat().st_mode)
            perms_ok = not (mode & (stat_mod.S_IRWXG | stat_mod.S_IRWXO))
            result["perms_ok"] = perms_ok
            text = target.read_text(encoding="utf-8")
            # M3: parse `export KEY=value` with a NON-EMPTY value (shape/presence
            # only -- never echo or store the value). A bare mention, a comment line,
            # or an empty value (e.g. `# BRICK_REPORT_SLACK_BOT_TOKEN=` or
            # `export BRICK_REPORT_SLACK_BOT_TOKEN=`) does NOT count as configured.
            has_token = _env_key_has_value(text, _SLACK_BOT_TOKEN_KEY)
            has_channel = _env_key_has_value(text, _SLACK_CHANNEL_ID_KEY)
            result["slack_configured"] = bool(has_token and has_channel)
            result["action"] = "validated"
            if not perms_ok:
                result["ok"] = False
                result["message_ko"] = (
                    f"report.env 권한이 느슨해요 → chmod 600 {target} 를 실행하세요 "
                    "(0600이어야 슬랙 토큰이 로드돼요)."
                )
            elif result["slack_configured"]:
                result["message_ko"] = "report.env 에 슬랙 키 2개가 이미 있어요 ✅ (그대로 둡니다)"
            else:
                result["message_ko"] = (
                    "report.env 는 있지만 슬랙 키 2개가 다 들어있진 않아요. "
                    "슬랙 알림을 켜려면 BRICK_REPORT_SLACK_BOT_TOKEN + "
                    "BRICK_REPORT_SLACK_CHANNEL_ID 를 채우세요 (없어도 로컬 기록은 작동)."
                )
                if token and channel:
                    values: dict[str, str] = {}
                    if not has_token:
                        values[_SLACK_BOT_TOKEN_KEY] = token
                    if not has_channel:
                        values[_SLACK_CHANNEL_ID_KEY] = channel
                    _append_report_env_values(target, values)
                    text = target.read_text(encoding="utf-8")
                    result["action"] = "installed"
                    result["slack_configured"] = True
                else:
                    record_sink_reachability(
                        SINK_REF_SLACK,
                        credentials_present=False,
                        reachability_status="not_configured",
                    )
                    return result
            if not token:
                token = _env_key_value(text, _SLACK_BOT_TOKEN_KEY)
            if not channel:
                channel = _env_key_value(text, _SLACK_CHANNEL_ID_KEY)
            check = (slack_api_call or _default_slack_api_call)(
                token=token,
                channel_id=channel,
                text="BRICK setup readiness check: Slack report sink is configured.",
                timeout=timeout_seconds,
            )
            ready = bool(check.get("ok"))
            result["slack_ready"] = ready
            result["reachability_status"] = "ready" if ready else "unreachable"
            record_sink_reachability(
                SINK_REF_SLACK,
                credentials_present=True,
                reachability_status=str(result["reachability_status"]),
                detail={
                    "status_code": check.get("status_code"),
                    "error_kind": check.get("error_kind") or check.get("slack_error"),
                },
            )
            if ready:
                result["message_ko"] = "슬랙 test message 확인까지 끝났어요 ✅"
            else:
                result["ok"] = False
                result["message_ko"] = "슬랙 test message 전송이 실패했어요. 토큰/채널을 확인하세요."
            return result

        if not token or not channel:
            # Friendly fallback: no file, no credentials -> advisory, NOT an error.
            result["action"] = "skipped"
            record_sink_reachability(
                SINK_REF_SLACK,
                credentials_present=False,
                reachability_status="not_configured",
            )
            result["message_ko"] = (
                "슬랙 알림은 아직 안 켰어요 (선택). 켜려면 ~/.brick/report.env (0600) 에 "
                "BRICK_REPORT_SLACK_BOT_TOKEN 과 BRICK_REPORT_SLACK_CHANNEL_ID 를 넣으세요. "
                "지금도 로컬 기록(local-inbox)은 그대로 작동해요."
            )
            return result

        _append_report_env_values(
            target,
            {
                _SLACK_BOT_TOKEN_KEY: token,
                _SLACK_CHANNEL_ID_KEY: channel,
            },
        )
        result["action"] = "installed"
        result["slack_configured"] = True
        result["perms_ok"] = True
        check = (slack_api_call or _default_slack_api_call)(
            token=token,
            channel_id=channel,
            text="BRICK setup readiness check: Slack report sink is configured.",
            timeout=timeout_seconds,
        )
        ready = bool(check.get("ok"))
        result["slack_ready"] = ready
        result["reachability_status"] = "ready" if ready else "unreachable"
        record_sink_reachability(
            SINK_REF_SLACK,
            credentials_present=True,
            reachability_status=str(result["reachability_status"]),
            detail={
                "status_code": check.get("status_code"),
                "error_kind": check.get("error_kind") or check.get("slack_error"),
            },
        )
        if ready:
            result["message_ko"] = "슬랙 키 저장 + test message 확인까지 끝났어요 ✅"
        else:
            result["ok"] = False
            result["message_ko"] = "슬랙 키는 저장했지만 test message 전송이 실패했어요."
        return result
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        result["ok"] = False
        result["action"] = "error"
        result["message_ko"] = "report.env 설정 중 문제가 생겼어요 (아래 안내 확인)."
        result["error_kind"] = type(exc).__name__
        result["error_message"] = str(exc)
        return result


def run_dashboard_provision_step(
    *,
    dashboard_ingest_url: str | None = None,
    dashboard_secret: str | None = None,
    dashboard_sa_key_path: str | None = None,
    dashboard_http_call: Any | None = None,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Provision/validate Dashboard sink env and cache a reachability check.

    No configured dashboard is a distinct non-fatal skip. Configured but
    unreachable is recorded as not-ready evidence.
    """

    import stat as stat_mod  # noqa: PLC0415

    target = _report_env_path()
    result: dict[str, Any] = {
        "ok": True,
        "path": str(target),
        "action": "",
        "dashboard_configured": False,
        "dashboard_ready": False,
        "perms_ok": None,
        "message_ko": "",
    }
    try:
        ingest_url = (dashboard_ingest_url or "").strip()
        secret = (dashboard_secret or "").strip()
        sa_key_path = (dashboard_sa_key_path or "").strip()
        if target.exists():
            mode = stat_mod.S_IMODE(target.stat().st_mode)
            perms_ok = not (mode & (stat_mod.S_IRWXG | stat_mod.S_IRWXO))
            result["perms_ok"] = perms_ok
            text = target.read_text(encoding="utf-8")
            if not ingest_url:
                ingest_url = _env_key_value(text, _DASHBOARD_INGEST_URL_KEY)
            if not secret:
                secret = _env_key_value(text, _DASHBOARD_SECRET_KEY)
            if not sa_key_path:
                sa_key_path = _env_key_value(text, _DASHBOARD_SA_KEY_PATH)
            if not perms_ok:
                result["ok"] = False
                result["action"] = "validated"
                result["message_ko"] = (
                    f"report.env 권한이 느슨해요 → chmod 600 {target} 를 실행하세요 "
                    "(0600이어야 대시보드 설정이 로드돼요)."
                )
                return result

        if not ingest_url or not secret:
            result["action"] = "skipped_not_configured"
            record_sink_reachability(
                SINK_REF_DASHBOARD,
                credentials_present=False,
                reachability_status="not_configured",
            )
            result["message_ko"] = (
                "대시보드 싱크는 아직 안 켰어요 (선택). 켜려면 ingest URL과 secret을 "
                "제공한 뒤 `brick sink add dashboard`를 다시 실행하세요."
            )
            return result

        values: dict[str, str] = {}
        existing_text = target.read_text(encoding="utf-8") if target.exists() else ""
        if not _env_key_has_value(existing_text, _DASHBOARD_INGEST_URL_KEY):
            values[_DASHBOARD_INGEST_URL_KEY] = ingest_url
        if not _env_key_has_value(existing_text, _DASHBOARD_SECRET_KEY):
            values[_DASHBOARD_SECRET_KEY] = secret
        if sa_key_path and not _env_key_has_value(existing_text, _DASHBOARD_SA_KEY_PATH):
            values[_DASHBOARD_SA_KEY_PATH] = sa_key_path
        if values:
            _append_report_env_values(target, values)
            result["action"] = "installed"
            result["perms_ok"] = True
        else:
            result["action"] = "validated"
            result["perms_ok"] = result["perms_ok"] if result["perms_ok"] is not None else True
        result["dashboard_configured"] = True
        check = (dashboard_http_call or _default_dashboard_http_call)(
            ingest_url=ingest_url,
            secret=secret,
            timeout=timeout_seconds,
        )
        ready = bool(check.get("ok"))
        result["dashboard_ready"] = ready
        result["reachability_status"] = "ready" if ready else "unreachable"
        record_sink_reachability(
            SINK_REF_DASHBOARD,
            credentials_present=True,
            reachability_status=str(result["reachability_status"]),
            detail={
                "status_code": check.get("status_code"),
                "error_kind": check.get("error_kind"),
            },
        )
        if ready:
            result["message_ko"] = "대시보드 설정 저장/검증 + reachability 확인까지 끝났어요 ✅"
        else:
            result["ok"] = False
            result["message_ko"] = "대시보드 설정은 저장했지만 reachability 확인이 실패했어요."
        return result
    except Exception as exc:  # noqa: BLE001 -- friendly field, never raise
        result["ok"] = False
        result["action"] = "error"
        result["message_ko"] = "대시보드 설정 중 문제가 생겼어요 (아래 안내 확인)."
        result["error_kind"] = type(exc).__name__
        result["error_message"] = str(exc)
        return result


def run_install_wizard(
    repo_root: Path | str | None = None,
    *,
    host: str = "codex",
    output_root: Path | str | None = None,
    allow_real_provider: bool = False,
    run_example: bool = True,
    wire_recording: bool = True,
    register_mcp: bool = True,
    place_skills: bool = True,
    slack_bot_token: str | None = None,
    slack_channel_id: str | None = None,
    command_runner: Any | None = None,
    provider_model_ref: str | None = None,
) -> dict[str, Any]:
    """The ONE ordered, idempotent, friendly-fallback install flow (`brick init`).

    Converges the two previously-disconnected install flows (the thin
    cli.py:_cmd_init and the richer run_onboard) into one ordered sequence:

      1 PRESENT  -> doctor (provider/gh readiness)
      2 PLUGIN   -> MCP register + skills place + recording hooks
      3 SLACK    -> provision/validate ~/.brick/report.env (0600)
      4+5 ONBOARD/EXAMPLE -> run_onboard (preflight + connect + example build)
      6 VERIFY   -> the caller (cli.py) runs check_profile --all ONCE at the end

    Each step degrades to a friendly advisory and continues; only a hard failure
    of the example build is fatal (preserving the prior cli.py contract). NEVER
    raises. The VERIFY step (6) is intentionally NOT run here -- the CADENCE is
    per-step compileall + check_profile --all ONCE, which the cli.py wrapper owns.
    """

    repo = _safe_repo_root(repo_root)
    steps: dict[str, Any] = {}

    # 1 PRESENT
    steps["present"] = run_doctor(command_runner=command_runner)

    # 2 REGISTER: LLM provider registration, if the requested host is ready.
    steps["provider_register"] = run_provider_register_step(
        host,
        model_ref=provider_model_ref,
        command_runner=command_runner,
    )

    # 3 PLUGIN: MCP register + skills place + recording hooks
    if register_mcp:
        steps["mcp_register"] = run_mcp_register_step(repo_root=repo)
    if place_skills:
        steps["skills_place"] = run_skills_place_step(repo_root=repo)
    if wire_recording:
        steps["recording"] = run_recording_setup(repo_root=repo)

    # 4 SLACK
    steps["slack"] = run_slack_provision_step(
        slack_bot_token=slack_bot_token,
        slack_channel_id=slack_channel_id,
    )

    # 5 SMOKE (preflight + connect + example build + handoff)
    steps["onboard"] = run_onboard(
        host,
        repo_root=repo,
        run_example=run_example,
        output_root=output_root,
        allow_real_provider=allow_real_provider,
        command_runner=command_runner,
    )

    # Honest aggregate: the example build is the only hard gate (mirrors the prior
    # cli.py contract); every other step is a friendly advisory that never blocks.
    #
    # M4 (FAIL-CLOSED): the hard gate requires example.ok to be EXPLICITLY True. A
    # missing/None ok (shape drift) is NOT silently treated as green -- it is
    # not_proven, so the gate stays closed (fatal_ok False). Likewise an advisory
    # step with a missing ok is recorded as not_proven rather than assumed ok.
    example = steps["onboard"].get("example_result", {}) if isinstance(steps["onboard"], dict) else {}
    fatal_ok = example.get("ok") is True
    advisory_steps = [
        (key, step) for key, step in steps.items()
        if key != "onboard" and isinstance(step, dict)
    ]
    # OBSERVED facts (support records what each step reported; it does not synthesize
    # a single boolean verdict). A step is observed-ok only when it EXPLICITLY says so.
    advisory_step_ok = {key: (step.get("ok") is True) for key, step in advisory_steps}
    not_proven: list[str] = []
    if example.get("ok") is None:
        not_proven.append("onboard.example_result.ok absent -> hard gate not_proven (fatal_ok closed)")
    for key, step in advisory_steps:
        if step.get("ok") is None:
            not_proven.append(f"steps.{key}.ok absent -> advisory step not_proven")
    # H5: ordered_steps carries the ACTUAL step keys (dict insertion order == run
    # order) so a consumer that walks ordered_steps to look up steps[key] always
    # resolves. The 6-phase human narrative (present/plugin/slack/onboard/verify)
    # lives in phase_narrative, separate from the real per-step keys.
    return {
        "kind": "install-wizard",
        "repo_root": str(repo),
        "ordered_steps": list(steps.keys()),
        "phase_narrative": ["present", "plugin", "slack", "onboard", "verify"],
        "steps": steps,
        "ok": fatal_ok,
        "advisory_step_ok": advisory_step_ok,
        "not_proven": not_proven,
        "verify_note": "step 6 (verify) runs check_profile --all ONCE in the cli wrapper",
    }


# ---------------------------------------------------------------------------
# ONBOARD DOCTOR (ONBOARD-POLISH 0611)
#
# ``onboard doctor`` exposes the EXISTING never-raising preflight as a one-shot
# diagnosis surface: it probes the gh login the install.sh clone path depends
# on, runs preflight_provider for every supported host, and prints a fixed
# symptom -> prescription table. Diagnosis ONLY: read-only, never raises, and
# the CLI ALWAYS exits 0 (a missing provider is a ❌ row + a one-line
# prescription, not a failure of the doctor itself). The provider
# prescriptions are the SAME strings agent_adapter's preflight hints already
# carry (npm install -g ... / codex login) -- copied, not invented.
# ---------------------------------------------------------------------------

# Fixed symptom -> prescription rows: the failures cold-start users actually
# hit on the documented paths (quickstart / install.sh / first Building run).
DOCTOR_SYMPTOM_PRESCRIPTIONS_KO: tuple[tuple[str, str], ...] = (
    (
        "ModuleNotFoundError: No module named 'brick_protocol' (또는 'yaml')",
        "저장소 루트에서 'uv run python3 ...' 형식으로 실행하세요. "
        "(uv 없이 쓰려면 'PYTHONPATH=support/import_identity python3 ...' "
        "+ 전역 PyYAML 필요)",
    ),
    (
        "FileExistsError: Building root already exists",
        "building_id 를 새로 정하거나, 같은 자리를 일부러 다시 쓰려면 "
        "overwrite_existing=True 를 명시적으로 넘기세요. (위자드 예제는 자동 처리)",
    ),
    (
        "local_cli_missing (codex CLI가 없음)",
        "npm install -g @openai/codex 후 codex login",
    ),
    (
        "local_cli_missing (claude CLI가 없음)",
        "npm install -g @anthropic-ai/claude-code",
    ),
    (
        "local_cli_missing (gemini CLI/API key가 없음)",
        "gemini CLI 설치 후 GEMINI_API_KEY 또는 GOOGLE_API_KEY 를 설정하세요",
    ),
)


def _doctor_python_row() -> dict[str, Any]:
    version = ".".join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info[:2] >= (3, 11)
    if ok:
        message = f"Python {version} 확인 ✅"
    else:
        message = f"Python {version} 은 너무 낮아요 → Python 3.11 이상 필요"
    return {
        "target": "python",
        "ok": ok,
        "version": version,
        "minimum_version": "3.11",
        "message_ko": message,
    }


def _doctor_command_row(command: str, *, target: str | None = None) -> dict[str, Any]:
    import shutil  # noqa: PLC0415

    observed_target = target or command
    resolved = shutil.which(command)
    if resolved:
        return {
            "target": observed_target,
            "ok": True,
            "path": resolved,
            "message_ko": f"{command} 확인 ✅",
        }
    return {
        "target": observed_target,
        "ok": False,
        "path": None,
        "message_ko": f"{command} 가 PATH에서 보이지 않아요 → 먼저 설치해 주세요",
    }


def _doctor_disk_row(*, path: Path | None = None) -> dict[str, Any]:
    import shutil  # noqa: PLC0415

    target_path = path or _REPO_ROOT
    minimum_free_bytes = 500 * 1024 * 1024
    try:
        usage = shutil.disk_usage(target_path)
        free_bytes = int(usage.free)
        ok = free_bytes >= minimum_free_bytes
        free_mb = free_bytes // (1024 * 1024)
        if ok:
            message = f"디스크 여유 공간 {free_mb}MB 확인 ✅"
        else:
            message = f"디스크 여유 공간이 {free_mb}MB 입니다 → 500MB 이상 권장"
        return {
            "target": "disk",
            "ok": ok,
            "path": str(target_path),
            "free_bytes": free_bytes,
            "minimum_free_bytes": minimum_free_bytes,
            "message_ko": message,
        }
    except Exception as exc:  # noqa: BLE001 -- doctor never raises
        return {
            "target": "disk",
            "ok": False,
            "path": str(target_path),
            "free_bytes": None,
            "minimum_free_bytes": minimum_free_bytes,
            "message_ko": f"디스크 여유 공간을 확인하지 못했어요 ({type(exc).__name__}).",
        }


def _doctor_github_network_row() -> dict[str, Any]:
    import socket  # noqa: PLC0415

    host = "github.com"
    try:
        with socket.create_connection((host, 443), timeout=3):
            pass
        return {
            "target": host,
            "ok": True,
            "port": 443,
            "message_ko": "github.com 네트워크 연결 확인 ✅",
        }
    except Exception as exc:  # noqa: BLE001 -- doctor never raises
        return {
            "target": host,
            "ok": False,
            "port": 443,
            "message_ko": (
                "github.com 에 연결하지 못했어요 → 네트워크/VPN/프록시를 확인해 주세요 "
                f"({type(exc).__name__})"
            ),
        }


def run_doctor(*, command_runner: Any | None = None) -> dict[str, Any]:
    """Run environment checks and provider preflights. NEVER raises.

    Returns {rows, symptom_table, all_ok}. ``all_ok`` summarizes the rows, but
    the CLI entry ALWAYS exits 0: doctor is a diagnosis record, not a gate. It
    proves no provider availability, judges no success/quality, and chooses no
    Movement.
    """

    rows: list[dict[str, Any]] = []
    try:
        rows.append(_doctor_python_row())
        rows.append(_doctor_command_row("pipx"))
        rows.append(_doctor_command_row("git"))
        rows.append(_doctor_command_row("uv"))
        rows.append(_doctor_disk_row())
        rows.append(_doctor_github_network_row())
        for host in SUPPORTED_HOSTS:
            status = _preflight_step(host, command_runner=command_runner)
            row = {
                "target": host,
                "ok": bool(status.get("ok")),
                "message_ko": str(status.get("message_ko") or ""),
            }
            for evidence_key in (
                "adapter_ref",
                "authed",
                "api_key_env_present",
                "credential_validity",
            ):
                if evidence_key in status:
                    row[evidence_key] = status[evidence_key]
            rows.append(row)
    except Exception as exc:  # noqa: BLE001 -- friendly row, never raise
        rows.append(
            {
                "target": "doctor",
                "ok": False,
                "message_ko": f"진단 중에 문제가 생겼어요 ({type(exc).__name__}).",
            }
        )
    return {
        "rows": rows,
        "symptom_table": list(DOCTOR_SYMPTOM_PRESCRIPTIONS_KO),
        "all_ok": all(bool(row.get("ok")) for row in rows),
    }


def _render_doctor_text(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=== Brick Protocol 진단 (onboard doctor) ===\n")
    lines.append("1) 준비 상태")
    for row in result.get("rows", []):
        mark = "✅" if row.get("ok") else "❌"
        lines.append(f"   {mark} {row.get('target', '')}: {row.get('message_ko', '')}")
    lines.append("")
    lines.append("2) 증상 → 처방")
    for symptom, prescription in result.get("symptom_table", []):
        lines.append(f"   - {symptom}")
        lines.append(f"     → {prescription}")
    lines.append("")
    lines.append(
        "진단은 기록일 뿐이에요: 아무것도 바꾸지 않고, 항상 exit 0 입니다. "
        "(❌ 줄이 있으면 그 옆의 처방 한 줄만 따라 하면 돼요.)"
    )
    return "\n".join(lines)


def _handoff_message_ko(host: str) -> str:
    """Step 4: plain-Korean closing handoff that NAMES the Phase-1 seam verb."""

    return (
        "이제 에이전트한테 말 거세요:\n"
        "  · \"브릭이 뭐야?\"  (개념이 궁금할 때)\n"
        "  · \"___ 만들어줘\"  (빈칸에 만들고 싶은 걸 적으세요)\n"
        "task 파일은 따로 만들 필요 없어요 — 할 일을 그냥 글로 전하세요.\n"
        "(인테이크에 task_statement 로 텍스트를 넘기면, 기계가 그 글을 빌딩\n"
        " 증거 work/task.md 로 기록해요. 파일 기반 task_source_ref 는 자동화\n"
        " 경로로 그대로 남아 있어요.)\n"
        "\n"
        "더 들여다보고 싶으면, 말로 전한 task로 빌딩을 시작하는 다음 단계\n"
        "입구(seam)는\n"
        f"  {SEAM_VERB}\n"
        "(task_statement 텍스트(또는 task 파일) + 고른 preset → 실행 중인 빌딩)\n"
        "이에요. 막히면 그냥 한국어로 물어보면 돼요. 천천히 하셔도 괜찮아요 🙂"
    )


def run_onboard(
    host: str,
    repo_root: Path | str | None = None,
    *,
    run_example: bool = True,
    output_root: Path | str | None = None,
    allow_real_provider: bool = False,
    command_runner: Any | None = None,
) -> dict[str, Any]:
    """Run the friendly, NEVER-raising onboarding flow.

    Returns a structured dict:
        {host, preflight, preflight_readiness, connect_hint, example_result,
         handoff_message_ko, ok}

    Each step is wrapped so a failure becomes a friendly field, never a raised
    traceback. The example step routes the first Building through the PART-1 seam
    ``support.operator.driver.run_building_intake`` (recorded as
    ``example_result["routed_through"]``).

    ``preflight_readiness`` records the observed provider readiness
    (ready / unauthed / missing / unknown) as an auditable field, not just the
    Korean preflight message. That readiness drives the example adapter:

    - By default (``allow_real_provider=False``) the example runs on the
      in-process read-only ``adapter:local`` with an all-read-only preset --
      friendly even when the provider is missing / unauthed, never touching the
      repo.
    - With ``allow_real_provider=True`` AND a recorded ``ready`` observed-write
      provider (codex/claude/gemini local), the SAME seam runs
      the example on that adapter (a real-provider Building). When the provider
      is NOT ready it FALLS BACK to ``adapter:local``
      (still friendly, never raises). The adapter used + WHY are recorded on the
      example_result.

    ``ok`` is True only when both the preflight and (when requested) the example
    step report ok. (A bogus / missing-provider host makes ``ok`` False even
    though the friendly adapter:local fallback example still runs without
    raising.) The connect step never blocks ``ok``.
    """

    normalized_host = _normalize_host(host)
    root = _safe_repo_root(repo_root)

    preflight = _preflight_step(normalized_host, command_runner=command_runner)
    readiness = _preflight_readiness(preflight)
    connect_hint = _connect_step(normalized_host, root)

    if run_example:
        example_result = _example_step(
            repo_root=root,
            output_root=output_root,
            preflight=preflight,
            readiness=readiness,
            allow_real_provider=allow_real_provider,
            command_runner=command_runner,
        )
    else:
        example_result = {
            "ok": True,
            "ran": False,
            "message_ko": "예제 실행은 건너뛰었어요.",
        }

    ok = (
        bool(preflight.get("ok"))
        and bool(example_result.get("ok"))
    )

    return {
        "host": normalized_host,
        "preflight": preflight,
        "preflight_readiness": readiness,
        "connect_hint": connect_hint,
        "example_result": example_result,
        "handoff_message_ko": _handoff_message_ko(normalized_host),
        "ok": ok,
    }


def _render_flow_text(result: dict[str, Any]) -> str:
    """Render the onboarding flow as plain-Korean text for the CLI entry."""

    lines: list[str] = []
    host = result.get("host") or "(없음)"
    lines.append(f"=== Brick Protocol 시작하기 (host: {host}) ===\n")

    preflight = result.get("preflight") or {}
    lines.append("1) provider 준비 상태")
    lines.append(f"   {preflight.get('message_ko', '(상태 없음)')}")
    lines.append(f"   - 준비도(기록): {result.get('preflight_readiness', 'unknown')}\n")

    connect_hint = result.get("connect_hint") or {}
    lines.append("2) 연결 설정")
    lines.append(f"   {connect_hint.get('message_ko', '(안내 없음)')}")
    config_text = connect_hint.get("config_text") or ""
    if config_text.strip():
        lines.append("")
        lines.append(config_text.rstrip("\n"))
    lines.append("")

    example_result = result.get("example_result") or {}
    lines.append("3) 첫 예제 빌딩")
    lines.append(f"   {example_result.get('message_ko', '(결과 없음)')}")
    if example_result.get("error_message"):
        lines.append(
            f"   - 에러 내용: {example_result.get('error_kind', '')}: "
            f"{example_result.get('error_message', '')}"
        )
    routed = example_result.get("routed_through")
    if routed:
        lines.append(f"   - 통과 경로(seam): {routed}")
        lines.append(f"   - 사용한 adapter: {example_result.get('adapter_ref', '')}")
        lines.append(f"   - 선택 근거: {example_result.get('adapter_choice_basis', '')}")
    if example_result.get("ran"):
        lines.append(f"   - building_id: {example_result.get('building_id', '')}")
        lines.append(f"   - frontier: {example_result.get('frontier_kind', '')}")
        lines.append(f"   - 결과 저장 위치: {example_result.get('evidence_root', '')}")
    lines.append("")

    lines.append("4) 다음 단계")
    lines.append(result.get("handoff_message_ko", ""))
    lines.append("")

    lines.append(f"준비 완료: {'예 ✅' if result.get('ok') else '아직이요 (위 안내를 따라 주세요)'}")
    return "\n".join(lines)


GOAL_APPROVE_SEAM_VERB = "support.operator.onboard.run_goal_approve_entry"
GOAL_APPROVE_ACTIONS = ("forward", "stop")
_GOAL_PROPOSAL_FILENAME = "proposed-building-graph.json"
_BUILD_SELECTED_ADAPTER = "codex-local"


_RESULT_SUMMARY_PROOF_LIMITS = [
    "support evidence only",
    "static evidence files only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
]

_RESULT_SUMMARY_FORBIDDEN_KEYS = {
    "ok",
    "success",
    "complete",
    "quality",
    "verdict",
    "status",
    "pass",
    "fail",
}

_RESULT_SUMMARY_CARRIED_CLOSURE_KEYS = frozenset(
    {
        "deliverable_crosscheck",
        "transition_concern_evidence",
    }
)


def summarize_building_result(
    evidence_root: str | Path,
    *,
    repo_root: Path | str = _REPO_ROOT,
) -> dict[str, Any]:
    """Gather a no-raise support summary from one Building evidence root.

    This is a read-side support projection over already-written evidence. It
    records facts only and never chooses Movement or judges success/quality.
    """

    try:
        repo = _safe_repo_root(repo_root)
        root = _repo_path(repo, evidence_root)
        frontier = dict(observe_building_frontier(root, repo_root=repo))
        summary: dict[str, Any] = {
            "kind": "building_result_summary",
            "schema_version": "building-result-summary-0",
            "building_root": _rel(repo, root),
            "frontier_kind": _text_or_none(frontier.get("frontier_kind")),
            "frontier_reason": _text_or_none(frontier.get("frontier_reason")),
            "step_attempts": _summary_step_attempts(root),
            "closure": _summary_latest_closure(root),
            "link_paused_rows": _summary_link_paused_rows(root),
            "adapter_error_rows": _summary_adapter_error_rows(root),
            "dispatch_timing_ms_total": _summary_dispatch_timing_ms_total(root),
            "commit_sha_present": None,
            "wip_anchor_present": _result_summary_wip_anchor_present(repo, root.name),
            "proof_limits": list(_RESULT_SUMMARY_PROOF_LIMITS),
            "not_proven": [
                "commit SHA presence from evidence_root alone",
                "semantic correctness of recorded Agent returns",
                "whether caller/COO should resume, reroute, or close",
            ],
        }
        return _strip_result_summary_forbidden_keys(summary)
    except Exception as exc:  # noqa: BLE001 -- no-raise support projection
        return {
            "kind": "building_result_summary",
            "schema_version": "building-result-summary-0",
            "building_root": None,
            "frontier_kind": None,
            "frontier_reason": None,
            "step_attempts": None,
            "closure": None,
            "link_paused_rows": None,
            "adapter_error_rows": None,
            "dispatch_timing_ms_total": None,
            "commit_sha_present": None,
            "wip_anchor_present": None,
            "proof_limits": list(_RESULT_SUMMARY_PROOF_LIMITS),
            "not_proven": [
                f"summary read raised {type(exc).__name__}",
                "semantic correctness of recorded Agent returns",
                "whether caller/COO should resume, reroute, or close",
            ],
        }


def _text_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _summary_step_output_packets(root: Path) -> tuple[Mapping[str, Any], ...] | None:
    step_outputs_dir = root / "work" / "step-outputs"
    if not step_outputs_dir.is_dir():
        return None
    packets: list[Mapping[str, Any]] = []
    for path in sorted(step_outputs_dir.glob("*/step-output.json")):
        packet = _read_json_mapping(path)
        if packet:
            packets.append(packet)
    return tuple(packets)


def _summary_step_attempts(root: Path) -> list[dict[str, Any]] | None:
    packets = _summary_step_output_packets(root)
    if packets is None:
        return None
    attempts_by_step: dict[str, int] = {}
    for packet in packets:
        step_ref = packet.get("step_ref")
        if not isinstance(step_ref, str) or not step_ref.strip():
            continue
        attempt = packet.get("attempt_index")
        if isinstance(attempt, int) and attempt > 0:
            attempts_by_step[step_ref] = max(attempts_by_step.get(step_ref, 0), attempt)
        else:
            attempts_by_step[step_ref] = max(attempts_by_step.get(step_ref, 0), 1)
    return [
        {"step_ref": step_ref, "attempt_count": attempt_count}
        for step_ref, attempt_count in sorted(attempts_by_step.items())
    ]


def _summary_latest_closure(root: Path) -> dict[str, Any] | None:
    packets = _summary_step_output_packets(root)
    if packets is None:
        return None
    closure_packets = [packet for packet in packets if _summary_is_closure_packet(packet)]
    if not closure_packets:
        return None
    packet = max(
        closure_packets,
        key=lambda item: item.get("attempt_index") if isinstance(item.get("attempt_index"), int) else 0,
    )
    returned = packet.get("returned")
    if not isinstance(returned, Mapping):
        returned = {}
    return {
        "deliverable_crosscheck": (
            returned.get("deliverable_crosscheck")
            if "deliverable_crosscheck" in returned
            else None
        ),
        "transition_concern_evidence": (
            returned.get("transition_concern_evidence")
            if isinstance(returned.get("transition_concern_evidence"), Mapping)
            else None
        ),
    }


def _summary_is_closure_packet(packet: Mapping[str, Any]) -> bool:
    step_ref = str(packet.get("step_ref") or "")
    step_template_ref = str(packet.get("step_template_ref") or "")
    brick_row = packet.get("brick_row")
    if isinstance(brick_row, Mapping):
        step_template_ref = step_template_ref or str(brick_row.get("step_template_ref") or "")
    return step_ref.endswith("-closure") or step_template_ref.endswith(":closure")


def _summary_link_paused_rows(root: Path) -> list[dict[str, Any]] | None:
    path = root / "raw" / "link.jsonl"
    if not path.is_file():
        return None
    rows: list[dict[str, Any]] = []
    for record in _jsonl_records(path):
        if record.get("transition_lifecycle_state") != "paused":
            continue
        reason_refs = record.get("transition_lifecycle_reason_refs")
        rows.append(
            {
                "step_ref": _summary_text(record.get("step_ref")),
                "pending_target_ref": _summary_text(
                    record.get("transition_lifecycle_pending_target_ref")
                ),
                "reason_refs": [
                    str(item)
                    for item in reason_refs
                    if isinstance(item, str)
                ]
                if isinstance(reason_refs, Sequence) and not isinstance(reason_refs, (str, bytes))
                else [],
                "required_disposition_owner": _summary_text(
                    record.get("transition_lifecycle_required_disposition_owner")
                ),
            }
        )
    return rows


def _summary_adapter_error_rows(root: Path) -> list[dict[str, Any]] | None:
    path = root / "raw" / "adapter-error.jsonl"
    if not path.is_file():
        return None
    return [
        {
            "step_ref": _summary_text(record.get("step_ref")),
            "error_kind": _summary_text(record.get("error_kind")),
            "exception_type": _summary_text(record.get("exception_type")),
            "message_excerpt": _summary_text(record.get("message_excerpt")),
        }
        for record in _jsonl_records(path)
    ]


def _summary_dispatch_timing_ms_total(root: Path) -> float | None:
    path = root / "raw" / "adapter-usage.jsonl"
    if not path.is_file():
        return None
    total = 0.0
    observed = False
    for record in _jsonl_records(path):
        if record.get("support_record_role") != "adapter-dispatch-timing":
            continue
        timing = record.get("adapter_dispatch_timing")
        duration = timing.get("duration_ms") if isinstance(timing, Mapping) else None
        if isinstance(duration, (int, float)):
            total += float(duration)
            observed = True
    return round(total, 3) if observed else None


def _summary_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _strip_result_summary_forbidden_keys(value: Any, *, key: str | None = None) -> Any:
    if key in _RESULT_SUMMARY_CARRIED_CLOSURE_KEYS:
        return value
    if isinstance(value, dict):
        stripped: dict[str, Any] = {}
        for raw_key, child in value.items():
            if raw_key in _RESULT_SUMMARY_FORBIDDEN_KEYS:
                continue
            stripped[raw_key] = _strip_result_summary_forbidden_keys(child, key=raw_key)
        return stripped
    if isinstance(value, list):
        return [_strip_result_summary_forbidden_keys(item) for item in value]
    return value


def _result_summary_wip_anchor_present(
    repo_root: Path | str | None,
    building_id: Any,
) -> bool | None:
    if repo_root is None:
        return None
    if not isinstance(building_id, str) or not building_id.strip():
        return False
    return reclaim_wip_anchor(repo_root, building_id) is not None


def _result_summary_with_sandbox_anchors(
    evidence_root: str | Path,
    *,
    repo_root: Path | str,
    building_id: Any,
    commit_sha: Any,
) -> dict[str, Any]:
    summary = summarize_building_result(evidence_root, repo_root=repo_root)
    summary["commit_sha_present"] = bool(commit_sha)
    summary["wip_anchor_present"] = _result_summary_wip_anchor_present(
        repo_root,
        building_id,
    )
    return _strip_result_summary_forbidden_keys(summary)


def render_proposal_for_human(proposal_ref: Any) -> str:
    """Render a frozen proposal snapshot as a plain-Korean pre-run preview.

    This is read-side support projection only. It reads a caller/COO-declared
    composed plan and names what will run; it does not approve, choose Movement,
    or judge quality.
    """

    plan, _proposal_path = _load_goal_proposal(proposal_ref)
    return _render_goal_proposal_plan(plan)


def build(
    graph: Any,
    *,
    goal: str,
    declared_by: str,
    author_ref: str,
    action: str = "forward",
    output_root: Path | str | None = None,
    write_scope: Mapping[str, Any] | None = None,
    expansion_budget: Any | None = None,
    expansion_node_budgets: Mapping[str, Any] | None = None,
    gates: Sequence[Any] = (),
    command_runner: Any | None = None,
    local_callables: Mapping[str, Any] | None = None,
    adapter_timeout_seconds: int = 120,
) -> dict[str, Any]:
    """One-call goal build: compose, freeze, render, then route approval.

    This is a support convenience wrapper over the existing seams. It keeps the
    pre-run proposal and approval result visible, but hides repo/output/worktree
    plumbing and never bypasses the human/COO ``forward`` / ``stop`` gate.
    """

    from brick_protocol.support.operator.assembly import (  # noqa: PLC0415
        assemble,
        persist_proposed_building_graph,
    )

    composed = assemble(
        graph,
        declared_by=declared_by,
        task=goal,
        repo_root=_REPO_ROOT,
        adapter=_BUILD_SELECTED_ADAPTER,
        gates=gates,
        write_scope=write_scope,
        expansion_budget=expansion_budget,
        expansion_node_budgets=expansion_node_budgets,
    )
    run_output_root = _build_output_root(composed.building_id, output_root)
    proposal_path = persist_proposed_building_graph(
        composed,
        _build_proposal_root(run_output_root),
    )
    rendered = render_proposal_for_human(proposal_path)
    approval = run_goal_approve_entry(
        proposal_path,
        action=action,
        author_ref=author_ref,
        output_root=run_output_root,
        repo_root=_REPO_ROOT,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_timeout_seconds=adapter_timeout_seconds,
    )
    return {
        "building_id": composed.building_id,
        "proposal_ref": str(proposal_path),
        "proposal_render": rendered,
        "approval_result": approval,
    }


def run_goal_approve_entry(
    proposal_ref: Any,
    *,
    action: str = "forward",
    author_ref: str = "coo:smith",
    output_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, Any] | None = None,
    command_runner: Any | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Any | None = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> dict[str, Any]:
    """Approve or stop a frozen pre-run proposal.

    ``forward`` walks the already-persisted composed plan through
    ``run_building_plan`` inside the existing worktree-sandbox bracket.
    ``stop`` records no Building root and runs nothing.
    """

    from brick_protocol.support.operator.driver import (  # noqa: PLC0415
        BuildingIntakeRunResult,
        _run_in_worktree_sandbox,
    )
    from brick_protocol.support.operator.run import run_building_plan  # noqa: PLC0415

    action_text = str(action).strip().lower()
    author_text = str(author_ref).strip()
    result: dict[str, Any] = {
        "ok": False,
        "ran": False,
        "action": action_text,
        "author_ref": author_text,
        "routed_through": GOAL_APPROVE_SEAM_VERB,
    }
    if action_text not in GOAL_APPROVE_ACTIONS:
        result.update(
            {
                "error_kind": "invalid_goal_approve_action",
                "error_message": "pre-run approval action must be forward or stop.",
                "message_ko": "굴리기 전 승인은 forward 또는 stop만 가능해요.",
            }
        )
        return result
    if not (author_text.startswith("coo:") or author_text.startswith("human:")):
        result.update(
            {
                "error_kind": "invalid_author_ref",
                "error_message": "author_ref must start with coo: or human:.",
                "message_ko": "작성자 ref는 coo: 또는 human: 으로 시작해야 해요.",
            }
        )
        return result

    try:
        plan, proposal_path = _load_goal_proposal(proposal_ref)
        _validate_frozen_goal_plan(plan)
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "proposal snapshot을 읽거나 검증할 수 없어요.",
            }
        )
        return result

    building_id = _required_plan_text(plan, "building_id")
    result["building_id"] = building_id
    if proposal_path is not None:
        result["proposal_ref"] = str(proposal_path)

    if action_text == "stop":
        result.update(
            {
                "ok": True,
                "ran": False,
                "message_ko": "stop 처분이라 frozen plan을 실행하지 않았어요.",
            }
        )
        return result

    repo = _safe_repo_root(repo_root)
    durable_output = _goal_approval_output_root(output_root, proposal_path)
    run_plan_path = _goal_approval_plan_path(
        plan,
        proposal_path=proposal_path,
        durable_output=durable_output,
    )
    run_overwrite_existing = overwrite_existing or _proposal_root_is_prerun_only(
        proposal_path,
        durable_output=durable_output,
        building_id=building_id,
    )

    def _run_frozen_plan(repo_root_inner: Path, adapter_cwd: Path) -> BuildingIntakeRunResult:
        del repo_root_inner
        run_result = run_building_plan(
            run_plan_path,
            output_root=durable_output,
            overwrite_existing=run_overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            proof_limits=proof_limits,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
        )
        return BuildingIntakeRunResult(
            building_id=building_id,
            plan_path=run_plan_path,
            plan_shape=str(plan.get("plan_shape") or ""),
            walker_mode="dynamic",
            walker_mode_basis=(
                "pre-run human/COO approval ran a frozen composed plan through "
                "run_building_plan; no compose_building call"
            ),
            run_result=run_result,
            task_source_basis="task_statement",
        )

    try:
        sandbox_result = _run_in_worktree_sandbox(
            repo,
            building_id=building_id,
            durable_output=durable_output,
            run_dispatch=_run_frozen_plan,
        )
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "frozen plan 실행 중 문제가 생겼어요.",
            }
        )
        return result

    result.update(
        {
            "ok": sandbox_result.frontier_kind == "complete",
            "ran": True,
            "plan_path": str(run_plan_path),
            "evidence_root": sandbox_result.evidence_root,
            "frontier_kind": sandbox_result.frontier_kind,
            "frontier_reason": sandbox_result.frontier_reason,
            "isolation_mode": sandbox_result.isolation_mode,
            "isolation_reason": sandbox_result.isolation_reason,
            "commit_sha": sandbox_result.commit_sha,
            "wip_anchor_ref": sandbox_result.wip_anchor_ref,
            "wip_commit_sha": sandbox_result.wip_commit_sha,
            "worktree_path": sandbox_result.worktree_path,
            "worktree_disposed": sandbox_result.worktree_disposed,
            "result_summary": _result_summary_with_sandbox_anchors(
                sandbox_result.evidence_root,
                repo_root=repo,
                building_id=sandbox_result.building_id,
                commit_sha=sandbox_result.commit_sha,
            ),
            "proposal_root_reused": run_overwrite_existing and not overwrite_existing,
        }
    )
    return result


LAUNCH_ASSEMBLED_SEAM_VERB = "support.operator.onboard.launch_assembled_building"


def launch_assembled_building(
    composed: Any,
    *,
    project_ref: str | None = None,
    declared_by: str = "coo:smith",
    repo_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, Any] | None = None,
    command_runner: Any | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Any | None = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> dict[str, Any]:
    """Internal/non-customer helper for an already-``assemble()``-d graph.

    This helper is not the P3 customer Easy Building route. Customer-facing graph
    work enters through ``brick build --graph`` / ``support.operator.cli build
    --graph`` and then ``driver.run_customer_graph_building_in_sandbox``. This
    internal helper remains historical/support plumbing for already-composed
    objects and must not be presented as a separate official route.

    This is the assemble-path twin of ``run_goal_approve_entry``'s ``forward``
    branch. ``build`` (the goal path) and that approval entry always interpose a
    human/COO ``forward`` / ``stop`` decision; this verb is for the autonomous
    operator who has ALREADY judged the graph shape (via ``assemble()``) and wants
    to run it. It hides the four launch sharp-edges so the operator only ever
    declares the graph:

    1. COMPOSED-OBJECT vs DICT. ``run_building_plan`` reads its plan through
       ``_fixture_mapping`` (Mapping | str | Path); a ``ComposedGraph`` is none of
       those and ``Path(composed)`` raises an opaque ``TypeError``. This verb never
       hands the object across — it persists ``composed.composed_plan`` to a JSON
       file FIRST (the same on-disk plan the goal path writes) and runs that path.
    2. OUTPUT_ROOT MUST BE A VESSEL. A free-form root makes
       ``project_ref_for_building_root`` return ``None`` and the report sinks fall
       silent. This verb accepts a VESSEL ``project_ref`` and derives the durable
       root through the ONE seam ``buildings_root_for`` (never a hand-joined path);
       an omitted ``project_ref`` uses ``DEFAULT_BUILDINGS_ROOT`` (itself the
       project #1 vessel root), so the derived root is ALWAYS a vessel.
    3. WORKTREE OWNERSHIP. ``run_building_plan`` writes ``adapter_cwd`` directly;
       on a real adapter that is the live tree. This verb runs inside the existing
       ``_run_in_worktree_sandbox`` bracket (probe / create-at-base / commit-on-
       complete / dispose), so the live tree is never mutated and one worktree is
       created per launch (NO fan-out).
    4. NAME COLLISION. ``assembly.build([...])`` (the graph-list builder) and the
       goal-path ``build(graph, goal=...)`` share a bare verb. This verb has a
       distinct name and a distinct contract (it takes the COMPOSED graph, not a
       node list and not a goal string), so the operator never confuses the two.

    It is pure support mechanics: it authors no Movement, chooses no agent outside
    the kind→lane bind the graph already declares, and judges no success / quality
    (``ok`` reflects only the observed worktree frontier, support evidence only).
    """

    from brick_protocol.support.operator.assembly import (  # noqa: PLC0415
        ComposedGraph,
        persist_proposed_building_graph,
    )
    from brick_protocol.support.operator.driver import (  # noqa: PLC0415
        BuildingIntakeRunResult,
        _run_in_worktree_sandbox,
    )
    from brick_protocol.support.operator.run import run_building_plan  # noqa: PLC0415
    from brick_protocol.support.recording.capture import (  # noqa: PLC0415
        DEFAULT_BUILDINGS_ROOT,
        buildings_root_for,
    )

    result: dict[str, Any] = {
        "ok": False,
        "ran": False,
        "declared_by": str(declared_by).strip(),
        "routed_through": LAUNCH_ASSEMBLED_SEAM_VERB,
    }

    if not isinstance(composed, ComposedGraph):
        result.update(
            {
                "error_kind": "invalid_composed_graph",
                "error_message": (
                    "launch_assembled_building() requires the ComposedGraph returned "
                    "by assemble(); got " + type(composed).__name__
                ),
                "message_ko": "assemble()가 돌려준 ComposedGraph를 그대로 넘겨주세요.",
            }
        )
        return result

    building_id = composed.building_id
    result["building_id"] = building_id

    # MINE #2 cut: the durable root is ALWAYS a vessel. A declared project_ref is
    # derived through the ONE seam; an omitted one falls back to the project #1
    # vessel root (DEFAULT_BUILDINGS_ROOT), which is itself a vessel.
    try:
        if project_ref is not None:
            durable_output = buildings_root_for(project_ref)
        else:
            durable_output = Path(DEFAULT_BUILDINGS_ROOT)
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "project_ref(그릇)에서 buildings 루트를 만들 수 없어요.",
            }
        )
        return result
    result["durable_output"] = str(durable_output)

    repo = _safe_repo_root(repo_root)
    adapter_cwd_refusal = _unsafe_live_repo_adapter_cwd(adapter_cwd, repo_root=repo)
    if adapter_cwd_refusal is not None:
        result.update(adapter_cwd_refusal)
        return result

    # MINE #1 cut: persist the composed plan to a path FIRST, so the object never
    # reaches run_building_plan's _fixture_mapping (which would Path() it and raise).
    try:
        durable_output.mkdir(parents=True, exist_ok=True)
        run_plan_path = durable_output / _composition_run_plan_filename(building_id)
        run_plan_path.write_text(
            json.dumps(composed.composed_plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "composed plan을 디스크에 기록할 수 없어요.",
            }
        )
        return result
    result["plan_path"] = str(run_plan_path)

    def _run_composed_plan(
        repo_root_inner: Path, sandbox_cwd: Path
    ) -> BuildingIntakeRunResult:
        del repo_root_inner
        run_result = run_building_plan(
            run_plan_path,
            output_root=durable_output,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd if adapter_cwd is not None else sandbox_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            proof_limits=proof_limits,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
        )
        return BuildingIntakeRunResult(
            building_id=building_id,
            plan_path=run_plan_path,
            plan_shape=str(composed.composed_plan.get("plan_shape") or ""),
            walker_mode="dynamic",
            walker_mode_basis=(
                "launch_assembled_building ran an assemble()-composed plan through "
                "run_building_plan; no human forward/stop gate"
            ),
            run_result=run_result,
            task_source_basis="task_statement",
        )

    # MINE #3 cut: one worktree per launch (NO fan-out); the live tree is untouched.
    try:
        sandbox_result = _run_in_worktree_sandbox(
            repo,
            building_id=building_id,
            durable_output=durable_output,
            run_dispatch=_run_composed_plan,
        )
    except Exception as exc:  # noqa: BLE001 -- friendly support entry
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "composed plan 실행 중 문제가 생겼어요.",
            }
        )
        return result

    result.update(
        {
            "ok": sandbox_result.frontier_kind == "complete",
            "ran": True,
            "evidence_root": sandbox_result.evidence_root,
            "frontier_kind": sandbox_result.frontier_kind,
            "frontier_reason": sandbox_result.frontier_reason,
            "isolation_mode": sandbox_result.isolation_mode,
            "isolation_reason": sandbox_result.isolation_reason,
            "commit_sha": sandbox_result.commit_sha,
            "wip_anchor_ref": sandbox_result.wip_anchor_ref,
            "wip_commit_sha": sandbox_result.wip_commit_sha,
            "worktree_path": sandbox_result.worktree_path,
            "worktree_disposed": sandbox_result.worktree_disposed,
            "result_summary": _result_summary_with_sandbox_anchors(
                sandbox_result.evidence_root,
                repo_root=repo,
                building_id=sandbox_result.building_id,
                commit_sha=sandbox_result.commit_sha,
            ),
        }
    )
    return result


def _composition_run_plan_filename(building_id: str) -> str:
    """The on-disk plan filename for an assemble-path launch (slug-safe)."""

    return f"{_path_slug(building_id)}-composed-plan.json"


def _load_goal_proposal(proposal_ref: Any) -> tuple[Mapping[str, Any], Path | None]:
    from brick_protocol.support.operator.assembly import ComposedGraph  # noqa: PLC0415

    if isinstance(proposal_ref, ComposedGraph):
        return copy.deepcopy(proposal_ref.composed_plan), None
    if isinstance(proposal_ref, Mapping):
        return copy.deepcopy(proposal_ref), None
    path = _proposal_path_from_ref(proposal_ref)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError("proposal snapshot must be a JSON object")
    return value, path


def _proposal_path_from_ref(proposal_ref: Any) -> Path:
    path = Path(str(proposal_ref)).expanduser()
    if path.is_dir():
        path = path / _GOAL_PROPOSAL_FILENAME
    return path.resolve()


def _validate_frozen_goal_plan(plan: Mapping[str, Any]) -> None:
    if str(plan.get("plan_shape") or "") != "graph":
        raise ValueError("frozen proposal must be a graph Building Plan")
    _required_plan_text(plan, "building_id")
    if not _optional_plan_text(plan.get("task_source_ref")):
        raise ValueError("frozen proposal is missing task_source_ref")
    if not _optional_plan_text(plan.get("task_statement")):
        raise ValueError("frozen proposal is missing task_statement")
    if not isinstance(plan.get("brick_steps"), list):
        raise ValueError("frozen proposal is missing brick_steps")
    if not isinstance(plan.get("link_edges"), list):
        raise ValueError("frozen proposal is missing link_edges")


def _goal_approval_output_root(
    output_root: Path | str | None,
    proposal_path: Path | None,
) -> Path:
    if output_root is not None:
        return Path(output_root).expanduser().resolve()
    if proposal_path is not None and proposal_path.name == _GOAL_PROPOSAL_FILENAME:
        parent = proposal_path.parent.parent
        if parent != proposal_path.parent:
            return parent.resolve()
    return Path.home() / ".brick" / "goal-runs"


def _goal_approval_plan_path(
    plan: Mapping[str, Any],
    *,
    proposal_path: Path | None,
    durable_output: Path,
) -> Path:
    if proposal_path is not None:
        return proposal_path
    building_id = _required_plan_text(plan, "building_id")
    plan_path = durable_output / _path_slug(building_id) / _GOAL_PROPOSAL_FILENAME
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return plan_path


def _build_output_root(building_id: str, output_root: Path | str | None = None) -> Path:
    if output_root is not None:
        return Path(output_root).expanduser().resolve()
    stamp = _utc_timestamp_slug()
    return Path.home() / ".brick" / "goal-runs" / f"{_path_slug(building_id)}-{stamp}"


def _build_proposal_root(output_root: Path) -> Path:
    return output_root.parent / f"{output_root.name}-proposals"


def _utc_timestamp_slug() -> str:
    from datetime import datetime, timezone  # noqa: PLC0415

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _proposal_root_is_prerun_only(
    proposal_path: Path | None,
    *,
    durable_output: Path,
    building_id: str,
) -> bool:
    if proposal_path is None:
        return False
    root = (durable_output / building_id).resolve()
    if proposal_path.parent.resolve() != root:
        return False
    try:
        entries = list(root.iterdir())
    except FileNotFoundError:
        return False
    if len(entries) != 1:
        return False
    entry = entries[0]
    return (
        entry.resolve() == proposal_path.resolve()
        and entry.name == _GOAL_PROPOSAL_FILENAME
        and entry.is_file()
        and not entry.is_symlink()
    )


def _render_goal_proposal_plan(plan: Mapping[str, Any]) -> str:
    building_id = str(plan.get("building_id") or "")
    steps = [step for step in plan.get("brick_steps", ()) if isinstance(step, Mapping)]
    edges = [edge for edge in plan.get("link_edges", ()) if isinstance(edge, Mapping)]
    groups = [group for group in plan.get("groups", ()) if isinstance(group, Mapping)]
    fan_in_groups = [
        group for group in groups if str(group.get("group_role") or "").strip() == "fan_in"
    ]
    fan_in_labels: dict[str, str] = {}
    edge_by_ref = {str(edge.get("edge_ref") or ""): edge for edge in edges}
    for index, group in enumerate(fan_in_groups, start=1):
        label = f"합류 {index}"
        for member_ref in _text_list(group.get("member_refs")):
            edge = edge_by_ref.get(member_ref)
            if isinstance(edge, Mapping):
                target = str(edge.get("target_step_ref") or "").strip()
                if target:
                    fan_in_labels[target] = label

    fan_out_counts: dict[str, int] = {}
    for group in groups:
        if str(group.get("group_role") or "").strip() != "fan_out":
            continue
        member_refs = _text_list(group.get("member_refs"))
        for member_ref in member_refs:
            edge = edge_by_ref.get(member_ref)
            if isinstance(edge, Mapping):
                source = str(edge.get("source_step_ref") or "").strip()
                if source:
                    fan_out_counts[source] = max(fan_out_counts.get(source, 0), len(member_refs))

    lines = [
        "=== 굴리기 전 proposal 미리보기 ===",
        f"building_id: {building_id}",
        f"단계: {len(steps)}개",
        f"합류점 {len(fan_in_groups)}개",
        "",
    ]
    for index, step in enumerate(steps, start=1):
        step_ref = str(step.get("step_ref") or "").strip()
        kind = _step_kind(step)
        agent_ref = _agent_ref(step) or "agent 미지정"
        link_bits: list[str] = []
        if fan_out_counts.get(step_ref):
            link_bits.append(f"fan_out {fan_out_counts[step_ref]}갈래")
        if fan_in_labels.get(step_ref):
            link_bits.append(fan_in_labels[step_ref])
        if not link_bits:
            link_bits.append(_next_link_label(step_ref, edges))
        gate_label = _gate_label(step_ref, edges)
        write_label = _write_scope_label(step)
        lines.append(f"{index}. {kind} — {step_ref}")
        lines.append(f"   누구: {agent_ref}")
        lines.append(f"   링크: {', '.join(bit for bit in link_bits if bit)}")
        lines.append(f"   게이트: {gate_label}")
        lines.append(f"   쓰기영역: {write_label}")
    return "\n".join(lines)


def _step_kind(step: Mapping[str, Any]) -> str:
    ref = str(step.get("step_template_ref") or "").strip()
    return ref.split(":", 1)[-1] if ":" in ref else ref or "unknown"


def _agent_ref(step: Mapping[str, Any]) -> str:
    row = _step_row(step, "Agent")
    return str(row.get("agent_object_ref") or "").strip()


def _write_scope_label(step: Mapping[str, Any]) -> str:
    row = _step_row(step, "Brick")
    scope = row.get("write_scope")
    requires = bool(row.get("requires_brick_write_scope"))
    if not isinstance(scope, Mapping) and not requires:
        return "읽기/기록만"
    allowed = scope.get("allowed_paths") if isinstance(scope, Mapping) else ()
    allowed_text = ", ".join(_text_list(allowed)) or "선언 필요"
    return f"✍️ 파일 씀: {allowed_text}"


def _next_link_label(step_ref: str, edges: list[Mapping[str, Any]]) -> str:
    labels: list[str] = []
    for edge in edges:
        if str(edge.get("source_step_ref") or "").strip() != step_ref:
            continue
        target = str(edge.get("target_step_ref") or "").strip()
        if not target:
            link_row = _link_row(edge)
            target = str(link_row.get("target_ref") or "boundary").strip()
        labels.append(f"다음 {target}")
    return ", ".join(labels) if labels else "다음 없음"


def _gate_label(step_ref: str, edges: list[Mapping[str, Any]]) -> str:
    refs: list[str] = []
    for edge in edges:
        if str(edge.get("source_step_ref") or "").strip() != step_ref:
            continue
        refs.extend(_text_list(_link_row(edge).get("declared_gate_refs")))
    return ", ".join(dict.fromkeys(refs)) if refs else "기본 전이"


def _step_row(step: Mapping[str, Any], owner_axis: str) -> Mapping[str, Any]:
    for row in step.get("rows", ()):
        if isinstance(row, Mapping) and str(row.get("owner_axis") or "") == owner_axis:
            return row
    return {}


def _link_row(edge: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = edge.get("rows")
    if isinstance(rows, list) and rows and isinstance(rows[0], Mapping):
        return rows[0]
    return {}


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _required_plan_text(plan: Mapping[str, Any], key: str) -> str:
    text = _optional_plan_text(plan.get(key))
    if not text:
        raise ValueError(f"frozen proposal is missing {key}")
    return text


def _optional_plan_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _path_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "proposal"


def _approval_route_decision_basis_fields(
    *,
    action: str,
    author_ref: str,
    frontier_before: Mapping[str, Any],
    paused_at_ref: str,
) -> dict[str, Any]:
    """Return raw Link-row basis fields for a human/COO forward disposition."""

    if action != "forward":
        return {}
    frontier_reason = str(frontier_before.get("frontier_reason") or "").strip()
    if not frontier_reason:
        return {}
    override_refs = [f"override:{frontier_reason}"]
    if paused_at_ref:
        override_refs.append(f"override:paused-at:{paused_at_ref}")
    return {
        "route_decision_override_refs": override_refs,
        "route_decision_reviewer_observation_refs": [
            f"observation:{frontier_reason}",
        ],
        "route_decision_proof_limits": [
            "caller/COO authored disposition basis evidence only",
            "support mirrored the observed hold reason onto the Link row",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "route_decision_not_proven": [
            "whether the caller/COO disposition is sufficient for any other hold",
            "semantic correctness of the held Building work",
            f"author identity beyond declared ref {author_ref}",
        ],
    }


def _approval_route_decision_basis_recorded(
    link_path: Path,
    row: Mapping[str, Any],
) -> bool:
    expected_action = row.get("transition_lifecycle_disposition_action")
    expected_resumed_from = row.get("transition_lifecycle_resumed_from_ref")
    expected_pending_target = row.get("transition_lifecycle_pending_target_ref")
    expected_overrides = row.get("route_decision_override_refs")
    if not expected_overrides:
        return True
    for record in _jsonl_records(link_path):
        if (
            record.get("transition_lifecycle_disposition_action") == expected_action
            and record.get("transition_lifecycle_resumed_from_ref") == expected_resumed_from
            and record.get("transition_lifecycle_pending_target_ref")
            == expected_pending_target
            and record.get("route_decision_override_refs") == expected_overrides
        ):
            return True
    return False


def _invalid_disposition_menu_result(
    *,
    action_text: str,
    allowed_actions: Sequence[str],
    hold_reason: str,
) -> dict[str, Any]:
    allowed = [str(item) for item in allowed_actions]
    allowed_text = ", ".join(allowed)
    return {
        "error_kind": "invalid_disposition_for_hold",
        "error_message": (
            f"action {action_text!r} is not admitted for hold_reason={hold_reason!r}; "
            f"allowed disposition actions: {allowed_text}"
        ),
        "message_ko": (
            f"이 hold에서는 {action_text} 처분을 쓸 수 없어요. "
            f"가능한 처분: {allowed_text}"
        ),
        "allowed_disposition_actions": allowed,
        "not_resumable_by": [action_text],
    }


def run_approve_entry(
    building_ref: str | Path,
    *,
    action: str | None = None,
    author_ref: str | None = None,
    budget_increment: int | None = None,
    reroute_target_ref: str | None = None,
    re_instruction: str | None = None,
    output_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Append a human/COO disposition row for a held Building, then resume it.

    This is a support convenience wrapper around already-written evidence. It
    observes the frontier, mirrors the admitted transition_lifecycle disposition
    row shape into raw/link.jsonl, and calls ``resume_building_plan``.
    It does not choose Movement, targets, sufficiency, quality, or success.
    """

    import json  # noqa: PLC0415

    from brick_protocol.support.operator.run import resume_building_plan  # noqa: PLC0415

    repo = _safe_repo_root(repo_root)
    building_text = str(building_ref).strip()
    action_text = str(action or "").strip().lower()
    author_text = str(author_ref or "").strip()
    reroute_target_text = str(reroute_target_ref or "").strip()
    result: dict[str, Any] = {
        "ok": False,
        "building_ref": building_text,
        "action": action_text,
        "author_ref": author_text,
        "disposition_written": False,
    }
    if not building_text:
        result.update(
            {
                "error_kind": "invalid_building_ref",
                "error_message": "building ref가 비어 있어요.",
                "message_ko": "승인할 building을 지정해야 해요.",
            }
        )
        return result
    if not action_text:
        result.update(
            {
                "error_kind": "missing_disposition_action",
                "error_message": "approval/resume requires an explicit disposition action.",
                "message_ko": "resume하려면 사람이 고른 disposition action이 필요해요.",
            }
        )
        return result
    if not author_text:
        result.update(
            {
                "error_kind": "missing_disposition_author",
                "error_message": "approval/resume requires an explicit human/COO author_ref.",
                "message_ko": "resume하려면 human:/coo: 작성자 ref가 필요해요.",
            }
        )
        return result
    if action_text not in DISPOSITION_ACTIONS:
        result.update(
            {
                "error_kind": "invalid_action",
                "error_message": "action은 forward, stop, raise, reroute 중 하나여야 해요.",
                "message_ko": "지원하지 않는 승인 동작이에요.",
            }
        )
        return result
    if action_text == "reroute" and not reroute_target_text:
        result.update(
            {
                "error_kind": "missing_reroute_target_ref",
                "error_message": "reroute action에는 reroute_target_ref가 필요해요.",
                "message_ko": "reroute에는 사람이 고른 target ref가 필요해요.",
            }
        )
        return result
    if action_text != "reroute" and reroute_target_text:
        result.update(
            {
                "error_kind": "invalid_reroute_target_ref",
                "error_message": "reroute_target_ref는 reroute action에만 쓸 수 있어요.",
                "message_ko": "reroute target은 action=reroute에서만 쓸 수 있어요.",
            }
        )
        return result
    if not (author_text.startswith("coo:") or author_text.startswith("human:")):
        result.update(
            {
                "error_kind": "invalid_author_ref",
                "error_message": "author_ref는 coo: 또는 human: 접두로 시작해야 해요.",
                "message_ko": "작성자 ref는 coo: 또는 human: 으로 시작해야 해요.",
            }
        )
        return result
    re_instruction_text = str(re_instruction or "").strip()
    if action_text == "reroute" and not re_instruction_text:
        result.update(
            {
                "error_kind": "missing_re_instruction",
                "error_message": "human/COO reroute action requires re_instruction.",
                "message_ko": "사람/COO reroute에는 재시도 지시문 re_instruction이 필요해요.",
            }
        )
        return result
    parsed_budget: int | None = None
    if budget_increment is not None:
        if action_text != "raise":
            result.update(
                {
                    "error_kind": "invalid_budget_increment",
                    "error_message": "budget_increment는 raise action에만 쓸 수 있어요.",
                    "message_ko": "forward/stop에는 budget_increment를 붙일 수 없어요.",
                }
            )
            return result
        try:
            parsed_budget = int(budget_increment)
        except (TypeError, ValueError):
            parsed_budget = 0
        if parsed_budget <= 0:
            result.update(
                {
                    "error_kind": "invalid_budget_increment",
                    "error_message": "raise budget_increment는 양의 정수여야 해요.",
                    "message_ko": "raise에는 양의 budget_increment가 필요해요.",
                }
            )
            return result
    elif action_text == "raise":
        result.update(
            {
                "error_kind": "missing_budget_increment",
                "error_message": "raise action에는 budget_increment가 필요해요.",
                "message_ko": "raise에는 budget_increment가 필요해요.",
            }
        )
        return result

    building_root, building_root_candidates = _resolve_approval_building_root(
        building_text,
        output_root=output_root,
        repo_root=repo,
    )
    if building_root is None:
        result.update(
            {
                "error_kind": "building_root_not_found",
                "error_message": (
                    "building root not found for building_ref "
                    f"{building_text!r}; checked: "
                    + ", ".join(str(path) for path in building_root_candidates)
                ),
                "message_ko": "지정한 building root를 찾을 수 없어요.",
                "building_root_candidates": [
                    str(path) for path in building_root_candidates
                ],
            }
        )
        return result
    result["building_root"] = str(building_root)
    result["evidence_root"] = str(building_root)

    try:
        frontier_before = dict(observe_building_frontier(building_root, repo_root=repo))
    except Exception as exc:  # noqa: BLE001 -- CLI support surface returns evidence
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "building frontier를 읽을 수 없어요.",
            }
        )
        return result

    frontier_kind_before = str(frontier_before.get("frontier_kind") or "")
    result["frontier_kind_before"] = frontier_kind_before
    result["frontier_kind"] = frontier_kind_before
    result["frontier_reason_before"] = str(frontier_before.get("frontier_reason") or "")
    correction_refs = frontier_before.get("correction_observation_refs")
    if isinstance(correction_refs, Sequence) and not isinstance(
        correction_refs, (str, bytes)
    ):
        result["correction_observation_refs"] = [
            str(ref) for ref in correction_refs if str(ref).strip()
        ]
    if frontier_before.get("frontier_kind_uncorrected"):
        result["frontier_kind_uncorrected"] = str(
            frontier_before.get("frontier_kind_uncorrected") or ""
        )
    hold_record_w: Mapping[str, Any] = {}
    evidence_w: Mapping[str, Any] = {}
    adapter_error_hold_recorded = False
    try:
        from brick_protocol.support.operator.walker_resume import (  # noqa: PLC0415
            _adapter_error_hold_without_return,
            _read_written_dynamic_plan,
        )

        _plan_w, evidence_w = _read_written_dynamic_plan(building_root)
        raw_hold_record_w = evidence_w.get("hold") or {}
        hold_record_w = raw_hold_record_w if isinstance(raw_hold_record_w, Mapping) else {}
        adapter_error_hold_recorded = _adapter_error_hold_without_return(hold_record_w)
    except FileNotFoundError:
        pass
    if frontier_kind_before == "chat_session_parked":
        result.update(
            {
                "error_kind": "chat_session_parked_not_resumable",
                "error_message": (
                    "chat_session_parked는 onboard approve 대상이 아니에요."
                ),
                "message_ko": (
                    "이 building은 chat_session_parked 상태라 approve로 재개하지 않아요."
                ),
            }
        )
        return result
    if frontier_kind_before == "complete":
        result.update(
            {
                "ok": True,
                "message_ko": "이미 완료된 building이라 승인 동작이 필요 없어요.",
            }
        )
        return result
    if (
        frontier_kind_before not in {"link_paused", "human_review_waiting"}
        and not adapter_error_hold_recorded
    ):
        result.update(
            {
                "error_kind": "not_approval_hold",
                "error_message": "승인 대상 hold 상태가 아니에요.",
                "message_ko": "승인 대상 hold가 아니어서 disposition을 쓰지 않았어요.",
            }
        )
        return result
    if adapter_error_hold_recorded and frontier_kind_before not in {
        "link_paused",
        "human_review_waiting",
    }:
        result["approval_hold_source"] = "dynamic_walker_evidence.adapter_error_frontier"
    latest_lifecycle = frontier_before.get("latest_transition_lifecycle") or {}
    if not isinstance(latest_lifecycle, dict):
        latest_lifecycle = {}
    pending_target_ref = str(
        latest_lifecycle.get("transition_lifecycle_pending_target_ref") or ""
    )
    if not pending_target_ref and adapter_error_hold_recorded:
        pending_target_ref = str(hold_record_w.get("pending_target_ref") or "")
    disposition_pending_target_ref = (
        reroute_target_text if action_text == "reroute" else pending_target_ref
    )
    paused_at_ref = str(
        latest_lifecycle.get("transition_lifecycle_paused_at_ref") or ""
    )
    if not paused_at_ref and adapter_error_hold_recorded:
        paused_at_ref = str(hold_record_w.get("paused_at_ref") or "")
    result["pending_target_ref"] = disposition_pending_target_ref
    if disposition_pending_target_ref != pending_target_ref:
        result["held_pending_target_ref"] = pending_target_ref
        result["reroute_target_ref"] = disposition_pending_target_ref
    result["paused_at_ref"] = paused_at_ref
    if not pending_target_ref:
        result.update(
            {
                "error_kind": "missing_pending_target_ref",
                "error_message": "pending_target_ref가 비어 있어요.",
                "message_ko": "다음 target ref가 기록돼 있지 않아 fail-closed 했어요.",
            }
        )
        return result
    if not paused_at_ref:
        result.update(
            {
                "error_kind": "missing_paused_at_ref",
                "error_message": "paused_at_ref가 비어 있어요.",
                "message_ko": "어떤 hold를 재개하는지 기록돼 있지 않아 fail-closed 했어요.",
            }
        )
        return result

    menu_precheck_missing_error: Exception | None = None
    try:
        from brick_protocol.support.operator.walker_resume import (  # noqa: PLC0415
            hold_disposition_action_menu,
            resume_budget_recovery_decision,
            validate_hold_disposition_action,
        )

        if not evidence_w:
            from brick_protocol.support.operator.walker_resume import (  # noqa: PLC0415
                _read_written_dynamic_plan,
            )

            _plan_w, evidence_w = _read_written_dynamic_plan(building_root)
            raw_hold_record_w = evidence_w.get("hold") or {}
            hold_record_w = raw_hold_record_w if isinstance(raw_hold_record_w, Mapping) else {}
        try:
            allowed_actions = validate_hold_disposition_action(
                action_text,
                hold_record_w,
                frontier_reason=result["frontier_reason_before"],
            )
        except ValueError as exc:
            hold_reason = str(
                hold_record_w.get("hold_reason") or result["frontier_reason_before"] or "unknown"
            )
            menu = hold_disposition_action_menu(
                hold_record_w,
                frontier_reason=result["frontier_reason_before"],
            )
            result.update(
                _invalid_disposition_menu_result(
                    action_text=action_text,
                    allowed_actions=menu,
                    hold_reason=hold_reason,
                )
            )
            result["error_message"] = str(exc)
            return result
        result["allowed_disposition_actions"] = list(allowed_actions)
        resume_budget_recovery_decision(
            evidence=evidence_w,
            action=action_text,
            hold_record=hold_record_w,
            pending_target=disposition_pending_target_ref,
        )
    except FileNotFoundError as exc:
        menu_precheck_missing_error = exc
    except ValueError as exc:
        result.update(
            {
                "error_kind": "resume_budget_precheck_refused",
                "error_message": str(exc),
                "message_ko": "예산 정합성 검증에서 걸려 disposition을 쓰지 않았어요.",
            }
        )
        return result

    prepared_adapter_cwd, adapter_cwd_observation = _prepare_resume_adapter_cwd(
        repo_root=repo,
        building_id=building_root.name,
        adapter_cwd=adapter_cwd,
    )
    if adapter_cwd_observation is not None:
        result.update(adapter_cwd_observation)
    if prepared_adapter_cwd is None:
        return result
    if menu_precheck_missing_error is not None:
        result.update(
            {
                "error_kind": type(menu_precheck_missing_error).__name__,
                "error_message": str(menu_precheck_missing_error),
                "message_ko": "resume evidence를 읽을 수 없어 disposition을 쓰지 않았어요.",
            }
        )
        return result

    link_path = building_root / "raw" / "link.jsonl"
    if not link_path.parent.is_dir():
        result.update(
            {
                "error_kind": "missing_raw_link_dir",
                "error_message": f"raw/link.jsonl parent does not exist: {link_path.parent}",
                "message_ko": "raw/link.jsonl을 쓸 evidence 폴더가 없어요.",
            }
        )
        return result

    building_id = building_root.name
    row: dict[str, Any] = {
        "raw_ref": f"raw:link:disposition:{action_text}",
        "building_id": building_id,
        "step_ref": f"human-disposition-{action_text}",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_resumed_from_ref": paused_at_ref,
        "transition_lifecycle_pending_target_ref": disposition_pending_target_ref,
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": action_text,
        "transition_author_ref": author_text,
    }
    if result.get("correction_observation_refs"):
        row["correction_observation_refs"] = list(result["correction_observation_refs"])
    if result.get("frontier_kind_uncorrected"):
        row["frontier_kind_uncorrected"] = result["frontier_kind_uncorrected"]
    if parsed_budget is not None:
        row["transition_lifecycle_budget_increment"] = parsed_budget
    row.update(
        _approval_route_decision_basis_fields(
            action=action_text,
            author_ref=author_text,
            frontier_before=frontier_before,
            paused_at_ref=paused_at_ref,
        )
    )
    # ④ RE-INSTRUCTION authoring: the human/COO may carry a corrected how-to to
    # the retried target Brick on THIS same disposition row. re_instruction is an
    # already-admitted transition_lifecycle key (link/transition.py) consumed by
    # the resume seed (walker_resume.py) and stamped onto the redo target's prompt
    # (walker_kernel.py / adapter_grant_policy.py). It rides the SAME author gate
    # validated above (coo:/human:) -- NO new authority surface. Free text;
    # present-only injection: absent => target runs its original work unchanged.
    if re_instruction_text:
        row["transition_lifecycle_re_instruction"] = re_instruction_text
    try:
        with link_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 -- support evidence, no traceback surface
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": "disposition row를 raw/link.jsonl에 쓰지 못했어요.",
            }
        )
        return result

    result["disposition_written"] = True
    result["disposition_row"] = row
    try:
        resume_building_plan(
            building_root,
            adapter_cwd=prepared_adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
        )
        frontier_after = dict(observe_building_frontier(building_root, repo_root=repo))
        if (
            action_text == "forward"
            and str(frontier_after.get("frontier_kind") or "") == "complete"
        ):
            from brick_protocol.support.operator.driver import (  # noqa: PLC0415
                _FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_REASON,
                _WRITE_SCOPE_FORBIDDEN_DIFF_PRESENT_REASON,
                _fake_landing_forward_disposition_recorded,
                _record_fake_landing_hold_for_plan,
                _record_write_scope_forbidden_diff_hold_for_plan,
                _write_need_complete_with_forbidden_diff_for_plan,
                _write_need_complete_without_scoped_diff_for_plan,
            )

            manifest_path = building_root / "evidence" / "evidence-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, Mapping):
                raise ValueError("evidence-manifest.json must contain a mapping")
            snapshot = manifest.get("plan_snapshot")
            if not isinstance(snapshot, Mapping):
                raise ValueError("evidence-manifest.json plan_snapshot must contain a mapping")
            plan_rows_copy = snapshot.get("plan_rows_copy")
            if not isinstance(plan_rows_copy, str) or not plan_rows_copy.strip():
                raise ValueError("evidence-manifest.json is missing plan_snapshot.plan_rows_copy")
            plan_copy = json.loads(plan_rows_copy)
            if not isinstance(plan_copy, Mapping):
                raise ValueError("plan_snapshot.plan_rows_copy must decode to a mapping")
            if _write_need_complete_with_forbidden_diff_for_plan(
                prepared_adapter_cwd,
                plan_copy,
            ) and not _fake_landing_forward_disposition_recorded(
                building_root,
                plan_copy,
                reason=_WRITE_SCOPE_FORBIDDEN_DIFF_PRESENT_REASON,
            ):
                _record_write_scope_forbidden_diff_hold_for_plan(building_root, plan_copy)
                frontier_after = dict(
                    observe_building_frontier(building_root, repo_root=repo)
                )
            elif _write_need_complete_without_scoped_diff_for_plan(
                prepared_adapter_cwd,
                plan_copy,
            ) and not _fake_landing_forward_disposition_recorded(
                building_root,
                plan_copy,
                reason=_FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_REASON,
            ):
                _record_fake_landing_hold_for_plan(building_root, plan_copy)
                frontier_after = dict(
                    observe_building_frontier(building_root, repo_root=repo)
                )
        if (
            action_text == "forward"
            and str(frontier_after.get("frontier_kind") or "") == "complete"
            and not _approval_route_decision_basis_recorded(link_path, row)
        ):
            durable_row = dict(row)
            durable_row["raw_ref"] = f"raw:link:disposition:{action_text}:basis"
            durable_row["raw_refs"] = [durable_row["raw_ref"]]
            with link_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        durable_row,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            frontier_after = dict(
                observe_building_frontier(building_root, repo_root=repo)
            )
    except Exception as exc:  # noqa: BLE001 -- disposition is already written
        result.update(
            {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
                "message_ko": (
                    "disposition은 썼지만 resume_building_plan 실행 중 문제가 생겼어요."
                ),
            }
        )
        return result

    result["frontier_kind"] = str(frontier_after.get("frontier_kind") or "")
    result["frontier_reason"] = str(frontier_after.get("frontier_reason") or "")
    result["ok"] = True
    result["message_ko"] = "승인 disposition을 쓰고 resume_building_plan을 호출했어요."
    return result


def _render_approve_text(result: dict[str, Any]) -> str:
    """Render the approve result as plain-Korean text for the CLI entry."""

    lines: list[str] = []
    lines.append("=== Brick Protocol: held building 승인 ===\n")
    lines.append(f"building: {result.get('building_root') or result.get('building_ref', '')}")
    lines.append(f"action: {result.get('action', '')}")
    lines.append(f"author: {result.get('author_ref', '')}")
    lines.append(f"disposition written: {result.get('disposition_written', False)}")
    if result.get("frontier_kind_before"):
        lines.append(f"frontier(before): {result.get('frontier_kind_before', '')}")
    if result.get("frontier_kind"):
        lines.append(f"frontier(after): {result.get('frontier_kind', '')}")
    if result.get("pending_target_ref"):
        lines.append(f"pending target: {result.get('pending_target_ref', '')}")
    if result.get("paused_at_ref"):
        lines.append(f"resumed from: {result.get('paused_at_ref', '')}")
    allowed_actions = result.get("allowed_disposition_actions")
    if isinstance(allowed_actions, Sequence) and not isinstance(allowed_actions, (str, bytes)):
        lines.append("allowed actions: " + ", ".join(str(item) for item in allowed_actions))
    not_resumable_by = result.get("not_resumable_by")
    if isinstance(not_resumable_by, Sequence) and not isinstance(not_resumable_by, (str, bytes)):
        lines.append("not resumable by: " + ", ".join(str(item) for item in not_resumable_by))
    if result.get("evidence_root"):
        lines.append(f"evidence: {result.get('evidence_root', '')}")
    lines.append("")
    lines.append(str(result.get("message_ko") or ""))
    if result.get("error_message"):
        lines.append(f"에러 종류: {result.get('error_kind', '')}")
        lines.append(f"에러 내용: {result.get('error_message', '')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:]) if argv is None else list(argv)
    # ``onboard doctor``: diagnosis-only subcommand. Runs the gh probe + every
    # provider preflight, prints the symptom -> prescription table, and ALWAYS
    # exits 0 (diagnosis is a record, not a gate).
    if args_list[:1] == ["doctor"]:
        sys.stdout.write(_render_doctor_text(run_doctor()))
        sys.stdout.write("\n")
        return 0
    # ``onboard goal-approve <proposal>``: pre-run human/COO approval over a
    # frozen proposal snapshot. This is distinct from ``onboard approve``, which
    # resumes an already-started held Building.
    if args_list[:1] == ["goal-approve"]:
        goal_approve_parser = argparse.ArgumentParser(
            prog="onboard goal-approve",
            description=(
                "Approve or stop a frozen pre-run proposal snapshot. forward "
                "runs proposed-building-graph.json through run_building_plan; "
                "stop runs nothing."
            ),
        )
        goal_approve_parser.add_argument(
            "proposal",
            help="Path to proposed-building-graph.json, or its containing directory.",
        )
        goal_approve_parser.add_argument(
            "--action",
            choices=GOAL_APPROVE_ACTIONS,
            default="forward",
            help="Pre-run disposition action.",
        )
        goal_approve_parser.add_argument(
            "--author",
            default="coo:smith",
            help="Disposition author ref; must start with coo: or human:.",
        )
        goal_approve_parser.add_argument(
            "--output-root",
            default=None,
            help="Durable evidence root; defaults to the proposal parent root.",
        )
        goal_approve_parser.add_argument(
            "--repo",
            default=None,
            help="Repo root override for the worktree-sandbox bracket.",
        )
        goal_approve_parser.add_argument(
            "--overwrite-existing",
            action="store_true",
            help="Allow an existing Building evidence root to be overwritten.",
        )
        goal_approve_parser.add_argument(
            "--timeout",
            dest="adapter_timeout_seconds",
            type=int,
            default=120,
            help="Adapter timeout seconds passed to run_building_plan.",
        )
        goal_approve_args = goal_approve_parser.parse_args(args_list[1:])
        goal_approve_result = run_goal_approve_entry(
            goal_approve_args.proposal,
            action=goal_approve_args.action,
            author_ref=goal_approve_args.author,
            output_root=goal_approve_args.output_root,
            repo_root=goal_approve_args.repo,
            overwrite_existing=goal_approve_args.overwrite_existing,
            adapter_timeout_seconds=goal_approve_args.adapter_timeout_seconds,
        )
        sys.stdout.write(json.dumps(goal_approve_result, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return 0 if goal_approve_result.get("ok") else 1
    # ``onboard approve <building>``: append a human/COO disposition row for a
    # held Building and call resume_building_plan(building_root). The row mirrors
    # the admitted checker shape; this support wrapper chooses no Movement.
    if args_list[:1] == ["approve"]:
        approve_parser = argparse.ArgumentParser(
            prog="onboard approve",
            description=(
                "Append a human/COO disposition row for a held Building, then "
                "resume it. Relative buildings resolve under ~/.brick/goal-runs "
                "unless --output-root is supplied."
            ),
        )
        approve_parser.add_argument("building", help="Building id or absolute path.")
        approve_parser.add_argument(
            "--action",
            choices=DISPOSITION_ACTIONS,
            required=True,
            help="Disposition action. raise requires --budget-increment.",
        )
        approve_parser.add_argument(
            "--author",
            required=True,
            help="Disposition author ref; must start with coo: or human:.",
        )
        approve_parser.add_argument(
            "--budget-increment",
            type=int,
            default=None,
            help="Positive budget increment, allowed only with --action raise.",
        )
        approve_parser.add_argument(
            "--reroute-target",
            dest="reroute_target_ref",
            default=None,
            help="Declared Brick node ref selected by the human/COO for --action reroute.",
        )
        approve_parser.add_argument(
            "--re-instruction",
            dest="re_instruction",
            default=None,
            help="Corrected how-to text carried to the retried target Brick.",
        )
        approve_parser.add_argument(
            "--output-root",
            default=None,
            help="Root for relative building ids (default: ~/.brick/goal-runs).",
        )
        approve_parser.add_argument(
            "--repo",
            default=None,
            help="Repo root override for frontier observation.",
        )
        approve_parser.add_argument(
            "--adapter-cwd",
            default=None,
            help="Working directory passed to resumed adapter calls.",
        )
        approve_parser.add_argument(
            "--timeout",
            dest="adapter_timeout_seconds",
            type=int,
            default=120,
            help="Adapter timeout seconds passed to resume_building_plan.",
        )
        approve_args = approve_parser.parse_args(args_list[1:])
        approve_result = run_approve_entry(
            approve_args.building,
            action=approve_args.action,
            author_ref=approve_args.author,
            budget_increment=approve_args.budget_increment,
            reroute_target_ref=approve_args.reroute_target_ref,
            re_instruction=approve_args.re_instruction,
            output_root=approve_args.output_root,
            repo_root=approve_args.repo,
            adapter_cwd=approve_args.adapter_cwd,
            adapter_timeout_seconds=approve_args.adapter_timeout_seconds,
        )
        sys.stdout.write(_render_approve_text(approve_result))
        sys.stdout.write("\n")
        return 0 if approve_result.get("ok") else 1
    parser = argparse.ArgumentParser(
        description=(
            "Friendly, never-raising onboarding flow. Prints the preflight + "
            "connect + a first example Building (routed through the PART-1 seam "
            "driver.run_building_intake) in plain Korean. Also: the 'doctor' "
            "subcommand prints a symptom -> prescription diagnosis and always "
            "exits 0."
        )
    )
    parser.add_argument("host", choices=SUPPORTED_HOSTS)
    parser.add_argument(
        "--no-example",
        action="store_true",
        help="Skip running the bundled example Building.",
    )
    parser.add_argument(
        "--real-provider",
        action="store_true",
        help=(
            "Allow the example to run on the REAL provider's observed-write "
            "adapter (codex/claude/gemini local) when preflight "
            "reports it READY; otherwise falls back to adapter:local. "
            "Default: adapter:local only."
        ),
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Repo root override (default: computed from this file's location).",
    )
    parser.add_argument(
        "--recording",
        action="store_true",
        help=(
            "OPT-IN: wire the auto-recording hooks into THIS checkout "
            "(.claude/hooks + .codex/hooks + settings/hooks JSON, paths "
            "computed from the actual repo root). Idempotent; never silently "
            "overwrites a user-modified file (compare + skip + warn)."
        ),
    )
    args = parser.parse_args(args_list)
    # The CLI keeps the first example's evidence so a brand-new customer can go
    # to the printed "결과 저장 위치" and actually READ it (work/task.md, the
    # lifecycle root). ~/.brick is the established BRICK user dir (already holds
    # report.env) and lives OUTSIDE the repo/worktree, so "작업 트리는 건드리지
    # 않았어요" stays true. run_building_intake passes overwrite_existing=True for
    # this example, so re-running the wizard overwrites cleanly (no accumulation).
    # Library callers of run_onboard keep output_root=None (ephemeral temp dir);
    # ONLY this CLI default changes.
    example_root = Path.home() / ".brick" / "onboard-example"
    example_root.mkdir(parents=True, exist_ok=True)
    result = run_onboard(
        args.host,
        repo_root=args.repo,
        run_example=not args.no_example,
        output_root=example_root,
        allow_real_provider=args.real_provider,
    )
    sys.stdout.write(_render_flow_text(result))
    sys.stdout.write("\n")
    ok = bool(result.get("ok"))
    if args.recording:
        recording = run_recording_setup(repo_root=args.repo)
        sys.stdout.write(_render_recording_text(recording))
        sys.stdout.write("\n")
        ok = ok and bool(recording.get("ok"))
    # Honest exit status: ok:false (preflight/example/recording problem) exits
    # nonzero so scripts and the installer can SEE the failure, while the
    # friendly Korean guidance above stays the human surface.
    return 0 if ok else 1


__all__ = [
    "build",
    "LAUNCH_ASSEMBLED_SEAM_VERB",
    "DOCTOR_SYMPTOM_PRESCRIPTIONS_KO",
    "GOAL_APPROVE_ACTIONS",
    "GOAL_APPROVE_SEAM_VERB",
    "EXAMPLE_DECLARED_BY",
    "EXAMPLE_LOCAL_PRESET_REF",
    "EXAMPLE_PLAN_REL",
    "EXAMPLE_REAL_PRESET_REF",
    "EXAMPLE_TASK_SOURCE_REF",
    "RECORDING_HOOK_TEMPLATES",
    "SEAM_VERB",
    "SUPPORTED_HOSTS",
    "main",
    "run_doctor",
    "run_approve_entry",
    "run_goal_approve_entry",
    "run_onboard",
    "render_proposal_for_human",
    "run_recording_setup",
    "run_install_wizard",
    "run_mcp_register_step",
    "run_skills_place_step",
    "run_slack_provision_step",
]


if __name__ == "__main__":
    raise SystemExit(main())
