The review's load-bearing facts check out against the repo: no `FIRST_USE.md` is produced anywhere (only referenced in a doc), `pyproject.toml` has zero `[project.scripts]`, `mcp_projection.py` self-bootstraps `sys.path` at line 31 before imports while `coo_operating_chain.py` uses bare `from support.connection...` imports (the namespace trap), `agent_adapter.py` already runs subprocess 22× inside `connection/` (C2 misread confirmed), no `credentials.env`/`load_dotenv` loader exists, and the atomic `os.open(..., O_CREAT, 0o600)` pattern lives at agent_adapter.py:1666. Writing the final design now.

---

# BRICK 고객 Install UX — 최종 설계서

제출: Smith | 작성: COO | 상태: 기획(구현 전) | 적대검수 3렌즈 blocker·major 반영 완료

---

## ① 한 줄 요약 + 고객 여정

**한 줄:** 고객은 `brick` 한 단어만 외우면, 주술(`uv run python3 -c "exec(...)"`) 없이 **설치 → 인증 → 첫 빌드 → 증거 확인**까지 한 호흡에 끝낸다. 첫 성공은 "진짜 인증" 없이 3~4분 안에 떨어지고, Slack·실제 LLM은 그 다음의 선택 업셀이다.

**비유:** `gh auth login` / `stripe login`처럼 — 명령 하나가 안전하게 손을 잡고 데려간다. 단, BRICK은 **첫 성공을 먼저 보여주고 그다음에 "진짜로 만들래?"를 묻는다**(검수 반영: 인증 디투어를 첫 green 앞에 두지 않는다).

```
   고객 머신                         BRICK                              결과물
 ┌───────────┐
 │ gh clone  │  ← 딱 한 줄 수동 (C3: {OWNER} 치환, 제거 불가)
 │ install.sh│──→ uv sync → brick 진입점 설치 → brick init 자동실행
 └─────┬─────┘
       │
       ▼
   $ brick   (인자 없음)
       │  최초 실행 감지 → init 깔때기 (TTY면 대화형 / 非TTY·CI면 자동 skip-all)
       ▼
 ┌──────────────────────────────────────────────────────┐
 │ [1] doctor   python/uv/repo/import-identity 점검 (입력0)│
 │ [2] build    adapter:local 예제 ~1.6s, 격리워크트리 (입력0)│ ← 첫 성공 먼저!
 │ [3] verify   check_profile --all → "모두 통과 ✅"        │
 │ [4] 닫기      cat ~/.brick/onboard-example/.../FIRST_USE.md│ ← 사람이 읽는 1파일
 └──────────────────────────┬───────────────────────────┘
                            │  ← 여기까지 3~4분, green 본 뒤
                            ▼  "이제 진짜로 만들래?" (선택 업셀)
        ┌──────────────┬──────────────┬──────────────┐
        │ auth login   │ slack connect│ mcp install  │
        │ codex/claude │ 토큰+채널+테스트│ claude/codex │
        │ /gemini      │              │              │
        └──────────────┴──────────────┴──────────────┘
                            ▼
                   brick build --real-provider --task '…'
                   (진짜 코드 변경 + 거버넌스 증거)
```

핵심 설계 결정 3가지(검수 후 확정):
- **깔때기 역전** — adapter:local zero-config 성공을 **끝까지 본 다음** 인증을 권한다. cold 머신에서 vendor-login 디투어를 첫 green 앞에 두지 않는다.
- **닫기 = 1파일** — 30개 증거 스파인 더미가 아니라 사람이 읽는 `FIRST_USE.md` 한 장을 만들고, 그걸 열라고 안내한다.
- **non-TTY 안전** — `brick init </dev/null`·CI 파이프는 `input()` EOF로 죽지 않고 자동 skip-all 실행(never-raise 보장).

---

## ② brick CLI 명령 트리

