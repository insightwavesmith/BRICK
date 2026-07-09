# BRICK Official Route Memo (COO living memory)

| | |
|---|---|
| **Status** | support evidence · update at every Goal Exit |
| **Updated** | 2026-07-09 |
| **Authority for current ladder** | `GOAL/04-goal-phases-0709-route-and-frontier.md` |
| **Active COO goal** | `ACTIVE_COO_GOAL.md` — **EXIT** residual push-all (R1–R11 terminal) |
| **Exit freeze** | `residual-push-exit-0709.md` |
| **Closure (prior ladder)** | `GOAL/05-coo-ladder-closure-0709.md` (operator closed) |

---

## 1. 사람 앞문 (공식 발사 — 한 길)

```text
# 정식 graph-decl 발사 (assemble-arg only; raw graph packet 거부)
brick build --graph-decl <decl.json|yaml> [--forward ...]

# 또는 preset (해당 시)
brick build --preset <name> ...

# resume (approval-hold ledger 있을 때만)
brick build resume --decl <resume-declaration.json>

# 검증 계열 (판정 아님)
check_profile.py --all          # REAL HOME
check_profile.py --profile ...
brick verify / frontier inspect # exit 0 of build ≠ PASS
```

**금지 (공식 루트 아님)**
- raw graph packet을 `--graph-decl`에 넣기 (retired)
- operator가 return-shape / carry / template 수동 주입
- live checkout에서 COO 직접 제품 구현 (declared Building + worktree)
- hold 없는 `link_paused`에 resume 반복

### Mid-walk approval-hold (G0 probe 0709 — 이미 되는 문법)

Per-node `gates` on a **non-terminal** node (exactly one outgoing EdgeSpec).  
Terminal/closure node에 gates 붙이면 `observed 0` 로 assemble 실패.

```yaml
# sketch — assemble-arg / graph-decl nodes[]
nodes:
  - kind: design
    work_statement: "..."
    gates: [coo-review]    # mid HOLD after this node
  - kind: work
    work_statement: "..."
  - kind: closure
    work_statement: "..."
# 금지: closure에 gates: [...]  (outgoing 0)
# top-level gates: [human-review] → final boundary only
```

Probe report: `status/kernel/g0-route-fuel-probe-report-0709.md`

---

## 2. Pause 두 종류 (운영 모델)

| | (A) approval-hold | (B) walk-on concern |
|---|---|---|
| ledger | hold 있음 | 없음 |
| resume | OK | **dead_end** |
| 처분 | resume forward/reroute | salvage WIP / 재발사 |

---

## 3. Resume declaration 최소 모양

```json
{
  "building_ref": "/ABS/PATH/to/buildings/<id>",
  "author_ref": "coo:...",
  "chain": "single|until-terminal",
  "dispositions": [
    { "on": "<hold_reason or frontier match>", "action": "forward|raise|stop" }
  ]
}
```

dead_end 힌트 `COO_GATE_HARVEST_SHA`는 **orphan ledger 실측 있을 때만**. walk-on이면 salvage.

---

## 4. Goal ladder (현재)

```text
G0 Route Fuel     ← ACTIVE (resume 연료 복구)
G1 Continuity     hold→resume→complete dogfood
G2 Authoring      W1 잔여 (G1 후 본발사)
G3 Prevention     L1/L2/L3 live (G1 후)
G4 UX #5#6
G5 Structural     human gate
G6 Release
```

**구현 분업 (Smith 0709)**  
- G0–G1 Exit: Grok 세션 서브에이전트 가능 (Building 필수는 아님)  
- G1 Exit 이후 제품 구현: **BRICK 공식 Building만**

---

## 5. Phase exit 시 이 파일에 반드시 갱신

- [ ] 새 공식 CLI 플래그/문법  
- [ ] hold 선언 예시 path  
- [ ] resume 성공 dogfood building_id  
- [ ] salvage 예외 정책 변경 여부  
- [ ] HEAD / origin 참고 commit  

### Exit log

| When | Goal | Note |
|---|---|---|
| 2026-07-09 | **G3 observe EXIT** | L1/L2 hooks + L3-3a observe landed; hook unit test + import_identity_modes green; L3-3b Smith HOLD |
| 2026-07-09 | **G4 EXIT** | progress autorefresh + charter-fill WIP land; customer_project_progress_cli green |
| 2026-07-09 | **G5 gate-ready** | no vessel migrate / no Route V2 beyond A code; human gates explicit |
| 2026-07-09 | **G6 measured EXIT** | brick_cli_entrypoint + read_side (product_no_smith embed) green; driver0 dirty-cwd red on dirty tree; full release not_proven |
| 2026-07-09 | **LADDER CLOSED** | ACTIVE_COO_GOAL COMPLETED — see 05-coo-ladder-closure-0709.md |
| 2026-07-09 | — | Memo created; G0 open; Deku impl frozen |
| 2026-07-09 | **G0 EXIT** | resume `dead_end_kind` honesty; mid-node `gates:[coo-review]` assemble HOLD proven; terminal gates fail-closed with hint |
| 2026-07-09 | **G2 profiles green** | building_call_authoring/lowering/structure_plan_fan_barrier rc=0 after fixtures admission + untracked buildings archive
| 2026-07-09 | **G2 Building complete** | `g2-authoring-w1b-0709b` hold→resume→complete; WIP landed on main as 0b2f43dc5 (authoring STEP3 fixtures/checkers). Product Exit still needs focused profile green on main.
| 2026-07-09 | **G1 EXIT** | dogfood `g1-mid-hold-resume-dogfood-0709`: graph-decl → link_paused(coo hold) → `brick resume` forward → fake_landing hold → resume forward → **frontier=complete** |

### Official commands proven this exit

```text
brick build --graph-decl …/fixtures/g1-mid-hold-resume-dogfood-decl-0709.yaml --forward
brick resume --decl …/resume-declarations/g1-mid-hold-resume-dogfood-0709-forward.json
brick resume --decl …/resume-declarations/g1-mid-hold-resume-dogfood-0709-forward-b.json
# evidence_root: /Users/smith/.brick/project/brick-protocol/buildings/g1-mid-hold-resume-dogfood-0709
```

---

## 6. Deku (참고 · 구현 동결)

- Design: `/Users/smith/projects/deku/docs/ARCHITECTURE.md`  
- Status: `/Users/smith/projects/deku/docs/DEKU_STATUS.md`  
- 재개: Deku G0 Face first, after BRICK G0–G1 route fuel  
