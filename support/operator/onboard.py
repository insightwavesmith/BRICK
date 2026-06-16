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
                   observed-write adapter (adapter:codex-local / adapter:claude-local).
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from brick_protocol.support.connection import connect
from brick_protocol.support.connection.agent_adapter import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_LOCAL,
    adapter_is_write_capable,
    invoke_claude_text,
    invoke_codex_text,
    invoke_gemini_text,
    preflight_provider,
)
from brick_protocol.support.operator.driver import run_building_intake
from brick_protocol.support.operator.frontier_observation import (
    observe_building_frontier,
)
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
# adapter_is_write_capable -- currently adapter:codex-local / adapter:claude-local),
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
# CLI); ``codex``/``claude``/``gemini`` are the admitted local CLI providers.
_HOST_ADAPTER_REF = {
    "codex": ADAPTER_CODEX_LOCAL,
    "claude": ADAPTER_CLAUDE_LOCAL,
    "gemini": ADAPTER_GEMINI_LOCAL,
    "local": ADAPTER_LOCAL,
}
# ``connect`` only renders codex/claude config; other hosts get a friendly note.
_CONNECT_TARGETS = {"codex", "claude"}

SUPPORTED_HOSTS = tuple(_HOST_ADAPTER_REF)


def _safe_repo_root(repo_root: Path | str | None) -> Path:
    if repo_root is None:
        return _REPO_ROOT
    try:
        return Path(repo_root).resolve()
    except Exception:  # noqa: BLE001 -- never raise on a bad path
        return _REPO_ROOT


def _normalize_host(host: Any) -> str:
    return host.strip().lower() if isinstance(host, str) else ""


def _preflight_step(host: str) -> dict[str, Any]:
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
        status = preflight_provider(adapter_ref)
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
      ``adapter_is_write_capable``, currently adapter:codex-local /
      adapter:claude-local -- never a hardcoded provider literal). Uses a preset
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


def _example_step(
    *,
    repo_root: Path,
    output_root: Path | str | None,
    preflight: dict[str, Any],
    readiness: str,
    allow_real_provider: bool,
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
    (adapter:codex-local / adapter:claude-local). Which adapter ran, and WHY, is
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
        )
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
            # Name the ACTUAL ready provider (codex OR claude -- observed-write
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
        "설계AI 키 없음",
        "설계AI를 claude/codex로 고르면 별도 API 키가 필요 없고, "
        "gemini를 고르면 GEMINI_API_KEY (또는 GOOGLE_API_KEY)를 설정하세요.",
    ),
    (
        "gh 인증 에러 (clone/pull 실패)",
        "gh auth login (gh가 없으면 https://cli.github.com 에서 설치)",
    ),
)


def _doctor_gh_row() -> dict[str, Any]:
    """gh login probe for the clone/pull path. Read-only, never raises."""

    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    target = "gh (저장소 받기/갱신)"
    if shutil.which("gh") is None:
        return {
            "target": target,
            "ok": False,
            "message_ko": (
                "gh CLI가 없어요 → https://cli.github.com 에서 설치한 뒤 "
                "gh auth login"
            ),
        }
    try:
        completed = subprocess.run(  # noqa: S603 -- fixed argv, read-only probe
            ("gh", "auth", "status"),
            capture_output=True,
            timeout=10,
            check=False,
        )
        authed = completed.returncode == 0
    except Exception:  # noqa: BLE001 -- doctor never raises
        authed = False
    if authed:
        return {"target": target, "ok": True, "message_ko": "GitHub 로그인 확인 ✅"}
    return {
        "target": target,
        "ok": False,
        "message_ko": "GitHub 로그인이 안 돼 있어요 → gh auth login",
    }


