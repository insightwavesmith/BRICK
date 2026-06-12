# 작업 대기열 (선언, 0612) — Smith·운영자 합의분

선언일 뿐 실행 아님 (스케줄러 아님). 각 항목은 빌딩으로 착수될 때 이 문서에서 지워지고
그 빌딩의 장부가 진실이 된다. 갱신 주체 = 운영자, 승인 = Smith.

## 진행 중 (빌딩으로 가동, 0612)
- notify-v2-vessel-guard-voice — 알림 2차(대기열 0번) + F12 가드(대기열 7번) 묶음 — 보행 중
- f13-frontier-declared-edge-fallback-0612 — frontier 폴백이 그래프 선언행을 closed로 오독
  (F9/F9B 후 3번째 동일표면; notify-v2 보행 중 closed 투영으로 발견, 0612) — 보행 중

## 완료 (0612, 빌딩 닫힘·머지됨)
- f9 / f10 / f11 / onboarding(C3) / provider-ladder(D) — origin/main bf199ac 웨이브에 포함

## 대기 (빌딩 미착수)
1. 대시보드 델타 IAP 통행증 — **인프라 풀림(0612 실측)**: SA 개인키 서명 JWT +
   aud=정확한 endpoint URL(경로 포함)로 POST /ingest 200, 브라우저 즉시 델타 수신.
   남은 것 = report_sinks dashboard 싱크 Authorization 헤더 배선(작은 빌딩,
   notify-v2 머지 후 — 같은 표면 충돌 방지). 레시피 = 운영자 기억 + DEPLOY.md 반영 예정.
2. 제품판 깃헙 릴리스 — 태그 + 동네 제외 내보내기 + 새 클론 → install.sh → 첫 빌딩 실측 (운영자 직접)
   + 배포 버튼 2종(버셀=정적 사진 모드 / Docker호스트=실시간 모드) README 박기
   + AI-실행가능 온보딩 검증: 그쪽 운영자 AI가 문서만 보고 설치~대시보드까지 가는가
     (명령어·기대출력·실패신호 완비, README→DEPLOY.md 동선) — Smith 0612
3. 어댑터 도그푸딩 1호 — Smith가 직접 봉투 집기→일→제출 (+ 과금 분류 실측 = 설계서 전제)
4. F8 경로조각 휴리스틱 정밀화 — token/auth 단어 오탐 (3회 물림; 단일소스 원칙으로)
5. QA 바깥렌즈 계약 — QA 브릭 spec 개정: 증상 기반 독립재현 의무
   + 시공자 픽스처 재사용 금지 + 실진입표면 검증 1개 (F9 반쪽-green의 구조 처방, Smith 0612)
6. 함대 첫 실전 = 마당 회고 분석 (Smith 0612) — 도그푸딩 1호 후, recon-fleet으로
   전체 빌딩 장부를 다중렌즈 분석(무효패턴·QA품질·게이트행동·비용) → 개선 대기열 도출
   (claude 렌즈 1 포함; 함대 preset의 첫 실전을 자기 회고로)

7. (→ notify-v2-vessel-guard-voice 빌딩으로 착수됨, 0번과 묶음) F12 벨 자기간섭+헛벨 —
   외부 싱크는 진짜 그릇(project/) 소속 빌딩만, 임시 output_root 빌딩은 자기 루트
   우편함까지만. 수리 후 열쇠 재활성화(~/.brick/report.env.disabled → report.env).

## 닫힌 결정 (참조)
- 박제(임포터)는 유지하되 "빌딩 밖 작업 후 사후신고" 패턴은 금지 (Smith 0612)
- 시공 = codex(gpt-5.5 xhigh) 전용, claude = 운영+검수(D 이후 렌즈 1) (Smith 0612)
- 대시보드 = 자가배포 모델, 인증은 인프라 위임 (Smith 0612)
