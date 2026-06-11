#!/usr/bin/env python3
"""PIN-ESTATE-INTEGRITY: three disciplines over the live history-doc pin estate.

After W2 DOC-DECOUPLE (82 decorative pins retired, ledger
``archive/PIN-RETIREMENT-LEDGER-0611.md``) the surviving history-doc pin estate
was small and load-bearing; CLEAN-YARD v3 (0611) retired the last of it WITH
its subjects (the estate is now EMPTY by design -- standing history docs left
for the frozen museum and their properties became executed cases). This
checker ports the ACTIVE-SPEC-SPINE-0 grounding disciplines (concept lift from
the never-merged ``codex/active-spec-spine-0`` branch,
``d5bc86e:support/checkers/check_doc_grounding.py``; its JSON claim dataset is
dead and deliberately NOT ported) onto that estate:

  (a) DECORATIVE-PIN REJECTION (branch concept: ``_execute_recipe`` rejecting
      ``path_exists``-only recipes, d5bc86e:154-157): a ``text_contains`` /
      ``text_absent`` pin block on a history doc must pin CONTENT (>= 1
      non-blank needle), a ``json_required_paths`` block on a history doc must
      require >= 1 key path (a keyless json block asserts the file parses, not
      that any recorded field survived — decoration), and a history doc
      carrying a ``path_exists`` pin must ALSO carry at least one content pin
      (text needle or json required key) somewhere in the estate. A
      path-existence-only history pin is decoration: it asserts a file is
      there, not that the recorded meaning survived. ``path_absent`` items are
      content-ful by nature (an anti-resurrection assertion) and carry no
      needle requirement.

  (b) ADVERSARIAL PIN PROBES (branch concept: ``_execute_adversarial_probe``,
      d5bc86e:215-251, scoped down to per-doc temp copies instead of full repo
      copies): for a deterministic SAMPLE of the live estate (generalized
      CLEAN-YARD v3 0611: first text_contains + first/last text_absent blocks
      when any exist; an EMPTY estate -- the shipped state -- yields an empty
      sample and the six synthetic FIRE probes stay the anti-tautology),
      copy ONLY the pinned doc into a temp repo, run the REAL
      production pin runner (``rule_runners.text_rule``) for sanity, MUTATE the
      pinned text (remove a pinned needle / inject a forbidden stale literal),
      and assert the pin runner REDs with its expected rejection. This proves
      the surviving pins actually fire, instead of trusting that they would.

  (c) PIN-ESTATE RATCHET (branch concept: ratchet growth requires a recorded
      human disposition, d5bc86e:339-397): the counted estate must match the
      LATEST dated disposition entry in
      ``support/checkers/pin_estate_baseline.yaml``. Growth OR shrink of the
      history-doc pin estate without appending a new dated human disposition
      line REDs. Silent pin deletion is exactly how W2 found 82 decorations; a
      change must leave a dated trace.

      HONEST LIMIT — the ratchet is tamper-EVIDENT, not tamper-PROOF. A single
      change can still drift the estate AND append a fresh dated disposition
      entry with the matching new counts; nothing here can distinguish that
      from a legitimate disposition (the dated note IS the trace a reviewer
      audits — the mechanism guarantees a reviewable trace exists, not that
      the trace is honest). What IS mechanically closed (codex-review
      tightening A, 0611): rewriting the recorded latest entry IN-PLACE.
      ``structure_template_integrity.yaml`` carries a ``text_contains`` pin on
      the latest disposition entry's exact count lines + note, so an in-place
      baseline rewrite REDs unless the SAME change also touches the profile
      pin — a two-place, review-visible change. Convention: every appended
      disposition extends that profile pin to the new latest entry.

Anti-tautology: six synthetic FIRE probes run RED-first on every invocation
(a decorative path-only block, an empty-needle block, a keyless
json_required_paths block, a suppressed-mutation probe that must report "pin
did not fire", a drifted ratchet count, and a disposition without a dated
note). A FIRE probe that is NOT rejected makes ``main()`` return non-zero, so
a silently-neutered discipline drives ``--all`` RED.

Collector scope (codex-review tightening B, 0611): the estate counts
``path_exists`` / ``path_absent`` items, ``text_contains`` / ``text_absent``
blocks, and ``json_required_paths`` blocks whose target hits a history
prefix. The first cut counted only path_exists + the two text kinds, so a
path_absent or json_required_paths block on a history doc could enter or
leave the estate without the ratchet noticing; both kinds are 0 on today's
tree, and any future one now requires a dated disposition.

Support evidence only. This checker decides nothing; it is not source truth,
not success judgment, not quality judgment, and not Movement authority. It
admits no axis/fact class and imports no axis module.
"""

