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
import hashlib
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
    "draft_launch_guidance",
    "draft_rule_violations",
    "write_draft_declaration",
    "answer_fingerprint",
    "ANSWER_FINGERPRINT_PREFIX",
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
OPUS48_QA = {
    "adapter_ref": "adapter:claude-local",
    "model_ref": "model:claude:claude-opus-4-8",
    "reasoning_effort_ref": "effort:xhigh",
}
# G1 (walk-results-adopted-0707 §G1): 엔진쪽/매우 중요 QA = fable5, 그 외 QA = opus-4-8.
CODEX = {"adapter_ref": "adapter:codex-local"}
GEMINI_REVIEW = {"adapter_ref": "adapter:gemini-local"}

DEEP_TIMEOUT_SECONDS = 10800
ISOLATION_ONCE_SENTENCE = "격리 --all은 /tmp 로그로 1회만."
NO_COMMIT_SENTENCE = "git commit 금지."

# D3 — 답-지문 (answer fingerprint). A draft stamps ONE canonical answer
# sha256 + UTC timestamp line onto the EXISTING rationale output (no new vessel:
# the rationale markdown home is reused). The fingerprint is a deterministic
# digest of the canonical (normalized) sizing answers — it lets ``draft-diff``
# prove which answer set produced a given rationale without a second store.
# Support evidence only: the digest chooses no Movement, route, or verdict.
ANSWER_FINGERPRINT_PREFIX = "answer_fingerprint"


def answer_fingerprint(sizing_answers: Mapping[str, Any]) -> str:
    """Return the canonical sha256 hex digest of a normalized sizing-answer map.

    The digest is computed over ``json.dumps(..., sort_keys=True)`` of the
    string-coerced answer map, so it is stable across dict ordering and Python
    runs. Support evidence only — a content digest, not a verdict or route.
    """

    canonical = {str(k): str(v) for k, v in dict(sizing_answers).items()}
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# §A3 draft-time rule table (walk-results-adopted-0707.md). These RED/WARN
# literals are profile-pinned; the ``# RULE-RED*``/``# RULE-WARN*`` marker
# comments in ``draft_rule_violations`` are the mutation probes' targets
# (deleting a rule block must flip the pin checker to rc=1). Support evidence
# only — none of this chooses Movement, route, sufficiency, success, or quality.
# ---------------------------------------------------------------------------
DEEP_TIER_MODEL_REFS = frozenset(
    {"model:sakana:fugu-ultra", "model:claude:claude-fable-5"}
)
DEEP_TIER_MODEL_TAILS = frozenset(
    ref.rsplit(":", 1)[-1] for ref in DEEP_TIER_MODEL_REFS
)
FAN_WIDTH_CEILING = 3
_EXPANSION_BUDGET_MODES = ("per-node", "aggregate")
_AGGREGATE_BUDGET_KEY = "total"
_XHIGH_EFFORT_REFS = frozenset({"effort:xhigh", "xhigh"})

RED1_FAN_WIDTH = "graph-draft RED-1: fan width exceeds 3"
RED2_WRITE_SET_OVERLAP = "graph-draft RED-2: partition branch write-sets intersect"
RED3_DEEP_TIER_TIMEOUT = (
    "graph-draft RED-3: deep-tier casting with adapter_timeout_seconds below 10800"
)
RED4_BRANCH_CONTRACT = "graph-draft RED-4: fan branch missing concern_key/objective"
RED5_STAGE2_FINISH = (
    "graph-draft RED-5: stage-2 draft missing done_line/residual_owner"
)
RED6_BUDGET_MODE = (
    "graph-draft RED-6: expansion budget mixes per-node and aggregate modes"
)
WARN1_XHIGH_BURST = "graph-draft WARN-1: more than 2 concurrent xhigh fan siblings"
WARN2_LOW_TIER_WORK = (
    "graph-draft WARN-2: entangled/walker-adjacent surface with low-tier work casting"
)

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

# D1/D2 — 9th sizing answer (width_signals) + parallel-fan casting ladder and
# statements. width_signals is a SEPARATE optional key: it is NOT appended to
# SIZING_QUESTION_IDS (the required-8 contract stays exactly 8) and NOT added to
# SIZING_ANSWER_ENUMS. Absent → 0 → width 1 (safe default). (§A1.2/§A2/§E.)
WIDTH_SIGNALS_KEY = "width_signals"
_DESIGN_FAN_LADDER: tuple[Mapping[str, str], ...] = (FABLE5, FUGU, CODEX)
_DESIGN_FAN_CONCERN_TAILS: tuple[str, ...] = (
    "design-fable5",
    "design-fugu",
    "design-codex",
)
PARALLEL_DESIGN_STMT = (
    "병렬 독립 설계(상호 열람 금지): 형제 설계 가지의 증거를 읽지 마라. 담당 관점에서 "
    "설계·partition_plan을 반환하라. 판정 금지 — 수렴은 closure, 2단은 새 선언."
)
WORK_PARTITION_STMT = (
    "파티션 시공(형제 write 구역 침범 금지): 자기 write_scope 안에서만 시공하라. 판정 금지."
)
PARTITION_MERGE_STMT = (
    "파티션 병합(수렴): 형제 파티션의 반환을 하나로 통합 관찰하고 잔여·충돌을 기록하라. 판정 금지."
)
# D2② residual-owner default for a ceiling-truncated width decision (§A2
# residual_owner semantics, RED-5 연계). Support evidence only — not a verdict.
RESIDUAL_PARTITION_OWNER = "coo"

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


