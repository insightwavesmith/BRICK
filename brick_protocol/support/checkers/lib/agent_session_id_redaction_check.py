"""Agent session-id redaction kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes static provider/runtime session-id redaction boundaries; it owns no
axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.chat_session_park_check import (
    _chat_session_probe_ulid_text,
    _chat_session_probe_uuid_text,
)
from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError, to_posix


# ---------------------------------------------------------------------------
# AGENT-SESSION-ID-REDACTION guard (TREASURE PORT 2, 0611). Lifted from the
# never-merged codex/agent-axis-slice-a-0605 branch
# (2d44fc7:brick_protocol/support/checkers/lib/kernel_checks.py:1188-1273, regexes + scan
# logic verbatim) and adapted to today's tree: the archive/ museum W2 moved
# frozen history into is now a scan root, and the branch's "zero-tolerance, no
# allowlist" stance (it REDACTED its 45 historical sites) is replaced by the
# 0611 operator policy: frozen building evidence and archived history are NOT
# rewritten; the investigator-verified legacy leaks are carried on an explicit
# per-path allowlist of frozen line-content hashes (codex-review tightening C
# replaced the original line-COUNT budgets, which let a same-count swap
# through), and any NEW leak fails closed.
#
# AGENTS principle: a provider-specific (or runtime) session id must NEVER be
# stored in a support record, projection, or evidence surface. The adapter
# exception frontier scrubs them at the durable boundary
# (brick_protocol/support/operator/run.py::_safe_exception_excerpt); this is the STATIC
# counterpart that forbids a raw session id from being committed into the kernel
# status records, building work/evidence, the review dispositions, or the
# archived history.
#
# Detection (layout-robust; the branch's first cut demanded a same-line cue and
# so MISSED the dominant real layouts -- a "Claude session id:" label line above
# a UUID in a fenced ```text block, and "PID / <uuid>" subagent rows). Now:
#   * ANY RFC-4122-shaped UUID (incl. UUIDv7) OR Crockford-base32 ULID, with NO
#     cue requirement. Legit identifiers in these roots are slug ids and 64-hex
#     sha256 hashes, which are never UUID/ULID-shaped, so a bare one here is
#     always a runtime/session/run id (re-verified on today's tree 0611: every
#     hit in the scan roots is one of the 6 allowlisted legacy session-id sites).
#   * keyed forms  session_id / session_token / provider_session / resume_token /
#     conversation_id / continuation_id : <v> (also "key":"<v>" compact JSON and
#     camelCase/prefixed keys via a lazy [\w-]*? prefix; the value must contain a
#     digit, so "session id: unknown" is NOT flagged)
#   * prefixed value tokens  sess_/sess- / provider-session- / resume-token- /
#     chatcmpl- / ya29. (Google OAuth) / JWT (eyJ.x.y)  (the underscore/dash
#     forms require a digit in the value, so prose like "provider-session-looking"
#     is NOT flagged)
# Deliberately OUT of static scope (ACCEPTED RESIDUAL, zero live instances): a
# generic provider OBJECT-id prefix sweep (run_/msg_/resp_/thread_/step_/...) is
# NOT flagged here because it collides with legitimate dev identifiers
# (run_compose0, run_gemini35_flash); and note the run.py error-text redactor
# does NOT sweep those prefixes either, so there is no separate compensating
# control for them. A bare opaque token with no session key and no known shape
# (e.g. a dash-less 32-hex id, which would collide with MD5) is likewise not
# statically detectable without false-positives. The standing guarantee for
# those is that the engine must not STORE provider ids in the first place (the
# run.py exception-frontier redactor scrubs the KNOWN session formats).
_SESSION_ID_VALUE_TOKEN_RES = (
    # sess_ AND sess- (OpenAI emits both underscore and dash session prefixes).
    re.compile(r"(?i)\bsess[_-](?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bprovider-session-(?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bresume[_-]token[_-](?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bchatcmpl-[A-Za-z0-9]{6,}"),
    re.compile(r"\bya29\.[A-Za-z0-9._-]{10,}"),                                    # Google OAuth token
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),  # JWT (3 segments)
)
# Bare ULID (Crockford base32, 26 chars, excludes I/L/O/U) -- some providers issue
# ULID session ids. Empirically FP-clean: legit ids in the scan roots are slug URNs
# + 64-hex sha256, neither of which is a 26-char uppercase ULID.
_SESSION_ID_ULID_RE = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")
# Quoted-or-bare session key followed by an id-shaped value. Covers the KV form
# (session_id: <uuid>), compact JSON ("session_id":"01HX..."), AND camelCase /
# prefixed keys (providerSessionId, chat_session_id) via the lazy [\w-]*? prefix.
# The value lookahead requires a DIGIT so a real id (UUID/ULID/chatcmpl all carry
# digits) is caught while prose like "session id: unknown" is not; and the value
# class excludes '<', so the "<redacted-session-id>" placeholder is NOT re-flagged.
_SESSION_ID_KEYED_RE = re.compile(
    r"(?i)['\"]?\b[\w-]*?"
    r"(?:session[ _-]?id|session[ _-]?token|provider[ _-]?session|resume[ _-]?token"
    r"|conversation[ _-]?id|continuation[ _-]?id)"
    r"\b['\"]?\s*[:=]\s*['\"]?(?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"
)
_SESSION_ID_UUID_PATTERN = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_SESSION_ID_UUID_RE = re.compile(rf"\b{_SESSION_ID_UUID_PATTERN}\b")
_CLAUDE_ARTIFACT_UUID_RE = re.compile(
    rf"https://claude\.ai/code/artifact/(?P<artifact_uuid>{_SESSION_ID_UUID_PATTERN})"
)
# PROJECT-0 S1-C: project scan roots are derived PER VESSEL (every
# project/<id>/buildings + project/<id>/status — a new project must never be a
# silently unscanned landing zone for session-id leaks; widened 0611 from
# project #1's status/kernel to full status/, re-verified 0 offenders). The
# static roots stay literal. The frozen-history allowlist below is keyed by
# exact path and is unchanged by this widening.
_SESSION_ID_STATIC_SCAN_ROOTS = (
    "brick_protocol/support/docs/reviews",
    # CLEAN-YARD v3 (0611): the archive/ museum root left for the frozen
    # history repo; the per-vessel project roots + reviews remain the scan
    # surface (a resurrected archive/ would be rejected by path admission
    # before it could become a landing zone).
)


def _session_id_scan_roots(repo: Path) -> tuple[str, ...]:
    project_roots = [
        to_posix(path.relative_to(repo))
        for pattern in ("*/buildings", "*/status")
        for path in sorted((repo / "project").glob(pattern))
        if path.is_dir()
    ]
    return tuple(project_roots) + _SESSION_ID_STATIC_SCAN_ROOTS
_SESSION_ID_SCAN_SUFFIXES = (".md", ".json", ".jsonl", ".txt")
# FROZEN-HISTORY ALLOWLIST — EMPTY in the product repo (REPO-SPLIT seed 0611,
# checker-split-map-0611.md ⚠1): the 6-file/8-line frozen legacy allowlist
# moved to the history repo WITH the files it froze. The one allowlisted file
# that ships product-side (the p9 catalog dogfood work record) had its single
# legacy session-id line REDACTED in the product copy instead of carried as an
# allowlist row, so a new user's evidence tree starts with ZERO tolerated
# session-id lines. Any future entry here requires the same discipline the
# history repo used: path -> tuple of sha256[:16] digests of the EXACT
# offending line content (a ceiling, not a pin — see run_agent_session_id_redaction).
_SESSION_ID_LEGACY_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # 0612 (F11 evidence, frozen): building adapter-30-s2-s3-submit-resume's QA
    # honestly DESCRIBED its negative probe and embedded the RFC example UUID
    # (123e4567-...) in the probe text — not a real session id. The same
    # observation also reports the F11 gap (UUID accepted in dict-KEY position
    # by the submission rejector), queued for repair. Two lines, digest-frozen.
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/evidence/claim_trace/agent/returned_claims.json": ("8cdb07e6a732f184",),
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/work/step-outputs/adapter-30-s2-s3-submit-resume-code-attack-qa-attempt-1/step-output.json": ("d55e8f20f0e2107a",),
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/raw/agent-return.jsonl": ("be1f92f79aac6848",),
}


def _session_line_digest(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]


def _line_without_allowed_artifact_uuid(line: str) -> str:
    return _CLAUDE_ARTIFACT_UUID_RE.sub(
        lambda match: match.group(0).replace(
            match.group("artifact_uuid"), "<artifact-uuid>"
        ),
        line,
    )


def _line_carries_session_id(line: str) -> bool:
    uuid_scan_line = _line_without_allowed_artifact_uuid(line)
    if _SESSION_ID_UUID_RE.search(uuid_scan_line) or _SESSION_ID_ULID_RE.search(line):
        return True
    if _SESSION_ID_KEYED_RE.search(line):
        return True
    if any(pattern.search(line) for pattern in _SESSION_ID_VALUE_TOKEN_RES):
        return True
    return False


def _session_id_redaction_fire_probe() -> None:
    """Built-in anti-tautological FIRE probe (CLEAN-YARD v3, ⚠ §1-1).

    The product allowlist is EMPTY and the product tree carries zero leaks, so
    without a probe the scan could silently stop matching and stay green. On
    every invocation this builds a TEMP repo with one synthetic vessel whose
    status/kernel record carries a fake provider session id (a bare UUID --
    the dominant real leak layout) and asserts the REAL scan path reports it;
    then asserts the same vessel WITHOUT the leak scans clean. The temp tree
    is removed by the TemporaryDirectory context. A probe that does not fire
    raises ProfileError, so --all EXITs non-zero.
    """

    # One leak line PER detection pattern, each crafted so only ITS matcher
    # catches it. A single combined line would let one pattern die silently
    # behind another.
    family_leaks = {
        "bare-uuid": "subagent row " + _chat_session_probe_uuid_text(),
        "bare-ulid": "subagent row " + _chat_session_probe_ulid_text(),
        "keyed-session": "conversation_id: abc123def456ghi",
        "value-token-session-prefix": "transport sess_a1b2c3d4e5f6g7",
        "value-token-provider-session": "transport provider-session-a1b2c3d4",
        "value-token-resume-token": "transport resume_token_a1b2c3d4",
        "value-token-chat-completion": "transport chatcmpl-a1b2c3d4",
        "value-token-google-oauth": "transport ya29.a1b2c3d4e5",
        "value-token-jwt": "transport eyJa1b2c3d4.eyJe5f6g7h8.sig9",
    }
    with tempfile.TemporaryDirectory(prefix="bp-session-id-fire-") as tmp:
        probe_repo = Path(tmp)
        kernel_dir = probe_repo / "project" / "fire-probe-vessel" / "status" / "kernel"
        kernel_dir.mkdir(parents=True)
        leak_doc = kernel_dir / "fire-probe-record.md"
        body_lines = ["# synthetic FIRE probe record", ""]
        family_lineno: dict[str, int] = {}
        for family, leak in family_leaks.items():
            body_lines.append(leak)
            family_lineno[family] = len(body_lines)
        leak_doc.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
        offenders = _collect_session_id_offenders(probe_repo)[0]
        offender_linenos: set[int] = set()
        for entry in offenders:
            tail = entry.rsplit(":", 1)[-1].split(" ")[0]
            if tail.isdigit():
                offender_linenos.add(int(tail))
        for family, lineno in family_lineno.items():
            if lineno not in offender_linenos:
                raise ProfileError(
                    "agent_session_id_redaction FIRE probe did NOT fire for the "
                    f"{family} detection family: a synthetic session-id leak in a "
                    "temp-generated vessel was not reported (that matcher has "
                    "stopped matching; the empty-allowlist green is no longer "
                    "trustworthy)"
                )
        leak_doc.write_text(
            "# synthetic FIRE probe record\n\n"
            "allowed artifact URL "
            f"https://claude.ai/code/artifact/{_chat_session_probe_uuid_text()}\n",
            encoding="utf-8",
        )
        artifact_offenders = _collect_session_id_offenders(probe_repo)[0]
        if artifact_offenders:
            raise ProfileError(
                "agent_session_id_redaction FIRE probe over-fired on a Claude "
                f"artifact URL UUID path segment: {artifact_offenders[:3]}"
            )
        leak_doc.write_text(
            "# synthetic FIRE probe record\n\n"
            "not an allowed artifact URL "
            f"https://example.invalid/artifact/{_chat_session_probe_uuid_text()}\n",
            encoding="utf-8",
        )
        broad_url_offenders = _collect_session_id_offenders(probe_repo)[0]
        if not broad_url_offenders:
            raise ProfileError(
                "agent_session_id_redaction FIRE probe did NOT fire for a UUID "
                "path segment on a non-Claude artifact URL; the artifact exception "
                "has widened beyond its admitted boundary"
            )
        leak_doc.write_text(
            "# synthetic FIRE probe record\n\nno session id here\n", encoding="utf-8"
        )
        clean_offenders = _collect_session_id_offenders(probe_repo)[0]
        if clean_offenders:
            raise ProfileError(
                "agent_session_id_redaction FIRE probe over-fired: a clean "
                f"synthetic vessel reported offenders: {clean_offenders[:3]}"
            )


def _collect_session_id_offenders(repo: Path) -> tuple[list[str], int, dict[str, int]]:
    inspected = 0
    offenders: list[str] = []
    allowlisted_lines: dict[str, int] = {}
    for root_rel in _session_id_scan_roots(repo):
        root = repo / root_rel
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in _SESSION_ID_SCAN_SUFFIXES:
                continue
            inspected += 1
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = to_posix(path.relative_to(repo))
            frozen = _SESSION_ID_LEGACY_ALLOWLIST.get(rel)
            hits = [
                (lineno, line)
                for lineno, line in enumerate(text.splitlines(), start=1)
                if _line_carries_session_id(line)
            ]
            if frozen is None:
                offenders.extend(f"{rel}:{lineno}" for lineno, _line in hits)
                continue
            remaining = Counter(frozen)
            matched = 0
            for lineno, line in hits:
                digest = _session_line_digest(line)
                if remaining.get(digest, 0) > 0:
                    remaining[digest] -= 1
                    matched += 1
                else:
                    offenders.append(
                        f"{rel}:{lineno} (offending line's content hash {digest} is "
                        "not a frozen allowlisted legacy line of this file; a "
                        "same-count replacement, swap, or addition is a NEW leak)"
                    )
            if matched:
                allowlisted_lines[rel] = matched
    return offenders, inspected, allowlisted_lines


def run_agent_session_id_redaction(repo: Path) -> KernelResult:
    # RED-first: prove the scan still fires on a synthetic leak in a
    # temp-generated vessel before trusting the live tree's green.
    _session_id_redaction_fire_probe()
    offenders, inspected, allowlisted_lines = _collect_session_id_offenders(repo)
    if offenders:
        listing = "\n".join(offenders[:25])
        raise ProfileError(
            "provider/runtime session id present in a support record, building "
            "work/evidence, review disposition, or archived history outside the "
            "frozen-history allowlist; it must be redacted per the AGENTS "
            "session-id principle:\n"
            f"{listing}"
        )
    return KernelResult(
        check_id="agent_session_id_redaction",
        inspected=inspected,
        output=(
            "FIRE probe fired (synthetic leak in a temp vessel RED); no NEW "
            "provider/runtime session id in scanned support records, "
            "building work/evidence, review dispositions, or archived history; "
            f"{len(allowlisted_lines)} frozen-history legacy file(s) whose "
            f"{sum(allowlisted_lines.values())} offending line(s) all matched "
            "their frozen content hashes."
        ),
    )


def _run_agent_axis_behavioral_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "agent_axis_behavioral",
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
    needle = "def run_agent_session_id_redaction(repo: Path) -> KernelResult:"
    poisoned = "def run_agent_session_id_redaction_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(
            "agent_session_id_redaction mutation probe could not find redaction entrypoint"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".agent-session-id-redaction-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_agent_axis_behavioral_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "agent_session_id_redaction mutation probe did not turn "
                "agent_axis_behavioral profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_agent_axis_behavioral_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "agent_session_id_redaction mutation probe restored source but "
            f"agent_axis_behavioral remained RED:\n{excerpt}"
        )

    return [
        "agent session-id redaction mutation RED probe passed: disabling the "
        "moved run_agent_session_id_redaction entrypoint made check_profile.py "
        "--profile agent_axis_behavioral exit non-zero, then restoring the "
        "temp-backed self file returned agent_axis_behavioral to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for agent session-id redaction."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_agent_session_id_redaction "
            "entrypoint, assert agent_axis_behavioral profile exits RED, restore "
            "from a temp backup, then assert agent_axis_behavioral is GREEN"
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
            else [run_agent_session_id_redaction(repo).output]
        )
    except ProfileError as exc:
        print("agent session-id redaction check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
