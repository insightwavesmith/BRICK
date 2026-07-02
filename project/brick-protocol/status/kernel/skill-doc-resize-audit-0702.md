# 스킬·문서 리사이즈 전수측정 (0702) — 24레인 sonnet 감사 요약

Status: support evidence only. Not source truth / success / quality / Movement authority.
측정: read-only 워크플로우 24레인 (pin맵 1 + 스킬 12 + 발사부채 4 + 문서census 5 + 병합 2).
전체 원자료: 세션 워크플로우 저널 wf_474d099b-778. 이 문서는 COO 요약본.

## 1. Pin 지도

스킬/문서를 겨냥한 체커 pin 타깃 **59건**. 최고 밀도: `building-coordination/SKILL.md`
coordination-order 블록(21스텝, text_contains ~10+), `task_intake/SKILL.md` Do/Don't
블록(~85문구, coo_operating_chain). `project-creation`은 pin 0. **리사이즈는 pin맵 없이 불가.**

## 2. 스킬 감량표 (repo 2,237줄 → 목표 ~1,590줄)

| 파일 | 현재 | 목표 | 주요 삭감 |
|---|---|---|---|
| task_intake | 431 | 300 | 서사·인터뷰 원론·3중 반복 면책문구 (pinned 필드목록 보존) |
| brick-task-author | 383 | 260 | G1 JSON 중복예시, 서사 압축 (에러표·PHASE1 템플릿·분류표 보존) |
| building-coordination | 331 | 220 | 도그푸드 일화, task_intake 중복 → 포인터 (pinned 21스텝 보존) |
| native-dispatch-recording | 250 | 175 | hooks JSON 예시, 3중 반복 면책 |
| building-sizing-method | 193 | 140 | P3기본형·공식경로 중복 → brick-task-author 포인터 |
| 소형 5종 (make-a-*/project-creation) | 419 | 345 | 서두 법 단락 압축, 검증 명령·불변식 보존 |
| 초소형 8종 | 232 | 150 | code-analyzer/zero-script-qa/design-depth-check → evidence-shape-check 흡수, scoped-implementation → software-architecture 흡수 |

단일소스화: 큰일P3규칙·공식경로·어댑터제약 = brick-task-author가 정본, 타 파일은 pinned 문구+포인터.

## 3. 사본 드리프트 (즉시 조치 필요)

- template building-sizing-method가 agent 사본보다 **앞섬** (0702 pin 복구가 template에만 감) → agent를 template에서 재sync.
- agent make-an-agent가 template보다 앞섬 (write-tier policy) → template을 agent에서 재sync.
- **live ~/.claude/skills**: brick-task-author 447줄 diff(PHASE3 이전 세대), task-intake↔task_intake 이름 불일치, APPLY-LIST의 삭제 지시 미이행(brick-hold-triage 등 — 단 재복사 후 삭제 순서 필수). axis-check/gap-detector/structure-validator는 repo 출처 없음 — Smith 확인 필요.
- APPLY-LIST.md 전면 재작성 필요 (0623 세대, --graph 현행 서술).

## 4. 발사부채 실측 (4계열)

1. **task.md 미주입 확정(HIGH)**: goal→work/task.md는 증거물일 뿐, 어떤 경로도 레인 프롬프트에 주입 안 함. 규칙: 레인이 봐야 할 계약은 work_statement에 직접. (0702 조사빌딩 폴백 증상의 원인 확정)
2. **에러 인벤토리**: 발사경로 raise **101곳**(assembly 75 + spec 19 + onboard 7) vs 스킬 표 9행. 누락 대가족: route/reroute/hold, gates 계열, write_scope 상세(금지 세그먼트 .git/.env/.pem/secret 등), 노드 정체성(kind 중복 alias).
3. **one-call build() 표면**: output_root(goal-runs 하드코딩=벨 단절)·write_scope·**gates(인자 자체 없음=항상 완전무인)** 전부 미통과. 엔진 수정 후보: 세 인자 시그니처 추가+통과.
4. **스킬 오류 실측**: ① coo-review 주장은 top-level 경로만 참 — **per-node gates=는 coo-review도 HOLD를 박는다** ② '주말 default'는 날짜조건 로직 없음(서술 허구) ③ effort 어휘 EFFORT_LEVELS {none,minimal,low,medium,high,...} 실존, EFFORT_SCOPE는 gemini-local 제외 — 문서화 0 ④ model ref는 SHAPE 검증(스펠링 자유).

## 5. 문서 코퍼스 (150개 23,141줄)

- **헌법 정의처 확정**: Global Operating Rules 1-10 = `brick-6-surface-audit-repair-goal-0630.md`(469줄 골 문서 내부). 3축 헌법+Success 4항목 = `customer-ready-goal-phases-0629.md`. → 한 화면 standalone 헌법 문서로 추출 후보.
- 분류: active-canonical/stale ~44 / **아카이브 후보 ~108** (superseded ~20 + closed-record ~75 + stale무참조 ~8).
- 주의: GOAL/*.md는 symlink(대상만 이동+재연결), discipline-audit-0618.md는 leaked text 의심(일괄이동 제외), 이동 후 --all 필수(문서 path pin 존재).