def _normalize_width_signals(answers: Mapping[str, Any]) -> int:
    """9th answer (D1): 폭 신호 사다리. 부재 → 0(폭 1). 기형 값은 fail-closed 거부.

    ``width_signals`` is an OPTIONAL key kept OUTSIDE the required-8 sizing
    contract: a missing key is the safe default (0 → width 1). A malformed value
    (bool, negative, float, non-digit text, or any non-int/non-digit-string) is
    rejected with ``ValueError`` rather than silently coerced — guessing the
    width would mis-cast fan risk. Values above the ceiling are accepted here and
    clamped later by ``_fan_width`` (keeps the min-3 ceiling load-bearing).
    """
    if not isinstance(answers, Mapping) or WIDTH_SIGNALS_KEY not in answers:
        return 0
    raw = answers[WIDTH_SIGNALS_KEY]
    if isinstance(raw, bool):
        raise ValueError(f"width_signals={raw!r} must be a non-negative integer (0=폭 1)")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and raw.strip().isdigit():
        value = int(raw.strip())
    else:
        raise ValueError(f"width_signals={raw!r} must be a non-negative integer (0=폭 1)")
    if value < 0:
        raise ValueError(f"width_signals={value} must be >= 0")
    return value


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
# H3 — width computation (D2): fan width N = min(신호 사다리, 비충돌 파티션 수, 3).
# The disjoint-scope grouping is a union-find over the SAME conservative
# _entries_overlap used by the RED-2 write-set scan, so a work fan drafted here is
# pairwise-disjoint by construction. Support evidence only — no launch, no verdict.
# ---------------------------------------------------------------------------
def _disjoint_scope_groups(allowed_paths: Sequence[str]) -> list[list[str]]:
    """Union-find over ``_entries_overlap``: 비충돌 파티션 수 = ``len(groups)``."""
    groups: list[list[str]] = []
    for entry in [str(p).strip() for p in allowed_paths if str(p).strip()]:
        hits = [g for g in groups if any(_entries_overlap(entry, e) for e in g)]
        merged = [entry]
        for g in hits:
            merged.extend(g)
            groups.remove(g)
        groups.append(merged)
    return groups


def _fan_width(width_signals: int, *, partition_count: int | None = None) -> int:
    """폭 = min(신호 사다리, [비충돌 파티션 수], 상한 3), 최소 1. (§A1.2 폭 공식.)"""
    ladder = width_signals if partition_count is None else min(width_signals, partition_count)
    return max(1, min(ladder, FAN_WIDTH_CEILING))  # RULE-WIDTH-CEILING


