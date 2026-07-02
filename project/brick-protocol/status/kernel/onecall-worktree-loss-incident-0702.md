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
