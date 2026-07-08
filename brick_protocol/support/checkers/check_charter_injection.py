#!/usr/bin/env python3
"""CHARTER-INJECT (0618): every role's runtime work packet carries the project charter.

A BRICK Building runs inside a project vessel (``project/<id>/``). The vessel's
README is its charter (헌장 — why the project exists, what it builds, what it
must keep). Before this wiring the work/qa/closure Agent received its packet
with the charter injected 0% of the time: it judged the work blind, and the
evidence never recorded which charter it saw.

This checker asserts the INJECTION (the soft seam the audit found open), not
enforcement. For a declared project vessel, ``render_agent_instruction_packet``
must, for EVERY role:

  1. carry a non-empty ``charter_resources`` entry whose body is the project's
     own README.md text;
  2. stamp the top-level ``charter_ref`` / ``project_ref`` evidence fields
     (mirrored next to ``agent_object_ref``) so any sink records the charter
     the Agent saw;
  3. reach the built provider prompt (codex AND claude) intact — the charter
     rides the ``agent_instruction_packet`` carrier through ``_build_prompt``.

It also asserts the honesty boundary of the seam:

  4. NO project_ref (a ref-less / default-root building) injects no charter and
     stamps no ``charter_ref`` — and never crashes;
  5. an undeclared / charterless project degrades the same way (loudly nothing,
     no crash) — a missing charter is RED at the project_declaration checker,
     not a Building-run crash;
  6. injection is ADD-ONLY: the prompt/skill/discipline/hook/tool-policy
     resources are byte-identical whether or not a charter is present.

Anti-tautology: the probe synthesizes a project vessel (README + project.json)
in a temp tree (``brick_protocol/agent/`` symlinked to the real axis so role resolution is
real) and drives the REAL renderer. The mutation-RED witness: if the injection
line in ``_charter_resources`` is disabled (made to always return ``[]``), this
checker's positive assertion (1) fails and ``main()`` returns non-zero, so
``--all`` EXITs non-zero.

Support evidence only: proves the charter is PRESENT in the packet/prompt and
the evidence field is stamped. It does NOT prove the charter text is truthful,
that the Agent obeyed it, nor source truth / success / quality / Movement
authority.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

# Roles spanning the work/qa/closure lanes the audit names. The charter must
# reach EVERY one (work-only injection was the explicit non-goal).
PROBE_ROLES = ("dev", "qa", "qa-lead", "inspector", "coo", "cto-lead")

PROBE_VESSEL_ID = "charter-inject-probe"
PROBE_PROJECT_REF = f"project:{PROBE_VESSEL_ID}"
PROBE_CHARTER = (
    "# Charter inject probe\n\n"
    "이 프로젝트는 charter 주입 probe 전용 헌장이다.\n"
    "WHY: prove the work packet carries the project direction.\n"
    "MUST-KEEP: CHARTER-INJECT-PROBE-SENTINEL must reach every role.\n"
)
# A unique sentinel from the README body — its presence in the packet/prompt is
# the load-bearing proof the actual charter TEXT (not just a ref) was injected.
PROBE_CHARTER_SENTINEL = "CHARTER-INJECT-PROBE-SENTINEL"
PROBE_DECLARATION = {
    "project_ref": PROBE_PROJECT_REF,
    "label": "charter inject probe project",
    "direction": "prove the charter reaches every role packet",
    "done_means": "charter_resources present for every role",
    "out_of_scope": "everything real",
    "managers": ["smith"],
    "declared_by": "smith",
    "declared_at": "2026-06-18T00:00:00+00:00",
    "charter_ref": f"project/{PROBE_VESSEL_ID}/README.md",
}

_BYTE_IDENTICAL_KEYS = (
    "prompt_resources",
    "skill_resources",
    "hook_resources",
    "tool_policy_resources",
    "discipline_resources",
    "adapter_refs",
)


def _ensure_import_path(repo: Path) -> None:
    ensure_checker_imports(repo)


def _make_probe_repo(real_repo: Path, tmp_root: Path) -> Path:
    """A temp repo whose ``brick_protocol/agent/`` axis is the real one (real role resolution)
    and whose ``project/<probe>/`` is a synthetic declared vessel. Writes only
    into the temp tree — never the real ``project/``."""

    probe_repo = tmp_root / "repo"
    probe_repo.mkdir()
    # Symlink the real Agent axis so role objects/prompts/skills/disciplines/
    # hooks/tool_policies resolve for real; the renderer reads only repo/brick_protocol/agent.
    (probe_repo / "brick_protocol").mkdir(parents=True, exist_ok=True)
    os.symlink(real_repo / "brick_protocol" / "agent", probe_repo / "brick_protocol" / "agent", target_is_directory=True)
    vessel = probe_repo / "project" / PROBE_VESSEL_ID
    vessel.mkdir(parents=True)
    (vessel / "README.md").write_text(PROBE_CHARTER, encoding="utf-8")
    (vessel / "project.json").write_text(
        json.dumps(PROBE_DECLARATION, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return probe_repo


def run_fire_probes(repo: Path) -> list[str]:
    """Drive the REAL renderer over a synthetic vessel. Returns failure
    messages (empty = the injection seam behaved)."""

    from brick_protocol.support.connection.agent_resources import (
        render_agent_instruction_packet,
    )
    from brick_protocol.support.connection.agent_adapter import (
        AgentAdapterRequest,
        _LOCAL_CLI_SPECS,
    )
    from brick_protocol.support.connection.adapter_constants import (
        ADAPTER_CODEX_LOCAL,
        ADAPTER_CLAUDE_LOCAL,
    )
    from brick_protocol.support.connection.adapter_grant_policy import (
        _build_prompt,
    )

    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="charter-inject-fire-") as tmp:
        probe_repo = _make_probe_repo(repo, Path(tmp))

        for role in PROBE_ROLES:
            # (1)+(2) declared vessel -> charter injected for EVERY role.
            try:
                packet = render_agent_instruction_packet(
                    role, repo_root=probe_repo, project_ref=PROBE_PROJECT_REF
                )
            except Exception as exc:  # noqa: BLE001 — a crash here IS the finding
                failures.append(f"role {role}: declared-vessel render crashed: {exc!r}")
                continue
            charters = packet.get("charter_resources", [])
            if not charters:
                failures.append(
                    f"role {role}: charter_resources EMPTY for a declared project vessel "
                    "(charter NOT injected — the 0% gap the audit found)"
                )
                continue
            body = str(charters[0].get("body", ""))
            if PROBE_CHARTER_SENTINEL not in body:
                failures.append(
                    f"role {role}: injected charter body is missing the README sentinel "
                    "(a ref without the charter TEXT is not an injection)"
                )
            if packet.get("charter_ref") != PROBE_DECLARATION["charter_ref"]:
                failures.append(
                    f"role {role}: top-level charter_ref evidence field not stamped "
                    f"(got {packet.get('charter_ref')!r})"
                )
            if packet.get("project_ref") != PROBE_PROJECT_REF:
                failures.append(
                    f"role {role}: top-level project_ref evidence field not stamped "
                    f"(got {packet.get('project_ref')!r})"
                )

        # (3) the charter reaches the actual built provider prompt (both hosts).
        dev_packet = render_agent_instruction_packet(
            "dev", repo_root=probe_repo, project_ref=PROBE_PROJECT_REF
        )
        for adapter in (ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL):
            request = AgentAdapterRequest(
                building_id="charter-inject-probe-1",
                agent_object_ref="agent-object:dev",
                adapter_ref=adapter,
                callable_ref="",
                brick_instance_ref="brick-001",
                next_brick_instance_ref="brick-002",
                work_statement="charter-inject probe",
                agent_instruction_packet=dev_packet,
            )
            prompt = _build_prompt(request, _LOCAL_CLI_SPECS[adapter])
            if PROBE_CHARTER_SENTINEL not in prompt:
                failures.append(
                    f"adapter {adapter}: built provider prompt does not carry the charter "
                    "(charter never reaches the host LLM)"
                )

        # (4) NO project_ref -> no charter, no charter_ref, no crash.
        try:
            no_ref = render_agent_instruction_packet("dev", repo_root=probe_repo)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"ref-less render crashed (must degrade, not crash): {exc!r}")
            no_ref = {}
        if no_ref.get("charter_resources"):
            failures.append(
                "ref-less building injected a charter (charter must be empty without a "
                "project_ref)"
            )
        if "charter_ref" in no_ref:
            failures.append(
                "ref-less building stamped a charter_ref evidence field (must be omitted "
                "when no charter was injected)"
            )

        # (5) undeclared / charterless project -> degrade, no crash.
        try:
            undeclared = render_agent_instruction_packet(
                "dev", repo_root=probe_repo, project_ref="project:does-not-exist"
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"undeclared-project render crashed (must degrade, not crash): {exc!r}"
            )
            undeclared = {}
        if undeclared.get("charter_resources"):
            failures.append(
                "undeclared project injected a charter (must degrade to no charter)"
            )

        # (6) injection is ADD-ONLY: the other resources are byte-identical
        # whether or not a charter is present.
        base = render_agent_instruction_packet("dev", repo_root=probe_repo)
        with_charter = render_agent_instruction_packet(
            "dev", repo_root=probe_repo, project_ref=PROBE_PROJECT_REF
        )
        for key in _BYTE_IDENTICAL_KEYS:
            if json.dumps(base.get(key), sort_keys=True) != json.dumps(
                with_charter.get(key), sort_keys=True
            ):
                failures.append(
                    f"charter injection altered {key!r} (injection must be add-only)"
                )

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: a declared project vessel's README charter is "
            "injected into EVERY role's runtime instruction packet (work/qa/closure "
            "alike), reaches the built codex+claude prompt, stamps the charter_ref "
            "evidence field, and degrades gracefully (no charter / no crash) without a "
            "declared project. Does not prove charter truthfulness, Agent obedience, "
            "source truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    _ensure_import_path(repo)

    try:
        failures = run_fire_probes(repo)
    except (OSError, ValueError) as exc:
        print(f"charter injection rejected: {exc}")
        return 1

    if failures:
        print("charter injection rejected (work packet does not carry the project charter):")
        for failure in failures:
            print(f"- {failure}")
        print(
            "proof limit: this checker proves the charter is injected into the packet/"
            "prompt and the evidence field is stamped; it does not prove the charter is "
            "truthful, that the Agent obeyed it, nor source truth, success, quality, or "
            "Movement authority."
        )
        print(
            "prescription: render_agent_instruction_packet must inject the project "
            "README charter (brick_protocol/support/connection/agent_resources._charter_resources) for "
            "every role; the call sites (brick_protocol/support/operator/run.py, walker_kernel.py) must "
            "derive the vessel project_ref from the building_root."
        )
        return 1

    print(
        "charter injection passed: the declared probe vessel's README charter is injected "
        f"into all {len(PROBE_ROLES)} probed role packets (work/qa/closure lanes), reaches "
        "the built codex and claude prompts, stamps the charter_ref + project_ref evidence "
        "fields, and degrades gracefully (ref-less + undeclared project -> no charter, no "
        "crash; injection is add-only / byte-identical for the other resources)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