# ---------------------------------------------------------------------------
# H3b — the STANDARD QA fan (D2①: a width-fan does NOT downgrade QA to a single
# gemini review). Shared by the spine shape and the partition (work/design) fan
# shapes so an escalated split still gets the full attack-QA fan (code-attack-qa
# + evidence-integrity, + axis-attack-qa on a costly contract surface) at the
# G1 casting tier. Support evidence only — no launch, no verdict.
# ---------------------------------------------------------------------------
def _qa_fan_branches(
    answers: Mapping[str, str],
    escalated: bool,
    rows: list[dict[str, str]],
    *,
    contract_vocab: bool,
) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = [
        {
            "kind": "code-attack-qa",
            "concern_key": "code-attack-qa",
            "objective": CODE_QA_STMT,
            "work_statement": CODE_QA_STMT,
            **(FABLE5 if escalated else OPUS48_QA),
        },
        {
            "kind": "evidence-integrity",
            "concern_key": "evidence-integrity",
            "objective": EVIDENCE_QA_STMT,
            "work_statement": EVIDENCE_QA_STMT,
            **OPUS48_QA,
        },
    ]
    if answers["failure_cost"] == "high" and contract_vocab:
        branches.append(
            {
                "kind": "axis-attack-qa",
                "concern_key": "axis-attack-qa",
                "objective": AXIS_QA_STMT,
                "work_statement": AXIS_QA_STMT,
                **OPUS48_QA,
            }
        )
    # Rule ⑨ — fable5 QA 동시 버스트 회피: at most one fable5 fan sibling; the
    # other lenses run opus-4-8 (G1: 그 외 QA = Opus 4.8 xhigh).
    if escalated:
        rows.append(
            {
                "rule_id": "rule9-fable5-burst",
                "decision": "at most one fable5 fan sibling; others opus-4-8",
                "basis": "fable5 QA 동시 버스트 회피 (그 외 렌즈 = opus-4-8 xhigh, §G1)",
            }
        )
    return branches


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
    width_signals: int = 0,
) -> list[dict[str, Any]]:
    deep = escalated or answers["difficulty"] in _HARD_DIFFICULTIES
    nodes: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # D2 — width computation + fan auto-proposal (감지-후-방치 소멸: the old
    # note-split-candidate detect row is absorbed into rule-width-decision).
    # The proposal is a CANDIDATE only: no action key, no launch — the assemble
    # default (stop) governs (Rule 3). RED-1~6 stay load-bearing: a proposal that
    # violated a rule would be self-rejected at the precheck seam before assemble.
    # ------------------------------------------------------------------
    proposal_on = (
        answers["splittable"] == "yes"
        and answers["file_conflict"] == "no"
        and width_signals > 0
    )
    groups = _disjoint_scope_groups(write_scope.get("allowed_paths", ()))
    fan_n = (
        (_fan_width(width_signals) if deep else _fan_width(width_signals, partition_count=len(groups)))
        if proposal_on
        else 1
    )
    if answers["splittable"] == "yes":
        rows.append(
            {
                "rule_id": "rule-width-decision",
                "decision": (
                    f"N={fan_n} (신호={width_signals}, 비충돌 파티션={len(groups)}, "
                    f"상한={FAN_WIDTH_CEILING})"
                ),
                "basis": (
                    "폭=min(신호 사다리, 비충돌 파티션 수, 3) — walk-results-adopted-0707 §A "
                    "(감지→제안; note-split-candidate 흡수)"
                ),
            }
        )
    if proposal_on and fan_n >= 2:  # RULE-WIDTH-FAN-PROPOSAL
        if deep:
            branches = [
                {
                    "kind": "design",
                    "concern_key": tail,
                    "objective": PARALLEL_DESIGN_STMT,
                    "work_statement": PARALLEL_DESIGN_STMT,
                    **cast,
                }
                for cast, tail in zip(
                    _DESIGN_FAN_LADDER[:fan_n],
                    _DESIGN_FAN_CONCERN_TAILS[:fan_n],
                )
            ]
            rows.append(
                {
                    "rule_id": "rule-fan-proposal",
                    "decision": f"design fan ×{fan_n} → closure (상호 열람 금지)",
                    "basis": "2단 표준형: 1단=설계 수렴 홀드, 2단=새 선언 (§A1.3, §E)",
                }
            )
            return [
                {"fan": {"branches": branches}},
                {"kind": "closure", "work_statement": CLOSURE_STMT, **CODEX},  # RULE4-FAN-CONVERGENCE (design-fan arm)
            ]
        branches = [
            {
                "kind": "work",
                "concern_key": f"work-partition-{i + 1}",
                "objective": WORK_PARTITION_STMT + " 구역: " + ", ".join(group),
                "work_statement": work_stmt + "\n\n" + WORK_PARTITION_STMT + " 구역: " + ", ".join(group),
                **CODEX,
                "write_scope": {
                    "allowed_paths": list(group),
                    "forbidden_paths": list(write_scope.get("forbidden_paths", ())),
                },
            }
            for i, group in enumerate(groups[:fan_n])
        ]
        rows.append(
            {
                "rule_id": "rule-fan-proposal",
                "decision": f"work fan ×{fan_n} → merge → QA fan → closure (write 구역 서로소)",
                "basis": f"비충돌 파티션 {len(groups)}개 실측 — RED-2 서로소 by construction",
            }
        )
        # D2② residual-partition record: when the width ceiling (3) or the signal
        # ladder truncates the disjoint partition set, the leftover partitions are
        # NOT dropped silently — they are named on a residual row (owner = coo) so
        # a stage-2 partition_plan can carry them under done_line/residual_owner
        # (§A2, RED-5 연계). Support evidence only — not a verdict, not a launch.
        residual_groups = groups[fan_n:]
        if residual_groups:
            residual_paths = [p for group in residual_groups for p in group]
            rows.append(
                {
                    "rule_id": "rule-residual-partition",
                    "decision": (
                        f"잔여 파티션 {len(residual_groups)}개 → residual_owner="
                        f"{RESIDUAL_PARTITION_OWNER}: " + "; ".join(", ".join(g) for g in residual_groups)
                    ),
                    "basis": (
                        "폭 상한/신호 절단으로 남은 파티션은 done_line/residual_owner 증거로 보존 "
                        "— walk-results-adopted-0707 §A2 (RED-5 연계)"
                    ),
                }
            )
        # D2① — a width-fan does NOT downgrade QA to a single gemini review: the
        # partitions merge into ONE convergence work node (its own write_scope is
        # the full declared scope), then the STANDARD attack-QA fan runs before
        # closure — identical QA depth to the non-split spine (§A2 qa_plan).
        merge_stmt = work_stmt + "\n\n" + PARTITION_MERGE_STMT
        if residual_groups:
            merge_stmt += "\n\n잔여 파티션(후속 발주 후보): " + "; ".join(
                ", ".join(g) for g in residual_groups
            )
        qa_branches = _qa_fan_branches(answers, escalated, rows, contract_vocab=contract_vocab)
        return [
            {"fan": {"branches": branches}},
            {
                "kind": "work",
                "work_statement": merge_stmt,
                **CODEX,
                "write_scope": dict(write_scope),
            },  # RULE4-FAN-CONVERGENCE (work-fan merge convergence)
            {"fan": {"branches": qa_branches}},
            {"kind": "closure", "work_statement": CLOSURE_STMT, **CODEX},  # RULE4-FAN-CONVERGENCE (work-fan QA arm)
        ]

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
        # D2① — the STANDARD attack-QA fan (shared with the width-fan shape via
        # _qa_fan_branches: identical casting so a split never degrades QA depth).
        branches = _qa_fan_branches(answers, escalated, rows, contract_vocab=contract_vocab)
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