| 명령 | 하는 일 | 검수 반영 핵심 |
|---|---|---|
| `brick` | 최초 실행(config 없음)→`init` 진입 / 이후→`status` 요약 | — |
| `brick init` | **얇은 오케스트레이터**. `[doctor]→[build예제]→[verify]→[닫기]` 순서만 잇고 로직 0. Enter=수락/s=건너뜀. **non-TTY면 자동 skip-all** | ★깔때기 역전: 인증은 첫 green **이후** 업셀로만 / TTY 감지 P3 불변식 |
| `brick build [--task] [--preset] [--adapter local] [--real-provider]` | 인자 없으면 내장 예제·adapter:local·~1.6s. **driver의 기존 격리 워크트리 seam 재사용**(bare-repo 변이 금지) | ★`--task` 실빌드는 building_id에 timestamp/uuid 부여 → 재실행 FileExistsError 회피 |
| `brick verify` (별칭 `check`) | `check_profile.py --all` 래핑. PYTHONPATH/cwd **스스로 해결**(검수: 없으면 ModuleNotFoundError, 있으면 green) | 진입점 부트스트랩이 선결(③·⑤ 참조) |
| `brick doctor` | onboard `run_doctor` 승격. 항상 exit0(진단≠게이트). 증상→처방, 막힌 줄마다 다음 verb 출력. `--json` | — |
| `brick status` | repo 루트·선택 어댑터·slack on/off(**토큰 마스킹**)·MCP 목록·마지막 증거 경로. **비밀 절대 미출력** | ★`mask_secret()` 통과, 토큰 꼬리 4byte도 미노출 |
| `brick auth login <codex\|claude\|gemini> [...]` | codex/claude=`--version` probe→미인증시 **vendor login 스폰**(BRICK은 토큰 비소유). gemini=getpass API키→keychain/0600 | ★vendor 스폰 argv에 비밀 0(RAW_SECRET_PATTERNS로 검사) |
| `brick auth status [--json]` | 3-provider 준비도(ready/unauthed/missing/unknown). 토큰 마스킹 | — |
| `brick slack connect` | 토큰(getpass)+채널→xoxb- 형식검사→keychain/0600→**명시적 y/N**으로 `allow_real_slack_delivery=true`→실테스트 1발 | ★vessel guard(`external_delivery_allowed`)는 **건드리지 않음**(C1) |
| `brick slack test` | 지금 1패킷 전송, 타입드 사유(missing_env/auth_failed/channel_not_found) 보고. 무음실패 박멸 | ★요청객체·헤더·raw body 미출력, 엔진의 타입드 status만 |
| `brick mcp serve` | `serve_stdio` 얇은 별칭(이미 main()·__main__·self-bootstrap 보유) | 최저 리스크 |
| `brick mcp install <codex\|claude> [--print] [--dry-run]` | claude=`claude mcp add` 실행. codex=`~/.codex/config.toml` 멱등 머지+백업 | ★`connection/` 밖 신규 모듈(C2 정정: 디렉토리 금지 아님, 스타일 분리) |
| `brick mcp add/list/remove` | 외부 고객 MCP 흡수(현재 부재) | ★**P4b로 연기**: 임의 명령 등록=신뢰검토 별도, 헤더 비밀은 getpass(argv 금지) |
| `brick config get/set/list/path` | `~/.brick/config.toml`. **비밀은 set 차단**(auth/slack로만) | 평문-via-config 누수 차단 |

**오케스트레이터 불변식(법으로 강제):** `brick init`은 verb 호출을 **순서대로 잇기만** 한다. 신규 체커 프로파일이 "init은 concern 로직 0"을 강제 → 이중진실 회귀를 구조적으로 차단.

---

## ③ 설정 3종 흐름 + credential 안전처리

### 3A. LLM 인증 (codex / claude / gemini) — 2트랙, vendor 위임

```
brick auth login codex
  1. preflight: shutil.which('codex') + `codex --version` → ready|unauthed|missing
  2. missing  → 설치 힌트 출력 후 친절히 정지
     unauthed → `codex login` 스폰 (vendor OAuth, 고객은 BRICK 안에 머묾)
  3. 재-probe → "✅ codex 인증됨"
  4. BRICK은 readiness '상태'만 config에 캐시 — 토큰 값은 절대 미보관

brick auth login gemini --api
  • API키 getpass(에코오프). argv로 주면 거부(RAW_SECRET_PATTERNS).
  • 저장: keychain: 또는 ~/.brick/credentials.env (0600)
  • 런타임: GEMINI_API_KEY 없으면 부트스트랩이 주입. ENV 있으면 ENV 우선(CI 탈출구).
```

