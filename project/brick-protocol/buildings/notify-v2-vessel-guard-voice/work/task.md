# Notification v2 — real-vessel-only bell (F12) + human voice + stage dial

## Two halves, one surface (support/operator reporter + report_sinks + the walk-seam wiring)

### (1) F12 guard — the bell rings ONLY for real-vessel buildings
INCIDENT (operator-verified): checker runs create temp fixture buildings whose completions fired
the auto-wiring → Slack flooding ('무한 메시지') and a separate void: the bell's local-inbox write
landed inside a building's observed tree and the write observation voided that step.
REQUIRED:
- External sinks (slack, dashboard delta) fire ONLY when the finished/held building lives under
  the REAL repo's project/<vessel>/buildings/ (resolve via the same buildings_root_for seam —
  no path-string heuristics). Temp/fixture output_root buildings: NO external delivery; their
  local-inbox packet (if any) goes under THEIR OWN output root, never the repo's status/inbox.
- This kills both symptoms: no fixture spam, no foreign writes into observed trees.
- FIRE: a temp-root building completion attempts delivery -> probe shows external sender NOT
  invoked and repo inbox untouched; a real-vessel completion -> sender invoked once. Mutated
  guard removal -> RED (extend the reporter/notification pin).

### (2) Human voice + stage dial
The CURRENT message (real specimen): '브릭 빌딩 알림 / 상태: 멈춤·개입 필요 / 작업 단계: 작업 /
담당 역할: 워커 / 필요 조치: 호출자 또는 COO 처분 필요 / 운영 refs: ... step=-; ... / 한계: ...'
Smith's feedback: too stiff; wants stage-by-stage notifications.
REQUIRED:
- Headline = the building's human title (first line of work/task.md, trimmed; fallback to
  building_id), then short conversational Korean lines:
  example shape (adapt, don't hardcode this string):
  '🧱 <일감 제목>\n→ <상태 문장: 작업까지 끝났고 도장을 기다려요 / 완료됐어요 / 멈췄어요 — 살펴봐 주세요>\n
   누구: <차선 한글>\n다음: <필요 조치 문장 또는 없음>\nref: <building_id> · <frontier 한 줄>\n※ 상태 알림일 뿐 판정 아님'
- Hide empty fields (the 'step=-' case). Keep ONE compact ref line. The proof-limit stays as the
  short '※' line (law: projection-not-judgment must remain stated).
- STAGE DIAL via the existing report event policy vocabulary (vessel stamp / plan declaration):
  mode 'basic' (DEFAULT) = building_started, intervention_required(holds incl. parked),
  building_finished; mode 'verbose' = basic + one line per completed step (brick kind word).
  Set OUR vessel to verbose? NO — leave vessel config as basic default; verbose must be a
  declarable option proven by one temp drive. No new judgment vocabulary; labels from the
  canonical label_map.json only (extend it additively if a word is missing, keep parity pin).
- FIRE: render the specimen packet -> include before/after verbatim in your return; empty-field
  hiding probe; verbose-mode temp drive shows per-step lines; parity pin still green.

### Proof
Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3
support/checkers/check_profile.py --all in a TEMP SOURCE COPY (never in-tree — the bell/gate
self-interference is exactly what (1) fixes; say which copy). Plain-text refs only in returns.

### Constraints
support/* only. No scheduler/queue/retry/timer/thread. Notification failure never touches the
building's own evidence. No link/, agent/, brick/, project/ edits. No pin weakening. Korean
labels canonical; no i18n machinery.