# ---------------------------------------------------------------------------
# §A3 draft-time rule table body. Pure, read-only, no persist and no launch —
# turns a drafted declaration (+ optional partition_plan / sizing answers) into
# (RED literals, WARN literals). Support evidence only.
# ---------------------------------------------------------------------------
def _iter_fan_branches(declaration: Mapping[str, Any]) -> "list[list[Mapping[str, Any]]]":
    """Every fan block's branch list, in declaration order."""
    out: list[list[Mapping[str, Any]]] = []
    for node in declaration.get("nodes", ()) or ():
        if isinstance(node, Mapping) and "fan" in node:
            fan_block = node.get("fan") or {}
            branches = fan_block.get("branches", ()) if isinstance(fan_block, Mapping) else ()
            out.append([b for b in (branches or ()) if isinstance(b, Mapping)])
    return out


def _fan_branches_have_malformed(declaration: Mapping[str, Any]) -> bool:
    """True when any fan block declares a non-mapping (malformed) branch entry.

    Fail-closed (decision_ledger #8/#9 posture, shared with RED-3): a branch that
    is not a mapping cannot name concern_key/objective, so it must NOT be silently
    dropped from the RED-4 branch-contract scan — it counts as a violation.
    """
    for node in declaration.get("nodes", ()) or ():
        if not (isinstance(node, Mapping) and "fan" in node):
            continue
        fan_block = node.get("fan") or {}
        branches = fan_block.get("branches", ()) if isinstance(fan_block, Mapping) else ()
        for branch in branches or ():
            if not isinstance(branch, Mapping):
                return True
    return False


def _scope_segments(entry: str) -> list[str]:
    """Normalized path segments for a write-scope entry (trailing globs dropped)."""
    text = str(entry or "").strip().replace("\\", "/").strip("/")
    if not text:
        return []
    segments: list[str] = []
    for seg in text.split("/"):
        if seg in ("", "."):
            continue
        if seg == "**":
            # a recursive-glob tail matches any deeper segment; stop collecting
            # so a shorter prefix list is produced (prefix ⇒ overlap below).
            break
        segments.append(seg)
    return segments


def _segment_matches(a: str, b: str) -> bool:
    if any(ch in a for ch in "*?[") or any(ch in b for ch in "*?["):
        return True
    return a == b


def _entries_overlap(a: str, b: str) -> bool:
    """Conservative (over-approximating) static-prefix overlap of two entries.

    Segment-wise: a glob-bearing segment matches any segment; two entries overlap
    iff one segment list is a prefix of the other (decision_ledger #8). Empty
    (root) entries overlap everything.
    """
    sa = _scope_segments(a)
    sb = _scope_segments(b)
    if not sa or not sb:
        return True
    for seg_a, seg_b in zip(sa, sb):
        if not _segment_matches(seg_a, seg_b):
            return False
    return True


def _branch_allowed_paths(branch: Mapping[str, Any]) -> list[str]:
    """Allowed write paths declared on a branch, from either shape.

    A partition branch homes them under ``write_set.allowed``; a drafted fan
    branch (graph-decl node) homes them under ``write_scope.allowed_paths``.
    """
    out: list[str] = []
    ws = branch.get("write_set")
    if isinstance(ws, Mapping):
        for p in ws.get("allowed", ()) or ():
            if str(p).strip():
                out.append(str(p).strip())
    scope = branch.get("write_scope")
    if isinstance(scope, Mapping):
        for p in scope.get("allowed_paths", ()) or ():
            if str(p).strip():
                out.append(str(p).strip())
    return out


def _write_sets_intersect(branches: Sequence[Mapping[str, Any]]) -> bool:
    paths = [(_branch_allowed_paths(b)) for b in branches]
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            for x in paths[i]:
                for y in paths[j]:
                    if _entries_overlap(x, y):
                        return True
    return False


