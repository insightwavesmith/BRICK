# 사건 기록: 원콜 빌딩 워크트리 소실 + 미완 처분 작업물 유실 (0702)

Status: support evidence only. Not source truth / success / quality / Movement authority.
COO 직접 기록 — 증거는 전부 실측 행. 새 결함 가족 2종의 첫 관측.

## 타임라인 (UTC, 실측)

| 시각 | 사건 |
|---|---|
| 02:42:57 | 빌딩 A 발사 (`task-statement-a42afe59a712`, one-call build, 원콜 인자통과 구현) |
| ~02:42~02:5x | A의 design/work/code-qa/axis-qa 4걸음 정상 반환 (영수증 received 5 : return 4) |
| 02:57:29 | 빌딩 B 발사 (`task-statement-41515ae4ccc3`, 슬랙 수리) — **A의 closure 직전 창** |
| 02:5x | A의 closure 디스패치 → adapter-error `error_kind=local_cli_missing`, message `[Errno 2] No such file or directory: '/Users/smith/.brick/worktrees/ta…'` — **워크트리가 이미 없음** |
| 이후 | A: link paused → `frontier=agent_incomplete`, `ok=false`, `commit_sha=""`, `worktree_disposed=true` |

## 결함 가족 1 — 워크트리 소실 (병행 간섭 용의, 원인 미확정)

- 사실: A의 워크트리가 axis-qa 완료와 closure 디스패치 사이에 디스크에서 사라짐.
- 용의: 같은 창(02:57:29)에 발사된 B의 샌드박스 생성/정리 경로. 단 `driver.py`에서
  prune/rmtree 교차정리 로직은 grep으로 미발견 — **메커니즘 미확정**. git 자동
  worktree prune(gc.worktreePruneExpire) 등 대안 가설 열려 있음.
- 임시 규칙(원인 확정 전까지): **빌딩 단독 발사** — 앞 빌딩 frontier 확인 후 다음 발사.
- 원인 재구성 + 항구 수리는 태스크 #6 (dispose/보존 빌딩)에서.

## 결함 가족 2 — 미완 처분 작업물 유실 (설계 확정 사실)

- 설계: `_run_in_worktree_sandbox`는 "COMMIT on GENUINE completion only" — 미완이면
  커밋 없이 워크트리 처분.
- 결과: A의 work 레인은 `made_changes=True`였으나 `git fsck` dangling에도 커밋 없음 —
  **구현이 통째로 유실**. resume도 불가(adapter_cwd 소멸).
- 함의: 미완 빌딩의 처분은 복구 불가능한 파괴다. 엔진 보완 후보 = 미완 시 WIP 스냅샷
  커밋 또는 워크트리 보존(태스크 #6).

## 처분 기록

- A는 동일 task로 단독 재발사 (02:5x 이후, 슬랙 수리 랜딩 뒤) — 벨 수리 라이브 검증 겸용.
- brick-task-author PHASE 3.2 분류표에 두 가족 행 추가 (0702).
- 관련: 슬랙 수리 빌딩 fe6ccb5 (벨/구조도 — 본 사건과 별개 결함), 태스크 #1(재발주)/#6(보존).

## 원인 확정 (0702 후속 — run 2 재현 후 코드 실측)

run 2(완전 단독 발사)도 동일 지문으로 사망 → 병행 "빌딩" 간섭 가설 기각. 실체:
`support/operator/worktree_sandbox.py`의 `create_worktree_sandbox()`가 생성 시마다
`reap_stale_worktrees()`를 호출하는데, **reap에 생존(liveness) 검사가 없다** — 마커
(`.brick-engine-worktree`) 달린 `~/.brick/worktrees/` 아래 엔진 워크트리를 무조건
전부 강제 제거한다. 즉 어떤 경로로든(다른 빌딩 발사, 샌드박스를 만드는 체커 픽스처)
새 샌드박스가 생기는 순간 **돌고 있는 모든 빌딩의 워크트리가 파괴**된다.
- run 1 트리거: 02:57:29 빌딩 B 발사의 샌드박스 생성 (타이밍 일치).
- run 2 트리거(유력): 같은 창에 COO가 실행한 pin 프로파일의 샌드박스 생성 픽스처.
- 오전 빌딩들의 생존은 우연(해당 런 창에 샌드박스 생성 부재).
- 수리 방향: reap에 liveness 게이트(소유 런 사망 증명 시에만 제거) + 픽스처용
  엔진 워크트리 루트 격리(전역 `~/.brick/worktrees` 고정이 픽스처-실런 충돌의 뿌리).
- 임시 규칙 강화: 수리 랜딩 전까지 **빌딩 실행 중 어떤 발사·체커 스윕/프로파일 실행도 금지**.

## 3차 발생 (0702 오후 — paused 가족 + COO 게이트 과실)

- doc-archive 빌딩(link_paused, 정상 concern 홀드)의 워크트리가 bracket 종료 시 무조건
  dispose로 소멸 — **108건 문서 이동 작업물 유실 + resume 불능**. paused는 정상 경로라
  이 구멍은 매 홀드마다 작업물을 태운다 (가족 2의 paused 아종).
- 원인: reaper 수리(bec5b16)가 deliverable 2(미완 처분 보존)를 미구현한 채 랜딩 —
  **COO 3중 게이트가 deliverable 번호 전수 대조를 누락**한 검증 과실(자가 기록).
  게이트 규칙 보강: closure 대조는 deliverables 번호별 구현/미구현 전수로.
- 수리: dispose-preserve 빌딩 (미완 시 WIP 스냅샷 커밋+SHA 기록). 랜딩 전까지
  **concern-HOLD 가능성 있는 빌딩 발주 보류**.

## 종결 (0702 저녁 — 수리 랜딩)

- **가족 1(reap 파괴)**: bec5b16 liveness 게이트로 종결.
- **가족 2(미완 처분 유실)**: 0741a56 WIP 스냅샷+refs/brick/wip 앵커로 종결 — 홀드/미완은
  이제 SHA 회수 가능 사건이다. D3(evidence 스트림 기록)은 부분완성 수용, 소형 후속.
- 부수 확립: raise(예산 주입) 처분 실전 검증 / 기본 예산 5(reroute-defaults.yaml)의 DSL
  자동 적용은 인체공학 4번 / 운영 규율 "워크트리 게이트 조작 전 커밋" 추가(COO 자가 유실
  1회 반성 — 총 유실 6회 중 5회 엔진, 1회 운영자).
- 시공 여정: v1·v2(원콜, 자기 함정에 소각) → v3(레거시 홀드-안전 경로) → 홀드 →
  **raise 실전 성공** → 완주 → COO 도구 실수 유실 → 픽스처 스펙 기반 재구현 → 랜딩.
