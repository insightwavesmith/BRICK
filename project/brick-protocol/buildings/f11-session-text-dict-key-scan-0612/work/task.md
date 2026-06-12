# F11: chat-session leak rejector misses UUID/ULID-shaped text in dict KEY position

Found by the S2+S3 building's own attack-QA (recorded in its return): _reject_chat_session_session_text accepted a mapping whose KEY was a UUID-shaped string (value scanning only). Submissions/envelopes must reject session-shaped text in EVERY string position: dict keys, dict values, list items, nested at any depth.

REQUIRED: fix the rejector (support/operator/run.py chat-session validation helpers and/or support/recording/adapter_error_frontier.py _reject_session_like_text — find the actual owner(s) and unify on ONE walker that visits keys AND values recursively). Build the probe tokens at RUNTIME by concatenation (never write UUID-shaped literals into committed files — describe shapes, construct in probes).
PROOF: probes — mapping with UUID-shaped KEY rejected; ULID-shaped key rejected; nested dict/list key/value positions rejected; legitimate word-form tokens and ordinary text accepted (no false positive on 'task-source' style hyphenated words). FIRE: mutated walker that skips keys -> RED (extend the chat_session_park_seam pin's mutation set).
Full gate -> exit 0 (say which checkout/copy). Constraints: support/* only; fails-closed; no pin weakening; align precision with the existing word-boundary house standard.