**안전 원칙:** codex/claude 토큰은 **vendor 스토어**에 남는다(BRICK 비소유). BRICK이 쥐는 비밀은 gemini 키 + slack 토큰뿐.

### 3B. Slack — 명시 토글, 실테스트, 런타임 자동로드

```
brick slack connect
  1. 봇토큰 getpass (argv·history·스크롤백 절대 미노출)
  2. xoxb- 형식검사 (오타 조기 거부 — '검증'이 아니라 '오타 paste 거부')
  3. 채널 ID
  4. 저장: keychain: 또는 ~/.brick/credentials.env → 0600
  5. ★명시 "실제로 슬랙에 보낼까요? (y/N)" → allow_real_slack_delivery=true 기록
     ── external_delivery_allowed(C1: vessel guard, 경로파생, AUTO-ON)는 건드리지 않음·불가
  6. 실패킷 1발 → "✅ #channel 로 전송됨"  (마스킹 에코: xoxb-•••••• (54 chars))
```

**런타임 자동로드(트랩의 뿌리 수리):** `brick` 진입점이 매 실행 시 `~/.brick/credentials.env`를 **좁은 범위로**(report/provider sink만) `os.environ`에 주입. 오늘 repo에 **로더가 전혀 없어서**(검수 확인: `report_sinks`는 `os.environ`만 읽음) "source 잊으면 슬랙 무음"이 반복됐다. **안전 스코프:** 로드 시 파일 0600 검증(world-readable면 거부), doctor/status에 값 미출력, 임의 서브프로세스 env 오염 금지, ENV 우선.

⚠️ **검수 재스코핑(major):** 이 로더는 **opt-in Slack 분기**를 단단하게 할 뿐, **헤드라인 3분 경로를 막는 블로커가 아니다**(기본 경로는 Slack 미전송). 따라서 P2 우선순위는 FIRST_USE.md·TTY-안전 마법사를 **먼저**, 로더를 그 다음에.

### 3C. MCP — 양방향, action-side 분리

```
BRICK-as-server (요구3 전반):
  brick mcp serve          serve_stdio 얇은 별칭 (자체 부트스트랩, PYTHONPATH 불필요)
  brick mcp install claude `claude mcp add brick -- brick mcp serve`
  brick mcp install codex  ~/.codex/config.toml에 [mcp_servers.brick] 멱등머지 + 백업
                           ★connection/ 밖 신규 모듈. --print = render-only 폴백

외부 MCP 흡수 (요구3 후반, 현재 부재) — P4b로 연기:
  brick mcp add <name> --transport stdio|http <cmd…> [--scope user|project]
  • server def(command/url) → config.toml 평문 OK
  • 원격 auth 헤더/토큰 → ★getpass 입력(argv 금지) → keychain REFERENCE 키만 저장, 평문 금지
```

### credential 안전처리 — 검수 blocker/major 전면 반영

