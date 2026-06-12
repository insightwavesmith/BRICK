# Notification productization — customer-language Slack messages + walk-to-bus auto-wiring

## Objective
Make BRICK's notifications speak the customer's language and flow automatically. Two halves, one surface (support/operator/reporter.py + report_sinks.py):
(A) the Slack message must read like a status update a non-engineer understands — work-type and role words, not protocol refs;
(B) the engine must ring the bus by itself when a building finishes or stops — today ZERO notifications flow unless the operator drives the bus by hand.

## The "before" specimen (a real message we sent — this must change)
브릭 빌딩 알림 / 상태: 종료 / 빌딩: building-event-reporter-hook-0-0603-slack-auto-smoke /
Brick: building-boundary:...-closed / Agent: 마지막 완료 step work/step-outputs/...-attempt-1/step-output.json /
Link: 닫힌 경계 관찰; project/...#frontier:complete:event:building_finished / 한계: support 알림이며 ...

The customer needs: which building (human label), what happened (시작/완료/멈춤·개입 필요), which work stage (설계/개발/검수/마감 — translated from the brick step-template kind), who holds it (역할명), and what action is needed. Raw protocol refs may remain as ONE short secondary line for operators; headline lines must be human words. Keep the proof-limit line, phrased compactly.

## Where everything lives (recon-verified; re-verify with your read tools)
- Slack text composition: support/operator/report_sinks.py — _slack_message_text (~920), _slack_event_label (~941), _slack_brick_line (~959), _slack_agent_line (~966), _slack_link_line (~973). Entry: send_slack_report_packet (~391).
- Packet facts at render time: building_id, current_brick_ref, last_completed_step_ref, observed_board_state, frontier_ref, required_disposition_owner, project_ref. The brick step-template KIND and bound agent lane are derivable from the building's map/plan evidence — extend reporter.render_building_event_report_packet to carry current_work_kind and current_lane as PROJECTED FACTS (from declared refs only — never judgments).
- The dashboard ALREADY has Korean label maps: support/dashboard/src/data/labels.js (brick kinds → 계획/설계/개발 배분/작업/검수/점검/마감/공격검수; lanes → 리더/워커/리뷰어; display states; movements; disposition owners).

## REQUIRED: single-source the label maps (house principle: one predicate, two organs)
Introduce ONE canonical closed label map as DATA (e.g. support/operator/label_map.json or a python module of closed dicts) consumed by the Python renderer, AND a PARITY checker pin asserting dashboard labels.js stays consistent with the canonical map (mismatch/missing key = RED). Labels translate DECLARED refs only — no new judgment vocabulary.

## (B) Auto-wiring: walk → bus
- When a building run/resume reaches a terminal or held outcome (building_finished / intervention_required incl. chat_session_parked / building_started if cheap), the engine calls the existing render→deliver verbs SYNCHRONOUSLY, best-effort: local-inbox sink ALWAYS; slack only when BRICK_REPORT_SLACK_BOT_TOKEN/_CHANNEL_ID present; dashboard delta only when its env present. NO scheduler/queue/retry/thread/polling — one synchronous call at the seam, exceptions observed (support observation) but never breaking the walk's own evidence write.
- Wiring lives at the operator/run seam AFTER evidence is written (notification = projection of recorded evidence, never a precondition).
- Respect the existing report event policy vocabulary (reporter.report_event_policy_from_plan / vessel AUTO-ON stamp) — wire through it; absent policy → default = local-inbox + env-gated slack.

## Checker pins + FIRE
1. Label parity pin: canonical map vs dashboard labels.js — mutated mismatch → RED.
2. Message shape pin: rendered Slack text has human headline fields and NO raw step-output path in headlines (the specimen's Agent line is the regression case) → regression = RED.
3. Auto-wiring pin: temp run with slack env ABSENT → local-inbox packet written, slack NOT attempted; with fake env + injected sender → send invoked exactly once per terminal event; wiring removed = RED.
4. No-scheduler pin: the wiring introduces no thread/timer/sleep/queue constructs.
5. Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → exit 0 (say which checkout/copy).

## Hard constraints
- Labels = projections of declared refs; closed vocabulary only.
- Notification failure NEVER fails or delays the building's own evidence write.
- No link/ edits, no new Link vocabulary, no scheduler/queue/retry/timer, append-only project/ untouched, no pin weakening.
- Write scope: support/* only. Korean labels first-class; structure the map so English can be added later (no i18n machinery now).

## Proof required (run, report honestly)
- Render the specimen packet through the NEW renderer: include before/after text verbatim.
- Temp-drive a building with fake slack env via injected sender: show composed message + local-inbox file.
- All FIRE cases with actual outputs.
