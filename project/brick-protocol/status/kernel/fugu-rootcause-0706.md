# 푸구(fugu-ultra) 사망 근본원인 — 확정 (0706 오후, 재현으로 증명)

## 증상
codex-fugu-local(sakana:fugu-ultra) work 레인이 대형 발주에서 유서 없이 조용히 죽음(Case 9로 위장). cpath 수술 2연속 사망. 부검 진단 C(짧은 read-only)는 타이밍 운으로 통과.

## 근본원인 (격리 temp CODEX_HOME 재현으로 확정 — auth·config 전부 정상 배제 후)
격리 환경 실측 재현 결과:
```
ERROR: {"error":{"message":"Invalid value: 'image_generation'. Supported values are: 'function' and 'custom'.","type":"invalid_request_error","param":"tools","code":null}}
```
= **Sakana API가 codex 기본 요청의 `tools` 목록 중 `image_generation`을 거부**한다(sakana는 function·custom만 허용). codex는 매 요청에 자기 도구 세트를 실어보내는데, sakana 백엔드가 그 요청을 통째로 튕긴다 → 레인이 **인증이 아니라 첫 API 콜에서 즉사**. adapter-error도 안 남아 무유서(Case 9 위장).
부수: `warning: Model metadata for fugu-ultra not found` — 메타데이터 미등록(성능 저하 경고, 치명 아님).

## 정상 배제된 것 (전부 실측)
- auth command: temp home에서 OK (codex-fugu-token이 복사된 .env 읽음)
- provider 오버라이드: sakana 15개 전부 재발행됨(auth.command 포함 — 첫 "3개만" 판단은 앞 8개 자름 착시, 정정)
- credential 복사: auth.json+.env 정상 복사(158행)
- 슬롯 전환(2→1): ~/.codex/.env 반영, temp로 복사됨 — 키는 최신·유효

## 수리 방향 (새 세션 — 단순)
adapter_local_cli의 fugu(sakana-routed) 디스패치 argv에서 sakana 미지원 도구를 제거하는 `-c` 오버라이드 추가 — codex의 tools 목록에서 `image_generation`(및 sakana가 거부하는 기타)을 빼거나, sakana 라우팅 시 tools를 function/custom로 제한. 지점 = support/connection/adapter_local_cli.py codex exec argv 구성부. 픽스처: 격리 temp home + sakana 라우팅으로 tools-거부 재현→제거 후 pong.
동반 처방: fugu-ultra 모델 메타데이터 등록(경고 제거). 이 사망이 Case 9(무유서)로 위장된 것 자체가 R3(사망 감지)의 가치 재확인.

## 실측 명령 (새 세션 재현용)
T=$(mktemp -d); mkdir -p "$T/.codex"; cp ~/.codex/.env ~/.codex/auth.json "$T/.codex/"
printf 'reply pong\n' | CODEX_HOME="$T/.codex" codex exec --skip-git-repo-check --ignore-user-config \
  -c 'model_providers.sakana.base_url="https://api.sakana.ai/v1"' -c 'model_providers.sakana.wire_api="responses"' \
  -c 'model_providers.sakana.auth.command="/Users/smith/.local/bin/codex-fugu-token"' \
  --model fugu-ultra -c 'model_provider="sakana"'
→ tools image_generation 거부 에러 재현.

## 0706 저녁 정정

이 절은 기존 본문을 보존한 채 붙이는 정정 evidence다. 기존 본문은 오후 재현 기록으로 남기고, 저녁 시공의 근거 실측 1~5는 아래로 고정한다.

1. fugu-451-obit에서 보강할 직접 원인은 live provider 재현이 아니라 fixture로 재현 가능한 `451` / `content policy` 거부 신호다.
2. adapter 비정상 종료 분류는 stderr뿐 아니라 `codex exec --json` stdout JSONL의 `error` 및 `turn.failed` 이벤트에서도 같은 신호를 읽어야 한다.
3. stderr가 경고/소음일 때 유서의 `message_excerpt`는 stdout JSONL에 들어 있는 provider 실제 오류 문장을 먼저 보존해야 한다. 비밀 스크럽 경계는 유지한다.
4. adapter_error_frontier root-state guard는 걷는 Building 자신의 정상 산출물 루트에 있는 same-Building `raw/adapter-error.jsonl` 행을 full adapter-error frontier evidence로 받아야 한다.
5. foreign root 또는 다른 Building의 `raw/adapter-error.jsonl` 행은 계속 fail-closed로 남겨야 한다.

검증 경계: live provider CLI 호출은 금지한다. receiving lane에서 실행 가능한 증거는 fixture checker green 및 변이 RED 기록뿐이다.
