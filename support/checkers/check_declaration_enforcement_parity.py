#!/usr/bin/env python3
"""Check declared Brick-template enforcement has a live consumer or ledger row.

This checker covers two declaration/execution parity rules:

* every ``forbidden_return_keys`` item declared by Brick return templates is
  present in the Agent return-fact enforcement set, after the same key
  normalization used by ``agent.return_fact``;
* every narrow "future/later gate consumer" declaration in Brick template YAML
  is registered in ``brick/templates/enforcement-ledger.yaml``, and every ledger
  row still points at text that exists.

Support evidence only. It imports Agent return-fact constants read-only, writes
nothing, chooses no Movement, and judges neither success nor quality.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
for _entry in (_REPO_ROOT, _REPO_ROOT / "support" / "import_identity"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from agent.return_fact import (  # noqa: E402
    ALWAYS_SECRET_KEYS,
    TOP_LEVEL_VERDICT_KEYS,
)
from support.checkers.lib.yaml_subset import parse_yaml_subset  # noqa: E402


BRICK_RETURNS_ROOT = Path("brick") / "templates" / "bricks"
BRICK_RETURN_FILENAME = "return.yaml"
LEDGER_REL = Path("brick/templates/enforcement-ledger.yaml")
DECLARATION_SCAN_ROOT = Path("brick/templates")
DECLARATION_SCAN_EXCLUDES = {
    "brick/templates/enforcement-ledger.yaml",
}
DECLARATION_PHRASES = (
    "future Link-side completion gate consumes this declared field",
    "Link-side gate is a later consumer",
    "gate is a later consumer",
)
CASE_VARIANT_DECLARATION_PROBE = "FUTURE link-side completion GATE CONSUMES this declared field"
PROOF_LIMIT = (
    "proof limit: declaration-enforcement parity checker support evidence only; "
    "it does not prove source truth, success judgment, quality judgment, Movement "
    "authority, semantic fitness of future gates, or provider behavior."
)


class DeclarationEnforcementParityError(ValueError):
    """Raised when a declaration has no matching enforcement/ledger evidence."""


def _normalize_declared_return_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True)
class GatePendingDeclaration:
    path: str
    line_no: int
    text: str

    @property
    def ref(self) -> str:
        return f"{self.path}:{self.line_no}"


@dataclass(frozen=True)
class LedgerRow:
    declaration_ref: str
    declaration_text: str
    enforced_by: str | None
    gate_pending: str | None


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeclarationEnforcementParityError(f"{label} must be a mapping")
    return value


def _as_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeclarationEnforcementParityError(f"{label} must be non-blank text")
    return value.strip()


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DeclarationEnforcementParityError(f"{label} must be a list")
    return value


def _load_yaml_mapping(repo: Path, rel: Path) -> Mapping[str, Any]:
    path = repo / rel
    if not path.is_file():
        raise DeclarationEnforcementParityError(f"missing required file {rel}")
    try:
        parsed = parse_yaml_subset(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report parser errors as checker rejection.
        raise DeclarationEnforcementParityError(f"{rel} did not parse: {exc}") from exc
    return _as_mapping(parsed, str(rel))


def _forbidden_return_keys(doc: Mapping[str, Any], rel: Path) -> tuple[str, ...]:
    raw = doc.get("forbidden_return_keys")
    if raw is None:
        return ()
    values = _as_list(raw, f"{rel}:forbidden_return_keys")
    keys: list[str] = []
    for index, value in enumerate(values):
        keys.append(_as_text(value, f"{rel}:forbidden_return_keys[{index}]"))
    return tuple(keys)


def _enforced_return_key_set() -> frozenset[str]:
    return frozenset(
        _normalize_declared_return_key(key) for key in (TOP_LEVEL_VERDICT_KEYS | ALWAYS_SECRET_KEYS)
    )


def _assert_forbidden_key_parity(
    declared_by_file: Mapping[str, tuple[str, ...]],
    enforced_keys: frozenset[str],
) -> str:
    missing: list[str] = []
    for rel, keys in sorted(declared_by_file.items()):
        for key in keys:
            normalized = _normalize_declared_return_key(key)
            if normalized not in enforced_keys:
                missing.append(f"{rel}: forbidden_return_keys item {key!r} normalizes to {normalized!r}")
    if missing:
        raise DeclarationEnforcementParityError(
            "Brick return template forbidden_return_keys missing from Agent return-fact "
            "enforcement set:\n- " + "\n- ".join(missing)
        )
    total = sum(len(keys) for keys in declared_by_file.values())
    return (
        "forbidden-return-key parity green: "
        f"{total} declared key item(s) across {len(declared_by_file)} return template(s) "
        "are present in TOP_LEVEL_VERDICT_KEYS union ALWAYS_SECRET_KEYS after normalization."
    )


def _collect_forbidden_return_keys(repo: Path) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for path in sorted((repo / BRICK_RETURNS_ROOT).glob(f"*/{BRICK_RETURN_FILENAME}")):
        rel = path.relative_to(repo)
        keys = _forbidden_return_keys(_load_yaml_mapping(repo, rel), rel)
        if keys:
            result[str(rel)] = keys
    if not result:
        raise DeclarationEnforcementParityError(
            f"no forbidden_return_keys found under {BRICK_RETURNS_ROOT}/*/{BRICK_RETURN_FILENAME}"
        )
    return result


def _scan_gate_pending_declarations(repo: Path) -> tuple[GatePendingDeclaration, ...]:
    matches: list[GatePendingDeclaration] = []
    for path in sorted((repo / DECLARATION_SCAN_ROOT).glob("**/*.yaml")):
        rel = path.relative_to(repo).as_posix()
        if rel in DECLARATION_SCAN_EXCLUDES:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip().lstrip("#").strip()
            if _line_matches_gate_pending_declaration(stripped):
                matches.append(GatePendingDeclaration(rel, line_no, _declaration_match_text(stripped)))
    return tuple(matches)


def _line_matches_gate_pending_declaration(stripped: str) -> bool:
    """Match the narrow future/later gate-consumer declaration family."""
    normalized = " ".join(stripped.lower().replace("_", " ").replace("-", " ").split())
    if any(phrase.lower() in normalized for phrase in DECLARATION_PHRASES):
        return True
    has_gate = "gate" in normalized
    has_later_consumer = "later consumer" in normalized
    has_future_consumer = "future" in normalized and (
        "consumer" in normalized or "consumes" in normalized
    )
    return has_gate and (has_later_consumer or has_future_consumer)


def _declaration_match_text(stripped: str) -> str:
    normalized = " ".join(stripped.lower().replace("_", " ").replace("-", " ").split())
    for phrase in DECLARATION_PHRASES:
        if phrase.lower() in normalized:
            return phrase
    return "future/later gate-consumer declaration"


def _parse_ledger_rows(repo: Path) -> tuple[LedgerRow, ...]:
    doc = _load_yaml_mapping(repo, LEDGER_REL)
    rows = _as_list(doc.get("declarations"), f"{LEDGER_REL}:declarations")
    parsed: list[LedgerRow] = []
    for index, raw in enumerate(rows):
        row = _as_mapping(raw, f"{LEDGER_REL}:declarations[{index}]")
        declaration_ref = _as_text(
            row.get("declaration_ref"), f"{LEDGER_REL}:declarations[{index}].declaration_ref"
        )
        declaration_text = _as_text(
            row.get("declaration_text"), f"{LEDGER_REL}:declarations[{index}].declaration_text"
        )
        enforced_by_raw = row.get("enforced_by")
        gate_pending_raw = row.get("gate_pending")
        enforced_by = (
            _as_text(enforced_by_raw, f"{LEDGER_REL}:declarations[{index}].enforced_by")
            if enforced_by_raw is not None
            else None
        )
        gate_pending = (
            _as_text(gate_pending_raw, f"{LEDGER_REL}:declarations[{index}].gate_pending")
            if gate_pending_raw is not None
            else None
        )
        if (enforced_by is None) == (gate_pending is None):
            raise DeclarationEnforcementParityError(
                f"{LEDGER_REL}:declarations[{index}] must carry exactly one of "
                "enforced_by or gate_pending"
            )
        parsed.append(LedgerRow(declaration_ref, declaration_text, enforced_by, gate_pending))
    if not parsed:
        raise DeclarationEnforcementParityError(f"{LEDGER_REL}:declarations must not be empty")
    return tuple(parsed)


def _path_from_declaration_ref(ref: str) -> Path:
    marker = ".yaml"
    if marker not in ref:
        raise DeclarationEnforcementParityError(
            f"ledger declaration_ref {ref!r} must include a .yaml path"
        )
    return Path(ref[: ref.index(marker) + len(marker)])


def _line_no_from_declaration_ref(ref: str) -> int | None:
    suffix = ref.rsplit(":", 1)[-1]
    if suffix.isdigit():
        return int(suffix)
    return None


def _assert_ledger_rows_resolve(repo: Path, rows: Iterable[LedgerRow]) -> None:
    for row in rows:
        rel = _path_from_declaration_ref(row.declaration_ref)
        path = repo / rel
        if not path.is_file():
            raise DeclarationEnforcementParityError(
                f"{LEDGER_REL}: declaration_ref {row.declaration_ref!r} points at missing file"
            )
        lines = path.read_text(encoding="utf-8").splitlines()
        line_no = _line_no_from_declaration_ref(row.declaration_ref)
        if line_no is not None:
            if line_no < 1 or line_no > len(lines):
                raise DeclarationEnforcementParityError(
                    f"{LEDGER_REL}: declaration_ref {row.declaration_ref!r} line is out of range"
                )
            haystack = lines[line_no - 1]
        else:
            haystack = "\n".join(lines)
        if row.declaration_text not in haystack:
            raise DeclarationEnforcementParityError(
                f"{LEDGER_REL}: declaration_ref {row.declaration_ref!r} no longer contains "
                f"declaration_text {row.declaration_text!r}"
            )


def _assert_unique_refs(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise DeclarationEnforcementParityError(
            f"duplicate {label}(s): {', '.join(sorted(duplicates))}"
        )


def _assert_gate_pending_ledger_closure(
    declarations: tuple[GatePendingDeclaration, ...],
    rows: tuple[LedgerRow, ...],
) -> str:
    _assert_unique_refs((row.declaration_ref for row in rows), "ledger declaration_ref")
    row_refs = {row.declaration_ref for row in rows}
    missing = [declaration.ref for declaration in declarations if declaration.ref not in row_refs]
    if missing:
        raise DeclarationEnforcementParityError(
            "gate-pending declaration(s) missing from enforcement ledger:\n- "
            + "\n- ".join(missing)
        )
    declaration_refs = {declaration.ref for declaration in declarations}
    stale = [
        row.declaration_ref
        for row in rows
        if row.gate_pending is not None and row.declaration_ref not in declaration_refs
    ]
    if stale:
        raise DeclarationEnforcementParityError(
            "gate-pending ledger row(s) no longer correspond to scanned declaration text:\n- "
            + "\n- ".join(stale)
        )
    return (
        "gate-pending ledger closure green: "
        f"{len(declarations)} scanned declaration site(s) are registered and "
        f"{len(rows)} ledger row(s) resolve to live declaration text."
    )


def _assert_mutation_red_forbidden_key(
    declared_by_file: Mapping[str, tuple[str, ...]],
    enforced_keys: frozenset[str],
) -> str:
    if not any("good_enough" in keys for keys in declared_by_file.values()):
        raise DeclarationEnforcementParityError(
            "mutation RED failed: no declared good_enough key available to drop"
        )
    mutated = frozenset(enforced_keys - {"good_enough"})
    try:
        _assert_forbidden_key_parity(declared_by_file, mutated)
    except DeclarationEnforcementParityError:
        return (
            "mutation RED observed: dropping 'good_enough' from the in-memory "
            "Agent enforcement set is rejected."
        )
    raise DeclarationEnforcementParityError(
        "mutation RED failed: dropping 'good_enough' from the in-memory Agent "
        "enforcement set was still accepted"
    )


def _assert_mutation_red_ledger(
    declarations: tuple[GatePendingDeclaration, ...],
    rows: tuple[LedgerRow, ...],
) -> str:
    if not rows:
        raise DeclarationEnforcementParityError("mutation RED failed: no ledger row to drop")
    mutated = rows[1:] if len(rows) > 1 else ()
    try:
        _assert_gate_pending_ledger_closure(declarations, mutated)
    except DeclarationEnforcementParityError:
        return "mutation RED observed: dropping one in-memory ledger row is rejected."
    raise DeclarationEnforcementParityError(
        "mutation RED failed: dropping one in-memory ledger row was still accepted"
    )


def _assert_mutation_red_case_variant_declaration(
    declarations: tuple[GatePendingDeclaration, ...],
    rows: tuple[LedgerRow, ...],
) -> str:
    if not _line_matches_gate_pending_declaration(CASE_VARIANT_DECLARATION_PROBE):
        raise DeclarationEnforcementParityError(
            "mutation RED failed: case-variant future/later gate-consumer probe was not scanned"
        )
    if not declarations:
        raise DeclarationEnforcementParityError(
            "mutation RED failed: no declaration site available for case-variant probe"
        )
    probe = GatePendingDeclaration(
        declarations[0].path,
        max(declaration.line_no for declaration in declarations) + 1000,
        CASE_VARIANT_DECLARATION_PROBE,
    )
    try:
        _assert_gate_pending_ledger_closure(declarations + (probe,), rows)
    except DeclarationEnforcementParityError:
        return (
            "mutation RED observed: a case-variant future/later gate-consumer "
            "declaration without a ledger row is rejected."
        )
    raise DeclarationEnforcementParityError(
        "mutation RED failed: a case-variant future/later gate-consumer declaration "
        "without a ledger row was still accepted"
    )


def check(repo: Path) -> list[str]:
    declared_by_file = _collect_forbidden_return_keys(repo)
    enforced_keys = _enforced_return_key_set()
    forbidden_line = _assert_forbidden_key_parity(declared_by_file, enforced_keys)
    forbidden_red = _assert_mutation_red_forbidden_key(declared_by_file, enforced_keys)

    declarations = _scan_gate_pending_declarations(repo)
    if not declarations:
        raise DeclarationEnforcementParityError(
            "no gate-pending declaration phrases found under brick/templates"
        )
    rows = _parse_ledger_rows(repo)
    _assert_ledger_rows_resolve(repo, rows)
    ledger_line = _assert_gate_pending_ledger_closure(declarations, rows)
    ledger_red = _assert_mutation_red_ledger(declarations, rows)
    case_variant_red = _assert_mutation_red_case_variant_declaration(declarations, rows)
    return [
        forbidden_line,
        forbidden_red,
        ledger_line,
        ledger_red,
        case_variant_red,
        "scanned gate-pending declaration refs: "
        + ", ".join(declaration.ref for declaration in declarations),
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for Brick declaration/enforcement parity "
            "and gate-pending declaration ledger closure."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except DeclarationEnforcementParityError as exc:
        print("declaration-enforcement parity rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
