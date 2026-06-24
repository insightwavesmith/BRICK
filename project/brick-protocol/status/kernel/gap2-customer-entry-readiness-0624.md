# GAP2 고객 진입 준비도 상태 (0624)

Status: SUPPORT RECORD -- 고객 진입 표면의 현재 관찰 기록. 이 문서는 source truth /
success judgment / quality judgment / Movement authority가 아니다. 실행 여부와 다음 이동은
선언된 Building/Link 경계와 사람 판단이 따로 닫는다.

## 0. 한 줄

GAP2의 고객 진입 표면은 "설치 스크립트 -> `brick` 콘솔 진입점 -> `brick init` ->
로컬 예제 빌드 -> `FIRST_USE.md` -> `brick verify`"까지 repo 안에 실제 표면과
체커 핀이 생겼다. 남은 델타는 실제 새 고객 머신/릴리스 산출물에서의 외부 실행 증거,
provider 인증 이후의 real-provider 경로, 그리고 공개/배포 문서의 최종 동선 검증이다.

## 1. 관찰된 현재 표면

| 구간 | 관찰된 repo 표면 | 현재 의미 |
| --- | --- | --- |
| 설치 시작 | `support/onboarding/install.sh` | python/uv/clone/uv sync/pipx 설치 뒤 절대경로 `brick init --non-interactive --repo "$target"` 호출 |
| 고객 명령 | `pyproject.toml` `[project.scripts]` | `brick = "brick_protocol.support.operator.cli:main"` 콘솔 스크립트 선언 |
| CLI 부트스트랩 | `support/operator/cli.py` | repo 밖/PYTHONPATH unset 실행을 위해 repo root와 `support/import_identity`를 먼저 `sys.path`에 넣음 |
| 첫 실행 | `support/operator/cli.py::_cmd_init` | present/plugin/slack/onboard/example/verify를 순서대로 묶는 support 오케스트레이터 |
| 첫 읽을 파일 | `support/operator/first_use.py` | 성공한 로컬 예제 뒤 `FIRST_USE.md`를 쓰고, 예제 스텁 고지와 `brick auth login` / `--real-provider` 다음 동선을 명시 |
| 고객 작업 실행 | `support/operator/driver.py::run_customer_building_in_sandbox` | 고객 live tree를 직접 쓰지 않는 worktree sandbox 경로 |

## 2. 체커/핀 관찰

- `support/checkers/profiles/brick_cli_entrypoint.yaml`은 `pyproject.toml`,
  `support/operator/cli.py`, `support/operator/first_use.py`,
  `support/checkers/check_first_use_wizard.py` 존재와 주요 문구를 핀한다.
- 같은 프로파일의 kernel checks는 `brick_cli_entrypoint_smoke`와
  `first_use_wizard`다.
- `brick_cli_entrypoint_smoke`는 repo 밖/PYTHONPATH unset에서 CLI 부트스트랩을
  관찰한다.
- `first_use_wizard`는 simulated init에서 `FIRST_USE.md` 생성, 예제 스텁 고지,
  `brick auth login` + `--real-provider` funnel, 실패 시 no-write를 관찰한다.
- `support/checkers/check_profile.py`에는 두 kernel check가 등록되어 있다.

## 3. GAP2 준비도 델타

| 항목 | 현재 관찰 | 남은 델타 |
| --- | --- | --- |
| P1 콘솔 진입점 | 선언과 부트스트랩 핀 존재 | 실제 pipx 설치 후 `brick` 명령이 고객 셸에서 같은 경로로 뜨는지는 새 머신 실행 증거 필요 |
| P2 설치 스크립트 | clone-first, uv sync, pipx, 절대경로 init 호출이 스크립트에 있음 | release/export 산출물 기준으로 fresh clone부터 끝까지 실행한 transcript 필요 |
| P3 FIRST_USE | 생성기와 checker가 있음 | 실제 `brick init` 산출 output_root의 사람이 읽는 파일 내용 확인 transcript 필요 |
| P4 provider 업셀 | `brick auth login` 안내와 `--real-provider` 동선이 있음 | 실제 codex/claude/gemini 인증 상태별 고객 메시지와 real-provider 빌드 경로는 별도 실측 필요 |
| P5 검증 동선 | `brick verify`가 `check_profile --all` wrapper로 있음 | 고객 설치 환경에서 전체 `--all` 비용/시간/실패 메시지 실측 필요 |
| P6 live-tree 안전 | sandbox driver와 W1 checker 계열이 있음 | release 산출물/고객 repo 조합에서 live tree untouched 관찰 필요 |
| P7 문서/언어 | 설치 스크립트와 FIRST_USE는 한국어+영어 안내를 포함 | README/DEPLOY/릴리스 안내가 현재 CLI 동선과 완전히 일치하는지 별도 문서 스윕 필요 |

## 4. Proof Commands

이 문서를 작성하며 관찰한 명령:

```text
rg --files agent/skills project/brick-protocol/status/kernel
sed -n '1,220p' agent/skills/scoped-implementation/SKILL.md
sed -n '1,220p' agent/skills/protocol-boundary-watch/SKILL.md
rg -n "GAP2|customer-entry|readiness|remaining_delta|customer entry|Customer" project/brick-protocol/status project/brick-protocol -g '*.md' -g '*.yaml' -g '*.json'
find project/brick-protocol -path '*gap2*' -maxdepth 6 -type f
sed -n '1,240p' support/onboarding/install.sh
sed -n '1,260p' support/operator/cli.py
sed -n '260,470p' support/operator/cli.py
sed -n '1,180p' support/operator/first_use.py
sed -n '1,120p' support/checkers/profiles/brick_cli_entrypoint.yaml
rg -n "\[project\.scripts\]|brick =|support.operator.cli" pyproject.toml support/checkers -g '*.toml' -g '*.py' -g '*.yaml'
```

## 5. Not Proven

- 실제 fresh customer machine에서 install script가 끝까지 green인지.
- 네트워크, GitHub auth, pipx PATH refresh, uv installer 동작의 환경별 안정성.
- 실제 provider credential readiness 또는 provider-backed build 결과.
- 고객이 `FIRST_USE.md`를 읽고 다음 행동을 오해 없이 수행하는지.
- release/export 산출물이 이 checkout과 byte-for-byte 같은 고객 진입 표면을 포함하는지.
- 이 문서가 source truth, success judgment, quality judgment, Movement authority라는 것.

## 6. Remaining Delta

1. release/export 산출물에서 fresh-machine dry run transcript를 남긴다:
   clone -> install.sh -> pipx `brick` -> `brick init` -> `FIRST_USE.md` -> `brick verify`.
2. provider별 auth 상태를 3분기(missing/unauthed/ready)로 실측하고 고객 메시지를 캡처한다.
3. `--real-provider` task 1개를 customer sandbox 경로로 실행해 live tree untouched와 증거 루트를 같이 관찰한다.
4. README/DEPLOY/quickstart류 문서가 현재 `brick` CLI 동선과 어긋나는지 스윕한다.
5. 위 실측이 닫히기 전에는 "고객 진입 ready"를 이 문서에서 판단하지 않는다.