| 항목 | 검수가 깨뜨린 것 | 최종 설계 |
|---|---|---|
| **비밀 리졸버** | "기존 keychain:/env: 스킴 위에 얹는다"는 **거짓**. run.py:2758은 그 prefix를 path 해석에서 **제외**할 뿐, 값으로 푸는 리졸버가 **없음** | ★P2에서 **신규 보안표면으로 소유**. 단일 `resolve_secret_ref(ref)`: 백엔드 명시(env:/file:0600/keychain:), 백엔드 없으면 **평문 폴백 금지·하드페일**. keychain 쓰기는 raw 값 비영속 |
| **home-dir 사각지대** | `~/.brick/credentials.env`·persist된 증거가 **모든 누수방어 체커 스캔 밖**(session-id 리댁션·no-smith-residue는 repo-상대 루트만) | ★`--real-provider` 증거를 `~/.brick`에 persist 전 **home-dir 리댁션 패스** 통과 필수. 기본 예제는 adapter:local 스텁이라 live 비밀 0 |
| **0600 패턴 출처** | 인용한 report_sinks.py:952는 **서명키 tempfile**(write-then-chmod, TOCTOU 창) | ★**atomic** `os.open(path, O_CREAT\|O_WRONLY\|O_EXCL, 0o600)` 사용(출처 agent_adapter.py:1666). `~/.brick` 디렉토리 0700 |
| **마스킹 헬퍼** | repo에 mask/redact 함수 **없음**. xoxb- 꼬리 4byte 에코도 스크롤백 누수 | ★단일 `mask_secret()`: prefix+길이만(`xoxb-•••••• (54 chars)`), **토큰 byte 0**. 모든 status/doctor/connect/test 출력이 통과. 체커가 RAW_SECRET_PATTERNS 매칭 출력 시 FIRE |
| **Slack 에러 누수** | 새 `slack test`/`connect`가 naive `except: print(e)`면 Request·헤더·Bearer 노출 | ★요청객체·헤더·raw body 절대 미출력, 엔진 타입드 status만. agent_adapter.py:1059의 "body read+discard" 규율 명문화. 강제 401이 Bearer 미노출 확인하는 FIRE-probe 체커 |
| **vendor 스폰 argv** | codex/claude 스폰에 미래 '편의' 플래그가 토큰을 argv(ps·history)에 실을 수 있음 | ★하드 불변식: 스폰 argv·env에 credential 0, bare `codex login` 핸드오프뿐. 체커가 argv를 RAW_SECRET_PATTERNS로 검사 |
| **credentials.env 위치** | `.gitignore`에 없음 → 안전 근거는 "repo-외부 `$HOME`"이지 gitignore가 아님 | ★불변식 = "repo-외부 `$HOME` 경로". repo 안으로 옮기면 live 누수 → 금지 |

---

## ④ 첫 성공까지 (분·단계)

```
[0] 설치 — 수동 한 줄 (C3, 제거 불가)
    gh auth login
    gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
    # install.sh 확장: uv sync → brick 진입점 설치(.venv/bin or pipx) → brick init 자동실행
    # ★자동실행은 bare `brick`이 아니라 절대경로(.venv/bin/brick 또는 uv run brick)로 호출
    #   → PATH 활성화 여부에 첫 성공이 의존하지 않게

[1] brick           (인자 없음) → 최초 실행 → init. 외울 verb 0.
[2] [doctor]        python/uv/repo/import-identity/provider preflight — green 표, 입력0
[3] [build예제]      adapter:local, ~1.6s, 격리 워크트리 강제(repo 안전), 입력0   ← 첫 성공
[4] [verify]        check_profile --all → "모두 통과 ✅"
[5] 닫기            "✅ 첫 빌딩 증거: ~/.brick/onboard-example/onboarding-example-0/FIRST_USE.md
                     다음: cat 위 파일 ↑  그다음: brick auth login (진짜로 만들기)"
[업셀] brick auth login · brick slack connect · brick mcp install claude
```

**정직한 두 숫자:**
- **기본 skip-all 경로**(doctor→local 예제→verify→FIRST_USE.md): **3~4분**. 헤드라인 "첫 성공". 마법사가 기본으로 여기까지 몬다. Slack/MCP/real-provider는 **명시 opt-in 분기**.
- **풀 셋업**(codex login + Slack + 첫 실빌드): **~7분, 조건부** — codex/claude가 이미 로그인됐다는 가정. cold 머신은 vendor-CLI 설치+로그인 왕복이 더해지며 BRICK이 줄일 수 없음. 여정이 이 분기를 **각주에 숨기지 않고 명시**한다.