def run_doctor() -> dict[str, Any]:
    """Run every provider preflight + the gh probe. NEVER raises.

    Returns {rows, symptom_table, all_ok}. ``all_ok`` summarizes the rows, but
    the CLI entry ALWAYS exits 0: doctor is a diagnosis record, not a gate. It
    proves no provider availability, judges no success/quality, and chooses no
    Movement.
    """

    rows: list[dict[str, Any]] = []
    try:
        rows.append(_doctor_gh_row())
        for host in SUPPORTED_HOSTS:
            status = _preflight_step(host)
            rows.append(
                {
                    "target": host,
                    "ok": bool(status.get("ok")),
                    "message_ko": str(status.get("message_ko") or ""),
                }
            )
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


def _handoff_message_ko(host: str, design_brain: str | None = None) -> str:
    """Step 4: plain-Korean closing handoff that NAMES the Phase-1 seam verb."""

    selected_design_brain = _normalize_design_brain(host, design_brain)
    return (
        "이제 에이전트한테 말 거세요:\n"
        "  · \"브릭이 뭐야?\"  (개념이 궁금할 때)\n"
        "  · \"___ 만들어줘\"  (빈칸에 만들고 싶은 걸 적으세요)\n"
        "task 파일은 따로 만들 필요 없어요 — 할 일을 그냥 글로 전하세요.\n"
        "(인테이크에 task_statement 로 텍스트를 넘기면, 기계가 그 글을 빌딩\n"
        " 증거 work/task.md 로 기록해요. 파일 기반 task_source_ref 는 자동화\n"
        " 경로로 그대로 남아 있어요.)\n"
        "\n"
        "가장 쉬운 시작: 할 일을 한 줄로 적어 목표 명령에 그대로 넘기세요 —\n"
        "  onboard goal \"<할 일>\"\n"
        "AI가 보드(board)를 보고 빌딩을 알아서 구성해요(프리셋을 직접 안 골라도\n"
        "돼요). 격리된 작업 트리 안에서 실행되고, 당신의 실제 트리는 절대\n"
        "건드리지 않아요. 실행 브레인을 고르려면 --brain codex|claude|gemini|local\n"
        "(기본 local)을 붙이세요. 설계AI는 기본적으로 --brain을 따라가고,\n"
        "local만 설계AI가 없어 gemini로 대체돼요. 다르게 고르려면\n"
        "--design-brain codex|claude|gemini 를 붙이세요.\n"
        f"지금 안내 기준 설계AI: {selected_design_brain}\n"
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
    design_brain: str | None = None,
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
      provider (adapter:codex-local / adapter:claude-local), the SAME seam runs
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

    preflight = _preflight_step(normalized_host)
    readiness = _preflight_readiness(preflight)
    selected_design_brain = _normalize_design_brain(normalized_host, design_brain)
    design_preflight = _design_brain_preflight(selected_design_brain)
    design_readiness = _preflight_readiness(design_preflight)
    connect_hint = _connect_step(normalized_host, root)

    if run_example:
        example_result = _example_step(
            repo_root=root,
            output_root=output_root,
            preflight=preflight,
            readiness=readiness,
            allow_real_provider=allow_real_provider,
        )
    else:
        example_result = {
            "ok": True,
            "ran": False,
            "message_ko": "예제 실행은 건너뛰었어요.",
        }

    ok = (
        bool(preflight.get("ok"))
        and bool(design_preflight.get("ok"))
        and bool(example_result.get("ok"))
    )

    return {
        "host": normalized_host,
        "preflight": preflight,
        "preflight_readiness": readiness,
        "design_brain": selected_design_brain,
        "design_brain_preflight": design_preflight,
        "design_brain_readiness": design_readiness,
        "connect_hint": connect_hint,
        "example_result": example_result,
        "handoff_message_ko": _handoff_message_ko(
            normalized_host,
            selected_design_brain,
        ),
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
    lines.append(f"   - 준비도(기록): {result.get('preflight_readiness', 'unknown')}")
    design_preflight = result.get("design_brain_preflight") or {}
    lines.append(
        f"   - 설계AI({result.get('design_brain', '')}) 준비도: "
        f"{result.get('design_brain_readiness', 'unknown')}"
    )
    lines.append(f"     {design_preflight.get('message_ko', '(상태 없음)')}\n")

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


# H3b customer ENTRY: a free-form goal -> the design AI composes a building ->
# it runs in the W1 disposable worktree sandbox -> evidence. This is the
# customer's "use BRICK" command. It is a THIN CLI wrapper over the operator seam
# driver.run_goal_in_sandbox (which composes + runs in the sandbox); onboard adds
# only the goal-string read + the plain-Korean print of the composed nodes +
# evidence location. The live/customer tree is NEVER written (the seam runs the
# composed graph inside the disposable worktree; output_root lives under ~/.brick,
# OUTSIDE the repo). By default the design AI follows the selected execution
# ``--brain``; ``local`` has no text design seam, so it falls back to gemini.
GOAL_SEAM_VERB = "support.operator.driver.run_goal_in_sandbox"
GOAL_APPROVE_SEAM_VERB = "support.operator.onboard.run_goal_approve_entry"
GOAL_APPROVE_ACTIONS = ("forward", "stop")
_GOAL_PROPOSAL_FILENAME = "proposed-building-graph.json"

# The customer's EXECUTION-brain choice for `onboard goal`. ``local`` is the
# in-process read-only smoke adapter (default); ``codex`` / ``claude`` are
# WRITE-CAPABLE observed-write CLI adapters; ``gemini`` is an admitted non-write
# local CLI adapter. The mapping is execution selection only; the design-AI
# callable is selected separately below and injected through ``ai_invoke``.
_BRAIN_ADAPTER_REFS: dict[str, str] = {
    "local": "adapter:local",
    "codex": "adapter:codex-local",
    "claude": "adapter:claude-local",
    "gemini": "adapter:gemini-local",
}

# Design-AI prompt -> text seams. These are injected into driver.run_goal_in_sandbox
# through its existing ai_invoke seam; driver.py / auto_compose.py stay untouched.
_DESIGN_BRAIN_AI_INVOKE: dict[str, Callable[[str], str]] = {
    "gemini": invoke_gemini_text,
    "claude": invoke_claude_text,
    "codex": invoke_codex_text,
}

_DESIGN_BRAIN_PREFLIGHT_ADAPTER_REFS: dict[str, str] = {
    "gemini": "adapter:gemini-api",
    "claude": "adapter:claude-local",
    "codex": "adapter:codex-local",
}


def _brain_to_adapter_ref(brain: str) -> str:
    """Map a ``--brain`` choice to its adapter ref. Unknown brains fall back to
    the read-only ``adapter:local`` (friendly; never raises)."""

    return _BRAIN_ADAPTER_REFS.get(str(brain).strip().lower(), "adapter:local")


def _normalize_design_brain(brain: str, design_brain: str | None = None) -> str:
    """Resolve the design-AI choice for goal composition.

    Unspecified follows ``brain`` except ``local``, which has no text design seam
    and therefore falls back to gemini. Unknown library inputs are friendly and
    also fall back to gemini; the CLI constrains explicit values with argparse.
    """

    explicit = str(design_brain).strip().lower() if design_brain is not None else ""
    candidate = explicit or str(brain).strip().lower()
    if candidate in _DESIGN_BRAIN_AI_INVOKE:
        return candidate
    return "gemini"


def _design_brain_preflight(design_brain: str) -> dict[str, Any]:
    """Friendly design-AI readiness check. Never raises."""

    normalized = _normalize_design_brain(design_brain)
    adapter_ref = _DESIGN_BRAIN_PREFLIGHT_ADAPTER_REFS.get(normalized, "adapter:gemini-api")
    try:
        status = preflight_provider(adapter_ref)
    except Exception as exc:  # noqa: BLE001 -- goal entry must stay friendly
        return {
            "ok": False,
            "design_brain": normalized,
            "adapter_ref": adapter_ref,
            "message_ko": (
                "설계AI 준비 상태를 확인하는 중에 문제가 생겼어요. "
                "잠시 후 다시 시도해 주세요."
            ),
            "error_kind": type(exc).__name__,
        }
    result = dict(status)
    result["design_brain"] = normalized
    result["adapter_ref"] = adapter_ref
    if not result.get("ok"):
        if normalized == "gemini":
            result["message_ko"] = (
                str(result.get("message_ko") or "")
                or "설계AI gemini는 GEMINI_API_KEY (또는 GOOGLE_API_KEY)가 필요해요."
            )
        else:
            result["message_ko"] = (
                str(result.get("message_ko") or "")
                or f"설계AI {normalized} CLI 준비가 필요해요."
            )
    return result


def run_goal_entry(
    goal: str,
    *,
    repo_root: Path | str | None = None,
    output_root: Path | str | None = None,
    brain: str = "local",
    design_brain: str | None = None,
) -> dict[str, Any]:
    """Compose a free-form goal into a building + run it in the W1 sandbox.

    ``brain`` selects the EXECUTION adapter. ``design_brain`` selects the design
    AI callable injected through ``run_goal_in_sandbox(ai_invoke=...)``. When
    ``design_brain`` is omitted, design follows ``brain`` except ``local`` falls
    back to gemini. The engine's write-capability gate is unchanged.

    Returns a structured result dict (never raises on a normal run; a compose /
    key error is captured into ``error_*`` so the CLI prints friendly guidance and
    exits nonzero). The customer's live tree is never written."""

    from brick_protocol.support.operator.driver import run_goal_in_sandbox

    repo = _safe_repo_root(repo_root)
    durable = (
        Path(output_root).resolve()
        if output_root is not None
        else Path.home() / ".brick" / "goal-runs"
    )
    durable.mkdir(parents=True, exist_ok=True)
    normalized_brain = str(brain).strip().lower() or "local"
    adapter_ref = _brain_to_adapter_ref(normalized_brain)
    selected_design_brain = _normalize_design_brain(normalized_brain, design_brain)
    design_preflight = _design_brain_preflight(selected_design_brain)
    design_ai_invoke = _DESIGN_BRAIN_AI_INVOKE[selected_design_brain]
    result: dict[str, Any] = {
        "goal": goal,
        "routed_through": GOAL_SEAM_VERB,
        "brain": normalized_brain,
        "design_brain": selected_design_brain,
        "selected_adapter_ref": adapter_ref,
        "design_brain_preflight": design_preflight,
        "ok": False,
    }
    if not bool(design_preflight.get("ok")):
        result["error_kind"] = "design_brain_preflight_failed"
        result["error_message"] = (
            f"설계AI {selected_design_brain} 준비가 안 됐어요: "
            f"{design_preflight.get('message_ko', '')}"
        )
        return result
    try:
        run = run_goal_in_sandbox(
            goal,
            repo_root=repo,
            output_root=durable,
            ai_invoke=design_ai_invoke,
            selected_adapter_ref=adapter_ref,
            overwrite_existing=True,
        )
    except Exception as exc:  # noqa: BLE001 -- friendly surface: capture, never crash
        result["error_kind"] = type(exc).__name__
        result["error_message"] = str(exc)
        return result
    result["building_id"] = run.building_id
    result["composed_node_ids"] = list(run.composed_node_ids)
    result["isolation_mode"] = run.isolation_mode
    result["frontier_kind"] = run.frontier_kind
    result["evidence_root"] = run.evidence_root
    result["commit_sha"] = run.commit_sha
    result["ok"] = run.frontier_kind == "complete"
    return result


def _render_goal_text(result: dict[str, Any]) -> str:
    """Render the goal-journey result as plain-Korean text for the CLI entry."""

    lines: list[str] = []
    lines.append("=== Brick Protocol: 목표로 빌딩 만들기 ===\n")
    lines.append(f"목표(goal): {result.get('goal', '')}\n")
    if result.get("error_message"):
        lines.append("AI 합성 또는 실행에 실패했어요.")
        lines.append(f"   - 에러 종류: {result.get('error_kind', '')}")
        lines.append(f"   - 에러 내용: {result.get('error_message', '')}")
        lines.append(
            "   - 참고: 설계AI는 기본적으로 --brain을 따라가고, --brain local만 "
            "gemini로 대체돼요. gemini는 GEMINI_API_KEY 또는 GOOGLE_API_KEY가 "
            "필요하고, claude/codex는 로컬 CLI 준비 상태를 확인해요."
        )
        lines.append("")
        lines.append("준비 완료: 아직이요 (위 에러를 확인해 주세요)")
        return "\n".join(lines)
    lines.append("1) AI가 합성한 빌딩(노드)")
    nodes = result.get("composed_node_ids") or []
    if nodes:
        for node_id in nodes:
            lines.append(f"   - {node_id}")
    else:
        lines.append("   (합성된 노드 없음)")
    lines.append("")
    lines.append("2) 격리 실행(작업 트리는 건드리지 않았어요)")
    lines.append(f"   - building_id: {result.get('building_id', '')}")
    lines.append(
        f"   - 실행 브레인(brain): {result.get('brain', '')} "
        f"({result.get('selected_adapter_ref', '')})"
    )
    lines.append(f"   - 설계AI(design-brain): {result.get('design_brain', '')}")
    lines.append(f"   - 격리 모드: {result.get('isolation_mode', '')}")
    lines.append(f"   - frontier: {result.get('frontier_kind', '')}")
    lines.append(f"   - 통과 경로(seam): {result.get('routed_through', '')}")
    lines.append("")
    lines.append("3) 증거 저장 위치")
    lines.append(f"   - {result.get('evidence_root', '')}")
    if result.get("commit_sha"):
        lines.append(f"   - 완료 커밋: {result.get('commit_sha', '')}")
    lines.append("")
    lines.append(
        f"준비 완료: {'예 ✅' if result.get('ok') else '아직이요 (frontier가 complete가 아니에요)'}"
    )
    return "\n".join(lines)


def render_proposal_for_human(proposal_ref: Any) -> str:
    """Render a frozen proposal snapshot as a plain-Korean pre-run preview.

    This is read-side support projection only. It reads a caller/COO-declared
    composed plan and names what will run; it does not approve, choose Movement,
    or judge quality.
    """

    plan, _proposal_path = _load_goal_proposal(proposal_ref)
    return _render_goal_proposal_plan(plan)


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
            "isolation_mode": sandbox_result.isolation_mode,
            "isolation_reason": sandbox_result.isolation_reason,
            "commit_sha": sandbox_result.commit_sha,
            "worktree_path": sandbox_result.worktree_path,
            "worktree_disposed": sandbox_result.worktree_disposed,
            "proposal_root_reused": run_overwrite_existing and not overwrite_existing,
        }
    )
    return result


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