def _partition_branch_missing_write_set(
    partition_branches: Sequence[Mapping[str, Any]],
) -> bool:
    """True when any §A2 partition branch declares no usable allowed write path.

    Fail-open #1 closure (fail-closed posture, shared with RED-2): a partition
    branch with no ``write_set`` / an empty ``write_set.allowed`` cannot be proven
    disjoint from its siblings, so it must NOT slip past the overlap scan. This is
    partition-scoped on purpose — drafted read-only QA fan branches carry no
    write_set by design and must stay green.
    """
    for branch in partition_branches:
        ws = branch.get("write_set")
        allowed = ws.get("allowed", ()) if isinstance(ws, Mapping) else ()
        if not [str(p).strip() for p in (allowed or ()) if str(p).strip()]:
            return True
    return False


def _casting_model(casting: Mapping[str, Any]) -> str:
    for key in ("model", "model_ref"):
        val = str(casting.get(key) or "").strip()
        if val:
            return val
    return ""


def _is_deep_tier_model(model: str) -> bool:
    # Fail-open #3 closure: a deep-tier model ref authored with a case variant
    # (e.g. "model:sakana:FUGU-ULTRA") must NOT slip past the RED-3 timeout gate.
    # Normalize case before matching; the ref/tail sets are already lowercase.
    model = str(model or "").strip().lower()
    if not model:
        return False
    return model in DEEP_TIER_MODEL_REFS or model in DEEP_TIER_MODEL_TAILS


def _declared_deep_tier(
    declaration: Mapping[str, Any],
    partition_branches: Sequence[Mapping[str, Any]],
) -> bool:
    for node in declaration.get("nodes", ()) or ():
        if not isinstance(node, Mapping):
            continue
        if "fan" in node:
            fan_block = node.get("fan") or {}
            for branch in (fan_block.get("branches", ()) if isinstance(fan_block, Mapping) else ()):
                if isinstance(branch, Mapping) and _is_deep_tier_model(
                    str(branch.get("model_ref") or branch.get("model") or "")
                ):
                    return True
            continue
        if _is_deep_tier_model(str(node.get("model_ref") or node.get("model") or "")):
            return True
    for branch in partition_branches:
        casting = branch.get("casting")
        if isinstance(casting, Mapping) and _is_deep_tier_model(_casting_model(casting)):
            return True
    return False


def _partition_has_deep_tier(partition_plan: Mapping[str, Any] | None) -> bool:
    if not isinstance(partition_plan, Mapping):
        return False
    for branch in partition_plan.get("branches", ()) or ():
        if not isinstance(branch, Mapping):
            continue
        casting = branch.get("casting")
        if isinstance(casting, Mapping) and _is_deep_tier_model(_casting_model(casting)):
            return True
    return False


def _timeout_below(value: Any) -> bool:
    return not isinstance(value, int) or isinstance(value, bool) or value < DEEP_TIMEOUT_SECONDS


def _branch_timeout_below(partition_branches: Sequence[Mapping[str, Any]]) -> bool:
    for branch in partition_branches:
        casting = branch.get("casting")
        if not isinstance(casting, Mapping):
            continue
        if not _is_deep_tier_model(_casting_model(casting)):
            continue
        if _timeout_below(casting.get("timeout_seconds")):
            return True
    return False


