# P7 프레시머신 증명 (0703 — 현행 공식 경로 재증명, 0630 선례 갱신판)

Status: support evidence only. COO 운영자 프로브 실측 기록(스크립트 반복 실행, 로그 보존).
0630 선례(archive/0702-doc-archive/customer-ready-p7-current-origin-fresh-clone-proof-0630.md)를
현행 엔진으로 재증명 — 당시 경로(`--graph` CLI)는 폐기(헌법 Rule 10)됐으므로 공식 DSL 경로로.

## 최종 프로브 (PASS — 0703 14:13, 프로브 루트 /tmp/brick-p7-coo-proof-v2-20260703T141340)

| 단계 | 결과 | 증거 |
|---|---|---|
| D1a fresh clone (origin/main) | rc=0, HEAD=`3f45fd35` | logs/01-clone.out |
| D1b uv sync --locked | rc=0 | logs/02-uv-sync.out |
| D2 대화형 수집기+등록 (22a9080e 랜딩분) | rc=0 — codex/model:codex:default, providers.yaml 반영 | logs/04-intake.out |
| D3 공식 build (DSL one-call, codex-local work→closure) | 걸음 완주(agent returns 2) → **게이트 HOLD**(fake_landing_write_scope_diff_absent — 무diff 데모라 설계 발화) | logs/05-build.out |
| D4 사람 forward 처분 | ok=True, disposition_written=True → **frontier_kind=complete** | logs/06-dispose.out |

**의미**: 고객 전 사이클(설치→온보딩→발주→완주→게이트→도장→완공)이 프레시 환경에서 통째로
성립. D3~D4의 게이트 사이클은 0703 수리 3부작(09fa10c4 홀드 신원 → ca3b34c0 게이트의 처분
소비)의 라이브 종단 증명이기도 하다.

## 과정에서 캔 갭 (P7의 갭-추출 목적 적중 2건 — 전부 당일 수리·랜딩)

1. **게이트 홀드 처분 불가**(onboard.py:3366 fail-closed — 홀드 신원 미기록): 고객이 게이트에
   걸리면 갇힘 → 09fa10c4.
2. **처분 미소비**(forward 도장 후에도 재걸음이 게이트 재발화 → 영구 대기): → ca3b34c0
   (게이트가 원장의 처분 사실을 소비, 정체-일치 스코핑, 변이-RED pin).

## 캐비앗 (not_proven — 0630 선례와 동일 계열 + 신규 1)

- codex 자격은 실 홈에서 프레시 홈으로 **복사**(브랜뉴 인간의 로그인 transcript는 미증명).
- gh auth 없는 프레시 홈에서 doctor가 정확히 진단·안내함은 확인(정직 rc=1), 실제 신규 gh
  로그인 흐름은 미증명.
- **레인 샌드박스 네트워크 차단 실측(신규)**: fresh-clone 증명은 빌딩 레인으로 구조적 불가
  (DNS 차단) — P7류 프로브는 운영자 실행이 정답(빌딩 경유 1차 시도의 QA가 이를 정직 검증).
- provider 신뢰성·반복 재현성은 이 1회+0630 선례 외 미증명(P8이 갭 추출기로 이어받음).

## 프로브 이력 (같은 스크립트, 수리 전후 대조 — 로그 전부 보존)

- 1차(11:04, 빌딩 경유): 레인 네트워크 차단 실측 — 운영자 프로브로 전환.
- 2차(11:17, 운영자): clone·sync·온보딩·걸음 green, **갭 1 적중**(처분 fail-closed).
- 3차(12:04, 운영자): 갭 1 수리 후 — 처분은 성립, **갭 2 적중**(처분 미소비, 영구 대기).
- 최종(14:13, 운영자): **전 사이클 PASS** (본 문서).
