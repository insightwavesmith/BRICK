# Operator skill APPLY-LIST (0702 세대)

> 3면 동기화 계약: **agent/skills/ = 운영 정본**(체커 pin 대상), `brick/templates/skills/` =
> 선적(ship) 사본, `~/.claude/skills/` = live 배포면. 정본이 바뀌면 template과 live로
> 복사한다(방향 고정: agent → template → live). 그래프 발주의 공식 authoring/launch
> interface는 `assemble()`/`build()`/`fan()` DSL이다(Rule 10) — `brick build --graph
> <packet>` 저수준 CLI 입력은 retired고, 이 목록의 과거 세대(0623)가 그것을 현행처럼
> 안내했다.

## 0702 적용 기록 (COO 세션이 수행)

| 스킬 | 조치 |
|---|---|
| brick-task-author | agent 정본 → template/live 재복사 (DSL 구조규칙·에러표·체크리스트 포함 세대) |
| building-sizing-method | agent 정본 → template/live 재복사 (4축 카드 포함; template은 pin 호환문구 추가 보유) |
| building-coordination / evidence-verification | live 최초 동기화 (이전 APPLY-LIST 누락분) |
| make-a-brick / make-a-gate / make-an-agent | agent 정본 → template/live 재복사 |
| task_intake | live에 정본 이름으로 신규 배포 (구 `task-intake` 디렉토리는 아래 삭제 목록) |

## DELETE (Smith 터미널에서 — 세션이 live를 삭제하지 않는다)

```bash
# 통합·흡수된 잔재 (내용은 전부 정본 스킬이 커버)
rm -rf ~/.claude/skills/brick-hold-triage          # brick-task-author PHASE 3로 흡수
rm -rf ~/.claude/skills/brick-declaration-author   # make-a-brick/-an-agent/-a-gate로 대체
rm -rf ~/.claude/skills/axis-check                 # protocol-boundary-watch가 커버
rm -rf ~/.claude/skills/gap-detector               # evidence-shape-check가 커버
rm -rf ~/.claude/skills/structure-validator        # evidence-shape-check가 커버
rm -rf ~/.claude/skills/task-intake                # task_intake로 개명 배포됨
```

## 검증

적용 후 `PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py
--repo . --profile building_skill_preset_builder_composition` (template pin) 및
`--profile coo_operating_chain` (agent 정본 pin) green 확인.
