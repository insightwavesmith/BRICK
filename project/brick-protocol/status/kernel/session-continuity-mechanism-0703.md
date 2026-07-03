# 세션이어짐 기전 실측 정본 (0703 — COO 프로브, 배선 빌딩의 task 입력)

Status: support evidence only. audit-0703 4번 항목의 선결 조사 완결판 — 감사의 "공유
~/.codex SQLite 락 선결" 가정을 실측으로 대체한다.

## 실측 결론 3줄

1. **세션이 안 이어지는 직접 기전은 락이 아니라 홈의 수명이다**: codex 레인은 디스패치마다
   `tempfile.TemporaryDirectory(prefix="bp-codex-home-")`로 새 임시 CODEX_HOME을 만들고
   (adapter_local_cli.py:579), with 블록 종료 시 삭제한다(:275-283에서 env 주입). 세션
   영속화를 켜도 기록이 임시 홈과 함께 죽는다.
2. **공유 ~/.codex 락 문제는 현 구조에 비적용**: 레인은 ~/.codex를 직접 쓰지 않는다 —
   자격 파일만 임시 홈으로 복사(:288-303). 감사가 걱정한 동시빌딩 데드락의 전제가 없다.
3. **claude 레인은 실 HOME**(키체인 인증 제약, :106-113) — 세션 저장은 이미 영속.
   빠진 것은 attempt N의 세션 id 포착과 N+1에서의 `--resume <id>` 발급뿐.

## 배선 처방 (같은 빌딩 내 attempt 한정 — 타 빌딩 재발주는 새 세션이 맞음)

- **codex**: 임시 CODEX_HOME을 attempt-스코프 → **building-스코프**로 승격(워크트리
  `_worktree_path_for`의 building_id 키 선례 그대로). 빌딩별 홈 = 빌딩별 세션 저장 =
  락 공유 없음 → 동시성 선결 조건 자동 해소. attempt N>1에서 `codex resume --last`
  (같은 홈 안에서는 유일 세션) 또는 세션 id 추적. 빌딩 종료 시 홈 정리(기존 reaper 계열).
- **claude**: 실 HOME 그대로 두고, attempt N 반환에서 세션 id를 support 사실로 기록 →
  N+1 디스패치에 `--resume <id>`. `-c`(최근 세션)는 병행 빌딩과 섞이므로 금지.
- **모드 배선**: `session_continuity_mode`의 `continue_if_available`을 위 두 경로로 구현
  (4개 값 선언·admitted 확인됨 — agent_adapter.py:79-81,409-412; 현 배선은 none의
  `--no-session-persistence` 한 줄뿐 — adapter_local_cli.py:749).
- **관계**: Link Part1~3(종이 배달)과 보완 — 세션이 이어지면 재주입 필요가 줄고, 안
  이어지는 케이스(타 빌딩 재발주 등)에선 배달이 안전망(guide-2 §4 그대로).

## 검증 안 된 것

- codex 임시 홈 안에서 세션 영속화가 실제로 저장되는지(--no-session-persistence 제거 시) —
  배선 빌딩의 첫 프로브로.
- claude 세션 id의 비대화(-p) 모드 노출 방식(반환 JSON의 session_id 필드 여부) — 동상.
- gemini 레인은 세션 재개 개념 자체 미조사(후순위).
