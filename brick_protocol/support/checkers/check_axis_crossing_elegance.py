#!/usr/bin/env python3
"""Elegance guard: one canonical contract per crossing, no mixing, narrow waist.

The elegance yardstick (engine blueprint 0531 §1/§7, Smith 0531): at each AXIS
CROSSING exactly ONE canonical contract crosses; an axis's internal change hides
behind that contract (information hiding / narrow waist); a support module must
not bundle 2+ crossings' mechanics and must reach another axis ONLY via the
canonical contract (no axis-internal symbol import). Every support module is a
registered Table B row; god-modules carry a G6 decomposition ceiling
(owns_crossings <= ceiling). NOTE: G6 is a self-consistency check, not an
independently-enforced one-way ratchet — see check_g6_decomposition_ratchet's
proof-limit docstring (decision C 0601: the real re-bloat defense is G2+G1+G4).

This is an INDEPENDENT ORACLE. It imports NO Brick/Agent/Link axis module (and
no checker module that does — e.g. not check_profile, which imports
MOVEMENT_LITERALS). It hand-re-encodes the support forbidden-ownership baseline
(G5) rather than reading it from code, and it parses the two registry YAMLs with
its own minimal reader so it is not tautological with the parser under test.

Data-driven off two append-only registries:
  - brick_protocol/support/checkers/crossing_registry.yaml   (Table A, the 11 axis crossings)
  - brick_protocol/support/checkers/module_registry.yaml     (Table B, one row per support module)
Adding a crossing/module row needs NO edit to this guard.

Six FIRE-able rules (each has an anti-tautological negative probe that MUST turn
this check RED; the kernel check raises if any probe was not rejected):
  G1 one-contract-per-crossing   canonical_contract unique across crossings
  G2 no-mixing                   a non-exempt, non-decomposition module owns <=1
  G3 cross-via-canonical-only    AST-scan: every axis-internal import symbol is a
                                 canonical_symbol of a crossing defined in that
                                 axis file; no other axis-internal symbol crosses
  G4 unregistered-module-rejected every brick_protocol/support/*.py (minus __init__/test) is a
                                 module_registry row AND in the mag-0 path gate;
                                 bidirectional (registry <-> mag-0)
  G5 consume-not-author          each support row re-states the forbidden-author
                                 baseline (hand-re-encoded here, not read from code)
  G6 decomposition-target ceiling a row carrying decomposition_target owns
                                 <= its declared ceiling (self-consistency check,
                                 NOT an enforced one-way ratchet — see proof limit)

Proof limit: this guard governs SHAPE/boundary only. Behavior BODIES stay pinned
by check_axis_contract_projection / check_recording_checker_derived_contract /
the behavioral case checkers. Support evidence only: it decides nothing, is not
source truth, success judgment, quality judgment, or Movement authority, and
admits no axis or fact class.
"""

from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)


CROSSING_REGISTRY_REL = "brick_protocol/support/checkers/crossing_registry.yaml"
MODULE_REGISTRY_REL = "brick_protocol/support/checkers/module_registry.yaml"

# The three axes whose internal symbols may cross only via a canonical contract.
AXIS_PACKAGE_ROOTS = ("brick", "agent", "link")

# G5: the support forbidden-ownership baseline, HAND-RE-ENCODED here (NOT read
# from any module) so the guard independently asserts what support must never
# author. Every support-row forbidden_ownership must restate this set.
SUPPORT_FORBIDDEN_OWNERSHIP = frozenset(
    {
        "movement_author",
        "target_selector",
        "success_judge",
        "quality_judge",
        "route_invent",
    }
)

# Roles allowed to bundle 2+ crossings (mixing-exempt, with reason) — blueprint
# §4. Everything else is single-crossing under G2; god-modules instead carry a
# decomposition_target and are governed by the G6 ceiling (self-consistency).
MIXING_EXEMPT_ROLES = frozenset({"facade", "oracle", "carrier", "evidence-assembly"})

# G4 scope: support modules live under these roots. __init__.py is a package
# marker (excluded); test_* / *_test.py are tests (excluded).
SUPPORT_ROOT = "brick_protocol/support"

