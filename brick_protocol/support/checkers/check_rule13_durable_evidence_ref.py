#!/usr/bin/env python3
"""Rule 13 durable-evidence reference observation checker.

Support checker only: scans already-written durable Building evidence for
absolute local paths, username-bearing local paths, and session-temporary path
identifiers. It records observations only; it does not judge source truth,
success, quality, or Movement.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError, to_posix


_RULE13_SCAN_SUFFIXES = (".json", ".jsonl", ".md", ".txt", ".yaml", ".yml")
_RULE13_BUILDING_EVIDENCE_PARTS = frozenset({"work", "evidence", "raw"})

_ABSOLUTE_USER_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_:/.-])(?:/Users|/home)/[^\s`'\"<>{}\\]+"
)
_SESSION_TEMP_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_:/.-])(?:/private)?/(?:var/folders|tmp)/[^\s`'\"<>{}\\]+"
)

# Frozen-history content-hash exceptions. Existing historical durable evidence
# is not rewritten here; each admitted legacy line is frozen by exact line
# content hash so a same-count swap, replacement, or new local path REDs.
_RULE13_FROZEN_ALLOWLIST: dict[str, tuple[str, ...]] = {
    'project/brick-protocol/buildings/adapter-30-s1-park-2/evidence/claim_trace/agent/returned_claims.json': (
        'a4af6c3cf364cbb9',
        'ff40d4e8698ebc79',
    ),
    'project/brick-protocol/buildings/adapter-30-s1-park-2/raw/agent-return.jsonl': (
        'f285a237fb901a65',
    ),
    'project/brick-protocol/buildings/adapter-30-s1-park-2/work/step-outputs/adapter-30-s1-park-2-work-attempt-1/step-output.json': (
        'f68dc2ad09981818',
        'a4d7d8bd80875570',
    ),
    'project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/evidence/claim_trace/agent/returned_claims.json': (
        '7ff9f41f65e0034e',
        'e50cfa13e71ae209',
        '755bd9b20b6cd656',
        '357057af1a8755dc',
        '6df29c9ee4a2c895',
    ),
    'project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/raw/agent-return.jsonl': (
        '3988e72347d04306',
        '6580695a3d58a8e1',
        '880fe59835cdfbf9',
    ),
    'project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/work/step-outputs/adapter-30-s2-s3-submit-resume-closure-attempt-1/step-output.json': (
        'd4663c83d461b16d',
        'd4ed11a40dff22ed',
    ),
    'project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/work/step-outputs/adapter-30-s2-s3-submit-resume-evidence-integrity-attempt-1/step-output.json': (
        'acfb360f8a8418c5',
    ),
    'project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/work/step-outputs/adapter-30-s2-s3-submit-resume-work-attempt-1/step-output.json': (
        '35a73b9d36bc32a6',
        '11d0ee9c4c4bb478',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/evidence/claim_trace/agent/returned_claims.json': (
        'd3116895371a2554',
        '690ef344bd0dcd81',
        'b1e6b07564118b26',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/evidence/evidence-manifest.json': (
        '7a12ade402283a14',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/raw/agent-return.jsonl': (
        '74bb93e6b942b925',
        '820add8e51c64243',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/declared-building-plan.json': (
        '2b88987bce97f442',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/step-outputs/adapter-timeout-frontier-lifecycle-hardening-0625-code-attack-qa-attempt-1/step-output.json': (
        'aa4597709619c93f',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/step-outputs/adapter-timeout-frontier-lifecycle-hardening-0625-work-attempt-1/step-output.json': (
        'd9f19b47d4242091',
        '181cc3103600c962',
    ),
    'project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/task.md': (
        '4d9b13a1f6cd3600',
    ),
    'project/brick-protocol/buildings/broad-profile-drift-triage-0625/evidence/claim_trace/agent/returned_claims.json': (
        '4db281d36eeb06ab',
        'dc9df0cd88d39b63',
        '494c166b3d1cf05b',
        '494c166b3d1cf05b',
    ),
    'project/brick-protocol/buildings/broad-profile-drift-triage-0625/raw/agent-return.jsonl': (
        '3097d5e2b701354f',
        'b266411c29988e3e',
        'c81b9d7a3e7bf74a',
    ),
    'project/brick-protocol/buildings/broad-profile-drift-triage-0625/work/step-outputs/broad-profile-drift-triage-0625-closure-attempt-1/step-output.json': (
        '4e2f6d1084af19fb',
    ),
    'project/brick-protocol/buildings/broad-profile-drift-triage-0625/work/step-outputs/broad-profile-drift-triage-0625-plan-attempt-1/step-output.json': (
        'ef4efb784731830d',
        'ab98a39b03280cc2',
    ),
    'project/brick-protocol/buildings/broad-profile-drift-triage-0625/work/step-outputs/broad-profile-drift-triage-0625-review-attempt-1/step-output.json': (
        '4e2f6d1084af19fb',
    ),
    'project/brick-protocol/buildings/checker-profile-diet-implementation-plan-0625/evidence/claim_trace/agent/returned_claims.json': (
        '1e3e78fe2adea2bf',
    ),
    'project/brick-protocol/buildings/checker-profile-diet-implementation-plan-0625/raw/agent-return.jsonl': (
        'a154bd3725bfd0b0',
    ),
    'project/brick-protocol/buildings/checker-profile-diet-implementation-plan-0625/work/step-outputs/checker-profile-diet-implementation-plan-0625-plan-attempt-1/step-output.json': (
        '0db3dedf1148685a',
    ),
    'project/brick-protocol/buildings/claude-qa-execution-fresh-smoke-0625/evidence/claim_trace/agent/returned_claims.json': (
        '48ed7d174420c91d',
        'cd4e8968eadf0813',
    ),
    'project/brick-protocol/buildings/claude-qa-execution-fresh-smoke-0625/raw/agent-return.jsonl': (
        '2f0c832ab354d1eb',
    ),
    'project/brick-protocol/buildings/claude-qa-execution-fresh-smoke-0625/work/step-outputs/claude-qa-execution-fresh-smoke-0625-code-attack-qa-attempt-1/step-output.json': (
        '83d6843a0c3501a5',
        'd16b7fe109fb4929',
    ),
    'project/brick-protocol/buildings/four-llm-standard-graph-dogfood-design-0625/evidence/claim_trace/agent/returned_claims.json': (
        '0c6f8cb5042f49c9',
        '212ad09cd05aac3d',
    ),
    'project/brick-protocol/buildings/four-llm-standard-graph-dogfood-design-0625/raw/agent-return.jsonl': (
        '220a1d094da5c24d',
        'b2ccdd4362e9fa36',
    ),
    'project/brick-protocol/buildings/four-llm-standard-graph-dogfood-design-0625/work/step-outputs/four-llm-standard-graph-dogfood-design-0625-design-attempt-1/step-output.json': (
        '7565f90689991b89',
    ),
    'project/brick-protocol/buildings/four-llm-standard-graph-dogfood-design-0625/work/step-outputs/four-llm-standard-graph-dogfood-design-0625-review-attempt-1/step-output.json': (
        '2ac90d259c7ef2a6',
    ),
    'project/brick-protocol/buildings/four-provider-adapter-yaml-control-matrix-0625/evidence/claim_trace/agent/returned_claims.json': (
        'ddd693a298bde13b',
        'd618f4924247f0d0',
        '0d8fe24ca6f98a52',
    ),
    'project/brick-protocol/buildings/four-provider-adapter-yaml-control-matrix-0625/raw/agent-return.jsonl': (
        '183ff4456446acc7',
        '5c60c8f1d302c7e2',
        '57ff67803702e470',
    ),
    'project/brick-protocol/buildings/four-provider-adapter-yaml-control-matrix-0625/work/step-outputs/four-provider-adapter-yaml-control-matrix-0625-closure-attempt-1/step-output.json': (
        '45a9ffe3cd066968',
    ),
    'project/brick-protocol/buildings/four-provider-adapter-yaml-control-matrix-0625/work/step-outputs/four-provider-adapter-yaml-control-matrix-0625-plan-attempt-1/step-output.json': (
        '35d5fd2ebb4eb1ff',
    ),
    'project/brick-protocol/buildings/four-provider-adapter-yaml-control-matrix-0625/work/step-outputs/four-provider-adapter-yaml-control-matrix-0625-review-attempt-1/step-output.json': (
        '77aab7000b02979a',
    ),
    'project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/evidence/claim_trace/agent/returned_claims.json': (
        'b9641e65c29624e3',
        'b122819646b7ee5c',
    ),
    'project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/raw/agent-return.jsonl': (
        'b3aa812a5dc31ba0',
        'eebbc98687120d2b',
    ),
    'project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/work/step-outputs/gap2-customer-entry-readiness-0625-closure-attempt-1/step-output.json': (
        'e08fa1333d23e821',
    ),
    'project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/work/step-outputs/gap2-customer-entry-readiness-0625-review-attempt-1/step-output.json': (
        '82877bd34e46944d',
    ),
    'project/brick-protocol/buildings/p11-customer-dogfood-prep-0625/evidence/claim_trace/agent/returned_claims.json': (
        'e36f87b20b53de0f',
        'c8ae37b25ea29f35',
        '287153f450ab74ac',
    ),
    'project/brick-protocol/buildings/p11-customer-dogfood-prep-0625/raw/agent-return.jsonl': (
        '53aaefb736098261',
        '73c0fc825e9ca8b8',
        'ef268c9ca7f4d4ab',
    ),
    'project/brick-protocol/buildings/p11-customer-dogfood-prep-0625/work/step-outputs/p11-customer-dogfood-prep-0625-closure-attempt-1/step-output.json': (
        'a9b924885750056e',
    ),
    'project/brick-protocol/buildings/p11-customer-dogfood-prep-0625/work/step-outputs/p11-customer-dogfood-prep-0625-plan-attempt-1/step-output.json': (
        'f296610427d13730',
    ),
    'project/brick-protocol/buildings/p11-customer-dogfood-prep-0625/work/step-outputs/p11-customer-dogfood-prep-0625-review-attempt-1/step-output.json': (
        '9ae8ead12a899549',
    ),
    'project/brick-protocol/buildings/p7-evidence-root-location-policy-0625/evidence/evidence-manifest.json': (
        'e08d32dafc23ecff',
    ),
    'project/brick-protocol/buildings/p7-evidence-root-location-policy-0625/work/declared-building-plan.json': (
        'e433f4c18f085728',
    ),
    'project/brick-protocol/buildings/p7-evidence-root-location-policy-0625/work/task.md': (
        'b9f451d115fc2f9d',
    ),
    'project/brick-protocol/buildings/p9-checker-module-diet-followup-0625/evidence/claim_trace/agent/returned_claims.json': (
        '6de09c5794d30efe',
        '204d39775e907a15',
        'ee048a43d061e43b',
    ),
    'project/brick-protocol/buildings/p9-checker-module-diet-followup-0625/raw/agent-return.jsonl': (
        '4acfd0bf70816343',
        '0293c70743be9e00',
    ),
    'project/brick-protocol/buildings/p9-checker-module-diet-followup-0625/work/step-outputs/p9-checker-module-diet-followup-0625-plan-attempt-1/step-output.json': (
        'b30499be693392ab',
        '01e31fd82c37b602',
    ),
    'project/brick-protocol/buildings/p9-checker-module-diet-followup-0625/work/step-outputs/p9-checker-module-diet-followup-0625-review-attempt-1/step-output.json': (
        '19640cd241cd5d0e',
    ),
    'project/brick-protocol/buildings/p9-checker-profile-diet-design-0625/evidence/claim_trace/agent/returned_claims.json': (
        '9f55ef2ec79f758d',
        '1745750c800be730',
        'f5c9476c9fcd75d4',
        '9c15ded3eb8a0866',
        '709d5b9df4ab5b2e',
        '1e503e6a7002c974',
        '14bf0b04e5cef98c',
        '53d5a8306db00bf2',
    ),
    'project/brick-protocol/buildings/p9-checker-profile-diet-design-0625/raw/agent-return.jsonl': (
        '0d98833acc7ac40e',
        '615c432e459fcf61',
        '77934db2bf88f21d',
    ),
    'project/brick-protocol/buildings/p9-checker-profile-diet-design-0625/work/step-outputs/p9-checker-profile-diet-design-0625-closure-attempt-1/step-output.json': (
        '50dbc2094e81dd42',
        '31484ee5316a3be5',
        'fccdbba20b95416f',
    ),
    'project/brick-protocol/buildings/p9-checker-profile-diet-design-0625/work/step-outputs/p9-checker-profile-diet-design-0625-plan-attempt-1/step-output.json': (
        'ffbdfa4538934562',
        '9cedcb09508727f0',
        '98c1b124c2529896',
    ),
    'project/brick-protocol/buildings/p9-checker-profile-diet-design-0625/work/step-outputs/p9-checker-profile-diet-design-0625-review-attempt-1/step-output.json': (
        '1ec1fe0212e8dc2e',
        '7d791bc12bff3ffa',
    ),
}


def _rule13_line_digest(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]


def _rule13_scan_roots(repo: Path) -> tuple[Path, ...]:
    roots: list[Path] = []
    project_root = repo / "project"
    if not project_root.is_dir():
        return ()
    for building_root in sorted(project_root.glob("*/buildings/*")):
        if not building_root.is_dir():
            continue
        for part in sorted(_RULE13_BUILDING_EVIDENCE_PARTS):
            root = building_root / part
            if root.is_dir():
                roots.append(root)
    return tuple(roots)


def _rule13_text_files(repo: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for root in _rule13_scan_roots(repo):
        files.extend(
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.suffix in _RULE13_SCAN_SUFFIXES
        )
    return tuple(files)


def _rule13_line_violation_kinds(line: str) -> tuple[str, ...]:
    kinds: list[str] = []
    if _ABSOLUTE_USER_PATH_RE.search(line):
        kinds.append("absolute_local_user_path")
    if _SESSION_TEMP_PATH_RE.search(line):
        kinds.append("session_temporary_path")
    return tuple(kinds)


def _collect_rule13_durable_evidence_ref_violations(
    repo: Path,
    *,
    frozen_allowlist: Mapping[str, Sequence[str]] | None = None,
) -> tuple[list[str], int, dict[str, int]]:
    allowlist = frozen_allowlist if frozen_allowlist is not None else _RULE13_FROZEN_ALLOWLIST
    inspected = 0
    violations: list[str] = []
    allowlisted_lines: dict[str, int] = {}
    for path in _rule13_text_files(repo):
        inspected += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = to_posix(path.relative_to(repo))
        frozen = Counter(allowlist.get(rel, ()))
        matched = 0
        for lineno, line in enumerate(text.splitlines(), start=1):
            kinds = _rule13_line_violation_kinds(line)
            if not kinds:
                continue
            digest = _rule13_line_digest(line)
            if frozen.get(digest, 0) > 0:
                frozen[digest] -= 1
                matched += 1
                continue
            violations.append(
                f"{rel}:{lineno}: {','.join(kinds)} "
                f"(line content hash {digest} is not frozen-allowlisted)"
            )
        if matched:
            allowlisted_lines[rel] = matched
    return violations, inspected, allowlisted_lines


def _write_rule13_probe_tree(repo: Path, *, leak: bool) -> None:
    work = repo / "project" / "rule13-fixture" / "buildings" / "demo" / "work"
    evidence = repo / "project" / "rule13-fixture" / "buildings" / "demo" / "evidence"
    raw = repo / "project" / "rule13-fixture" / "buildings" / "demo" / "raw"
    for root in (work, evidence, raw):
        root.mkdir(parents=True, exist_ok=True)
    (work / "clean.json").write_text(
        '{"observed_evidence":["work/step-outputs/demo/step-output.json"]}\n',
        encoding="utf-8",
    )
    if leak:
        (work / "absolute-path.json").write_text(
            '{"observed":"/Users/smith/projects/BRICK/support/checkers"}\n',
            encoding="utf-8",
        )
        (evidence / "home-path.md").write_text(
            "durable evidence named /home/customer/brick-protocol here\n",
            encoding="utf-8",
        )
        (raw / "temp-path.jsonl").write_text(
            '{"tmp":"/private/var/folders/zz/session-id/tmp123/output.json"}\n',
            encoding="utf-8",
        )


def _rule13_fire_probe() -> int:
    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-rule13-clean-") as tmp:
        probe_repo = Path(tmp)
        _write_rule13_probe_tree(probe_repo, leak=False)
        violations, inspected_files, _ = _collect_rule13_durable_evidence_ref_violations(probe_repo)
        inspected += inspected_files
        if violations:
            raise ProfileError(
                "rule13_durable_evidence_ref clean-tree probe over-fired: "
                f"{violations[:3]}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-rule13-fire-") as tmp:
        probe_repo = Path(tmp)
        _write_rule13_probe_tree(probe_repo, leak=True)
        violations, inspected_files, _ = _collect_rule13_durable_evidence_ref_violations(probe_repo)
        inspected += inspected_files
        expected = {
            "absolute_local_user_path",
            "session_temporary_path",
        }
        observed = {
            kind
            for violation in violations
            for kind in expected
            if kind in violation
        }
        if observed != expected or len(violations) < 3:
            raise ProfileError(
                "rule13_durable_evidence_ref FIRE probe did NOT report every "
                f"Rule13 leak family; observed {violations!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-rule13-frozen-") as tmp:
        probe_repo = Path(tmp)
        _write_rule13_probe_tree(probe_repo, leak=False)
        target = (
            probe_repo
            / "project"
            / "rule13-fixture"
            / "buildings"
            / "demo"
            / "work"
            / "frozen.json"
        )
        frozen_line = '{"cwd":"/Users/smith/projects/BRICK"}'
        target.write_text(frozen_line + "\n", encoding="utf-8")
        rel = to_posix(target.relative_to(probe_repo))
        frozen_allowlist = {rel: (_rule13_line_digest(frozen_line),)}
        violations, inspected_files, allowlisted = _collect_rule13_durable_evidence_ref_violations(
            probe_repo,
            frozen_allowlist=frozen_allowlist,
        )
        inspected += inspected_files
        if violations or allowlisted.get(rel) != 1:
            raise ProfileError(
                "rule13_durable_evidence_ref frozen-hash probe did not honor "
                f"the exact content-hash exception: violations={violations!r}, "
                f"allowlisted={allowlisted!r}"
            )
        target.write_text('{"cwd":"/Users/smith/projects/BRICK-mutated"}\n', encoding="utf-8")
        mutated_violations, inspected_files, _ = _collect_rule13_durable_evidence_ref_violations(
            probe_repo,
            frozen_allowlist=frozen_allowlist,
        )
        inspected += inspected_files
        if not mutated_violations:
            raise ProfileError(
                "rule13_durable_evidence_ref mutation-RED did NOT fire when a "
                "frozen allowlisted line was replaced with different content"
            )
    return inspected


def run_rule13_durable_evidence_ref(repo: Path) -> KernelResult:
    probe_inspected = _rule13_fire_probe()
    violations, inspected, allowlisted_lines = _collect_rule13_durable_evidence_ref_violations(repo)
    if violations:
        listing = "\n".join(f"- {violation}" for violation in violations[:50])
        raise ProfileError(
            "Rule13 durable evidence ref observation found absolute local path, "
            "username-bearing local path, or session-temporary path evidence "
            "outside frozen content-hash exceptions:\n"
            + listing
        )
    return KernelResult(
        check_id="rule13_durable_evidence_ref",
        inspected=inspected + probe_inspected,
        output=(
            "Rule13 durable evidence ref observation passed: scanned Building "
            "work/evidence/raw text surfaces for /Users, /home, and session-temp "
            "path identifiers; clean/leak FIRE probes and frozen-line mutation-RED "
            "probe ran; "
            f"{len(allowlisted_lines)} frozen file(s) / "
            f"{sum(allowlisted_lines.values())} frozen line(s) matched exact "
            "content hashes."
        ),
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence Rule13 durable evidence reference checker."
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        result = run_rule13_durable_evidence_ref(repo)
    except ProfileError as exc:
        print("rule13 durable evidence ref check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    print(result.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
