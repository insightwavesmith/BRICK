# HANDOFF — 0710f (파블5 재개용 · 안전장치로 세션 조기 마감)

| 항목 | 값 |
|---|---|
| 기록 | 2026-07-10 오후 13:4x KST · Claude COO(파블5, 개발예외 세션) |
| 마감 사유 | Smith: "안전장치 걸렸다 페이블로 다시 열어야 함" — 세션 강제 재개 |
| checkout | `/Users/smith/projects/BRICK` |
| HEAD | `3e3b40975` (**push됨** — origin 동기) |
| repo dirty | **deku뿐** (deku는 Smith 직접 처리 선언 — 무접촉) |
| 진입정본(직전) | `HANDOFF-session-0710d-codex-to-fable5.md` → `CLOSURE-report-0710e-fable5-dev.md` |
| This | `HANDOFF-session-0710f-fable5-reopen.md` |
| 규율 | **믿지 말고 실측 대조.** 좌표는 HEAD 3e3b40975 기준 |

## 0-갱신 (마감 직전 회수 완료 — 아래 원문 §0의 "실행 중"은 종료됨)

```text
★발주1 reroute 완주 회수됨: 공식 reroute 처분 ok:True · 11/11 반환(재주행 포함) ·
  work2(gpt-5.6-sol)가 실제 구현함 — refs/brick/wip/l3-admission-allowlist-0710e에
  검증 앵커(wip_commit_verified): check_import_identity_modes.py +118 + 대상 체커 7파일
  allowlist 등록(+15씩) + adapter_capability_checks +30.
  frontier = link_paused (human-review 게이트 재대기).
  ★다음 세션 첫 작업: 이 WIP 내용 검수 → forward 처분(brick resume --decl) → land
  → import_identity_modes + 대상 프로파일 focused로 admission RED 소거 검증.
  (수리된 anchor 가드가 혼합 dirt를 정상 앵커한 첫 실전이기도 함)
★병렬 세션 주의: 마감 시점에 live repo에 내 것 아닌 dirty 2파일 관측
  (check_building_operator_driver0.py +82 · worktree_sandbox.py ±62/-49 재작업 흔적)
  + 미지 커밋 d721b697f — 다른 파블 세션이 이미 작업 중인 정황. 한 트리 두 손 금지:
  재개 세션은 먼저 어느 세션이 살아있는지/그 dirty가 누구 것인지 실측 대조부터.
```

## 0. ★지금 실행 중 — 죽이지 말 것 (최우선 회수 대상)

```text
발주1 reroute 재주행: l3-admission-allowlist-0710e
  무엇: 게이트 pause에서 공식 reroute 처분(brick resume --decl) → work attempt 2 실주행 중
  PID(마감시): brick python 3405 · work의 codex exec 4602 (gpt-5.6-sol xhigh)
  decl: <직전세션 scratchpad>/resume-l3-reroute.json (re_instruction은 endline 규칙 3조 준수:
        Done 종료선 재진술 + 실행가능 증명명령 + 범위밖은 COO게이트 반환 지시)
  evidence root: /Users/smith/.brick/project/brick-protocol/buildings/l3-admission-allowlist-0710e
  기대 흐름: work2(구현) → QA 3렌즈 replay → closure2 → human-review 게이트 재pause
  회수법: 프로세스 종료 대기 → frontier 관측 → 게이트 재pause면 검수 후
        forward 처분(brick resume --decl, on="declared Link transition_lifecycle.state is paused")
        → land 확인(refs/brick/landed/l3-*) → import_identity_modes + 대상 프로파일 focused 재실행
        으로 admission-원인 RED 소거 검증. 프로세스가 죽어 있으면 live2 회수 절차(관측→보존확인→재개).
  1차 시도 기록: work가 codex code-mode host 부재로 made_changes=False → QA가 replay_needed·
        verification_gap 적발 → closure가 implementation_gap+crosscheck(D1 diff 없음) 정직 반환
        → 게이트 pause. 전부 계약이 옳게 작동한 것. 환경 수리 후 reroute한 게 현재 주행.
```

## 1. 이 세션(0710e)이 끝낸 것 — 전부 push됨

```text
커밋 4: 7b25eb0d5(recast 9파일) · f71d67db2(dev 63파일: WO-1/2/3/4 + 소실문맥수리+O1-O3배선)
       · fd7eee385(커널문서 10) · 3e3b40975(E2E발 가드수리) → origin/main 동기
검증: --all delta-green(세션 신규 RED 1건→수리→0, 기준선=deku/admission/legacy 클래스,
     HEAD 임시worktree 대조법 — CLOSURE §3) · driver0/cli_entrypoint/resume_declaration/
     import_identity_modes focused 전부 PASS
O1 라이브 E2E 종결: freeze→digest forward→실발사(opus)→게이트pause→공식 resume
     (보존 worktree 그대로 재개=workspace continuity)→complete→landed
     refs/brick/landed/order-smoke-review-0710-c3a076b0a917→WIP release→dispose 실처분.
     ★E2E가 실전에서 가드 결함 3발화점(anchor 혼합거부/dispose ignored-only 좀비화)을
     잡아 수리시킴 = 3e3b40975
환경 수리: codex-code-mode-host 심링크(~/.local/bin ← ChatGPT.app Resources).
     오늘 08:53 앱 업데이트로 깨졌던 것 — 5.6sol 실행의 전제조건
정본: CLOSURE-report-0710e-fable5-dev.md(세션 전체) · queue §9.7 · 보드 ΦI #2/#3 갱신
```

