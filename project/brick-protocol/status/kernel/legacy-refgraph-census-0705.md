# 레거시 참조-그래프 전수 원장 (0705, legacy-refgraph-0705 빌딩 산출)

출처: 조사 빌딩 task-statement-dcf04f800022-node — codex 6존 병렬 조사(2라운드, QA 표본
반증 2회 경유) 380행 인벤토리. 마감 주의: closure 레인이 2회 무산(1회 = COO 재개 시
소멸-워크트리 경로 전달 실수로 adapter-error, 2회 = adapter-error 홀드에 대한 forward
재개가 원장 무변경 no-op — 엔진 관찰로 백로그 통보)되어, **최종 집계는 COO가 레인
step-output 원자료에서 기계 집계(파이썬)로 대체 수행**했다. 원자료는 빌딩 증거 트리에
전부 보존. 이 문서는 조사 원장이며 처분 확정이 아니다 — 처분은 Smith/COO 몫.

## 분류 통계 (380행, QA 반증 5행은 unknown 강등 반영)

| 분류 | 건수 | 뜻 |
|---|---|---|
| live-runtime | 217 | 런타임 코드가 로드/실행 — 불가침 |
| live-doc | 56 | 정본 문서 체인 |
| live-checker | 43 | 체커·픽스처가 소비 |
| example | 8 | 예제·온보딩 소비물 |
| debris | 52 | 참조 0 잔해 |
| unknown | 4 | 판정 불가(QA 강등 포함) |

존별 행수: z1 brick/ 78 · z2 operator 67 · z3 checkers 15 · z4 agent/link 76 ·
z5 recording/connection/onboarding/루트 91 · z6 status 53.

## 처분 후보 (전부 후보 — 확정 아님)

1. **delete 후보 52건 = 전원 `__pycache__` 바이트코드 캐시.** git 추적 0건,
   .gitignore:2-3이 이미 무시 중 — repo 청소가 아니라 로컬 디스크 청소다. 처방 한 줄:
   `find <repo> -name '__pycache__' -type d -prune -exec rm -rf {} +` (재생성 무해).
   Smith가 폴더 탐색에서 본 "낡아 보이는 것들"의 정체가 대부분 이것.
2. **archive 후보(kernel 문서) 4건**: goal-loop-progress-0702night-0703am(진행기록 종료) ·
   handoff-0704-t10-dynamic-graph(인계 완료 — 역사 기록) · discipline-audit-0618(참조 무) ·
   기타 z6 판정분. kernel-archive-classification-0702.md 선례 절차(이동 원장 동반)로.
   ※ z6가 함께 표기한 reroute-adoption-hold-cases-0703 · session-continuity-mechanism-0703은
   인용 실존으로 **STAY**.
3. **move 후보 1건**: link/movement.yaml — 체커 2곳 참조 중이라 이동 시 참조 갱신 동반 필수.
4. **잔해 ~3,500 언트래킹(inbox·buildings)**: z6 패턴 규칙 — 완결/사망 빌딩의 이벤트·vessel
   잔해는 아카이브 이동, **걷는 중이거나 홀드 중인 빌딩의 증거는 보존**(원자료: z6 행들).
5. **손대지 말 것 316건**(live-runtime+live-checker+live-doc): 특히 "낡아 보이는" 계약
   표면(transition-concern-return, reroute-defaults 등)은 심장부다.

## 이 판이 남긴 실측 (T10 이후 첫 실전 — 스킬 각인 재료)

- 홀드 생애주기 전체 실측: QA 우려 → 자동 재파견 1회 → 우려 재발 → 복수 주소로 자동
  채택 거부 → COO forward → adapter-error → 재처분. 설계 의도대로 작동.
- 각인 후보 3건: ①조사류 QA 계약에 "반증 잔여는 재파견 제안 대신 강등 목록 반환" 조항
  ②재개 adapter_cwd 중립-워크트리 관례의 기계화(발사 전 린트) ③리포터 벨 다이제스트
  (판 하나에 벨 15개 실측 — 묶음 배달 후보).
- 엔진 관찰 1건(백로그): adapter-error 홀드에 대한 forward 재개가 원장 무변경 no-op으로
  귀결 — 기전 미규명, 조사 후보.

증거 한계: 조사 원장. source truth·성공 판정 아님. 개별 행 원자료는
project/brick-protocol/buildings/legacy-refgraph-0705/ 증거 트리.

## rev-1 재조사 追記 (t10rev1-0706n — 이동 실행 없음)

대상: 처분 후보 #2의 4번째 archive 후보 = "기타 z6 판정분".

재조사 결론: **unresolvable-by-evidence 확정(rev-1 재확인)**. 원본 z6 인벤토리
행을 이 워크트리에서 복원할 수 없다 — 추측으로 대체 후보를 지목하지 않는다.

뒤진 곳(탐색 도메인):
- kernel 루트 전 `*.md` 74개 열거 (`ls project/brick-protocol/status/kernel/*.md`).
- 전-repo 참조 재census: 각 kernel basename에 대해 `grep -rIl`(`.git`·`__pycache__`
  제외) 참조 카운트, 자기-파일 자기-언급 제외.
- `archive/0705-legacy-refgraph/` — 이미 이동된 3건 실재 확인
  (goal-loop-progress-0702night-0703am, handoff-0704-t10-dynamic-graph,
  discipline-audit-0618).
- `t10-drive-runbook-0705.md` §5 — 기존 rev-1 발견 레인 결과("증거상 특정 불가").
- 본 census 처분후보 #2 행(:30-34).

안 뒤진 곳 / 부재(탐색 불가 도메인):
- `project/brick-protocol/buildings/legacy-refgraph-0705/` 증거 트리 — 이 워크트리에
  **부재**(`test -d` = MISSING). 380행 z6 원자 인벤토리, 즉 4번째 후보를 지목한
  원본 행이 여기 없다.
- git 히스토리·타 워크트리·빌딩 세션 step-output 원자료 — 선언 write_scope 밖·로컬 부재.

재census가 원본을 대체 못 하는 이유(실측): (a) 0705 이후 repo 상태 표류 — 3건이
이미 archive로 이동돼 kernel 루트에서 사라졌고 0706 신규 문서가 추가됨; (b) 원본
z6 인벤토리 부재.

추측 금지 준수: 신선 재census의 참조 0 kernel 문서 7건(bundle11b-order-draft-0705,
fixture-graph-helpers-spec-0704, handoff-coo-0705night-continuous,
handoff-coo-0706afternoon, handoff-coo-0706evening,
handoff-external-audit-track-0705, onboarding-minimal-set-0702)은 대부분 0705/0706
최근 라이브 핸드오프·활성 초안으로 역사-완결 프로파일이 아니다 — **4번째 후보로
지목하지 않음**(본 census 원칙 #4·#5: 걷는/최근 빌딩 증거 보존).

이동 실행: **없음**. 4번째 후보의 archive 이동은 rev-2(후속 v2b 승인 빌딩) 몫이며,
본 追記는 발견-전용으로 파일 이동 0건이다.

증거 한계: rev-1 조사 追記. source truth·성공·품질 판정 아님. Movement 선택 아님.
