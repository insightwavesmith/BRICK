"""Probe A2: the REAL entry surface (onboard.run_approve_entry action=stop) on the
documented adapter_error_frontier hold (quickstart.md:79) with an empty recorded
agent-return ledger — the paper-stop class the live resume accepts."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "support" / "import_identity"))
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location(
    "qa_mirror_checker",
    REPO / "support" / "checkers" / "check_resume_replay_disposition_mirror.py",
)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)

from brick_protocol.support.operator import onboard  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="bp-qa-selflock-a2-") as tmp:
        plan, _bricks = mc._chain_plan(
            "qaselflock-a2",
            ["design", "build", "review", "close"],
            {("design", "build"): "h1", ("review", "close"): "h2"},
            {"review": 5, "build": 5},
        )
        cb = mc._CountingCallable()
        result = mc._run_to_hold(REPO, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        manifest_path = root / "evidence" / "evidence-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plan_copy = json.loads(manifest["plan_snapshot"]["plan_rows_copy"])
        plan_copy["dynamic_walker_evidence"]["hold"]["hold_reason"] = (
            "adapter_error_frontier"
        )
        manifest["plan_snapshot"]["plan_rows_copy"] = json.dumps(plan_copy)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (root / "raw" / "agent-return.jsonl").write_text("", encoding="utf-8")
        cwd = Path(tmp) / "adapter-cwd"
        cwd.mkdir(parents=True, exist_ok=True)
        out = onboard.run_approve_entry(
            root,
            action="stop",
            author_ref="coo:smith",
            repo_root=REPO,
            adapter_cwd=cwd,
        )
        print(
            json.dumps(
                {
                    "ok": out.get("ok"),
                    "error_kind": out.get("error_kind"),
                    "error_message": out.get("error_message"),
                    "disposition_written": out.get("disposition_written"),
                    "frontier_kind_before": out.get("frontier_kind_before"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
