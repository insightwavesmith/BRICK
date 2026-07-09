#!/usr/bin/env python3
"""Building-local D2 real Conduct probe.

Runs against the shipped Deku checkout without DEKU_FORCE_MOCK, while using the
declared local_double worker and this building's raw/d2-scratch directory for
all probe state.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch


BUILDING_RAW = Path(__file__).resolve().parent
SCRATCH = BUILDING_RAW / "d2-scratch"
DEKU_ROOT = Path("/Users/smith/projects/deku")
TURN_COUNT = 13


def _prepare_environment() -> None:
    os.environ.pop("DEKU_FORCE_MOCK", None)
    os.environ["DEKU_WORKER_MODE"] = "local_double"
    os.environ["DEKU_PROFILE"] = "deku-1"
    os.environ["DEKU_PROBE_SCRATCH"] = str(SCRATCH)
    os.environ["DEKU_HOME"] = str(SCRATCH / "deku-home-real")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    Path(os.environ["DEKU_HOME"]).mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(DEKU_ROOT))


def _load_client():
    import deku_server
    from fastapi.testclient import TestClient

    importlib.reload(deku_server)
    deku_server._PROFILE = "deku-1"
    t0 = time.time()
    deku_server._ensure_loaded()
    load = {
        "loaded_in_s": round(time.time() - t0, 3),
        "profile": deku_server._PROFILE,
        "worker": os.environ.get("DEKU_WORKER_MODE"),
    }
    (SCRATCH / "d2-load.json").write_text(json.dumps(load, indent=2), encoding="utf-8")
    return deku_server, TestClient(deku_server.app), load


def _post_turn(client, payload: dict) -> dict:
    response = client.post("/v1/responses", json=payload)
    body = response.json()
    return {
        "status_code": response.status_code,
        "id": body.get("id"),
        "output_text": body.get("output_text") or "",
        "raw_status": body.get("status"),
    }


def _session_records() -> dict:
    home = Path(os.environ["DEKU_HOME"])
    root = home / "sessions"
    sessions = {}
    for entry in sorted(root.iterdir()) if root.exists() else []:
        if not entry.is_dir():
            continue
        pinboard = entry / "pinboard.json"
        state = entry / "state.json"
        events = entry / "event_log.jsonl"
        sessions[entry.name] = {
            "pinboard": json.loads(pinboard.read_text(encoding="utf-8")) if pinboard.exists() else {},
            "state": json.loads(state.read_text(encoding="utf-8")) if state.exists() else {},
            "event_count": len(events.read_text(encoding="utf-8").splitlines()) if events.exists() else 0,
        }
    return sessions


def _run_session(client) -> dict:
    turns = []
    seed_text = (
        "D2 seed=1 multi-round non-greeting path pin. Remember path pin exactly: "
        "/Users/smith/projects/deku/deku_server.py Error: D2-SEED-PIN-0709C. "
        "Analyze this as a hard session-conduct problem and answer with the path and error token."
    )
    seed = _post_turn(client, {"model": "deku-1-ultra", "input": seed_text})
    prev = seed["id"]
    turns.append(
        {
            "turn": 0,
            "kind": "seed_non_greeting_path_pin",
            "response_id": prev,
            "status_code": seed["status_code"],
            "blank": not seed["output_text"].strip(),
            "preview": seed["output_text"][:160],
        }
    )

    followups = 12
    for idx in range(1, followups + 1):
        prompt = "안녕" if idx % 2 else "hello"
        result = _post_turn(
            client,
            {
                "model": "deku-1",
                "previous_response_id": prev,
                "input": prompt,
            },
        )
        prev = result["id"]
        turns.append(
            {
                "turn": idx,
                "kind": "previous_response_id_followup",
                "response_id": prev,
                "status_code": result["status_code"],
                "blank": not result["output_text"].strip(),
                "preview": result["output_text"][:160],
            }
        )

    sessions = _session_records()
    pin_ok = any(
        "deku_server.py" in json.dumps(record.get("pinboard", {}), ensure_ascii=False)
        and "D2-SEED-PIN-0709C" in json.dumps(record.get("pinboard", {}), ensure_ascii=False)
        for record in sessions.values()
    )
    state_ok = any(int(record.get("state", {}).get("turn") or 0) >= TURN_COUNT for record in sessions.values())
    blank0 = sum(1 for turn in turns if turn["blank"]) == 0
    status_ok = all(turn["status_code"] == 200 for turn in turns)

    return {
        "turn_count": len(turns),
        "followups": followups,
        "blank0": blank0,
        "blank_turns": [turn["turn"] for turn in turns if turn["blank"]],
        "status_ok": status_ok,
        "pin_ok": pin_ok,
        "state_ok": state_ok,
        "turns": turns,
        "sessions": sessions,
    }


def _run_timeout(client) -> dict:
    def boom(slot, prompt):
        raise TimeoutError("worker timeout")

    with patch("deku.dispatch_worker", boom):
        result = _post_turn(
            client,
            {
                "model": "deku-1",
                "input": "timeout force_timeout probe; answer should be non-blank even if worker times out",
            },
        )
    return {
        "status_code": result["status_code"],
        "blank": not result["output_text"].strip(),
        "timeout_ok": result["status_code"] == 200 and bool(result["output_text"].strip()),
        "preview": result["output_text"][:160],
    }


def main() -> int:
    _prepare_environment()
    app_mod, client, load = _load_client()
    health = client.get("/healthz").json()
    session = _run_session(client)
    timeout = _run_timeout(client)
    summary = {
        "building_id": "deku-d2-real-conduct-0709c",
        "mock_off": os.environ.get("DEKU_FORCE_MOCK") != "1",
        "worker_mode": os.environ.get("DEKU_WORKER_MODE"),
        "deku_root": str(DEKU_ROOT),
        "scratch": str(SCRATCH),
        "load": load,
        "healthz": health,
        "checks": {
            "turns_10_to_20": 10 <= session["turn_count"] <= 20,
            "followups_12_plus": session["followups"] >= 12,
            "blank0": session["blank0"],
            "pin_ok": session["pin_ok"],
            "state_ok": session["state_ok"],
            "timeout_ok": timeout["timeout_ok"],
            "status_ok": session["status_ok"],
            "loaded": health.get("loaded") is True,
            "profile_real": health.get("profile") == "deku-1",
        },
        "session": session,
        "timeout": timeout,
    }
    log_text = json.dumps(summary, indent=2, ensure_ascii=False)
    (BUILDING_RAW / "d2-session.log").write_text(log_text + "\n", encoding="utf-8")
    (SCRATCH / "d2-session.log").write_text(log_text + "\n", encoding="utf-8")
    (BUILDING_RAW / "d2-summary.json").write_text(
        json.dumps(
            {
                "checks": summary["checks"],
                "turn_count": session["turn_count"],
                "followups": session["followups"],
                "blank_turns": session["blank_turns"],
                "scratch": str(SCRATCH),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    failed = [name for name, ok in summary["checks"].items() if not ok]
    print(log_text)
    if failed:
        print("D2_CHECKS_FAILED", failed, file=sys.stderr)
        return 1
    print("D2_CHECKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
