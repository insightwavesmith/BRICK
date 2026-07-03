"""Raw-evidence stream scrub kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes raw JSONL scrub behavior; it owns no axis crossing, decides no
Movement, and judges no success or quality.
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

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError


def run_raw_evidence_stream_scrub(repo: Path) -> KernelResult:
    from support.recording import raw_claim_trace

    opaque_credential = "sk-" + ("A" * 16)
    opaque_email = "person" + "@" + "example.test"
    opaque_session = {"body": "provider-session-" + ("B" * 16)}
    opaque_session_id = "provider-session-id-" + ("C" * 16)
    cases: tuple[tuple[str, Mapping[str, object], tuple[str, ...]], ...] = (
        (
            "brick-work.jsonl",
            {
                "raw_ref": "raw:brick:01",
                "raw_refs": ["raw:brick:01"],
                "step_ref": "scrub-work",
                "work_statement": opaque_credential,
                "proof_limits": ["preexisting proof limit"],
                "not_proven": ["preexisting not proven"],
            },
            (opaque_credential,),
        ),
        (
            "agent-received.jsonl",
            {
                "raw_ref": "raw:agent-received:01",
                "raw_refs": ["raw:agent-received:01"],
                "step_ref": "scrub-work",
                "provider_session": opaque_session,
            },
            (str(opaque_session["body"]),),
        ),
        (
            "agent-return.jsonl",
            {
                "raw_ref": "raw:agent:01",
                "raw_refs": ["raw:agent:01"],
                "step_ref": "scrub-work",
                "returned": {
                    "observed": {
                        "status": "ordinary nested status evidence",
                        "result": "ordinary nested result evidence",
                        "contact": opaque_email,
                    }
                },
            },
            (opaque_email,),
        ),
        (
            "agent-output-text.jsonl",
            {
                "raw_ref": "raw:agent-output-text:01",
                "raw_refs": ["raw:agent-output-text:01"],
                "step_ref": "scrub-work",
                "output_text": "full adapter output text with " + opaque_credential,
                "proof_limits": ["preexisting output text proof limit"],
                "not_proven": ["preexisting output text not proven"],
            },
            (opaque_credential,),
        ),
        (
            "adapter-error.jsonl",
            {
                "raw_ref": "raw:adapter-error:01",
                "raw_refs": ["raw:adapter-error:01"],
                "step_ref": "scrub-work",
                "message_excerpt": "ordinary status/result text remains evidence",
                "session_id": opaque_session_id,
            },
            (opaque_session_id,),
        ),
    )
    with tempfile.TemporaryDirectory(prefix="bp-raw-scrub-") as tmp_raw:
        raw_dir = Path(tmp_raw) / "root" / "raw"
        for stream_name, record, blocked_values in cases:
            path = raw_dir / stream_name
            raw_claim_trace._write_jsonl(path, (record,), [])
            text = path.read_text(encoding="utf-8")
            for blocked_value in blocked_values:
                if blocked_value in text:
                    raise ProfileError(f"raw_evidence_stream_scrub leaked blocked value in {stream_name}")
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            if len(rows) != 1:
                raise ProfileError(f"raw_evidence_stream_scrub expected one row in {stream_name}")
            row = rows[0]
            if row.get("raw_ref") != record["raw_ref"] or row.get("raw_refs") != record["raw_refs"]:
                raise ProfileError(f"raw_evidence_stream_scrub lost refs in {stream_name}")
            scrub = row.get("raw_evidence_scrub")
            if not isinstance(scrub, Mapping) or scrub.get("blocked") is not True:
                raise ProfileError(f"raw_evidence_stream_scrub lacked scrub evidence in {stream_name}")
            if not isinstance(row.get("proof_limits"), list) or not isinstance(row.get("not_proven"), list):
                raise ProfileError(f"raw_evidence_stream_scrub lacked proof evidence in {stream_name}")
            if stream_name == "agent-return.jsonl":
                returned = row.get("returned")
                if not isinstance(returned, Mapping):
                    raise ProfileError("raw_evidence_stream_scrub altered agent return shape")
                observed = returned.get("observed")
                if not isinstance(observed, Mapping):
                    raise ProfileError("raw_evidence_stream_scrub altered nested return evidence")
                if observed.get("status") != "ordinary nested status evidence":
                    raise ProfileError("raw_evidence_stream_scrub overblocked ordinary status evidence")
                if observed.get("result") != "ordinary nested result evidence":
                    raise ProfileError("raw_evidence_stream_scrub overblocked ordinary result evidence")
    return KernelResult(
        check_id="raw_evidence_stream_scrub",
        inspected=len(cases),
        output=(
            "raw_evidence_stream_scrub passed: brick-work, agent-received, "
            "agent-return, agent-output-text, and adapter-error raw JSONL "
            "streams scrub blocked body detail while preserving refs and "
            "ordinary nested evidence"
        ),
    )


def _run_raw_evidence_stream_scrub_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "raw_evidence_stream_scrub",
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
    needle = "def run_raw_evidence_stream_scrub(repo: Path) -> KernelResult:"
    poisoned = "def run_raw_evidence_stream_scrub_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("raw_evidence_stream_scrub mutation probe could not find entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".raw-evidence-stream-scrub-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_raw_evidence_stream_scrub_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "raw_evidence_stream_scrub mutation probe did not turn profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_raw_evidence_stream_scrub_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "raw_evidence_stream_scrub mutation probe restored source but profile "
            f"remained RED:\n{excerpt}"
        )

    return [
        "raw-evidence stream scrub mutation RED probe passed: disabling the moved "
        "run_raw_evidence_stream_scrub entrypoint made check_profile.py --profile "
        "raw_evidence_stream_scrub exit non-zero, then restoring the temp-backed "
        "self file returned the profile to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for raw-evidence stream scrub."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_raw_evidence_stream_scrub "
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
            else [run_raw_evidence_stream_scrub(repo).output]
        )
    except ProfileError as exc:
        print("raw-evidence stream scrub rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
