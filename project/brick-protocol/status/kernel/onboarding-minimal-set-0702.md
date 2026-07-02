# 고객 온보딩 최소셋 실측 (0702)

Status: support evidence only. read-only 조사(file:line 전수 근거, 추측 0) — 온보딩
Phase 2-3 빌딩의 task 입력. 배경: 레인 격리 실측(유저 우주 완전 차단, CLAUDE.md 라이브
프로브 포함)으로 "필요한 것만" 선별 가능해짐.

## 핵심 답 3개

1. **고객 COO 층은 브릭 MCP 등록 불필요** — 레인은 어댑터가 인라인 주입(--strict-mcp-config,
   adapter_local_cli.py:200-211/735-737), COO 운영은 CLI(brick build)+python 함수+스킬로 완결.
2. **온보딩(brick init)이 이미 갖춘 단계 전수**: PRESENT(doctor) → PROVIDER_REGISTER
   (~/.brick/providers.yaml) → **MCP_REGISTER**(claude mcp add + ~/.codex/config.toml) →
   **SKILLS_PLACE**(agent object에서 SKILL.md 렌더 → ~/.claude/skills/) → RECORDING(훅 복사·
   병합) → SLACK(report.env) → SMOKE → VERIFY. 전부 사용자 홈/임시 디렉토리만 씀(repo 무수정).
   전 단계 --skip-* 플래그 보유.
3. **"안 깔아도 된다" 확정 목록**: 고객의 개인 MCP/스킬/훅 전부 — 레인 격리가 어차피 차단
   (3사 메커니즘 상이하나 결과 동일). Slack/Dashboard도 선택(local-inbox 기본 동작).

## 최소셋 표 (요약)

| 필수 | python≥3.11 · uv · repo clone · pipx 진입점 |
|---|---|
| 선택(권장) | provider CLI 로그인(하나 이상) · 브릭 스킬 배치 · recording 훅 |
| 선택(옵션) | MCP 등록 · Slack 키 · Dashboard |
| 불필요 명시 | 개인 MCP/스킬/훅 일체 (격리 실측 근거) |

최소 실행형: `brick init --skip-plugin --skip-recording --skip-build`.

## Phase 2-3 빌딩에 넘길 판단거리 2개

1. **MCP_REGISTER 기본값 재검토**: COO 층에 MCP가 불필요하다는 실측과 "init이 기본으로
   등록"하는 현행이 어긋남 — opt-in으로 뒤집을지, COO층 MCP의 실효 도구가 있는지 확정.
2. **스킬 배포 경로 이원화**: SKILLS_PLACE는 agent object에서 SKILL.md를 **렌더**해 배치 —
   APPLY-LIST(agent/skills → live 복사) 계약과 별개의 4번째 표면. 두 경로의 정합(어느 쪽이
   고객 배포 정본인가) 결정 필요.

## P7 연계

P7 프레시머신 PASS 기준에 "유저 우주 무의존 프로브" 추가 후보: 격리 플래그 재현 실행에서
유저 지침 부재 확인(0702 CLAUDE.md 라이브 프로브 방법 — A/B 대조).