def _declaration_local_timeout_below(declaration: Mapping[str, Any]) -> bool:
    """True when a deep-tier declaration node/branch declares a local low timeout."""

    def _entry_low(entry: Mapping[str, Any]) -> bool:
        model = str(entry.get("model_ref") or entry.get("model") or "")
        if _is_deep_tier_model(model) and "timeout_seconds" in entry:
            return _timeout_below(entry.get("timeout_seconds"))
        casting = entry.get("casting")
        if isinstance(casting, Mapping) and _is_deep_tier_model(_casting_model(casting)):
            if "timeout_seconds" in casting and _timeout_below(casting.get("timeout_seconds")):
                return True
        return False

    for node in declaration.get("nodes", ()) or ():
        if not isinstance(node, Mapping):
            continue
        if _entry_low(node):
            return True
        fan_block = node.get("fan") if "fan" in node else None
        branches = fan_block.get("branches", ()) if isinstance(fan_block, Mapping) else ()
        for branch in branches or ():
            if isinstance(branch, Mapping) and _entry_low(branch):
                return True
    return False


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def draft_rule_violations(
    declaration: Mapping[str, Any],
    *,
    partition_plan: Mapping[str, Any] | None = None,
    answers: Mapping[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """§A3 draft-time rule table → (RED literals, WARN literals).

    Support evidence only — no verdict, Movement, route, sufficiency, success, or
    quality decision lives here. RED literals reject the draft at the precheck
    seam; WARN literals surface as advisory rationale rows only.
    """
    reds: list[str] = []
    warns: list[str] = []
    pplan = partition_plan if isinstance(partition_plan, Mapping) else None
    p_branches = [
        b for b in ((pplan or {}).get("branches", ()) or []) if isinstance(b, Mapping)
    ]
    fan_branch_lists = _iter_fan_branches(declaration)

    # RULE-RED1-FAN-WIDTH — declared fan width and partition width ceiling of 3.
    width_exceeded = any(len(branches) > FAN_WIDTH_CEILING for branches in fan_branch_lists)
    if pplan is not None:
        n = ((pplan.get("width_decision") or {}) if isinstance(pplan.get("width_decision"), Mapping) else {}).get("n")
        if (not isinstance(n, int) or isinstance(n, bool) or n > FAN_WIDTH_CEILING) or len(p_branches) > FAN_WIDTH_CEILING:
            width_exceeded = True
    if width_exceeded:
        reds.append(RED1_FAN_WIDTH)

    # RULE-RED2-WRITE-SET — pairwise write-set overlap among sibling branches.
    # Fail-open #1 closure: a §A2 partition branch that declares NO write_set (or
    # an empty allowed list) cannot be proven disjoint, so it fails closed to
    # RED-2 rather than passing. Drafted QA fan branches are read-only lenses and
    # legitimately carry no write_set, so this presence rule is partition-scoped.
    if RED2_WRITE_SET_OVERLAP not in reds and _partition_branch_missing_write_set(p_branches):
        reds.append(RED2_WRITE_SET_OVERLAP)
    for branches in fan_branch_lists:
        if RED2_WRITE_SET_OVERLAP in reds:
            break
        if _write_sets_intersect(branches):
            reds.append(RED2_WRITE_SET_OVERLAP)
            break
    if RED2_WRITE_SET_OVERLAP not in reds and _write_sets_intersect(p_branches):
        reds.append(RED2_WRITE_SET_OVERLAP)

    # RULE-RED3-DEEP-TIMEOUT — deep-tier casting must carry ≥10800s (fail-closed
    # on a missing/low top-level timeout or a low per-branch timeout).
    if _declared_deep_tier(declaration, p_branches):
        top_timeout = _int_or_none(declaration.get("adapter_timeout_seconds"))
        if (
            top_timeout is None
            or top_timeout < DEEP_TIMEOUT_SECONDS
            or _branch_timeout_below(p_branches)
            or _declaration_local_timeout_below(declaration)
        ):
            reds.append(RED3_DEEP_TIER_TIMEOUT)

    # RULE-RED4-BRANCH-CONTRACT — every fan/partition branch names concern_key +
    # objective (fan-branch-scoped; spine nodes exempt).
    # Fail-closed: a malformed (non-mapping) fan/partition branch cannot name the
    # contract fields, so it counts as a RED-4 violation rather than being dropped.
    red4 = _fan_branches_have_malformed(declaration)
    if not red4 and pplan is not None:
        raw_p_branches = (pplan.get("branches", ()) or [])
        if any(not isinstance(b, Mapping) for b in raw_p_branches):
            red4 = True
    for branches in fan_branch_lists:
        if red4:
            break
        for branch in branches:
            if not str(branch.get("concern_key") or "").strip() or not str(branch.get("objective") or "").strip():
                red4 = True
                break
        if red4:
            break
    if not red4:
        for branch in p_branches:
            if not str(branch.get("concern_key") or "").strip() or not str(branch.get("objective") or "").strip():
                red4 = True
                break
    if red4:
        reds.append(RED4_BRANCH_CONTRACT)

    # RULE-RED5-STAGE2-FINISH — a stage-2 draft (partition_plan present) declares
    # done_line + residual_owner.
    if pplan is not None:
        if not str(pplan.get("done_line") or "").strip() or not str(pplan.get("residual_owner") or "").strip():
            reds.append(RED5_STAGE2_FINISH)

    # RULE-RED6-BUDGET-MODE — expansion budget_mode is per-node XOR aggregate and
    # its budget keys match the declared mode.
    # Fail-open #2 closure (fail-closed posture): a stage-2 draft (partition_plan
    # present) must declare a well-formed expansion — a missing expansion, a
    # non-mapping/empty/malformed budgets container, or a non-positive-int budget
    # value all fail closed to RED-6 rather than passing.
    if pplan is not None:
        exp = pplan.get("expansion")
        if not isinstance(exp, Mapping):
            reds.append(RED6_BUDGET_MODE)
        else:
            mode = str(exp.get("budget_mode") or "").strip()
            raw_budgets = exp.get("budgets")
            budgets = raw_budgets if isinstance(raw_budgets, Mapping) else None
            branch_ids = {str(b.get("branch_id") or "").strip() for b in p_branches if str(b.get("branch_id") or "").strip()}
            bad = False
            if mode not in _EXPANSION_BUDGET_MODES:
                bad = True
            elif budgets is None or not budgets:
                # missing, non-mapping, or empty budgets — cannot bound the stage.
                bad = True
            elif _AGGREGATE_BUDGET_KEY in budgets and any(k != _AGGREGATE_BUDGET_KEY for k in budgets):
                bad = True  # mixed per-node + aggregate keys.
            elif mode == "per-node" and (_AGGREGATE_BUDGET_KEY in budgets or not set(budgets) <= branch_ids):
                bad = True
            elif mode == "aggregate" and (set(budgets) - {_AGGREGATE_BUDGET_KEY}):
                bad = True
            elif any(
                (not isinstance(v, int)) or isinstance(v, bool) or v <= 0
                for v in budgets.values()
            ):
                bad = True  # every declared budget must be a finite positive int.
            if bad:
                reds.append(RED6_BUDGET_MODE)

    # RULE-WARN1-XHIGH-BURST — more than 2 xhigh siblings in any single fan block
    # or the partition casting cohort (advisory only; literal ceiling of 2).
    def _xhigh_count(effort_refs: Sequence[str]) -> int:
        return sum(1 for e in effort_refs if str(e or "").strip() in _XHIGH_EFFORT_REFS)

    for branches in fan_branch_lists:
        efforts = [str(b.get("reasoning_effort_ref") or b.get("reasoning_effort") or b.get("effort") or "") for b in branches]
        if _xhigh_count(efforts) > 2:
            warns.append(WARN1_XHIGH_BURST)
            break
    if WARN1_XHIGH_BURST not in warns:
        p_efforts = [
            str((b.get("casting") or {}).get("effort") or "") if isinstance(b.get("casting"), Mapping) else ""
            for b in p_branches
        ]
        if _xhigh_count(p_efforts) > 2:
            warns.append(WARN1_XHIGH_BURST)

    # RULE-WARN2-LOW-TIER — entangled/walker-adjacent surface (from answers) with a
    # low-tier codex work node casting (advisory only; answer-gated).
    # Fail-open #4 closure: ``walker_adjacent==yes`` and a hard difficulty both
    # force escalation → the drafted work node is fugu, never codex-local, so those
    # two signals alone left WARN-2 structurally unreachable through the drafter.
    # ``file_conflict==yes`` ("work 병렬화 금지" — an entanglement signal) does NOT
    # force escalation, so it leaves a codex-local work node on a risky surface —
    # the exact 얽힘+저티어 case WARN-2 exists to surface (advisory only).
    if isinstance(answers, Mapping):
        surface_risk = (
            str(answers.get("walker_adjacent") or "").strip().lower() == "yes"
            or str(answers.get("difficulty") or "").strip().lower() in _HARD_DIFFICULTIES
            or str(answers.get("file_conflict") or "").strip().lower() == "yes"
        )
        if surface_risk:
            for node in declaration.get("nodes", ()) or ():
                if isinstance(node, Mapping) and node.get("kind") == "work" and str(node.get("adapter_ref") or "").strip() == "adapter:codex-local":
                    warns.append(WARN2_LOW_TIER_WORK)
                    break

    return _dedupe_texts(reds), _dedupe_texts(warns)


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
    partition_plan: Mapping[str, Any] | None = None,
) -> GraphDraftResult:
    """Draft a launch-ready candidate graph-decl from a task + 8 sizing answers.

    Returns a :class:`GraphDraftResult` whose ``declaration`` composes through
    ``assemble_graph_declaration`` (``precheck['literal']`` == ``COMPOSED OK
    <building_id>``) or carries ``composed_ok: False`` with the reject evidence.
    The declaration never carries ``action: forward`` (Rule 3).

    An optional ``partition_plan`` (the §A2 fan-partition proposal) marks a
    stage-2 draft: it feeds the §A3 draft-time rule table
    (:func:`draft_rule_violations`) and, when its casting is deep-tier, joins the
    ``deep_tier`` timeout derivation for generation self-coherence.
    """

    repo = Path(repo_root).resolve()
    norm = _normalize_answers(answers)
    # D1 — 9th answer, fail-closed BEFORE any shaping (a malformed width raises).
    width_signals = _normalize_width_signals(answers)
    rows: list[dict[str, str]] = []

    cv = _contract_vocab(norm, task_statement, contract_vocab)
    ro = _reorder(norm, task_statement, reorder)
    escalated = _escalated(norm, task_statement, rows, contract_vocab=cv, reorder=ro)
    deep_tier = (
        escalated
        or norm["difficulty"] in _HARD_DIFFICULTIES
        or _partition_has_deep_tier(partition_plan)
    )

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
        norm,
        work_stmt,
        write_scope,
        escalated,
        rows,
        contract_vocab=cv,
        width_signals=width_signals,
    )
    if verified_facts:
        # D1 — source_facts 전파: attach the verified sources to EVERY fan branch,
        # not just the first write/design petal. The spine shape carries a single
        # top-level work node; a width-fan carries the work/design lanes INSIDE a
        # fan block (work-partition branches, or design-fan branches) plus a merge
        # convergence work node and then the standard attack-QA fan. Attaching to
        # only the first petal silently drops rule ⑥ output for sibling lanes (the
        # 1st-pass QA observation: a drafted work fan received no source_facts).
        # Read-only QA/review fan branches are still branches of the proposal
        # evidence surface, so they inherit the same verified source_facts. The
        # closure node is not a branch/write-design lane and remains untouched.
        _WRITE_OR_DESIGN_KINDS = {"work", "design", "deep-design"}
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            if "fan" in node:
                fan_block = node.get("fan")
                branches = fan_block.get("branches", ()) if isinstance(fan_block, Mapping) else ()
                for branch in branches or ():
                    if isinstance(branch, dict):
                        branch["source_facts"] = list(verified_facts)
            elif node.get("kind") in _WRITE_OR_DESIGN_KINDS:
                node["source_facts"] = list(verified_facts)

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

    # decision_ledger #20 — file-conflict never changes graph shape. The old
    # note-split-candidate detect row is ABSORBED into the rule-width-decision row
    # emitted in _shape_nodes (감지-후-방치 소멸, D2); note-file-conflict stays a
    # separate no-parallel law and is also a fan-trigger blocker.
    if norm["file_conflict"] == "yes":
        rows.append(
            {
                "rule_id": "note-file-conflict",
                "decision": "graph shape unchanged (single work node)",
                "basis": "파일충돌: work 병렬화 금지 유지",
            }
        )

    # §A3 rule table — WARN rows are advisory; RED literals reject the draft at
    # the precheck seam (assemble skipped, cli.py turns composed_ok False → rc=1).
    reds, warns = draft_rule_violations(
        declaration, partition_plan=partition_plan, answers=norm
    )
    for text in warns:
        rows.append(
            {
                "rule_id": "warn1-xhigh-burst" if text == WARN1_XHIGH_BURST else "warn2-low-tier-work",
                "decision": text,
                "basis": "§A3 soft WARN — advisory rationale row only",
            }
        )
    if reds:  # RED-REJECT-SEAM — §A3 hard RED: reject the draft, never assemble it.
        precheck = {
            "composed_ok": False,
            "literal": "",
            "reject_evidence": "; ".join(reds),
        }
    else:
        precheck = _precheck(declaration, repo)
    return GraphDraftResult(
        declaration=declaration,
        rationale_rows=tuple(rows),
        sizing_answers={**norm, WIDTH_SIGNALS_KEY: str(width_signals)},
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
    lines.append(f"- {WIDTH_SIGNALS_KEY}: {result.sizing_answers.get(WIDTH_SIGNALS_KEY, '0')}")
    lines.append("")
    # D3 — 답-지문: one canonical answer sha256 + UTC line, reusing this existing
    # rationale home (no new vessel). draft-diff reads this line to bind a
    # rationale to the exact answer set that produced it.
    from datetime import datetime, timezone

    fp = answer_fingerprint(result.sizing_answers)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"- {ANSWER_FINGERPRINT_PREFIX}: sha256:{fp} @ {stamp}")
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