**aha-moment 정직 고지(검수 blocker 반영):**
- adapter:local 첫 증거는 **스텁**(진짜 코드 변경 아님). `FIRST_USE.md`가 반드시 명시: *"이건 예제입니다 — 실제 빌딩은 `brick auth login` 후 `--real-provider`."*
- ★`FIRST_USE.md`는 **빌드가 직접 생성한다**(현재 repo는 미생성 — starter-kit 문서에만 존재). 5줄 한국어: 무엇이 실행됐나·어댑터·증거 루트·다음 verb. 30파일 스파인 더미 대신 **고객이 여는 단 1파일**. 닫기 라인의 다음 액션은 "폴더 열어보세요"가 아니라 literal `cat …/FIRST_USE.md`.

---

## ⑤ 구현 로드맵 (무엇부터)

### P1 — 진입점 + 디스패처 (greenfield, 가장 큰 미구현 + ★숨은 진짜 블로커)

- `pyproject.toml`에 `[project.scripts] brick = "brick_protocol.support.operator.cli:main"` 추가(현재 0개).
- 신규 `cli.py`: argparse 서브커맨드 트리, 기존 seam 래핑(onboard main·run_doctor·run_building_intake·check_profile·serve_stdio).
- ★**진짜 블로커 = 듀얼 네임스페이스 import 트랩**(검수가 live 재현). console_script는 `sys.path[0]=''`로 뜨고, 전이 import 체인의 8개 모듈이 **bare `from support.connection...`**(예: coo_operating_chain.py:15)을 써서 `ModuleNotFoundError: No module named 'support'`. driver.py·onboard.py 자신은 FQ import지만 onboard는 self-bootstrap이 **없음** — 오늘 도는 건 `uv run`+editable .pth 덕.
  - **수리:** cli.py의 **최초 실행 라인**(brick_protocol/support import 전)이 **mcp_projection.py 패턴**(line 31)을 복제 — `sys.path.insert(0, repo_root)` **및** `sys.path.insert(0, repo_root/'support'/'import_identity')`. onboard.py 패턴(부트스트랩 없음)을 따르면 안 됨.
  - **게이트(P1 필수):** repo **밖** cwd에서 PYTHONPATH unset으로 `brick build`/`brick doctor` 실행 → ModuleNotFoundError 없음을 단언하는 체커. 이게 "진입점이 실제로 고객에게 동작한다"는 **유일한 증명**, 연기 불가.
- `brick build`/`verify`/`doctor`/`status` 먼저(README 3주술 박멸).
- ★**결정 #1(PATH 메커니즘)은 P1 선결**: install.sh의 `brick init` 자동실행이 PATH에 의존하므로. install.sh는 bare `brick`이 아니라 절대경로로 호출, PATH/활성화 노트는 마법사 **뒤에** 출력. `check_product_no_smith_residue`/`release_export_exclusion` pin 깨지 않기.

### P2 — Config + credential + 런타임 로더 (★보안 1급 빌드)

- `~/.brick/config.toml`(비밀 아님) + credential 스토어. ★keychain:/env: 스킴은 **존재하지 않으므로**(검수) 신규 `resolve_secret_ref` 리졸버를 소유: 평문 폴백 금지·하드페일.
- ★atomic `os.open(O_CREAT|O_EXCL, 0o600)` 생성(report_sinks.py:952 인용 폐기). `~/.brick` 0700.
- ★`mask_secret()` 단일 헬퍼 + 모든 출력 경유 + RAW_SECRET_PATTERNS 출력 FIRE 체커.
- ★home-dir 리댁션 패스(real-provider 증거 persist 전) + credentials.env 0600-on-load 체커.
- 런타임 로더: credentials.env → report/provider sink(좁은 스코프, ENV 우선). 체커: 값 미에코·blanket 주입 금지.
- `brick config get/set/list/path`(비밀 set 차단), `brick auth login/status`, `brick slack connect/test`.
- ★**P2 내부 우선순위:** FIRST_USE.md 생성·TTY-안전 마법사가 로더보다 **먼저**(전자=기본 경로 게이트, 로더=opt-in 게이트).

### P3 — 마법사 (얇은 오케스트레이터, ★greenfield 대화층)

