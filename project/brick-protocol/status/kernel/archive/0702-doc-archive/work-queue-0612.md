# 작업 대기열 (선언, 0612) — Smith·운영자 합의분

선언일 뿐 실행 아님 (스케줄러 아님). 각 항목은 빌딩으로 착수될 때 이 문서에서 지워지고
그 빌딩의 장부가 진실이 된다. 갱신 주체 = 운영자, 승인 = Smith.

## 진행 중 (빌딩으로 가동)
- (없음 — 0612 밤 기준)

## 완료 (0612, 빌딩 닫힘·머지됨)
- iap-dashboard-sink-passport-0612 — 대시보드 싱크 IAP 통행증(SA서명 JWT Authorization,
  키env 게이트) — 코드 e8f38fd, 증거 ad04a71; 실물 E2E http_2xx; 대기열 1번 마감
- f14-claim-trace-manifest-adapter-error-0612 — 어댑터-에러 홀드 후 폐장 시 claim_trace/
  매니페스트 불일치 수리(보존 방식)+재조정 동사+체커 핀 — ad04a71; iap·f14 실루트 재조정 완료
- f13-frontier-declared-edge-fallback-0612 — frontier 폴백이 그래프 선언행을 closed로 오독
  (F9/F9B 후 3번째 동일표면) — 폐장·머지·푸시 origin/main 2005c07 (0612 저녁);
  변이 RED 체커 핀 동봉, 운영자 FIRE 6종 직접 실행 green
- notify-v2-vessel-guard-voice — 알림 2차(0번) + F12 가드(7번) 묶음 — 폐장·머지 ec6ddfd (0612 낮)
- f9 / f10 / f11 / onboarding(C3) / provider-ladder(D) — origin/main bf199ac 웨이브에 포함

## 대기 (빌딩 미착수)
0. 어댑터-에러 경로 다지기 — F15(첫 스텝 에러 시 출생증명서 미기록→재개 불가;
   우회=overwrite 재발주) + F16(종이-stop 부재: 에러홀드 stop이 멈춘 스텝을 LIVE 재실행)
   + 옛 에러홀드 3동(provider-ladder, dashboard-productization ×2) stop 마감 묶음 (0612 실측)
0b. 폐장 템플릿 소수선 — parent_goal_delta_status 값 안에 'status' 키 유도 방지 힌트
   (codex 2/3회 양식 위반 실측; Smith 승인 0612)
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

7. (완료 — notify-v2 빌딩에 묶여 머지됨, 0612) F12 벨 자기간섭+헛벨 가드.
   열쇠 재활성화됨(~/.brick/report.env 활성).

## 닫힌 결정 (참조)
- 박제(임포터)는 유지하되 "빌딩 밖 작업 후 사후신고" 패턴은 금지 (Smith 0612)
- 시공 = codex(gpt-5.5 xhigh) 전용, claude = 운영+검수(D 이후 렌즈 1) (Smith 0612)
- 대시보드 = 자가배포 모델, 인증은 인프라 위임 (Smith 0612)
