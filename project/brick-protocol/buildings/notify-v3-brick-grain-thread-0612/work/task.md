# notify-v3 — brick-grain Slack notifications: one thread per building, one reply per incident

## Operator pre-analysis (VERIFIED — bounded reading list)
Read ONLY:
1. support/operator/reporter.py — emit_building_event_for_policy (~520), the human-voice
   renderer used by the slack sink (the notify-v2 voice: 🧱제목/상태문장/누구/다음/refs/※한계),
   report_event_policy_from_plan (~243: event_kinds, allow_real_slack_delivery).
2. support/operator/report_sinks.py — the slack sender path (SlackSender protocol
   (request, timeout)->(status, body), SLACK_API_URL chat.postMessage, env keys
   BRICK_REPORT_SLACK_BOT_TOKEN/_CHANNEL_ID), ReportSinkObservation discipline
   (status classes only, never bodies/secrets).
3. support/operator/run.py — _emit_building_event_best_effort (~1840) and its call
   sites (~1041 started, ~1116/1314/1392 terminal/hold): the EXISTING building-grain
   emit seams; also where step receipt/return raw rows are written
   (_run_building_step_without_writing ~1639) — the brick-grain seams live next to
   the SAME raw-row writes.
4. support/operator/walker_kernel.py — the dynamic walker's step close / gate
   transition / disposition consumption seams (where link rows and resumed rows land).
5. support/checkers/lib/kernel_checks.py — reporter_notification_projection section
   (the notify-v2 pin family: 14 Slack message shape assertions, auto-wire assertions,
   no-scheduler source files, G6 sink ceiling) — your new pins EXTEND this family.
Do NOT survey other modules.

## Approved structure (Smith 0612 — build EXACTLY this shape)
CHANNEL stays quiet (current 3 kinds only): building_started (parent message),
intervention_required (escalated), building_finished (escalated).
THREAD под the started parent message: ONE reply per incident, where
- incident = one step arc: 받음(HH:MM) → 반환(HH:MM, one-line summary) → 게이트
  결과(통과→다음스텝 / 홀드 / 합류 대기·성립)
- a human/COO disposition (forward/stop after a hold) = its OWN reply ("⤷ coo 도장")
- a step RETRY after adapter error = a NEW reply (append-only; never edit old replies)
Reply voice mirrors notify-v2 human voice; times KST HH:MM; numbered prefix ①②③
by declared sequence position; fan-in steps say 합류 대기/성립.

## Deliverables
1. New ADDITIVE event kinds: brick_received, brick_returned, gate_passed,
   disposition_applied — emitted at the seams that ALREADY write the corresponding
   raw rows (receipt write, return write, link transition write, resume disposition
   consumption). No new state, no timers; emission rides the existing fact writes
   best-effort (never breaks evidence writes — mirror _emit_building_event_best_effort).
2. Grain dial: env BRICK_REPORT_GRAIN, values "building" (DEFAULT — behavior
   byte-identical to today) | "brick" (thread replies on). Policy event_kinds extended
   additively; G6 sink ceiling unchanged (same 4 sinks).
3. Thread state WITHOUT sender state: when the slack sink delivers the building_started
   parent, record the returned message ts as a support observation file INSIDE the
   building root (e.g. raw/report-thread.jsonl or similar admitted support record —
   design decision; ts+channel are not secrets). Subsequent brick-grain sends READ that
   recorded ts from the root and post with thread_ts. Root missing the ts (e.g. start
   bell failed) -> brick events fall back to not_attempted observation (never invent a
   thread, never post to channel at brick grain).
4. Slack payload: chat.postMessage with thread_ts for replies; intervention_required /
   building_finished ALSO post to channel (current behavior) — optionally additionally
   into the thread (design decision, justify).
5. Checker pins (extend reporter_notification_projection family):
   a. grain dial absent/building -> emitted kinds and Slack payloads byte-identical to
      today (regression parity).
   b. grain=brick with captured sender: started parent ts recorded in root; a
      brick_returned reply carries thread_ts == recorded ts; reply text matches the
      approved shape (① prefix, 받음/반환/게이트 segments, KST times).
   c. disposition_applied reply after a hold-resume.
   d. Mutation probe: thread_ts attachment removed -> RED.
   e. F12 vessel guard still holds for ALL new kinds (temp-root building -> no external
      sink); no-scheduler source files list still green.

## Proof required (run yourself, report honestly — claims only from execution)
- compileall + git diff --check.
- Focused reporter profile green; mutation RED (show both).
- Full gate in TEMP SOURCE COPY (bake_dashboard_data_json() first, then --all exit 0;
  state the copy path).
- Do NOT post to real Slack from checkers or proofs — captured sender only. The real
  send is the operator's FIRE after merge.

## Hard constraints (law)
- write_scope support/* only; no link/, agent/, brick/, project/ edits.
- No scheduler/queue/retry/timer; no token caching; no new dependencies; stateless
  senders (thread ts lives in building evidence, read per send).
- Never log/record token values or message bodies in observations (status classes only).
- Plain-text refs only in returns; no packet echo; no npm/node in worktree.
- No pin weakening — extend the notify-v2 pin family additively.
