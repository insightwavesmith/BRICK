"""Weight -> graph-decl draft support module (Building #15 — graph-draft-0706n).

Turn an operator's ``(task text + 8 sizing answers)`` into a *launch-ready
candidate* graph-decl declaration plus a per-row rationale, and prove the draft
is assembly-valid by lowering it through the EXISTING
``assemble_graph_declaration`` in memory and returning the literal
``COMPOSED OK <building_id>``.

This is support evidence only. It is not source truth, success judgment,
quality judgment, or Movement authority. Per Rule 3 (자동발사 금지) this module
has NO import path to the launch seams: it never imports the launch driver, the
onboard entry module, or the walker modules; it never calls the sandbox-run or
goal-approve launch entrypoints; and it never emits a forward action — a drafted
declaration carries no ``action`` key, so the assemble default (``stop``)
governs. The draft is a candidate; confirming and launching it is the
operator's job.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

# The ONLY operator-surface import: the existing assembler used for in-memory
# validation (assembly.py:841). Rule "신규 조립기 금지" — drafts validate through
# this, never through a new assembler. The launch driver, the onboard entry
# module, and the walker modules are deliberately NOT imported here (checker +
# profile pin the absence).
from brick_protocol.support.operator.assembly import assemble_graph_declaration
from brick_protocol.brick.spec import derived_worktree_write_scope

__all__ = [
    "GraphDraftResult",
    "draft_graph_declaration",
    "write_draft_declaration",
]

PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN: tuple[str, ...] = (
    "provider reliability",
    "future Building correctness",
    "semantic quality of the drafted graph for a real task",
    "Movement outcome of the drafted Building",
)

# ---------------------------------------------------------------------------
# H1 casting table — one dict per casting; every row appended to ``rows``
# becomes a rationale.md line. (decision_ledger #6/#9; model-lane discipline.)
# ---------------------------------------------------------------------------
FUGU = {
    "adapter_ref": "adapter:codex-fugu-local",
    "model_ref": "model:sakana:fugu-ultra",
    "reasoning_effort_ref": "effort:xhigh",
}
FABLE5 = {
    "adapter_ref": "adapter:claude-local",
    "model_ref": "model:claude:claude-fable-5",
    "reasoning_effort_ref": "effort:xhigh",
}
CLAUDE_INHERIT_XHIGH = {
    "adapter_ref": "adapter:claude-local",
    "reasoning_effort_ref": "effort:xhigh",
}
CODEX = {"adapter_ref": "adapter:codex-local"}
GEMINI_REVIEW = {"adapter_ref": "adapter:gemini-local"}

DEEP_TIMEOUT_SECONDS = 10800
ISOLATION_ONCE_SENTENCE = "격리 --all은 /tmp 로그로 1회만."
NO_COMMIT_SENTENCE = "git commit 금지."

# ---------------------------------------------------------------------------
# Sizing-question contract (decision_ledger #2/#3). All 8 required; fail-closed
# on a missing/unknown answer (guessing would silently mis-cast risk).
# ---------------------------------------------------------------------------
SIZING_QUESTION_IDS: tuple[str, ...] = (
    "walker_adjacent",
    "size",
    "splittable",
    "file_conflict",
    "failure_cost",
    "human_approval",
    "termination_shape",
    "difficulty",
)
SIZING_ANSWER_ENUMS: Mapping[str, tuple[str, ...]] = {
    "walker_adjacent": ("yes", "no"),
    "size": ("small", "medium", "large"),
    "splittable": ("yes", "no"),
    "file_conflict": ("yes", "no"),
    "failure_cost": ("low", "high"),
    "human_approval": ("yes", "no"),
    "termination_shape": ("checker-pinned", "evidence-only", "doc"),
    "difficulty": ("simple", "honest", "medium", "complex", "entangled"),
}
_HARD_DIFFICULTIES = frozenset({"complex", "entangled"})

# decision_ledger #4 — derived escalation flags 2 (계약/게이트 어휘) and 4 (재발주).
# Explicit answer wins; else keyword scan of the task text.
_CONTRACT_VOCAB_RE = re.compile(
    r"게이트|gate|link-gate|계약|contract|return_shape|required_return", re.IGNORECASE
)
_REORDER_RE = re.compile(r"재발주|reorder|re-?order|재시도|reissue", re.IGNORECASE)

# H2 marker comment — mutation M3 deletes this line; probe P4 fires.
_RULE4_FAN_CONVERGENCE = "RULE4-FAN-CONVERGENCE"

# ---------------------------------------------------------------------------
# Work-statement scaffold fragments (rule ⑦ L1/L4, rule ⑧, rule ㉑ termination).
# ---------------------------------------------------------------------------
DEEP_DESIGN_STMT = (
    "심층 설계(열린 결정 반출 금지): task 계약 전문을 정독하고 초안의 모듈 거처·"
    "시그니처·8답→모양/캐스팅 매핑·CLI 배선·체커/변이를 결정표로 CLOSE 하라. "
    "미정 지점은 안전 기본값을 골라 decision_ledger에 기록하라 — 위로 올리지 마라. "
    "per_deliverable_plan·decision_ledger·hunk_sketches·mutation_designs·"
    "forbidden_drift 전부 반환."
)
REVIEW_STMT = "경량 리뷰(관찰만): 변경 범위·회귀 위험을 훑고 관찰만 반환. 판정 금지."
CODE_QA_STMT = (
    "공격 QA(관찰만): 규칙 결정표의 공허 가능성·자동발사 도달 경로·회귀를 사냥하고 "
    "전 관찰을 file:line으로 반환. 판정 금지."
)
EVIDENCE_QA_STMT = (
    "증거형태 QA(관찰만): Deliverables 번호별 증명 원문·리터럴 프로브 원문·변이 rc=1 검사. 판정 금지."
)
AXIS_QA_STMT = (
    "축 공격 QA(관찰만): Brick/Agent/Link 경계 혼입·계약 어휘 오용을 사냥하고 관찰만 반환. 판정 금지."
)
CLOSURE_STMT = (
    "종합: Deliverables 번호별 crosscheck, QA 관찰 종합, decision_ledger 일치 관찰, "
    "미해결은 transition_concern_evidence로. 판정 금지."
)

_TERMINATION_DELIVERABLE_LINES: Mapping[str, str] = {
    "checker-pinned": "D<n>: 체커 핀 + 변이-RED 2종+.",
    "evidence-only": "D<n>: 리터럴 프로브 원문 인용 증거.",
    "doc": "D<n>: 문서 산출물.",
}
_TERMINATION_PROOF_LINES: Mapping[str, str] = {
    "checker-pinned": "신설 체커 rc=0 + 변이 rc=1 리터럴.",
    "evidence-only": "리터럴 프로브 원문 인용.",
    "doc": "문서 완성 확인.",
}


@dataclass(frozen=True)
class GraphDraftResult:
    """One drafted graph-decl candidate plus its rationale and precheck.

    Support evidence only — no verdict, Movement, or route field lives here.
    """

    declaration: Mapping[str, Any]
    rationale_rows: tuple[Mapping[str, str], ...]
    sizing_answers: Mapping[str, str]
    precheck: Mapping[str, Any]
    proof_limits: tuple[str, ...] = PROOF_LIMITS
    not_proven: tuple[str, ...] = NOT_PROVEN


# ---------------------------------------------------------------------------
# Answer normalization (fail-closed).
# ---------------------------------------------------------------------------
def _normalize_answers(answers: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(answers, Mapping):
        raise TypeError("sizing answers must be a mapping keyed by question id")
    missing = [qid for qid in SIZING_QUESTION_IDS if qid not in answers]
    if missing:
        raise ValueError(
            "sizing answers missing required question id(s): " + ", ".join(missing)
        )
    normalized: dict[str, str] = {}
    for qid in SIZING_QUESTION_IDS:
        raw = answers[qid]
        text = str(raw).strip().lower()
        allowed = SIZING_ANSWER_ENUMS[qid]
        if text not in allowed:
            raise ValueError(
                f"sizing answer {qid}={raw!r} is not one of {list(allowed)}"
            )
        normalized[qid] = text
    return normalized


def _contract_vocab(answers: Mapping[str, Any], task_text: str, explicit: Any) -> bool:
    if explicit is not None:
        return bool(explicit)
    return bool(_CONTRACT_VOCAB_RE.search(task_text or ""))


def _reorder(answers: Mapping[str, Any], task_text: str, explicit: Any) -> bool:
    if explicit is not None:
        return bool(explicit)
    return bool(_REORDER_RE.search(task_text or ""))


# ---------------------------------------------------------------------------
# H1 — rule ①: risk-proportional escalation (4종).
# ---------------------------------------------------------------------------
def _escalated(
    answers: Mapping[str, str],
    task_text: str,
    rows: list[dict[str, str]],
    *,
    contract_vocab: bool,
    reorder: bool,
) -> bool:
    hits: list[str] = []
    if answers["walker_adjacent"] == "yes":
        hits.append("rule1-walker-adjacent")
    if contract_vocab:
        hits.append("rule1-contract-gate-vocab")
    if answers["failure_cost"] == "high":
        hits.append("rule1-costly-one-shot")
    if reorder:
        hits.append("rule1-reissue")
    for h in hits:
        rows.append(
            {
                "rule_id": h,
                "decision": "risk-proportional escalation",
                "basis": "answers/task-text",
            }
        )
    return bool(hits)


# ---------------------------------------------------------------------------
# Rule ⑤ — write_scope 승계 2법칙: allowed non-empty + forbidden key present,
# glob 전수, bare-dir 금지. (brick/spec.py:257-273; 0612 write_scope 문법 함정.)
# ---------------------------------------------------------------------------
def _normalize_scope_entry(entry: str, repo_root: Path, rows: list[dict[str, str]], *, field_name: str) -> str:
    text = entry.strip().replace("\\", "/")
    if not text or text == "." or any(ch in text for ch in "*?[]"):
        return text
    stem = text.rstrip("/")
    if text.endswith("/") or (repo_root / stem).is_dir():
        fixed = stem + "/**"
        rows.append(
            {
                "rule_id": "rule5-bare-dir-normalized",
                "decision": f"{field_name} {entry!r} → {fixed!r}",
                "basis": "brick/spec.py:264 rejects a bare-dir write entry",
            }
        )
        return fixed
    return text


def _dedupe_texts(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _normalize_write_scope(
    allowed_paths: Sequence[str],
    forbidden_paths: Sequence[str],
    rows: list[dict[str, str]],
    *,
    repo_root: Path,
) -> dict[str, list[str]]:
    allowed = [str(p).strip() for p in allowed_paths if str(p).strip()]
    if not allowed:
        derived = derived_worktree_write_scope()
        rows.append(
            {
                "rule_id": "rule5-write-scope-default",
                "decision": "allowed_paths empty → derived_worktree_write_scope",
                "basis": "scope is broad — narrow it before launch",
            }
        )
        return {
            "allowed_paths": list(derived["allowed_paths"]),
            "forbidden_paths": list(derived["forbidden_paths"]),
        }
    normalized_allowed: list[str] = []
    for entry in allowed:
        text = entry.replace("\\", "/")
        normalized_allowed.append(
            _normalize_scope_entry(text, repo_root, rows, field_name="allowed_paths")
        )
    forbidden = [
        _normalize_scope_entry(str(p), repo_root, rows, field_name="forbidden_paths")
        for p in forbidden_paths
        if str(p).strip()
    ]
    forbidden = _dedupe_texts([".git/**", *forbidden])
    return {"allowed_paths": normalized_allowed, "forbidden_paths": forbidden}


# ---------------------------------------------------------------------------
# Rule ⑥ — source_facts 실존 선검증: test -f AND git ls-files (read-only git).
# Raises BEFORE any file is written.
# ---------------------------------------------------------------------------
def _verify_source_facts(
    source_facts: Sequence[str],
    repo_root: Path,
    rows: list[dict[str, str]],
) -> tuple[str, ...]:
    verified: list[str] = []
    for raw in source_facts:
        rel = str(raw).strip()
        if not rel:
            continue
        candidate = (repo_root / rel)
        if not candidate.is_file():
            raise ValueError(
                f"source_fact {rel!r} does not exist as a file under {repo_root} "
                "(rule ⑥ test -f)"
            )
        proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=str(repo_root),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise ValueError(
                f"source_fact {rel!r} is not tracked by git ls-files (rule ⑥)"
            )
        rows.append(
            {
                "rule_id": "rule6-source-fact-verified",
                "decision": f"{rel} exists + tracked",
                "basis": "test -f + git ls-files --error-unmatch",
            }
        )
        verified.append(rel)
    return tuple(verified)


# ---------------------------------------------------------------------------
# Rule ⑦/⑧/㉑ — work_statement scaffold: guarantee ## Deliverables + D1: +
# 종료선 so L1/L4 pass; deep-tier appends the isolation/no-commit sentences.
# ---------------------------------------------------------------------------
def _scaffold_work_statement(
    task_statement: str,
    *,
    deep_tier: bool,
    termination_shape: str,
) -> str:
    body = (task_statement or "").rstrip()
    parts = [body] if body else []
    if "## Deliverables" not in body:
        deliverable = _TERMINATION_DELIVERABLE_LINES.get(
            termination_shape, "D1: 산출물."
        )
        d1 = deliverable.replace("D<n>", "D1")
        proof = _TERMINATION_PROOF_LINES.get(termination_shape, "")
        block = ["## Deliverables", d1]
        if proof:
            block.append(proof)
        parts.append("\n".join(block))
    if not re.search(r"(?im)^\s*(?:#{1,6}\s*)?종료선\s*:", body):
        parts.append("종료선: 선언 Deliverables 충족이면 끝.")
    if deep_tier:
        parts.append(ISOLATION_ONCE_SENTENCE)
        parts.append(NO_COMMIT_SENTENCE)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# H2 — node emission (fan 3법칙 by construction: fan only after a source node;
# every fan block followed by exactly one convergence node — closure; one
# fan-in per source cohort). Rule ②③④⑨.
# ---------------------------------------------------------------------------
def _shape_nodes(
    answers: Mapping[str, str],
    work_stmt: str,
    write_scope: Mapping[str, Any],
    escalated: bool,
    rows: list[dict[str, str]],
    *,
    contract_vocab: bool,
) -> list[dict[str, Any]]:
    deep = escalated or answers["difficulty"] in _HARD_DIFFICULTIES
    nodes: list[dict[str, Any]] = []

    if deep:
        # Rule ③ — 어려움+싼 work 조합이면 deep-design 자동 제안. We always prepend
        # for the deep tier (covers the hard+cheap AND hard+fugu case).
        nodes.append({"kind": "deep-design", "work_statement": DEEP_DESIGN_STMT, **FABLE5})
        rows.append(
            {
                "rule_id": "rule3-deep-design-inserted",
                "decision": "prepend fable5 deep-design node",
                "basis": "escalated or difficulty in {complex, entangled}",
            }
        )

    work_cast = FUGU if deep else CODEX
    rows.append(
        {
            "rule_id": "rule2-work-casting",
            "decision": f"work → {work_cast['adapter_ref']}",
            "basis": "difficulty/escalation-proportional casting (Smith 0706)",
        }
    )
    nodes.append(
        {
            "kind": "work",
            "work_statement": work_stmt,
            **work_cast,
            "write_scope": dict(write_scope),
        }
    )

    if answers["difficulty"] == "simple" and not escalated and answers["size"] == "small":
        # Rule (probe ②) — simple-doc gets a codex light chain with a gemini review.
        nodes.append({"kind": "review", "work_statement": REVIEW_STMT, **GEMINI_REVIEW})
        rows.append(
            {
                "rule_id": "shape-light-chain",
                "decision": "work → review(gemini) → closure",
                "basis": "simple + not escalated + size==small",
            }
        )
    else:
        branches: list[dict[str, Any]] = [
            {
                "kind": "code-attack-qa",
                "work_statement": CODE_QA_STMT,
                **(FABLE5 if escalated else CLAUDE_INHERIT_XHIGH),
            },
            {
                "kind": "evidence-integrity",
                "work_statement": EVIDENCE_QA_STMT,
                **CLAUDE_INHERIT_XHIGH,
            },
        ]
        if answers["failure_cost"] == "high" and contract_vocab:
            branches.append(
                {
                    "kind": "axis-attack-qa",
                    "work_statement": AXIS_QA_STMT,
                    **CLAUDE_INHERIT_XHIGH,
                }
            )
        # Rule ⑨ — fable5 QA 동시 버스트 회피: at most one fable5 fan sibling;
        # the other lenses inherit (model omitted).
        if escalated:
            rows.append(
                {
                    "rule_id": "rule9-fable5-burst",
                    "decision": "at most one fable5 fan sibling; others inherit",
                    "basis": "fable5 QA 동시 버스트 회피 (evidence-integrity model 생략)",
                }
            )
        nodes.append({"fan": {"branches": branches}})
        rows.append(
            {
                "rule_id": "shape-fan-qa",
                "decision": f"work → fan({len(branches)} lens) → closure",
                "basis": "honest/medium/escalated tier QA fan",
            }
        )

    # Rule ④ — the sole convergence node this drafter emits. The marker comment
    # is mutation M3's target (deleting it must leave no convergence node).
    nodes.append({"kind": "closure", "work_statement": CLOSURE_STMT, **CODEX})  # RULE4-FAN-CONVERGENCE
    return nodes


# ---------------------------------------------------------------------------
# Rule ⑩ — precheck: assemble in memory only (no persist, no run).
# ---------------------------------------------------------------------------
def _precheck(declaration: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    try:
        composed = assemble_graph_declaration(declaration, repo_root=repo_root)
    except Exception as exc:  # CompositionError / ValueError / TypeError — surfaced, not judged
        return {
            "composed_ok": False,
            "literal": "",
            "reject_evidence": f"{type(exc).__name__}: {exc}",
        }
    return {
        "composed_ok": True,
        "literal": f"COMPOSED OK {composed.building_id}",
        "node_count": len(composed.nodes),
        "ungated_write_node_warnings": [
            dict(w) for w in composed.ungated_write_node_warnings
        ],
    }


def _default_building_id() -> str:
    import secrets
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"brick-draft-{stamp}-{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# Public surface (D1).
# ---------------------------------------------------------------------------
def draft_graph_declaration(
    task_statement: str,
    answers: Mapping[str, Any],
    *,
    repo_root: Path | str,
    building_id: str | None = None,
    allowed_paths: Sequence[str] = (),
    forbidden_paths: Sequence[str] = (".git/**",),
    source_facts: Sequence[str] = (),
    declared_by: str = "coo",
    author_ref: str = "coo:graph-draft",
    contract_vocab: Any = None,
    reorder: Any = None,
) -> GraphDraftResult:
    """Draft a launch-ready candidate graph-decl from a task + 8 sizing answers.

    Returns a :class:`GraphDraftResult` whose ``declaration`` composes through
    ``assemble_graph_declaration`` (``precheck['literal']`` == ``COMPOSED OK
    <building_id>``) or carries ``composed_ok: False`` with the reject evidence.
    The declaration never carries ``action: forward`` (Rule 3).
    """

    repo = Path(repo_root).resolve()
    norm = _normalize_answers(answers)
    rows: list[dict[str, str]] = []

    cv = _contract_vocab(norm, task_statement, contract_vocab)
    ro = _reorder(norm, task_statement, reorder)
    escalated = _escalated(norm, task_statement, rows, contract_vocab=cv, reorder=ro)
    deep_tier = escalated or norm["difficulty"] in _HARD_DIFFICULTIES

    # Rule ⑥ — verify source facts BEFORE producing the draft body.
    verified_facts = _verify_source_facts(source_facts, repo, rows)

    write_scope = _normalize_write_scope(
        allowed_paths, forbidden_paths, rows, repo_root=repo
    )
    work_stmt = _scaffold_work_statement(
        task_statement,
        deep_tier=deep_tier,
        termination_shape=norm["termination_shape"],
    )
    nodes = _shape_nodes(
        norm, work_stmt, write_scope, escalated, rows, contract_vocab=cv
    )
    if verified_facts:
        # attach verified source facts to the work node (the write lane node).
        for node in nodes:
            if node.get("kind") == "work":
                node["source_facts"] = list(verified_facts)
                break

    bid = (building_id or "").strip() or _default_building_id()
    declaration: dict[str, Any] = {
        "building_id": bid,
        "declared_by": declared_by,
        "author_ref": author_ref,
        # Rule 3 — NO ``action`` key: assemble default (stop) governs; never forward.
        "task": task_statement or f"# {bid}",
        "write_scope": dict(write_scope),
        "nodes": nodes,
    }

    # Rule ⑧ — deep-tier: top-level timeout raise.
    if deep_tier:
        declaration["adapter_timeout_seconds"] = DEEP_TIMEOUT_SECONDS
        rows.append(
            {
                "rule_id": "rule8-timeout-raise",
                "decision": f"adapter_timeout_seconds={DEEP_TIMEOUT_SECONDS}",
                "basis": "심층 시공 timeout 자동 상향",
            }
        )

    # Rule ⑯ — human_approval==yes → declared human-review gate concept token.
    if norm["human_approval"] == "yes":
        declaration["gates"] = ["human-review"]
        rows.append(
            {
                "rule_id": "rule16-human-gate",
                "decision": "gates: ['human-review']",
                "basis": "human_approval==yes → link-gate:human on the final transition",
            }
        )

    # decision_ledger #20 — split/file-conflict never change graph shape.
    if norm["splittable"] == "yes" and norm["size"] == "large":
        rows.append(
            {
                "rule_id": "note-split-candidate",
                "decision": "graph shape unchanged (single work node)",
                "basis": "분할 후보: 별도 빌딩 발주 검토 — operator Movement-adjacent",
            }
        )
    if norm["file_conflict"] == "yes":
        rows.append(
            {
                "rule_id": "note-file-conflict",
                "decision": "graph shape unchanged (single work node)",
                "basis": "파일충돌: work 병렬화 금지 유지",
            }
        )

    precheck = _precheck(declaration, repo)
    return GraphDraftResult(
        declaration=declaration,
        rationale_rows=tuple(rows),
        sizing_answers=dict(norm),
        precheck=precheck,
    )


def _rationale_markdown(result: GraphDraftResult) -> str:
    lines = [
        f"# graph-draft rationale — {result.declaration.get('building_id', '')}",
        "",
        "support evidence only; not source truth / success / quality / Movement.",
        "",
        "## sizing answers",
    ]
    for qid in SIZING_QUESTION_IDS:
        lines.append(f"- {qid}: {result.sizing_answers.get(qid, '')}")
    lines.append("")
    lines.append("## rationale rows")
    lines.append("")
    lines.append("| rule_id | decision | basis |")
    lines.append("| --- | --- | --- |")
    for row in result.rationale_rows:
        lines.append(
            f"| {row.get('rule_id', '')} | {row.get('decision', '')} | {row.get('basis', '')} |"
        )
    lines.append("")
    lines.append("## precheck")
    lines.append(f"- composed_ok: {result.precheck.get('composed_ok')}")
    lines.append(f"- literal: {result.precheck.get('literal', '')}")
    if result.precheck.get("reject_evidence"):
        lines.append(f"- reject_evidence: {result.precheck['reject_evidence']}")
    lines.append("")
    return "\n".join(lines)


def write_draft_declaration(result: GraphDraftResult, out_path: Path | str) -> Path:
    """Write the decl JSON + a sibling ``<stem>-rationale.md``; return the decl path.

    Never writes inside the repo by policy of the caller (the CLI defaults the
    path under ``<brick_home>/drafts/``); this function honors whatever path it
    is given.
    """

    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result.declaration, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rationale_path = out.with_name(out.stem + "-rationale.md")
    rationale_path.write_text(_rationale_markdown(result), encoding="utf-8")
    return out