def run_approve_entry(
    building_ref: str | Path,
    *,
    action: str = "forward",
    author_ref: str = "coo:smith",
    budget_increment: int | None = None,
    reroute_target_ref: str | None = None,
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
    action_text = str(action).strip().lower()
    author_text = str(author_ref).strip()
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

    building_path = Path(building_text).expanduser()
    if building_path.is_absolute():
        building_root = building_path.resolve()
    else:
        durable = (
            Path(output_root).expanduser().resolve()
            if output_root is not None
            else Path.home() / ".brick" / "goal-runs"
        )
        building_root = (durable / building_path).resolve()
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
    if frontier_kind_before not in {"link_paused", "human_review_waiting"}:
        result.update(
            {
                "error_kind": "not_approval_hold",
                "error_message": "승인 대상 hold 상태가 아니에요.",
                "message_ko": "승인 대상 hold가 아니어서 disposition을 쓰지 않았어요.",
            }
        )
        return result

    latest_lifecycle = frontier_before.get("latest_transition_lifecycle") or {}
    if not isinstance(latest_lifecycle, dict):
        latest_lifecycle = {}
    pending_target_ref = str(
        latest_lifecycle.get("transition_lifecycle_pending_target_ref") or ""
    )
    disposition_pending_target_ref = (
        reroute_target_text if action_text == "reroute" else pending_target_ref
    )
    paused_at_ref = str(
        latest_lifecycle.get("transition_lifecycle_paused_at_ref") or ""
    )
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
    if parsed_budget is not None:
        row["transition_lifecycle_budget_increment"] = parsed_budget
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
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
        )
        frontier_after = dict(observe_building_frontier(building_root, repo_root=repo))
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
    # ``onboard goal "<text>"``: the H3b CUSTOMER ENTRY. Reads a free-form goal,
    # composes it into a building via the design AI (default: live gemini), runs
    # it in the W1 disposable worktree sandbox, and prints the composed nodes +
    # the evidence location in plain Korean. The live tree is NEVER written.
    if args_list[:1] == ["goal"]:
        goal_parser = argparse.ArgumentParser(
            prog="onboard goal",
            description=(
                "Customer entry: a free-form goal -> the design AI composes a "
                "building -> it runs in the W1 disposable worktree sandbox -> "
                "evidence. The live tree is never written. The design AI follows "
                "--brain by default; --brain local falls back to gemini."
            ),
        )
        goal_parser.add_argument("goal", help="The free-form goal text to build.")
        goal_parser.add_argument(
            "--repo",
            default=None,
            help="Repo root override (default: computed from this file's location).",
        )
        goal_parser.add_argument(
            "--output-root",
            default=None,
            help="Durable evidence root (default: ~/.brick/goal-runs, OUTSIDE the repo).",
        )
        goal_parser.add_argument(
            "--brain",
            choices=("local", "codex", "claude", "gemini"),
            default="local",
            help=(
                "Execution brain: 'local' (default, in-process read-only smoke) or "
                "the local CLI brains 'codex' (adapter:codex-local), 'claude' "
                "(adapter:claude-local), or 'gemini' (adapter:gemini-local). Every "
                "brain runs inside the W1 disposable worktree sandbox; the live "
                "tree is never written. A write-needing build on a read-only brain "
                "is rejected by the engine."
            ),
        )
        goal_parser.add_argument(
            "--design-brain",
            choices=("gemini", "claude", "codex"),
            default=None,
            help=(
                "Design AI for composing the Building. Default: follow --brain; "
                "--brain local falls back to gemini. claude/codex use local CLI "
                "preflight; gemini needs GEMINI_API_KEY or GOOGLE_API_KEY."
            ),
        )
        goal_args = goal_parser.parse_args(args_list[1:])
        goal_result = run_goal_entry(
            goal_args.goal,
            repo_root=goal_args.repo,
            output_root=goal_args.output_root,
            brain=goal_args.brain,
            design_brain=goal_args.design_brain,
        )
        sys.stdout.write(_render_goal_text(goal_result))
        sys.stdout.write("\n")
        return 0 if goal_result.get("ok") else 1
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
            default="forward",
            help="Disposition action. raise requires --budget-increment.",
        )
        approve_parser.add_argument(
            "--author",
            default="coo:smith",
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
            "adapter (adapter:codex-local / adapter:claude-local) when preflight "
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
    parser.add_argument(
        "--design-brain",
        choices=("gemini", "claude", "codex"),
        default=None,
        help=(
            "Design AI readiness to preflight for the follow-up 'onboard goal' "
            "handoff. Default: follow host; local falls back to gemini."
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
        design_brain=args.design_brain,
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
    "DOCTOR_SYMPTOM_PRESCRIPTIONS_KO",
    "_DESIGN_BRAIN_AI_INVOKE",
    "GOAL_APPROVE_ACTIONS",
    "GOAL_APPROVE_SEAM_VERB",
    "GOAL_SEAM_VERB",
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
    "run_goal_entry",
    "run_onboard",
    "render_proposal_for_human",
    "run_recording_setup",
]


if __name__ == "__main__":
    raise SystemExit(main())
