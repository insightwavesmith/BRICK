# COO 인수인계 — 0706 오후 세션 마감

세션 종료 사유: COO 도구 호출 문법 반복 파손(course/<Bash> 오출력 → 페이블→오푸스 전환). 알려진 세션-말 실수 클래스(메모리 brick-coo-operating-rules 각인). 안전을 위해 발주·수리 정지, 여기서 마감. **산출 손실 0.**

## 진입 정본 (새 세션이 먼저 읽을 것)
1. project/brick-protocol/status/kernel/goal-phases-consolidated-0702.md §마스터 잔여 큐 (§A~E·R·무마찰 절·초안기 #15·build()통일 #12) — 처분 단일소스
2. project/brick-protocol/status/kernel/fugu-rootcause-0706.md — 푸구 사망 근본원인 확정(즉시 수리감)
3. project/brick-protocol/status/kernel/postmortem-deep-0706a-diagnosis-synthesis.md — R1~R9 처방 정본
4. operator-ergonomics-wave-0705.md 표 13~18 (신규 실수 클래스)

## git 상태
로컬 HEAD = 54c6f684 (fugu 근본원인 문서). origin = 432451c7 (R4 랜딩분). **미push 1 = fugu 문서 커밋** — 새 세션 첫 작업: 이 문서까지 스윕&&push(또는 다음 --land에 동승). 수동 push 금지 규율은 --land 경유로 충족.

## 걷던 것 / 즉시 처분
| vessel | 상태 | 처분 |
|---|---|---|
| r3-fanwatch-0706a | work 걸음 중(팬 사망 감지 R3, 소켓 생존) | boundary 도달 시 러너 게이트→--land. **최우선**(다른 것 다 멈춰세우던 결함) |
| R4 land 스윕 | 백그라운드 --all 진행 중이었음 | 완료 확인 후 push 도달 여부 점검(미도달이면 재-스윕&&push) |
| r1identity-0706a | 게이트 NEEDS-OPERATOR | **재파견**: 정체성 가드가 wheel 설치면(pyproject 없음) 거부해 brick --help 깨짐 → 설치 vs 소스 모드 구분 |
| r5r8domain-0706a | 게이트 VACUOUS | **재파견**: 도메인 조항이 체커에 안 물림 → 실제 게이트하도록 |
| cpath-mirror-0706a/b | 무유서 사망 2회(=푸구 도구불일치) | 주차. **푸구 수리 후 재발사 or COO-직접**. concern-path는 loud 거부로 안전 봉인 중 |

## 푸구 근본원인 (fugu-rootcause-0706.md 요약 — 새 세션 즉시 수리)
Sakana API가 codex 기본 `tools` 목록의 `image_generation`을 거부(function·custom만) → fugu 레인이 첫 API 콜에서 즉사, 무유서(Case 9 위장). auth·config·복사·슬롯 전부 정상 배제됨. **수리(단순)**: adapter_local_cli codex-exec argv에서 sakana 라우팅 시 미지원 도구 제거 `-c` 오버라이드 + fugu-ultra 메타데이터 등록. **푸구 정책(0706)**: work 위험-비례 승격 티어 — 수리 전까지 푸구 캐스팅 보류.

## 마스터 잔여 큐 (우선순위)
1. **R3 랜딩** (걷는 중, 최우선 — 자율운행 반복 위협 봉합)
2. **푸구 도구불일치 수리** (fugu-rootcause 문서 기반, 단순, 재현명령 있음)
3. **R1·R5R8 재파견** (실물 결함, 좁음)
4. cpath 미러 수술(COO-직접 or 푸구 수리 후) → R2 → 자기잠금 (walker_kernel 직렬)
5. R9 모델-레인 규율 정합 · Case 8 정찰 (소형·병렬)
6. #15 가중치→그래프 초안기 + #12 build() 단일진입 (R웨이브 후, cli/assembly 이음새)
7. T10 fresh 0705c (저우선, 스탬프)

## 오늘 랜딩(원격 봉인) 19건 요약
W1 웨이브 전체(K1'·K2'·K4') · walker 미러 수술+도그푸드 · wheel B+하이지엔 · A+ W2(공허검증 차단) · expand() · erg5(자동앵커)+erg6(--graph-decl=무마찰 판정선 도달) · 11B 후속 · 부검-딥 1회차(3두뇌, R1~R8 채택) · R4(어댑터 유서). 주차 vessel 7기 원장 마감. 도구: coo_gate_runner.sh(게이트+--land, 수동 머지·push 대체).

## 콘솔
Artifact: https://claude.ai/code/artifact/b7c11b80-62ee-4d67-a063-6eb70c8a8e03 (한국어 체크리스트, 상태 바뀔 때 재배포).

## 새 세션 각인
- 긴 연속 운행 시 도구 호출 문법 자기점검(이 파손이 세션 말 반복). cwd 리셋 함정: 발사는 cd repo && 선행 or 절대경로.
- 머지·push 수동 금지 — coo_gate_runner.sh --land 전용.
- CLI 발주는 repo 자신 .venv/bin/brick + --repo 명시 + --adapter adapter:codex-local(--real-provider 무-adapter는 프리셋별 캐스팅 드리프트, 표 17).
