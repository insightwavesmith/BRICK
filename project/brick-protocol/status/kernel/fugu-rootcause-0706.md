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
