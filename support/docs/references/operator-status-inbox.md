# Operator status-inbox watch loop

This page covers the operator-session watch loop for the local status inbox.
It moved out of `README.md` (split 0701, see
`project/brick-protocol/status/kernel/brick-followon-doc-skill-checker-catalog-0701.md`)
because it is operator-runbook material for a session already running the
protocol, not first-clone quickstart material. For getting started, see
[quickstart](quickstart.md) and [setup](setup.md).

운영자 세션 표준은 status inbox 감시를 같이 켜는 것입니다. export 직후에는
`project/`가 없고, 첫 onboard/run 이 로컬 vessel을 만들 수 있어요.

```bash
cd ~/BRICK
while true; do
  if [ -d project/brick-protocol/status/inbox ]; then
    find project/brick-protocol/status/inbox -maxdepth 1 -type f -name '*.json' -print | tail -20
  else
    printf '%s\n' 'status inbox not created yet'
  fi
  sleep 5
done
```

예상 출력은 알림 packet이 없으면 빈 줄 또는 `status inbox not created yet`,
알림이 생기면 `project/brick-protocol/status/inbox/*.json` 경로입니다. 실패
신호는 `No such file or directory`를 숨기지 않은 watch, 또는 repo 루트가 아닌
곳에서 실행한 경우입니다.