def draft_launch_guidance(draft_path: Path | str) -> str:
    """Operator-facing launch guidance for a drafted graph-decl (표22 발사 이중 열쇠).

    A drafted declaration carries no ``action`` key, so the assemble default
    (``stop``) governs — the draft is a frozen preview. An operator launches it
    WITHOUT editing the declaration file by passing the CLI ``--forward`` flag,
    which the build surface resolves with priority CLI > file > default stop. The
    flag is only the surface of an explicit human launch act; Rule 3 (자동발사
    금지) stays law — no ``--forward`` and a stop/omitted file action still means
    no launch (this surface has no auto-fire path).

    This is draft-surface messaging only; it reaches no launch seam, chooses no
    Movement/route, and is not source truth, success/quality judgment, or
    Movement authority.
    """

    return (
        "발사는 운영자 몫: 초안을 검토한 뒤 직접 실행하세요 → "
        f"brick build --graph-decl {draft_path} "
        "(선언 action 기본값 stop = 동결 미리보기; 파일 편집 없이 바로 발사하려면 "
        "--forward 를 붙이세요; 이 표면에는 자동발사 경로가 없습니다)"
    )


def write_draft_declaration(result: GraphDraftResult, out_path: Path | str) -> Path:
    """Write the decl JSON + a sibling ``<stem>-rationale.md``; return the decl path.

    Never writes inside the repo by policy of the caller (the CLI defaults the
    path under ``<brick_home>/drafts/``); this function honors whatever path it
    is given.

    Fail-open #5 closure: a draft whose precheck did not compose (``composed_ok``
    False — the §A3 RED-REJECT-SEAM or an assemble reject) is stamped on disk with
    a passive ``draft_rejected`` marker carrying the reject evidence, so the
    persisted artifact self-identifies as a rejected draft and cannot be mistaken
    for a launch-ready declaration. The marker is a recorded fact only — it is not
    an ``action``/Movement key, chooses no route, and grants no launch authority
    (assemble ignores it; the default ``stop`` still governs).
    """

    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    declaration: dict[str, Any] = dict(result.declaration)
    if not result.precheck.get("composed_ok"):
        declaration["draft_rejected"] = {
            "composed_ok": False,
            "reject_evidence": str(result.precheck.get("reject_evidence", "")),
            "note": "rejected draft — not launch-ready; fix the reject_evidence before build",
        }
    out.write_text(
        json.dumps(declaration, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rationale_path = out.with_name(out.stem + "-rationale.md")
    rationale_path.write_text(_rationale_markdown(result), encoding="utf-8")
    return out