from __future__ import annotations

import argparse
import os.path as _osp
import shutil
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
for _entry in (_REPO_ROOT, _osp.join(_REPO_ROOT, "support", "import_identity")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from support.checkers.lib.yaml_subset import (  # noqa: E402
    ProfileError,
    parse_yaml_subset,
)


PROFILE_DIR = "support/checkers/profiles"
BASELINE_PATH = "support/checkers/pin_estate_baseline.yaml"
BASELINE_SCHEMA = "pin-estate-baseline/v1"
# History-doc surfaces: the status kernel (incl. current-working-context.md),
# the spec museum feeder, and the archive museum W2 moved frozen docs into.
HISTORY_PREFIXES = (
    "project/brick-protocol/status/kernel/",
    "support/docs/spec/",
    "archive/",
)
TEXT_PIN_KINDS = ("text_contains", "text_absent")
JSON_PIN_KIND = "json_required_paths"
PATH_PIN_KINDS = ("path_exists", "path_absent")
# Discipline (b) sample: generalized (CLEAN-YARD v3, 0611) -- no bespoke doc
# anchor; see _select_probe_sample (empty estate => empty sample; the six
# synthetic FIRE probes stay the anti-tautology).


class PinEstateError(Exception):
    """Raised when a pin-estate discipline rejects the estate."""


@dataclass(frozen=True)
class PinBlock:
    profile: str
    kind: str  # path_exists | path_absent | text_contains | text_absent | json_required_paths
    doc: str
    # text kinds: text needles; json_required_paths: required key paths;
    # path kinds: empty.
    needles: tuple[str, ...]


def _needle_list(block: Mapping[str, Any], label: str) -> tuple[str, ...]:
    needles = block.get("texts", block.get("text"))
    if isinstance(needles, str):
        return (needles,)
    if isinstance(needles, list) and all(isinstance(item, str) for item in needles):
        return tuple(needles)
    raise PinEstateError(f"{label}: text pin block carries no parseable texts/text")


def collect_history_pins(repo: Path) -> list[PinBlock]:
    profiles = sorted((repo / PROFILE_DIR).glob("*.yaml"))
    if not profiles:
        raise PinEstateError(f"no profiles found under {PROFILE_DIR}")
    pins: list[PinBlock] = []
    for profile_path in profiles:
        parsed = parse_yaml_subset(profile_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, Mapping):
            raise PinEstateError(f"{profile_path.name}: profile did not parse to a mapping")
        for kind in PATH_PIN_KINDS:
            for item in parsed.get(kind, []) or []:
                if isinstance(item, str) and item.startswith(HISTORY_PREFIXES):
                    pins.append(PinBlock(profile_path.name, kind, item, ()))
        for kind in TEXT_PIN_KINDS:
            for item in parsed.get(kind, []) or []:
                if not isinstance(item, Mapping):
                    continue
                doc = item.get("path", "")
                if isinstance(doc, str) and doc.startswith(HISTORY_PREFIXES):
                    needles = _needle_list(item, f"{profile_path.name}:{kind}:{doc}")
                    pins.append(PinBlock(profile_path.name, kind, doc, needles))
        for item in parsed.get(JSON_PIN_KIND, []) or []:
            if not isinstance(item, Mapping):
                continue
            doc = item.get("path", "")
            if isinstance(doc, str) and doc.startswith(HISTORY_PREFIXES):
                required = item.get("required")
                if required is None:
                    keys: tuple[str, ...] = ()
                elif isinstance(required, list) and all(
                    isinstance(entry, str) for entry in required
                ):
                    keys = tuple(required)
                else:
                    raise PinEstateError(
                        f"{profile_path.name}:{JSON_PIN_KIND}:{doc}: required must be a "
                        "list of key-path strings"
                    )
                pins.append(PinBlock(profile_path.name, JSON_PIN_KIND, doc, keys))
    return pins


# ---------------------------------------------------------------------------
# Discipline (a): DECORATIVE-PIN REJECTION
# ---------------------------------------------------------------------------

def validate_non_decorative(pins: list[PinBlock]) -> None:
    # Content pins = text needles OR json required keys; path_absent is a
    # content-ful negative assertion on its own and json keyless blocks are
    # rejected below, so neither rescues a bare path_exists.
    content_pinned_docs = {
        pin.doc
        for pin in pins
        if pin.needles and pin.kind in (*TEXT_PIN_KINDS, JSON_PIN_KIND)
    }
    for pin in pins:
        if pin.kind in TEXT_PIN_KINDS:
            if not pin.needles:
                raise PinEstateError(
                    f"decorative pin: {pin.profile} {pin.kind} on {pin.doc} pins no text "
                    "(a history-doc text pin must carry at least one needle)"
                )
            for needle in pin.needles:
                if not needle.strip():
                    raise PinEstateError(
                        f"decorative pin: {pin.profile} {pin.kind} on {pin.doc} carries a "
                        "blank needle (texts must be non-empty content, not placeholders)"
                    )
        if pin.kind == JSON_PIN_KIND and not pin.needles:
            raise PinEstateError(
                f"decorative pin: {pin.profile} {JSON_PIN_KIND} on history doc {pin.doc} "
                "requires no key paths; a json block that only asserts the file parses "
                "as JSON, not that any recorded field survived, is decoration"
            )
    for pin in pins:
        if pin.kind == "path_exists" and pin.doc not in content_pinned_docs:
            raise PinEstateError(
                f"decorative pin: {pin.profile} path_exists on history doc {pin.doc} has no "
                "accompanying content pin (text needle or json required key) anywhere in "
                "the profile estate; a rule block whose only assertion is path-existence "
                "on a history doc is decoration"
            )


# ---------------------------------------------------------------------------
# Discipline (b): ADVERSARIAL PIN PROBES
# ---------------------------------------------------------------------------

def _select_probe_sample(pins: list[PinBlock]) -> list[PinBlock]:
    """Deterministic adversarial sample over whatever text pins survive.

    CLEAN-YARD v3 (Smith 0611): the product repo ships ZERO standing dogfood
    evidence, so the history-doc pin estate may legitimately be EMPTY (the old
    anchors -- the KEEP-LIVE CWC structure block and the two anti-stale
    text_absent guards -- left with their subjects; the same properties are
    now executed cases over check-time generated evidence). With an empty
    estate the adversarial sample is empty and the six synthetic FIRE probes
    (run RED-first on every invocation, incl. the suppressed-mutation probe
    that drives the REAL probe executor over a temp doc) remain the
    anti-tautology. When text pins DO exist on the history prefixes again,
    the sample is the first text_contains block plus the first and last
    text_absent blocks (sorted by profile/doc), so a re-grown estate is
    probed without a bespoke anchor.
    """

    text_contains = sorted(
        (pin for pin in pins if pin.kind == "text_contains"),
        key=lambda pin: (pin.profile, pin.doc),
    )
    anti_stale = sorted(
        (pin for pin in pins if pin.kind == "text_absent"),
        key=lambda pin: (pin.profile, pin.doc),
    )
    sample: list[PinBlock] = []
    if text_contains:
        sample.append(text_contains[0])
    if anti_stale:
        sample.append(anti_stale[0])
        if anti_stale[-1] is not anti_stale[0]:
            sample.append(anti_stale[-1])
    return sample


def _run_text_rule(temp_repo: Path, pin: PinBlock, needles: tuple[str, ...]) -> None:
    """Run the REAL production pin runner against the temp copy."""
    from support.checkers.lib.rule_runners import text_rule

    text_rule(pin.kind, temp_repo, {pin.kind: [{"path": pin.doc, "texts": list(needles)}]})


def _execute_pin_probe(repo: Path, pin: PinBlock, *, mutate: bool = True) -> None:
    """Copy the pinned doc to a temp repo, mutate the pinned text, expect RED.

    ``mutate=False`` exists ONLY for the FIRE self-probe: an unmutated copy must
    make this function reject with "pin did not fire" (proving the probe cannot
    pass vacuously).
    """
    source = repo / pin.doc
    if not source.is_file():
        raise PinEstateError(f"probe target doc missing on disk: {pin.doc}")
    needle = pin.needles[0]
    temp_root = Path(tempfile.mkdtemp(prefix="pin-estate-probe-"))
    try:
        target = temp_root / pin.doc
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        target.write_text(text, encoding="utf-8")
        # Sanity: the live pin must hold on the unmutated copy, else the live
        # estate itself is stale and the probe would prove nothing.
        try:
            _run_text_rule(temp_root, pin, pin.needles)
        except ProfileError as exc:
            raise PinEstateError(
                f"probe sanity failed: live pin {pin.profile} {pin.kind} {pin.doc} does not "
                f"hold on an unmutated copy: {exc}"
            ) from exc
        if mutate:
            if pin.kind == "text_contains":
                mutated = text.replace(needle, "", 1)
                if mutated == text:
                    raise PinEstateError(
                        f"probe mutation impossible: needle {needle!r} not found in {pin.doc}"
                    )
            else:  # text_absent: inject the forbidden stale literal
                mutated = text + "\n" + needle + "\n"
            target.write_text(mutated, encoding="utf-8")
        try:
            _run_text_rule(temp_root, pin, pin.needles)
        except ProfileError as exc:
            expected = f"{pin.kind} rejected"
            if expected not in str(exc):
                raise PinEstateError(
                    f"probe REDDED for the wrong reason on {pin.doc}: {exc}"
                ) from exc
            return
        raise PinEstateError(
            f"pin did not fire: {pin.profile} {pin.kind} on {pin.doc} stayed green "
            "against mutated pinned text"
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def run_adversarial_probes(repo: Path, pins: list[PinBlock]) -> list[str]:
    probed: list[str] = []
    for pin in _select_probe_sample(pins):
        _execute_pin_probe(repo, pin)
        probed.append(f"{pin.profile}:{pin.kind}:{pin.doc}")
    return probed


# ---------------------------------------------------------------------------
# Discipline (c): PIN-ESTATE RATCHET
# ---------------------------------------------------------------------------

def _estate_counts(pins: list[PinBlock]) -> dict[str, int]:
    counts = {
        "path_exists_blocks": sum(1 for pin in pins if pin.kind == "path_exists"),
        "path_absent_blocks": sum(1 for pin in pins if pin.kind == "path_absent"),
        "text_contains_blocks": sum(1 for pin in pins if pin.kind == "text_contains"),
        "text_absent_blocks": sum(1 for pin in pins if pin.kind == "text_absent"),
        "json_required_paths_blocks": sum(1 for pin in pins if pin.kind == JSON_PIN_KIND),
        "text_needles": sum(
            len(pin.needles) for pin in pins if pin.kind in TEXT_PIN_KINDS
        ),
        "json_required_keys": sum(
            len(pin.needles) for pin in pins if pin.kind == JSON_PIN_KIND
        ),
    }
    counts["total_blocks"] = (
        counts["path_exists_blocks"]
        + counts["path_absent_blocks"]
        + counts["text_contains_blocks"]
        + counts["text_absent_blocks"]
        + counts["json_required_paths_blocks"]
    )
    return counts


def _require_int(value: Any, label: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PinEstateError(f"{label} must be an integer, observed {value!r}") from exc


def validate_ratchet(baseline_data: Any, pins: list[PinBlock]) -> dict[str, int]:
    if not isinstance(baseline_data, Mapping):
        raise PinEstateError("pin estate baseline must parse to a mapping")
    if baseline_data.get("schema") != BASELINE_SCHEMA:
        raise PinEstateError(f"pin estate baseline schema must be {BASELINE_SCHEMA!r}")
    dispositions = baseline_data.get("dispositions")
    if not isinstance(dispositions, list) or not dispositions:
        raise PinEstateError("pin estate baseline must carry a non-empty dispositions list")
    previous_date = ""
    for index, entry in enumerate(dispositions):
        if not isinstance(entry, Mapping):
            raise PinEstateError(f"dispositions[{index}] must be a mapping")
        date = str(entry.get("date", "")).strip()
        note = str(entry.get("note", "")).strip()
        if not date:
            raise PinEstateError(
                f"dispositions[{index}] lacks a date; estate changes need a dated human "
                "disposition line"
            )
        if not note:
            raise PinEstateError(
                f"dispositions[{index}] lacks a disposition note; estate changes need a "
                "recorded human disposition, not a bare count edit"
            )
        if date < previous_date:
            raise PinEstateError(
                f"dispositions[{index}] date {date!r} is older than the previous entry "
                f"{previous_date!r}; the disposition ledger is append-only"
            )
        previous_date = date
    latest = dispositions[-1]
    observed = _estate_counts(pins)
    for key, observed_value in observed.items():
        recorded = _require_int(latest.get(key), f"latest disposition {key}")
        if recorded != observed_value:
            raise PinEstateError(
                f"pin estate drifted without a new dated disposition: {key} recorded "
                f"{recorded}, observed {observed_value}; append a dated disposition entry "
                f"to {BASELINE_PATH} (growth AND shrink both require a human trace)"
            )
    return observed


def _load_baseline(repo: Path) -> Any:
    baseline_path = repo / BASELINE_PATH
    if not baseline_path.is_file():
        raise PinEstateError(f"pin estate baseline file missing: {BASELINE_PATH}")
    return parse_yaml_subset(baseline_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# FIRE probes (anti-tautology; RED-first on every run)
# ---------------------------------------------------------------------------

def _fire_baseline_data(counts: Mapping[str, int], **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "date": "2026-06-11",
        "note": "synthetic FIRE disposition",
        **{key: value for key, value in counts.items()},
    }
    entry.update(overrides)
    return {"schema": BASELINE_SCHEMA, "dispositions": [entry]}


def run_fire_probes(repo: Path, pins: list[PinBlock]) -> list[str]:
    counts = _estate_counts(pins)
    synthetic_doc = "archive/SYNTHETIC-FIRE-DOC-0611.md"
    probes: list[tuple[str, Any]] = [
        (
            "decorative_path_only_block",
            lambda: validate_non_decorative(
                pins + [PinBlock("synthetic.yaml", "path_exists", synthetic_doc, ())]
            ),
        ),
        (
            "decorative_blank_needle",
            lambda: validate_non_decorative(
                pins + [PinBlock("synthetic.yaml", "text_contains", synthetic_doc, ("  ",))]
            ),
        ),
        (
            "decorative_json_no_required_keys",
            lambda: validate_non_decorative(
                pins
                + [
                    PinBlock(
                        "synthetic.yaml",
                        JSON_PIN_KIND,
                        "archive/SYNTHETIC-FIRE-DOC-0611.json",
                        (),
                    )
                ]
            ),
        ),
        ("probe_suppressed_mutation_must_red", lambda: _fire_suppressed_mutation(repo)),
        (
            "ratchet_count_drift",
            lambda: validate_ratchet(
                _fire_baseline_data({**counts, "total_blocks": counts["total_blocks"] + 1}),
                pins,
            ),
        ),
        (
            "ratchet_disposition_without_note",
            lambda: validate_ratchet(_fire_baseline_data(counts, note=""), pins),
        ),
    ]
    rejected: list[str] = []
    for probe_id, probe in probes:
        try:
            probe()
        except PinEstateError:
            rejected.append(probe_id)
        else:
            raise PinEstateError(f"FIRE probe did not reject: {probe_id}")
    return rejected


def _fire_suppressed_mutation(repo: Path) -> None:
    """A probe whose mutation is suppressed must report "pin did not fire"."""
    temp_root = Path(tempfile.mkdtemp(prefix="pin-estate-fire-"))
    try:
        doc_rel = "archive/synthetic-fire-probe-doc.md"
        doc = temp_root / doc_rel
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("SYNTHETIC PINNED NEEDLE\n", encoding="utf-8")
        pin = PinBlock("synthetic.yaml", "text_contains", doc_rel, ("SYNTHETIC PINNED NEEDLE",))
        _execute_pin_probe(temp_root, pin, mutate=False)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pin-estate integrity: decorative-pin rejection, adversarial pin probes, "
            "and the pin-estate ratchet over the surviving history-doc pin estate. "
            "Support evidence only; not source truth, success judgment, quality "
            "judgment, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        pins = collect_history_pins(repo)
        fired = run_fire_probes(repo, pins)
        validate_non_decorative(pins)
        probed = run_adversarial_probes(repo, pins)
        counts = validate_ratchet(_load_baseline(repo), pins)
    except (OSError, ProfileError, PinEstateError) as exc:
        print(f"pin estate integrity rejected: {exc}", file=sys.stderr)
        return 1
    print(
        "pin estate integrity passed: "
        f"{counts['total_blocks']} history-doc pin block(s) "
        f"({counts['path_exists_blocks']} path_exists / "
        f"{counts['path_absent_blocks']} path_absent / "
        f"{counts['text_contains_blocks']} text_contains / "
        f"{counts['text_absent_blocks']} text_absent / "
        f"{counts['json_required_paths_blocks']} json_required_paths, "
        f"{counts['text_needles']} text needle(s), "
        f"{counts['json_required_keys']} json required key(s)) matched the dated baseline; "
        f"{len(probed)} adversarial pin probe(s) fired RED on mutated copies "
        f"({', '.join(probed)}); {len(fired)} FIRE probe(s) rejected."
    )
    print(
        "proof limit: support evidence only; this checker does not prove source truth, "
        "success judgment, quality judgment, Movement authority, that unsampled pins "
        "fire, or that pinned prose still matches code behavior (the W2 ledger's "
        "file:line citations carry that)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