- `brick init`은 P1/P2 verb 순서만. 신규 체커: init concern-로직 0.
- ★**TTY 감지 불변식:** stdin이 TTY 아니면 `input()` 호출 없이 자동 skip-all(doctor→local 예제→verify) 실행. onboard.py에 `input()`/`getpass`/`stdin`이 **전무**(검수 확인) → 대화층은 net-new, EOF 크래시 방지를 `--non-interactive` 법에 포함.

### P4 — MCP 양방향

- **P4a:** `brick mcp serve`(얇은 별칭) + `brick mcp install --print`(connect.py의 기존 render 함수 재사용 → near-zero 코드) + `claude mcp add` 스폰(claude가 자기 스토어 소유, 저위험).
- **P4b(연기):** `~/.codex/config.toml` 자동머지(결정 #4 게이트: 백업+dry-run+"설정 자동변경 안 함" 원칙 충돌 해소 후) + 외부 MCP 흡수(`add/list/remove`, 임의명령 등록 신뢰검토 + 헤더 getpass).
- ★C2 정정 반영: `connection/`에 subprocess **금지 규칙은 없음**(agent_adapter.py가 이미 22× 사용). 신규 모듈은 **스타일 분리**일 뿐, 새 체커가 정말 필요한지 vs agent_adapter 선례 재사용으로 충분한지 P4에서 판정.

**전 단계 공통 CLI 법:** 모든 verb는 **멱등("이미 됨"=green)** + **`--json`** + **`--non-interactive`**(CI/무인 탈출구) 동반.

---

## ⑥ Smith 결정 필요사항

1. **PATH 설치 메커니즘 — pipx vs `.venv/bin` + shell-rc?** `.venv/bin/brick`은 비활성 셸에서 안 보임 → 첫날 "한 verb" 깨짐. pipx는 글로벌 PATH지만 의존성 추가. install.sh는 무엇에 commit? **(P1 블로커 — 검수: 자동실행이 여기 의존하므로 P1 선결)**
2. **keychain 지금 vs env-file 먼저?** 오늘 `keyring`/`getpass` 저장 전무. v1은 `credentials.env`(0600, repo-외부)만 내고 OS-keychain은 연기? **권고: env-file 먼저.**
3. **외부 MCP 흡수(`mcp add/list/remove`) — v1 vs v2?** 임의명령 등록 신뢰질문이 있는 최대 net-new 표면. **권고: P4b로 연기**(v1은 BRICK-as-server만). 요구3은 양쪽 다 원함 — 페이징 수용 확인.
4. **`brick mcp install`의 `~/.codex/config.toml` 자동머지** = BRICK 첫 파일변이 outbound, connect.py가 의도적으로 지킨 경계 침범(onboard.py:242 "설정 파일은 자동으로 바꾸지 않아요"). 멱등머지+백업+`--print`로 수용? 아니면 render-only 유지하고 고객이 paste?
5. **`brick slack connect`의 실테스트 자동전송** = 진짜 side-effect. 유지(좋은 신호)하되 전송 전 y/N으로 충분? 아니면 `--test` 뒤로도 게이팅?
6. **호스티드 설치 / 공개 배포** — C3가 `curl|sh`를 막음(`{OWNER}` 잔재가 헌법적 pin). 교육 사명(아이들 조립) 고려 시, 공개배포 트랙을 **별도 골**로 열 가치? 아니면 clone-first 무기한 유지?

---

## ⑦ 적대검수가 남긴 위험 (반영했지만 잔존하는 것)

| # | 위험 | 상태 | 잔존 노출 |
|---|---|---|---|
| R1 | **진입점 네임스페이스 트랩** — console_script `sys.path[0]=''` → bare-`support` 8모듈 ModuleNotFoundError(operator의 `/tmp` 트랩이 제품 정문에 재현) | **설계 반영**: cli.py 최초줄 2-insert 부트스트랩 + repo-밖 cwd 게이트 체커 | 부트스트랩을 "한 줄"로 경시하면 고객 첫 명령에서 깨짐. **P1 게이트 필수** |
| R2 | **비밀 리졸버가 graft가 아니라 net-new 보안코드** — 기존 keychain:/env: 스킴은 read-side 부재 | **설계 반영**: P2가 리졸버 소유, 평문 폴백 금지 | 스케줄 압박에 "얇은 graft"로 다루면 토큰 핸들링 버그(평문 폴백·world-readable temp·argv 누수) 유입 지점 |
| R3 | **home-dir 사각지대** — credentials.env·persist 증거가 모든 누수방어 체커 스캔 밖 | **설계 반영**: real-provider persist 전 home-dir 리댁션 패스 + 0600-on-load 체커. 기본 예제=stub(비밀0) | real-provider 증거를 home에 persist하는 순간 session-id 누수가 안 잡힘 → 리댁션 패스 미구현 시 라이브 위험 |
| R4 | **FIRST_USE.md 미존재** — 닫기 라인이 빌드가 안 만드는 파일을 가리킴(검수 grep 확인) | **설계 반영**: 빌드가 직접 5줄 생성, 고객이 여는 1파일 | 검수 원문대로 출하하면 첫 고객이 aha-moment 순간 dead path 착륙 |
| R5 | **마법사 greenfield + non-TTY EOF** — onboard.py에 input()/getpass 전무, CI 파이프 EOF 크래시 | **설계 반영**: TTY 감지 불변식, 非TTY 자동 skip-all | 대화층 빌드 비용을 "graft"로 과소평가하면 첫 cold-CI 실행에서 never-raise 약속 깨짐 |
| R6 | **깔때기 역설계 위험** — cold 머신에서 인증 디투어가 첫 green 앞에 놓이면 함정-이탈 지점 | **설계 반영**: 깔때기 역전, 인증은 첫 green 이후 업셀 | 마법사 카피가 다시 `auth login`을 먼저 권하면 재발 |
| R7 | **`brick build --task` FileExistsError** — 같은 building_id 재실행 시 hard fail(repo가 문서화한 실패모드) | **설계 반영**: 실빌드 id에 timestamp/uuid, 충돌은 "resuming/--new-id" 처방 | "멱등=green" 법이 예제(overwrite)/실빌드(unique-id)로 분기됨을 명시 안 하면 raw FileExistsError가 고객에 노출 |
| R8 | **Slack/MCP 에러·argv Bearer 누수** | **설계 반영**: 타입드 status만, body read+discard, getpass-not-argv, FIRE-probe 체커 | naive `except: print(e)` 한 줄이면 헤더·Bearer 노출. 체커가 마지막 잡이 |

**검수 종합 판정 반영:** 골격(zeroconf+verbs)과 여정은 sound, 로드-베어링 claim 대부분 실행으로 확인됨. 단 (1) credential 층은 "얇은 graft 세트"가 아니라 **1급 보안 빌드**로 다뤄야 안전하고, (2) 진입점 부트스트랩+PATH+네임스페이스는 trivial이 아닌 **유일한 로드-베어링 30%**다. 이 둘을 위 표대로 처리하면 3~4분 기본 경로는 진짜로 매끄럽다.

---

**구현 핵심 파일:** `pyproject.toml`(`[project.scripts]` 추가), 신규 `support/operator/cli.py`(디스패처·부트스트랩 mcp_projection.py:31 패턴 복제), `support/operator/onboard.py`(main·run_doctor 승격·input() 전무→대화층 net-new), `support/operator/driver.py`(run_building_intake·격리 워크트리 seam), `support/operator/report_sinks.py:545-556`(Slack env·무음실패 지점·런타임 로더 타깃), 신규 `resolve_secret_ref`/`mask_secret` 헬퍼 + atomic 0600(출처 `agent_adapter.py:1666`), `support/connection/mcp_projection.py`(serve_stdio), `connection/` **밖** 신규 MCP-install 모듈, `support/checkers/check_profile.py`(`brick verify`), 신규 체커 프로파일 4종(진입점 repo-밖 부트스트랩 게이트 / init concern-로직 0 / credentials 로더 스코프·0600-on-load / mask_secret RAW_SECRET_PATTERNS 출력 FIRE).