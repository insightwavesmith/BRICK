#!/usr/bin/env python3
"""Rule-pinning checker for the graph-draft drafter (Building #15).

Drives ``draft_graph_declaration`` IN-PROCESS over fixed answer fixtures and
asserts the rule-source teeth ①~⑩ hold. This checker is support evidence only:
it is not source truth, success judgment, quality judgment, or Movement
authority. It NEVER writes files — drafts are composed in memory only
(``write_draft_declaration`` is not called), so there is no fixture home dispute
and no live-inbox write.

Probes:
  P1  rule ①②⑧  walker-adjacent+complex → fugu work + deep-design + 10800s
  P2  no over-escalation  simple-doc → codex work, no deep-design, no 10800
  P4  rule ④  every fan block is followed by a convergence node
  P3  rule ⑩  both fixture drafts return the COMPOSED OK literal
  P5  Rule 3  the drafter/CLI draft surfaces reach no launch seam (text scan)
  P6  rule ⑤  bare-directory write_scope entries normalize to explicit globs

P4 runs before P3 so mutation M3 (deleting the convergence emission) hits the
P4 literal first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
for _path in (str(_REPO_ROOT), str(_IMPORT_IDENTITY_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from brick_protocol.support.operator.graph_draft import draft_graph_declaration

PROOF_LIMIT = "support evidence only; not source truth / success / quality / Movement"

# --- fixtures -------------------------------------------------------------
WALKER_COMPLEX_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "yes",
    "size": "medium",
    "splittable": "no",
    "file_conflict": "no",
    "failure_cost": "high",
    "human_approval": "no",
    "termination_shape": "checker-pinned",
    "difficulty": "complex",
}
SIMPLE_DOC_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "no",
    "size": "small",
    "splittable": "no",
    "file_conflict": "no",
    "failure_cost": "low",
    "human_approval": "no",
    "termination_shape": "doc",
    "difficulty": "simple",
}
HARD_TASK = "walker 인접 엔진 작업 — 심층 구현."
SIMPLE_TASK = "간단한 문서 한 줄 정리."

# Rule 3 launch-seam tokens that must NOT appear in the draft surfaces.
_LAUNCH_SEAM_TOKENS = (
    "run_customer_building_in_sandbox",
    "run_goal_approve_entry",
    "operator.driver",
    "operator import driver",
    "fire(",
    '"action": "forward"',
    "'action': 'forward'",
)


def _nodes(result: Any) -> list[Mapping[str, Any]]:
    return list(result.declaration["nodes"])


def _first_kind(nodes: Sequence[Mapping[str, Any]], kind: str) -> Mapping[str, Any] | None:
    for node in nodes:
        if node.get("kind") == kind:
            return node
    return None


def _has_kind(nodes: Sequence[Mapping[str, Any]], kind: str) -> bool:
    return _first_kind(nodes, kind) is not None


def _is_convergence(node: Mapping[str, Any]) -> bool:
    return "fan" not in node and node.get("kind") in {
        "closure",
        "work",
        "review",
        "inspect",
    }


def _violations(repo: Path) -> list[str]:
    out: list[str] = []
    hard = draft_graph_declaration(
        HARD_TASK,
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    simple = draft_graph_declaration(
        SIMPLE_TASK,
        SIMPLE_DOC_ANSWERS,
        repo_root=repo,
        allowed_paths=("support/operator/**",),
    )
    hard_nodes = _nodes(hard)
    simple_nodes = _nodes(simple)

    # P1 — rule ①②⑧: walker-adjacent+complex → fugu work + deep-design + 10800s.
    hard_work = _first_kind(hard_nodes, "work")
    if (
        hard_work is None
        or hard_work.get("adapter_ref") != "adapter:codex-fugu-local"
        or not _has_kind(hard_nodes, "deep-design")
        or hard.declaration.get("adapter_timeout_seconds") != 10800
    ):
        out.append(
            "graph-draft RED: walker-adjacent answers drafted a codex-solo work node (rule 1/2/8 violated)"
        )

    # P6 — rule ⑤: bare directory write_scope entries normalize to explicit globs.
    if hard_work is None or hard_work.get("write_scope", {}).get("allowed_paths") != ["support/**"]:
        out.append(
            "graph-draft RED: bare-directory write_scope was not normalized to an explicit glob"
        )

    # P2 — no over-escalation: simple-doc → codex work, no deep-design, no 10800.
    simple_work = _first_kind(simple_nodes, "work")
    if (
        simple_work is None
        or simple_work.get("adapter_ref") != "adapter:codex-local"
        or _has_kind(simple_nodes, "deep-design")
        or simple.declaration.get("adapter_timeout_seconds") == 10800
    ):
        out.append(
            "graph-draft RED: simple-doc answers escalated casting without a declared risk basis"
        )

    # P4 — rule ④: every fan block is followed by exactly one convergence node.
    # (Runs before P3 so mutation M3 hits this literal first.)
    for nodes in (hard_nodes, simple_nodes):
        for index, node in enumerate(nodes):
            if "fan" in node:
                following = nodes[index + 1] if index + 1 < len(nodes) else None
                if following is None or not _is_convergence(following):
                    out.append(
                        "graph-draft RED: fan block without following convergence node in draft"
                    )
                    break

    # P3 — rule ⑩: both fixture drafts return the COMPOSED OK literal.
    for res in (hard, simple):
        if not str(res.precheck.get("literal", "")).startswith("COMPOSED OK"):
            out.append(
                "graph-draft RED: draft precheck did not return the COMPOSED OK literal"
            )

    # P5 — Rule 3 structural absence: the draft surfaces reach no launch seam.
    surface_texts: list[str] = []
    module_src = (repo / "support/operator/graph_draft.py").read_text(encoding="utf-8")
    surface_texts.append(module_src)
    cli_src = (repo / "support/operator/cli.py").read_text(encoding="utf-8")
    draft_body = _extract_draft_bodies(cli_src)
    surface_texts.append(draft_body)
    reached_seam = False
    for text in surface_texts:
        for token in _LAUNCH_SEAM_TOKENS:
            if token in text:
                reached_seam = True
                break
        if reached_seam:
            break
    # The drafted declaration must carry no forward action.
    for res in (hard, simple):
        action = str(res.declaration.get("action", "")).strip().lower()
        if action == "forward":
            reached_seam = True
    if reached_seam:
        out.append("graph-draft RED: draft surface reaches a launch seam (Rule 3)")

    return out


def _extract_draft_bodies(cli_src: str) -> str:
    """Return only the draft-related CLI function bodies for the Rule 3 scan.

    The rest of cli.py legitimately imports the launch driver; we scan only the
    ``_run_draft`` / ``_cmd_draft`` / ``_render_draft`` bodies so the check
    fires exactly when a launch seam is wired into the draft path.
    """

    lines = cli_src.splitlines()
    body: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("def "):
            capture = line.startswith(
                ("def _run_draft", "def _cmd_draft", "def _render_draft")
            )
        if capture:
            body.append(line)
    return "\n".join(body)


def run(repo: Path) -> list[str]:
    violations = _violations(repo)
    return violations


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence rule-pinning checker for the graph-draft drafter."
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    violations = run(repo)
    if violations:
        print("graph_draft_rules rejected evidence:", file=sys.stderr)
        for line in violations:
            print(f"- {line}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    print("graph_draft_rules passed: 6 probe(s)")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
