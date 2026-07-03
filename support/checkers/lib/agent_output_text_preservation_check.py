"""Agent output-text preservation kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes adapter output-text side-channel preservation; it owns no axis
crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
)


def run_agent_output_text_preservation(repo: Path) -> KernelResult:
    """Pin full local-CLI output text to a support-only raw side-channel."""

    _ensure_import_identity(repo)
    from brick_protocol.support.connection import adapter_local_cli
    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection.adapter_constants import ADAPTER_CODEX_LOCAL
    from brick_protocol.support.recording import claims_agent
    from brick_protocol.support.recording import raw_claim_trace
    from brick_protocol.support.recording.contracts import RawClaimTracePacket

    full_text = (
        "received_work_ref: fixture-work\n"
        "made_changes: true\n"
        "changed_files: []\n"
        "observed_evidence: full adapter output text side-channel fixture\n"
        "commands_run: []\n"
        "blocked_or_missing_evidence: []\n"
        "handoff_refs: []\n"
        "not_proven: []\n"
    )

    def _fake_codex_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del cwd, timeout_seconds, env
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "0.46.0", "")
        return adapter.LocalCliCompleted(
            call,
            0,
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": full_text}}) + "\n",
            "",
        )

    request = adapter.AgentAdapterRequest(
        building_id="agent-output-text-preservation",
        agent_object_ref="agent-object:dev",
        adapter_ref=ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-output-text",
        next_brick_instance_ref="brick-output-text-next",
        required_return_shape=(
            "received_work_ref,made_changes,changed_files,observed_evidence,"
            "commands_run,blocked_or_missing_evidence,handoff_refs,not_proven"
        ),
    )
    result = adapter.connect_agent_brain(
        request,
        cwd=repo,
        timeout_seconds=5,
        command_runner=_fake_codex_runner,
    )
    if result.adapter_output_text != full_text:
        raise ProfileError("agent_output_text_preservation did not expose full output text side-channel")
    if not isinstance(result.returned_value, Mapping):
        raise ProfileError("agent_output_text_preservation returned_value was not a mapping")
    if full_text in json.dumps(result.returned_value, ensure_ascii=False, sort_keys=True):
        raise ProfileError("agent_output_text_preservation leaked full output text into AgentFact.returned")

    claim_facts = claims_agent._agent_claim_facts(
        (
            SimpleNamespace(
                preparation=SimpleNamespace(
                    step_rows=SimpleNamespace(step_ref="output-text-step"),
                    agent_object=SimpleNamespace(object_ref="agent-object:dev"),
                ),
                adapter_result=result,
                not_proven=(),
            ),
        ),
        proof_limits=(),
    )
    claim_raw_refs = claim_facts[0].get("raw_refs") if claim_facts else None
    if claim_raw_refs != ["raw:agent:01", "raw:agent-output-text:01"]:
        raise ProfileError("agent_output_text_preservation claim trace did not link output-text raw_ref")
    claim_fact = claim_facts[0].get("fact")
    if not isinstance(claim_fact, Mapping) or "output_text" in json.dumps(claim_fact, ensure_ascii=False):
        raise ProfileError("agent_output_text_preservation put output text into AgentFact body")

    raw_record = {
        "raw_ref": "raw:agent-output-text:01",
        "raw_refs": ["raw:agent-output-text:01"],
        "step_ref": "output-text-step",
        "agent_object_ref": "agent-object:dev",
        "output_text": "ordinary full output text plus " + ("sk-" + ("D" * 16)),
    }
    with tempfile.TemporaryDirectory(prefix="bp-agent-output-text-") as tmp:
        root = Path(tmp) / "root"
        raw_claim_trace._write_jsonl(root / "raw" / "agent-output-text.jsonl", (raw_record,), [])
        row_text = (root / "raw" / "agent-output-text.jsonl").read_text(encoding="utf-8")
        if "sk-" + ("D" * 16) in row_text:
            raise ProfileError("agent_output_text_preservation raw stream leaked credential text")
        row = json.loads(row_text)
        if row.get("raw_ref") != "raw:agent-output-text:01":
            raise ProfileError("agent_output_text_preservation raw stream lost raw_ref")
        if not isinstance(row.get("raw_evidence_scrub"), Mapping):
            raise ProfileError("agent_output_text_preservation raw stream did not record scrub evidence")

        (root / "evidence" / "claim_trace" / "agent").mkdir(parents=True, exist_ok=True)
        raw_claim_trace._write_json(
            root / "evidence" / "claim_trace" / "agent" / "returned_claims.json",
            {
                "facts": [
                    {
                        "raw_refs": ["raw:agent-output-text:01"],
                        "fact": {"returned": {"observed_evidence": ["fixture"]}},
                    }
                ]
            },
            [],
        )
        raw_claim_trace.reconcile_claim_trace_raw_manifest_from_raw(root)
        manifest = json.loads((root / "raw" / "raw-manifest.json").read_text(encoding="utf-8"))
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            raise ProfileError("agent_output_text_preservation manifest entries missing")
        output_entry = next(
            (entry for entry in entries if isinstance(entry, Mapping) and entry.get("path") == "raw/agent-output-text.jsonl"),
            None,
        )
        if output_entry is None or output_entry.get("axis_owner") != "Agent":
            raise ProfileError("agent_output_text_preservation manifest did not admit output text stream")

    returned_without_side_channel = adapter.AgentAdapterResult(
        request=request,
        returned_value={"observed_evidence": ["fixture"]},
    )
    if returned_without_side_channel.adapter_output_text:
        raise ProfileError("mutation RED failed: default adapter_output_text fabricated evidence")
    mutation_red_default = "mutation RED observed: empty adapter_output_text side-channel emits no fabricated text"

    if "adapter_output_text" in result.returned_value:
        raise ProfileError("mutation RED failed: adapter_output_text appeared inside returned_value")
    mutation_red_returned = "mutation RED observed: full output text side-channel is absent from AgentFact.returned"

    try:
        raw_claim_trace._raw_manifest_entry("raw/agent-output-text-mutated.jsonl", ["raw:agent-output-text:01"])
    except ValueError:
        mutation_red_manifest = "mutation RED observed: unsupported output-text stream name is rejected"
    else:
        raise ProfileError("mutation RED failed: unsupported output-text stream name was accepted")

    packet = RawClaimTracePacket(
        brick_raw_records=(),
        agent_raw_records=(),
        link_raw_records=(),
        brick_claim_facts=(),
        agent_claim_facts=(),
        link_transfer_claim_facts=(),
        link_carry_claim_facts=(),
        link_sufficiency_claim_facts=(),
        link_movement_claim_facts=(),
    )
    if packet.agent_output_text_raw_records:
        raise ProfileError("mutation RED failed: RawClaimTracePacket fabricated output-text records")
    mutation_red_packet = "mutation RED observed: packet default does not create an output-text stream"

    return KernelResult(
        check_id="agent_output_text_preservation",
        inspected=4,
        output=(
            "agent_output_text_preservation passed: full adapter output text rides a "
            "support-only side-channel, stays out of AgentFact.returned, persists "
            "through the raw scrub, and reconciles into raw-manifest; "
            f"{mutation_red_default}; {mutation_red_returned}; "
            f"{mutation_red_manifest}; {mutation_red_packet}"
        ),
    )


def _run_agent_output_text_preservation_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "agent_output_text_preservation",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_agent_output_text_preservation(repo: Path) -> KernelResult:"
    poisoned = "def run_agent_output_text_preservation_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("agent_output_text_preservation mutation probe could not find entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".agent-output-text-preservation-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_agent_output_text_preservation_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "agent_output_text_preservation mutation probe did not turn profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_agent_output_text_preservation_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "agent_output_text_preservation mutation probe restored source but profile "
            f"remained RED:\n{excerpt}"
        )

    return [
        "agent output-text preservation mutation RED probe passed: disabling the "
        "moved run_agent_output_text_preservation entrypoint made check_profile.py "
        "--profile agent_output_text_preservation exit non-zero, then restoring "
        "the temp-backed self file returned the profile to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for agent output-text preservation."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_agent_output_text_preservation "
            "entrypoint, assert its profile exits RED, restore from a temp backup, "
            "then assert the profile is GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_agent_output_text_preservation(repo).output]
        )
    except ProfileError as exc:
        print("agent output-text preservation rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