PROOF_LIMIT = (
    "proof limit: axis-crossing elegance guard governs shape/boundary only; it "
    "does not prove contract body behavior, source truth, success judgment, "
    "quality judgment, or Movement authority. Bodies stay pinned by "
    "axis_contract_projection / recording_checker_derived_contract / case checkers."
)


class CrossingEleganceError(ValueError):
    """Raised when the registry/code set violates an elegance rule."""


# ---------------------------------------------------------------------------
# minimal, self-contained YAML reader (registry subset only)
#
# Supports exactly what the two registries use: 2-space indentation, mappings,
# lists of mappings, inline ``[]`` empty lists, ``- scalar`` list items, and
# scalar values (str / true / false / "" / quoted). It is intentionally NOT the
# check_profile parser (independence / anti-tautology) and is forgiving enough
# for governance YAML while rejecting structural surprises.
# ---------------------------------------------------------------------------
def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or line[index - 1].isspace():
                return line[:index]
    return line


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [_scalar(item) for item in body.split(",")]
    return value


def _rows(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        without = _strip_comment(raw).rstrip()
        if not without.strip():
            continue
        indent = len(without) - len(without.lstrip(" "))
        if indent % 2:
            raise CrossingEleganceError(f"line {line_no}: indentation must use two-space steps")
        rows.append((indent, without.lstrip(" ")))
    return rows


def parse_registry_yaml(text: str) -> Any:
    rows = _rows(text)
    if not rows:
        return {}

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        _, content = rows[index]
        if content.startswith("- "):
            return parse_list(index, indent)
        return parse_map(index, indent)

    def parse_map(index: int, indent: int) -> tuple[dict[str, Any], int]:
        mapping: dict[str, Any] = {}
        while index < len(rows):
            cur_indent, content = rows[index]
            if cur_indent < indent or content.startswith("- "):
                break
            if cur_indent > indent:
                raise CrossingEleganceError(f"line {index + 1}: unexpected nested mapping")
            if ":" not in content:
                raise CrossingEleganceError(f"line {index + 1}: expected key: value")
            key, raw_value = content.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            if not raw_value:
                if index + 1 < len(rows) and rows[index + 1][0] > indent:
                    mapping[key], index = parse_block(index + 1, rows[index + 1][0])
                else:
                    mapping[key] = {}
                    index += 1
            else:
                mapping[key] = _scalar(raw_value)
                index += 1
        return mapping, index

    def parse_list(index: int, indent: int) -> tuple[list[Any], int]:
        values: list[Any] = []
        while index < len(rows):
            cur_indent, content = rows[index]
            if cur_indent != indent or not content.startswith("- "):
                break
            item = content[2:].strip()
            if item and ":" in item and not item.startswith(("'", '"')):
                key, _, after = item.partition(":")
                if key.strip() and (not after or after[0].isspace()):
                    item_map: dict[str, Any] = {}
                    raw_value = after.strip()
                    if not raw_value:
                        if index + 1 < len(rows) and rows[index + 1][0] > indent:
                            item_map[key.strip()], index = parse_block(index + 1, rows[index + 1][0])
                        else:
                            item_map[key.strip()] = {}
                            index += 1
                    else:
                        item_map[key.strip()] = _scalar(raw_value)
                        index += 1
                    if index < len(rows) and rows[index][0] > indent:
                        extra, index = parse_map(index, rows[index][0])
                        item_map.update(extra)
                    values.append(item_map)
                    continue
            values.append(_scalar(item))
            index += 1
        return values, index

    parsed, _next = parse_block(0, rows[0][0])
    return parsed


# ---------------------------------------------------------------------------
# registry loaders
# ---------------------------------------------------------------------------
def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CrossingEleganceError(f"{label} must be a mapping")
    return value


def _str_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def load_crossings(repo: Path) -> list[Mapping[str, Any]]:
    text = (repo / CROSSING_REGISTRY_REL).read_text(encoding="utf-8")
    doc = _mapping(parse_registry_yaml(text), CROSSING_REGISTRY_REL)
    rows = doc.get("crossings")
    if not isinstance(rows, list) or not rows:
        raise CrossingEleganceError(f"{CROSSING_REGISTRY_REL}: crossings must be a non-empty list")
    return [_mapping(row, f"{CROSSING_REGISTRY_REL}: crossings[]") for row in rows]


def load_modules(repo: Path) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    text = (repo / MODULE_REGISTRY_REL).read_text(encoding="utf-8")
    doc = _mapping(parse_registry_yaml(text), MODULE_REGISTRY_REL)
    rows = doc.get("modules")
    if not isinstance(rows, list) or not rows:
        raise CrossingEleganceError(f"{MODULE_REGISTRY_REL}: modules must be a non-empty list")
    ceilings = doc.get("decomposition_ceilings")
    ceiling_rows = ceilings if isinstance(ceilings, list) else []
    module_rows = [_mapping(row, f"{MODULE_REGISTRY_REL}: modules[]") for row in rows]
    # ONE row per module (the registry header's own rule): a duplicate row means
    # two divergent descriptions of the same module can drift apart silently
    # (found live 0611: dashboard_export.py registered twice). Fail closed here
    # so the census stays a census.
    seen_modules: dict[str, int] = {}
    for index, row in enumerate(module_rows):
        module_path = str(row.get("module", ""))
        if module_path in seen_modules:
            raise CrossingEleganceError(
                f"{MODULE_REGISTRY_REL}: duplicate modules[] row for "
                f"{module_path!r} (rows {seen_modules[module_path]} and {index}) "
                "— the registry is ONE row per module; merge or remove the stale row"
            )
        seen_modules[module_path] = index
    return (
        module_rows,
        [_mapping(row, f"{MODULE_REGISTRY_REL}: decomposition_ceilings[]") for row in ceiling_rows],
    )


# ---------------------------------------------------------------------------
# the six rules — each appends to a shared violations list
# ---------------------------------------------------------------------------
def check_g1_one_contract_per_crossing(
    crossings: Sequence[Mapping[str, Any]], violations: list[str]
) -> None:
    seen: dict[str, str] = {}
    for row in crossings:
        contract = str(row.get("canonical_contract", "")).strip()
        crossing_id = str(row.get("crossing_id", "<missing>")).strip()
        if not contract:
            violations.append(f"G1: crossing {crossing_id} has no canonical_contract")
            continue
        if contract in seen:
            violations.append(
                f"G1: contract {contract!r} reused by crossings "
                f"{seen[contract]},{crossing_id} (exactly one contract per crossing)"
            )
        else:
            seen[contract] = crossing_id


def check_g2_no_mixing(modules: Sequence[Mapping[str, Any]], violations: list[str]) -> None:
    for row in modules:
        module = str(row.get("module", "<missing>")).strip()
        role = str(row.get("role", "")).strip()
        decomposition_target = str(row.get("decomposition_target", "")).strip()
        owns = _str_list(row.get("owns_crossings"))
        # Role-exempt (facade/oracle/carrier/evidence-assembly) may bundle.
        if role in MIXING_EXEMPT_ROLES:
            continue
        # A declared god-module is governed by the G6 ceiling, not G2.
        if decomposition_target:
            continue
        if len(owns) > 1:
            violations.append(
                f"G2: module {module} owns {len(owns)} crossings (role={role!r}), max 1 "
                f"unless mixing-exempt role or decomposition_target: {owns}"
            )


def _axis_internal_imports(tree: ast.Module) -> list[tuple[str, str, int]]:
    """Return (axis_file, symbol, lineno) for every axis-internal import.

    An axis-internal import is ``from brick_protocol.{brick,agent,link}.<mod>
    import <sym>`` or ``from {brick,agent,link}.<mod> import <sym>``. Importing
    the axis SUBMODULE itself (``import brick.work``) without naming a symbol is
    treated as the module path with symbol "" (still attributed to that file).
    Catches nested (function-local) imports via ast.walk.
    """

    found: list[tuple[str, str, int]] = []
    # CLOSE-2/F3 (codex review 2): catch the five STATIC import reach forms, not just
    # `from axis.mod import sym`. Two binding maps:
    #   name_binding[local_name]   -> axis_file   (a Name that IS the axis submodule)
    #   dotted_binding["a.b.c"]    -> axis_file   (a bare-imported dotted module path)
    # then flag attribute access on either (the attr is the reached member).
    # SCOPE (codex review 3 P3): this covers the five STATIC import+attribute forms
    # only. DYNAMIC reach — getattr(gate, "_X"), importlib.import_module(...)._X,
    # __import__, string eval — is intentionally OUT OF SCOPE and NOT-PROVEN here;
    # AST cannot resolve dynamic targets without execution. Such reaches are a
    # support-authoring anti-pattern caught by review, not by this static guard.
    name_binding: dict[str, str] = {}
    dotted_binding: dict[str, str] = {}

    def _axis_file(parts: list[str]) -> str | None:
        if parts and parts[0] == "brick_protocol":
            parts = parts[1:]
        if len(parts) < 2 or parts[0] not in AXIS_PACKAGE_ROOTS:
            return None
        return f"brick_protocol/{parts[0]}/{parts[1]}.py"

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            mod_parts = node.module.split(".")
            stripped = mod_parts[1:] if mod_parts and mod_parts[0] == "brick_protocol" else mod_parts
            af = _axis_file(mod_parts)
            if af is not None:
                # `from axis.mod import sym` — sym is a member of that axis file.
                for alias in node.names:
                    found.append((af, alias.name, getattr(node, "lineno", 0)))
            elif (
                stripped and stripped[0] in AXIS_PACKAGE_ROOTS and len(stripped) == 1
            ):
                # `from brick_protocol.link import gate [as g]` — the imported
                # NAME is the axis SUBMODULE itself; bind it so `gate._x` is caught.
                for alias in node.names:
                    sub_af = _axis_file([stripped[0], alias.name])
                    if sub_af is not None:
                        name_binding[alias.asname or alias.name] = sub_af
        elif isinstance(node, ast.Import):
            # `import brick_protocol.link.gate [as g]` / `import link.gate`
            for alias in node.names:
                af = _axis_file(alias.name.split("."))
                if af is None:
                    continue
                if alias.asname:
                    name_binding[alias.asname] = af          # `as g` -> g._x
                else:
                    # bare: the bound name is the full dotted path; `a.b.c._x`.
                    dotted = alias.name
                    if dotted.startswith("brick_protocol."):
                        dotted = dotted[len("brick_protocol."):]
                    dotted_binding[dotted] = af
                    dotted_binding[alias.name] = af  # also the with-prefix form

    def _flatten(attr: ast.Attribute) -> tuple[str | None, str]:
        # Return (dotted-base-path, final-attr) for `a.b.c.x` -> ("a.b.c","x").
        final = attr.attr
        chain: list[str] = []
        cur: ast.expr = attr.value
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            chain.append(cur.id)
        else:
            return (None, final)
        return (".".join(reversed(chain)), final)

    if name_binding or dotted_binding:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            base, final = _flatten(node)
            lineno = getattr(node, "lineno", 0)
            # simple Name base: `g._x`
            if isinstance(node.value, ast.Name) and node.value.id in name_binding:
                found.append((name_binding[node.value.id], node.attr, lineno))
            # dotted base: `brick_protocol.link.gate._x` or `link.gate._x`
            elif base is not None and base in dotted_binding:
                found.append((dotted_binding[base], final, lineno))
    return found


def check_g3_cross_via_canonical_only(
    repo: Path,
    crossings: Sequence[Mapping[str, Any]],
    support_modules: Sequence[str],
    violations: list[str],
) -> int:
    # Build, per axis file, the union of canonical_symbols across the crossings
    # defined there (a file may host >1 crossing, e.g. brick_protocol/link/transition.py). Only
    # axis crossings contribute (support ReportPacket is not an axis crossing).
    canonical_by_file: dict[str, set[str]] = {}
    for row in crossings:
        if row.get("is_axis_crossing") is False:
            continue
        defined_at = str(row.get("defined_at", "")).strip()
        if not defined_at:
            continue
        canonical_by_file.setdefault(defined_at, set()).update(
            _str_list(row.get("canonical_symbols"))
        )

    inspected = 0
    for relative in support_modules:
        path = repo / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except SyntaxError as exc:
            violations.append(f"G3: module {relative} is not valid Python: {exc}")
            continue
        inspected += 1
        for axis_file, symbol, lineno in _axis_internal_imports(tree):
            allowed = canonical_by_file.get(axis_file)
            if allowed is None:
                violations.append(
                    f"G3: module {relative}:{lineno} imports from axis file {axis_file} "
                    "which declares no crossing in crossing_registry"
                )
                continue
            if symbol not in allowed:
                axis = axis_file.split("/", 1)[0]
                violations.append(
                    f"G3: module {relative}:{lineno} reaches axis-internal "
                    f"{axis}.{symbol} (not a canonical contract symbol of {axis_file})"
                )
    return inspected


def collect_support_modules(repo: Path) -> list[str]:
    """Every brick_protocol/support/*.py minus __init__.py and tests (G4 scope)."""

    root = repo / SUPPORT_ROOT
    out: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        name = path.name
        if name == "__init__.py":
            continue
        if name.startswith("test_") or name.endswith("_test.py"):
            continue
        out.append(path.relative_to(repo).as_posix())
    return out


def _mag0_registered_support_modules(repo: Path) -> set[str] | None:
    """Read the mag-0 path gate's view of which brick_protocol/support/*.py are admitted.

    Imported lazily and ONLY to read its pure path-classification function (no
    axis dependency). Returns None if the gate module is unavailable (then G4
    skips the bidirectional mag-0 tie rather than raising).
    """

    ensure_checker_imports(repo)
    try:
        from brick_protocol.support.checkers import check_package_path_admission as mag0
    except Exception:  # pragma: no cover - defensive
        return None
    admitted: set[str] = set()
    for relative in collect_support_modules(repo):
        # The gate's allowed_path is the file-tree authority.
        if mag0.allowed_path(relative) and mag0.forbidden_reason(relative) is None:
            admitted.add(relative)
    return admitted


def check_g4_unregistered_module_rejected(
    repo: Path,
    modules: Sequence[Mapping[str, Any]],
    support_modules: Sequence[str],
    violations: list[str],
) -> None:
    registered = {str(row.get("module", "")).strip() for row in modules}
    on_disk = set(support_modules)

    for relative in sorted(on_disk - registered):
        violations.append(
            f"G4: module {relative} present on disk but not registered in module_registry.yaml"
        )
    for module in sorted(registered - on_disk):
        violations.append(
            f"G4: registered module {module} missing from disk (brick_protocol/support/*.py)"
        )

    # Bidirectional mag-0 tie: every registered support module must also be
    # admitted by the file-tree path gate (and vice versa for what is on disk).
    mag0_admitted = _mag0_registered_support_modules(repo)
    if mag0_admitted is not None:
        for module in sorted(registered & on_disk):
            if module not in mag0_admitted:
                violations.append(
                    f"G4: registered module {module} is not admitted by the mag-0 path gate"
                )
        for relative in sorted(mag0_admitted - registered):
            violations.append(
                f"G4: mag-0-admitted module {relative} missing from module_registry.yaml"
            )


def check_g5_consume_not_author(
    modules: Sequence[Mapping[str, Any]], violations: list[str]
) -> None:
    for row in modules:
        module = str(row.get("module", "<missing>")).strip()
        echoed = set(_str_list(row.get("forbidden_ownership")))
        missing = sorted(SUPPORT_FORBIDDEN_OWNERSHIP - echoed)
        if missing:
            violations.append(
                f"G5: module {module} (support) is missing forbidden_ownership "
                f"echo {missing} (must re-state the support author-forbidden baseline)"
            )


def check_g6_decomposition_ratchet(
    modules: Sequence[Mapping[str, Any]],
    ceilings: Sequence[Mapping[str, Any]],
    violations: list[str],
) -> None:
    """G6: a god-module's owns_crossings must not exceed its declared ceiling.

    PROOF LIMIT (operator decision 0601, codex review F4): this compares the
    CURRENT ceiling to the CURRENT owns_crossings — it is a self-consistency
    check, NOT a true one-way ratchet. Raising a ceiling in this same file is
    not independently rejected here (a true ratchet would need a comparison the
    live file cannot self-provide, e.g. a git-committed prior value — which
    would inject a git/merge-base dependency into the otherwise pure checker).
    That is acceptable because G6 is a SECONDARY belt, not the real defense
    against re-bloating a decomposed module: a module regrowing to own >1
    crossing is caught FIRST by G2 (no-mixing, owns<=1 for non-exempt modules),
    and any NEW crossing must pass G1 (unique contract) + G4 (module registered)
    + the mag-0 admission. So G6 documents/tracks the post-split ceiling; the
    enforced "cannot re-bloat" invariant is G2+G1+G4. Recorded NOT-PROVEN:
    independent ratchet enforcement of a ceiling raise within a single commit.
    """

    ceiling_by_target: dict[str, int] = {}
    ceiling_module: dict[str, str] = {}
    for row in ceilings:
        target = str(row.get("target", "")).strip()
        if not target:
            continue
        raw = row.get("ceiling")
        try:
            ceiling_by_target[target] = int(raw)
        except (TypeError, ValueError):
            violations.append(f"G6: decomposition ceiling for {target!r} must be an integer")
            continue
        ceiling_module[target] = str(row.get("module", "")).strip()

    for row in modules:
        target = str(row.get("decomposition_target", "")).strip()
        if not target:
            continue
        module = str(row.get("module", "<missing>")).strip()
        owns = _str_list(row.get("owns_crossings"))
        if target not in ceiling_by_target:
            violations.append(
                f"G6: module {module} declares decomposition_target {target!r} "
                "with no ceiling in decomposition_ceilings"
            )
            continue
        ceiling = ceiling_by_target[target]
        if len(owns) > ceiling:
            violations.append(
                f"G6: god-module {module} owns_crossings {len(owns)} exceeds declared "
                f"ceiling {ceiling} for {target!r} (self-consistency check; re-bloat is "
                "independently caught by G2+G1+G4 — see proof limit)"
            )
        pinned_module = ceiling_module.get(target)
        if pinned_module and pinned_module != module:
            violations.append(
                f"G6: decomposition_target {target!r} ceiling is pinned to "
                f"{pinned_module}, not {module}"
            )


# ---------------------------------------------------------------------------
# orchestration over a real repo
# ---------------------------------------------------------------------------
def check_repo(repo: Path) -> list[str]:
    violations: list[str] = []
    crossings = load_crossings(repo)
    modules, ceilings = load_modules(repo)
    support_modules = collect_support_modules(repo)

    check_g1_one_contract_per_crossing(crossings, violations)
    check_g2_no_mixing(modules, violations)
    check_g3_cross_via_canonical_only(repo, crossings, support_modules, violations)
    check_g4_unregistered_module_rejected(repo, modules, support_modules, violations)
    check_g5_consume_not_author(modules, violations)
    check_g6_decomposition_ratchet(modules, ceilings, violations)
    return violations


# ---------------------------------------------------------------------------
# anti-tautological FIRE probes (one per rule, G1..G6)
#
# Each builds an in-memory violating registry/code case and asserts the
# corresponding checker function flags it. The kernel check raises if any probe
# is not rejected, so a rule that silently stops rejecting drives --all RED.
# ---------------------------------------------------------------------------
def _ok_crossings() -> list[dict[str, Any]]:
    return [
        {
            "crossing_id": "link_gate",
            "canonical_contract": "GateFact",
            "defined_at": "brick_protocol/link/gate.py",
            "canonical_symbols": ["GateFact"],
            "is_axis_crossing": True,
        },
        {
            "crossing_id": "link_movement",
            "canonical_contract": "MovementFact",
            "defined_at": "brick_protocol/link/movement.py",
            "canonical_symbols": ["MovementFact"],
            "is_axis_crossing": True,
        },
    ]


def _ok_module_row(module: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "module": module,
        "role": "operator",
        "owns_crossings": [],
        "consumes_crossings": [],
        "imports_axis": [],
        "forbidden_ownership": sorted(SUPPORT_FORBIDDEN_OWNERSHIP),
        "decomposition_target": "",
    }
    row.update(overrides)
    return row


def g1_probe() -> Mapping[str, Any]:
    """FIRE G1: a 2nd crossing reusing GateFact must be flagged."""

    crossings = _ok_crossings()
    crossings.append(
        {
            "crossing_id": "link_gate_clone",
            "canonical_contract": "GateFact",  # reused name
            "defined_at": "brick_protocol/link/gate.py",
            "canonical_symbols": ["GateFact"],
            "is_axis_crossing": True,
        }
    )
    violations: list[str] = []
    check_g1_one_contract_per_crossing(crossings, violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g1_one_contract_per_crossing",
        "rejected": any(v.startswith("G1:") for v in violations),
        "violations": violations,
    }


def g2_probe() -> Mapping[str, Any]:
    """FIRE G2: a non-exempt module owning 2 crossings must be flagged."""

    modules = [
        _ok_module_row(
            "brick_protocol/support/operator/route_materialization.py",
            owns_crossings=["link_movement", "link_gate"],  # 2 -> mixing
        )
    ]
    violations: list[str] = []
    check_g2_no_mixing(modules, violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g2_no_mixing",
        "rejected": any(v.startswith("G2:") for v in violations),
        "violations": violations,
    }


def g3_probe() -> Mapping[str, Any]:
    """FIRE G3: a forbidden axis-internal reach must be flagged — in each of the
    five STATIC import forms (dynamic reach is out of scope; see below).

    CLOSE-2/F3 (codex review 2): a probe that only plants
    `from axis.gate import _Internal` would let the OTHER static reach forms
    regress silently (codex found bare-full-path and from-package-import-submodule
    were not caught). This probe plants the FIVE STATIC forms in separate modules
    and requires the guard to reject each — so any future loosening of
    _axis_internal_imports turns this probe (and --all) red.
    SCOPE (codex review 3 P3): dynamic reach (getattr / importlib / __import__ /
    eval) is NOT covered and NOT-PROVEN — AST cannot resolve it; review catches it.
    """

    # (module_rel, source) — each reaches the non-canonical link.gate._GateInternalState
    forms = {
        "from_import_symbol": (
            "brick_protocol/support/operator/_g3_probe_a.py",
            "from brick_protocol.link.gate import GateFact\n"
            "from brick_protocol.link.gate import _GateInternalState\n",
        ),
        "import_as_alias": (
            "brick_protocol/support/operator/_g3_probe_b.py",
            "import brick_protocol.link.gate as _g\n"
            "_V = _g._GateInternalState\n",
        ),
        "bare_full_path": (
            "brick_protocol/support/operator/_g3_probe_c.py",
            "import brick_protocol.link.gate\n"
            "_V = brick_protocol.link.gate._GateInternalState\n",
        ),
        "from_pkg_import_submodule_alias": (
            "brick_protocol/support/operator/_g3_probe_d.py",
            "from brick_protocol.link import gate as _g4\n"
            "_V = _g4._GateInternalState\n",
        ),
        "from_pkg_import_submodule_bare": (
            "brick_protocol/support/operator/_g3_probe_e.py",
            "from brick_protocol.link import gate\n"
            "_V = gate._GateInternalState\n",
        ),
    }
    rejected_each: dict[str, bool] = {}
    all_violations: list[str] = []
    with tempfile.TemporaryDirectory(prefix="bp-elegance-g3-") as tmp:
        repo = Path(tmp)
        for label, (module_rel, src) in forms.items():
            target = repo / module_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(src, encoding="utf-8")
            violations: list[str] = []
            check_g3_cross_via_canonical_only(repo, _ok_crossings(), [module_rel], violations)
            target.unlink()
            rejected_each[label] = any("_GateInternalState" in v for v in violations)
            all_violations.extend(violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g3_cross_via_canonical_only",
        "rejected": all(rejected_each.values()),
        "rejected_by_form": rejected_each,
        "violations": all_violations,
    }


def g4_probe() -> Mapping[str, Any]:
    """FIRE G4: a support module on disk but not registered must be flagged."""

    with tempfile.TemporaryDirectory(prefix="bp-elegance-g4-") as tmp:
        repo = Path(tmp)
        new_rel = "brick_protocol/support/operator/new_helper.py"
        (repo / new_rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / new_rel).write_text("VALUE = 1\n", encoding="utf-8")
        # Registry knows nothing about new_helper.py.
        modules = [_ok_module_row("brick_protocol/support/operator/route_materialization.py")]
        support_modules = collect_support_modules(repo)  # includes new_helper.py
        violations: list[str] = []
        check_g4_unregistered_module_rejected(repo, modules, support_modules, violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g4_unregistered_module_rejected",
        "rejected": any("new_helper.py" in v and "not registered" in v for v in violations),
        "violations": violations,
    }


def g5_probe() -> Mapping[str, Any]:
    """FIRE G5: a support row dropping a forbidden_ownership entry must be flagged."""

    row = _ok_module_row("brick_protocol/support/operator/route_materialization.py")
    # Delete one required forbidden-author entry.
    row["forbidden_ownership"] = [
        item for item in row["forbidden_ownership"] if item != "movement_author"
    ]
    violations: list[str] = []
    check_g5_consume_not_author([row], violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g5_consume_not_author",
        "rejected": any(v.startswith("G5:") and "movement_author" in v for v in violations),
        "violations": violations,
    }


def g6_probe() -> Mapping[str, Any]:
    """FIRE G6: a god-module owning above its ceiling must be flagged."""

    modules = [
        _ok_module_row(
            "brick_protocol/support/operator/building_operation.py",
            owns_crossings=["link_gate", "link_movement"],  # 2
            decomposition_target="bo-god-probe",
        )
    ]
    ceilings = [
        {"target": "bo-god-probe", "module": "brick_protocol/support/operator/building_operation.py", "ceiling": 1}
    ]
    violations: list[str] = []
    check_g6_decomposition_ratchet(modules, ceilings, violations)
    return {
        "probe_ref": "axis-crossing-elegance-probe:g6_decomposition_ratchet",
        "rejected": any(v.startswith("G6:") and "exceeds declared ceiling" in v for v in violations),
        "violations": violations,
    }


def elegance_negative_probe_observations() -> tuple[Mapping[str, Any], ...]:
    return (
        g1_probe(),
        g2_probe(),
        g3_probe(),
        g4_probe(),
        g5_probe(),
        g6_probe(),
    )


def run_negative_probes() -> list[str]:
    """Run the six FIRE probes; return the probe_refs that were NOT rejected."""

    not_rejected: list[str] = []
    for observation in elegance_negative_probe_observations():
        if observation.get("rejected") is not True:
            not_rejected.append(str(observation.get("probe_ref") or "<missing-probe-ref>"))
    return not_rejected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Elegance guard (G1-G6): one canonical contract per crossing, no "
            "mixing, cross only via canonical contract, every support module "
            "registered, consume-not-author, decomposition ceiling (G6 = "
            "current-state self-consistency, not a one-way ratchet). Independent "
            "oracle; support evidence only."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    not_rejected = run_negative_probes()
    if not_rejected:
        print(
            "axis crossing elegance rejected: anti-tautological negative probe(s) "
            "were not rejected:",
            file=sys.stderr,
        )
        for probe_ref in not_rejected:
            print(f"- {probe_ref}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    repo = Path(args.repo).resolve() if args.repo else Path(".").resolve()
    try:
        violations = check_repo(repo)
    except (OSError, CrossingEleganceError) as exc:
        print(f"axis crossing elegance rejected: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    if violations:
        print("axis crossing elegance rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    crossings = load_crossings(repo)
    modules, _ceilings = load_modules(repo)
    axis_crossings = sum(1 for row in crossings if row.get("is_axis_crossing") is not False)
    print(
        "axis crossing elegance passed: "
        f"6 negative probe(s) rejected; {axis_crossings} axis crossing(s) and "
        f"{len(modules)} registered support module(s) inspected for one-contract-"
        "per-crossing, no-mixing, cross-via-canonical-only, module admission, "
        "consume-not-author, and decomposition ceiling (self-consistency, not a "
        "one-way ratchet)."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