## 2. ★발주2 — 준비됨·미발사 (다음 세션 두 번째 작업)

```text
proposal-root-reuse-0710e: stop→forward가 proposal root 재사용 못하는 결함 수리 발주
  task: <직전세션 scratchpad>/task-proposal-reuse.md (D1~D3+종료선)
  decl: /Users/smith/.brick/drafts/proposal-root-reuse-0710e-decl.json
  ★마지막 상태 = compose 실패 1건 남음 (한 줄 수정):
    deep-design 노드의 "model": "claude:claude-fable-5" → "model:claude:claude-fable-5"
    (admitted prefix 오류 — 에러문이 정확히 안내함)
  Smith 지시 반영: 기획=fable-5 xhigh, 개발=gpt-5.6-sol xhigh (recast 표 그대로)
  발사 절차: decl 수정 → build --graph-decl (stop, --overwrite-existing) →
    캐스팅표에 deep-design=claude-fable-5 확인(★아래 §3 함정 주의) → --forward
  ★발주1 land 후 발사 (순차 — rate limit 보호)
```

## 3. ★이 세션이 새로 발견한 결함 (미수리 — 후속 발주감)

```text
decl 캐스팅의 조용한 치환 (핸드오프 0710d §4-8 잔여의 발현):
  실측: decl 노드에 selected_model_ref="...fable-5"를 명시해도 composed plan은 opus-4-8.
  기전(추적 완료): assembly 노드번역(assembly.py:1015-1027 부근)은 짧은 키
    (adapter/model/model_ref)만 declared로 인정. selected_* 키는 opts로 통과되지만
    declared_model 플래그가 안 서서 "adapter만 선언" 판정 → DEFAULT_MODEL_REF_BY_ADAPTER로
    모델 자동충전이 명시값을 덮음. work 노드에서 안 보였던 이유 = dev 레인 기본과 우연히 일치.
  올바른 표면: decl에서는 짧은 키 사용 ("adapter": "claude-local",
    "model": "model:claude:claude-fable-5", "reasoning_effort_ref": "effort:xhigh").
  ★수리 발주감: decl 노드에서 selected_* 키를 fail-closed 거부하거나 정식 인정하도록
    (조용한 치환은 캐스팅 규칙 C1~C3 위반). DESIGN 문서 결정①과 연결.
fable-5 실사용 검증: 아직 실발사 0회 — 발주2의 deep-design이 첫 실전.
  admission은 recast로 열려 있음(un-retired). 치환 함정만 피하면 됨(위 짧은 키).
```

## 4. 나머지 잔여 (우선순위순)

```text
1. 발주1 회수→forward→land + admission RED 소거 검증 (§0)
2. 발주2 한줄수정→검수→발사→회수 (§2)
3. E2E 후속: --all 재스윕(발주1·2 착지 후 admission/assembly 클래스 소거 확인)
4. stash@{0} 태그 보존 — GO 대기 중 (명령: git tag archive/stash/2026-07-08-pre-c2-landing 'stash@{0}')
5. decl selected_* 조용한 치환 수리 발주 (§3)
6. n2 완전형 단판(임의root+프로세스 재시작+reroute+바이트+land 한 판) — 조각별 증명은 완료
7. DESIGN 미결 5건 + 슬랙 기본싱크 여부 (Smith)
8. wip 80 기착지분·live2 실빌딩 정리 (Smith 처분)
※ deku 전부 = Smith 직접 (이 세션부터 무접촉 지시)
```

## 5. 경로

```text
정본: CLOSURE-report-0710e-fable5-dev.md · AUDIT-full-consolidated-dev-handoff-0710.md(WO 스펙)
     · DESIGN-order-chain-casting-vocabulary-0710.md(발주체인·캐스팅·어휘 설계)
     · route-replay-choice-shape-ledger-0710.md · queue §9.6/§9.7 · 보드
발주 재료: ~/.brick/drafts/{l3-admission-allowlist,proposal-root-reuse}-0710e-decl.json
     + task 본문·resume decl은 직전세션 scratchpad(휘발 가능 — task 본문은 위 §2에 요지 보존됨,
     소실 시 CLOSURE와 이 문서로 재작성 가능)
보호앵커: refs/brick/wip/main-dirty-dev-0710d(052c008db — 커밋 전 스냅샷, 이제 참고용)
E2E 증거: ~/.brick/project/brick-protocol/buildings/order-smoke-review-0710 (landed)
```

## 6. 한 줄

```text
엔진 수리 전부 착지·push(4커밋), O1 라이브 E2E 완주(landed+가드결함 3발화점 수리 포함),
발주1은 1차 정직반환(구현갭) 후 환경수리+공식 reroute로 재주행 중(죽이지 말 것),
발주2는 fable-5 기획 캐스팅 한 줄 수정만 남음. 새 발견 = decl의 조용한 모델치환(수리 발주감).
데쿠는 Smith 직접. 다음: 발주1 회수 → 발주2 발사 → --all 재스윕.
```
