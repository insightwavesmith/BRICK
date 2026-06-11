#!/usr/bin/env python3
"""General invariant: every Building/evidence filesystem write-root is repo-anchored and single-source.

The recording/operator write path stores Building lifecycle, map, and evidence
output under a default root constant. If that constant is not anchored to the
repository (a bare ``"project/..."`` string, ``Path("project/...")``,
``Path.cwd() / ...``, an ``os.path.join``/f-string/concatenation, or an alias to
some other un-anchored variable), the output scatters under whatever directory
the process happens to run from. And if the same root name is defined in more
than one module, the write paths silently disagree. This checker keeps every
such root:

  1. ANCHORED -- positive proof: the RHS must reference one of the repo-anchor
     names (REPO_ROOT, __file__) or alias the canonical root constant. A value
     that references none of these (bare/relative string, Path("rel"),
     Path.cwd()/..., os.path.join(...), f-string, "a"+"b", None, or an alias to
     an un-anchored intermediate) is rejected. This is an allowlist, not a
     "anything-but-a-string-literal" denylist.
  2. SINGLE-SOURCE -- each root name is assigned in exactly one module (imports
     do not count); every other module imports it.
  3. DERIVATION SEAM (PROJECT-0 S1-D) -- ``buildings_root_for(project_ref)``,
     the one project_ref -> buildings-root derivation, exists EXACTLY ONCE
     across the code trees and every value it returns references a repo anchor.
  4. READ-SIDE VESSEL-LITERAL GUARD (PROJECT-0 S4-A) -- the ledger/dashboard
     read-side modules derive every vessel path through the seam or the
     declared project.json records; a returning project #1 literal (path or
     ref form) in those modules is a parallel derivation and REDs. S5-FIX:
     the scan also folds adjacent-constant concatenations and decodes bytes
     literals (both evaded the plain str-Constant walk), and four
     anti-tautology self-probes (plain / f-string / concat / bytes) plus a
     clean-module control run before the real scan.

Assignments are collected at MODULE scope (descending into if/try/for/with) but
NOT inside function/class bodies, so a conditionally-defined module root is seen
while a function-local variable that merely reuses the name is ignored. Tuple/
list unpacking of a root is itself rejected (a root must be a single anchored
assignment). The code trees support/, brick/, agent/, link/ are scanned.

Residual limits (defense-in-depth covers them): a file that fails to parse is
skipped (compileall is the syntax guard); a runtime-dynamic root with no
REPO_ROOT/__file__ reference is rejected by design (anchor explicitly).

Support evidence only: proves the root constants are anchored and single-source,
not that the resolved directory exists, nor source truth, success, quality, or
Movement authority.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


# Building/evidence filesystem write-root constant names.
ROOT_NAMES = frozenset(
    {
        "DEFAULT_BUILDINGS_ROOT",
        "DEFAULT_BUILDING_MAP_ROOT",
        "DEFAULT_BUILDING_EVIDENCE_ROOT",
    }
)
# PROJECT-0 S1-D: the ONE project_ref -> buildings-root derivation seam (one
# function, one home — support/recording/capture.py). The same anchor rules
# apply to the seam: it must exist EXACTLY ONCE across the code trees, and
# every value it returns must reference a repo anchor (REPO_ROOT / __file__ /
# the canonical root constants). S3 intake consumes this seam; pinning it here
# keeps a second, divergent derivation from quietly appearing elsewhere.
DERIVATION_SEAM_NAME = "buildings_root_for"
# A root RHS is anchored iff it references one of these names: the repo-anchor
# helpers REPO_ROOT / __file__, the canonical root constant it aliases, or the
# single derivation seam (PROJECT-0 S3-A: a value derived THROUGH the seam is
# repo-anchored because the seam's every return is itself proven anchored and
# the seam is proven single-home below — this is how DEFAULT_BUILDINGS_ROOT
# absorbs the project #1 literal without a parallel path-join).
ANCHOR_NAMES = frozenset({"REPO_ROOT", "__file__", DERIVATION_SEAM_NAME}) | ROOT_NAMES
SCAN_DIRS = ("support", "brick", "agent", "link")

# PROJECT-0 S4-A: the multi-project read-side modules must carry NO project #1
# string literal (path or ref form). The vessel set comes from the declared
# project.json records (through load_project_declaration) and every vessel
# path derives through the single seam — a returning literal in one of these
# modules is a parallel #1 default creeping back. ALL string constants are
# scanned via ast (docstrings included; comments are not constants).
READ_SIDE_NO_VESSEL_LITERAL_MODULES = (
    "support/operator/ledger_projection.py",
    "support/operator/dashboard_export.py",
    "support/operator/progress_projection.py",
)
VESSEL_LITERAL_FORMS = ("project/brick-protocol", "project:brick-protocol")


def _is_anchored(value: ast.expr) -> bool:
    for sub in ast.walk(value):
        if isinstance(sub, ast.Name) and sub.id in ANCHOR_NAMES:
            return True
    return False


def _module_level_assigns(node: ast.AST):
    """Yield Assign/AnnAssign at module scope.

    Descends into control-flow blocks (if/try/for/while/with) but NOT into
    function or class bodies, so a conditionally-defined module root is seen
    while a function-local shadow of the same name is ignored.
    """

    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, (ast.Assign, ast.AnnAssign)):
            yield child
        yield from _module_level_assigns(child)


def _root_targets(node: ast.stmt):
    """Yield (root_name, via_tuple) for each ROOT_NAME assignment target."""

    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    for target in targets:
        if isinstance(target, ast.Name):
            if target.id in ROOT_NAMES:
                yield target.id, False
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                if isinstance(elt, ast.Name) and elt.id in ROOT_NAMES:
                    yield elt.id, True


def _seam_function_defs(tree: ast.AST):
    """Yield module-level FunctionDefs named DERIVATION_SEAM_NAME."""

    for child in ast.iter_child_nodes(tree):
        if (
            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name == DERIVATION_SEAM_NAME
        ):
            yield child


def _seam_returns_anchored(func: ast.AST) -> bool:
    """Every non-bare return in the seam references a repo anchor name."""

    returns = [node for node in ast.walk(func) if isinstance(node, ast.Return)]
    value_returns = [node for node in returns if node.value is not None]
    if not value_returns:
        return False
    return all(_is_anchored(node.value) for node in value_returns)


def _folded_constant_text(node: ast.expr) -> str | None:
    """The textual value of a constant-only expression, or None.

    PROJECT-0 S5-FIX (rule 4 blind spots): a concatenated constant chain
    (``"project/" + "brick-protocol"``) and a bytes literal
    (``b"project/brick-protocol"``) both evaded the plain str-Constant scan
    (operator verified; f-strings WERE already caught via their Constant
    parts). Fold adjacent-constant BinOp(Add) chains and decode bytes (ascii,
    errors ignored) so the same literal cannot re-enter in either disguise.
    """

    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if isinstance(node.value, bytes):
            return node.value.decode("ascii", errors="ignore")
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _folded_constant_text(node.left)
        right = _folded_constant_text(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _read_side_vessel_literal_violations(repo: Path) -> list[str]:
    """Rule 4: no project #1 literal (str, bytes, or folded concat) in the
    read-side modules."""

    violations: list[str] = []
    for rel in READ_SIDE_NO_VESSEL_LITERAL_MODULES:
        path = repo / rel
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Constant, ast.BinOp)):
                continue
            text = _folded_constant_text(node)
            if text is None:
                continue
            for form in VESSEL_LITERAL_FORMS:
                if form in text:
                    violations.append(
                        f"{rel}:{node.lineno}: read-side module carries the project "
                        f"#1 literal {form!r} — vessel paths/refs must derive "
                        f"through {DERIVATION_SEAM_NAME} or the declared "
                        "project.json records, never a returning default string"
                    )
    return violations


_RULE4_PROBE_MODULE = READ_SIDE_NO_VESSEL_LITERAL_MODULES[0]
# Injection forms the rule-4 guard must each catch (PROJECT-0 S5-FIX FIRE):
# plain literal, f-string fragment, adjacent-constant concat, bytes literal.
_RULE4_INJECTIONS = (
    ("plain", 'A = "project/brick-protocol"\n'),
    ("f-string", 'B = f"project/brick-protocol/{X}"\n'),
    ("concat", 'C = "project/" + "brick-protocol"\n'),
    ("bytes", 'D = b"project/brick-protocol"\n'),
)


def run_rule4_fire_probes() -> list[str]:
    """Anti-tautology self-probes for rule 4. Returns failure messages.

    Synthesizes a temp tree holding ONE read-side module per injection form
    (plain / f-string / concat / bytes) plus one clean module; each injected
    form must produce a violation, the clean module none. A guard that goes
    blind to any form drives ``main()`` non-zero.
    """

    import tempfile

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="root-anchor-rule4-fire-") as tmp:
        tmp_root = Path(tmp)
        module_path = tmp_root / _RULE4_PROBE_MODULE
        module_path.parent.mkdir(parents=True)
        for label, injection in _RULE4_INJECTIONS:
            module_path.write_text("X = 'x'\n" + injection, encoding="utf-8")
            if not _read_side_vessel_literal_violations(tmp_root):
                failures.append(
                    f"rule-4 probe {label}: injected vessel literal was NOT "
                    "caught (guard is blind to this form)"
                )
        module_path.write_text(
            "X = 'x'\nCLEAN = 'no vessel literal here'\n", encoding="utf-8"
        )
        if _read_side_vessel_literal_violations(tmp_root):
            failures.append("rule-4 probe clean: a literal-free module was flagged")
    return failures


def find_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    defs: dict[str, list[str]] = {}
    seam_defs: list[tuple[str, bool]] = []
    violations.extend(_read_side_vessel_literal_violations(repo))
    for scan in SCAN_DIRS:
        base = repo / scan
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            rel = path.relative_to(repo).as_posix()
            for func in _seam_function_defs(tree):
                seam_defs.append((rel, _seam_returns_anchored(func)))
            for node in _module_level_assigns(tree):
                value = node.value
                if value is None:  # annotation-only
                    continue
                for name, via_tuple in _root_targets(node):
                    defs.setdefault(name, []).append(rel)
                    if via_tuple:
                        violations.append(
                            f"{rel}: {name} is assigned via tuple/list unpacking; a "
                            f"Building/evidence root must be a single REPO_ROOT-anchored "
                            f"assignment"
                        )
                    elif not _is_anchored(value):
                        violations.append(
                            f"{rel}: {name} is not repo-anchored; its value must derive "
                            f"from REPO_ROOT or Path(__file__) (or alias the canonical "
                            f"root), not a bare/relative/cwd/dynamic expression"
                        )
    for name, files in sorted(defs.items()):
        if len(files) > 1:
            violations.append(
                f"{name} defined in {len(files)} modules "
                f"({', '.join(sorted(files))}); a Building/evidence root must have "
                f"one canonical source (other modules import it)"
            )
    # PROJECT-0 S1-D: the derivation seam — exactly one home, anchored returns.
    if not seam_defs:
        violations.append(
            f"{DERIVATION_SEAM_NAME} is not defined anywhere under "
            f"{'/'.join(SCAN_DIRS)}; the project_ref -> buildings-root derivation "
            "seam must exist exactly once (support/recording/capture.py)"
        )
    elif len(seam_defs) > 1:
        violations.append(
            f"{DERIVATION_SEAM_NAME} defined in {len(seam_defs)} modules "
            f"({', '.join(sorted(rel for rel, _ in seam_defs))}); the derivation seam "
            "must have exactly one home (other modules import it)"
        )
    else:
        seam_rel, anchored = seam_defs[0]
        if not anchored:
            violations.append(
                f"{seam_rel}: {DERIVATION_SEAM_NAME} must return only repo-anchored "
                "values (every return references REPO_ROOT/__file__/the canonical "
                "root constants), not a bare/relative/cwd/dynamic expression"
            )
    return sorted(set(violations)), sum(len(f) for f in defs.values()) + len(seam_defs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every Building/evidence filesystem "
            "write-root constant is repo-anchored (positive REPO_ROOT/__file__ "
            "proof) and single-source. Does not prove the directory exists, nor "
            "source truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    probe_failures = run_rule4_fire_probes()
    if probe_failures:
        print("building root anchor rejected (rule-4 anti-tautology probe failure):")
        for failure in probe_failures:
            print(f"- {failure}")
        return 1

    try:
        violations, count = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"building root anchor rejected: {exc}")
        return 1

    if violations:
        print("building root anchor rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that Building/evidence root "
            "constants are repo-anchored and single-source; it does not prove the "
            "resolved directory exists, nor source truth, success, quality, or "
            "Movement authority."
        )
        return 1

    print(
        "building root anchor passed: "
        f"{count} Building/evidence root definition(s) (incl. the single "
        f"{DERIVATION_SEAM_NAME} derivation seam) repo-anchored and single-source."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
