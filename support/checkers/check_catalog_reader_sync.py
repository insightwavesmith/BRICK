#!/usr/bin/env python3
"""General invariant: every catalog-file path a code reader names resolves to an existing file.

Brick template catalog files live under ``brick/templates/``. Production readers
(plan_rendering, mcp_projection, building_design_toolkit, and any reader added
later) name catalog file paths to load them. If a catalog restructure (Phase F)
moves or renames a file
without syncing a reader, that reader silently points at a path that no longer
exists. This checker fails when any catalog-file path a support/ reader names
does not resolve to an existing file.

It catches BOTH a direct string literal and a STATICALLY-CONSTRUCTED path:
``"brick/templates/" + "x.yaml"``, ``Path("brick") / "templates" / "x.yaml"``,
``os.path.join("brick", "templates", "x.yaml")``, and an all-constant f-string
all fold to the same path and are checked. A path with a RUNTIME-dynamic part
(an f-string/join with a variable) cannot be statically resolved and is out of
scope — such readers should use a direct literal or a future central catalog-path
helper.

Scope is code readers only; other catalog-path references are guarded elsewhere
(profiles by check_profile path_exists/path_absent; Building plan template refs by
the catalog-restructure checker's physical-binding resolution). That checker is
the single negative-fixture owner (it must name deleted/old/bad catalog paths)
and is excluded, as is any explicit ``tests/`` directory.

Residual limits (honest, not silently capped): a runtime-dynamic path (an
f-string/join with a variable) cannot be resolved here; and ANY static
``brick/templates/*.yaml`` literal is checked for existence, so an illustrative
example/hint string must name a real catalog file (or omit the ``.yaml`` suffix).
A future central catalog-path helper that all readers route through would close
both — only helper inputs would need checking.

Support evidence only: proves reader catalog paths resolve, not that the file
content is correct, nor source truth, success, quality, or Movement authority.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


CATALOG_PREFIX = "brick/templates/"
SCAN_DIR = Path("support")
# Single negative-fixture owner (see module docstring): excluded so its
# deliberately-non-existent catalog paths are not mistaken for broken readers.
FIXTURE_OWNER = "support/checkers/check_brick_template_catalog_restructure.py"
# Path-join callables whose all-constant args fold to a path.
_JOIN_CALLS = {"Path", "PurePath", "PurePosixPath", "os.path.join", "posixpath.join", "path.join"}


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        cur = func.value
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def _fold(node: ast.expr) -> str | None:
    """Fold a node to a string IFF it is a fully-static string/path construction.

    Constant, all-constant f-string, "a"+"b", Path(...)/'x',
    os.path.join(consts). Returns None if any part is runtime-dynamic.
    """

    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        out: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                out.append(value.value)
            else:
                return None  # FormattedValue -> runtime dynamic
        return "".join(out)
    if isinstance(node, ast.BinOp):
        left, right = _fold(node.left), _fold(node.right)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Div):
            return left.rstrip("/") + "/" + right.lstrip("/")
        return None
    if isinstance(node, ast.Call) and _call_name(node) in _JOIN_CALLS:
        parts = [_fold(arg) for arg in node.args]
        if parts and all(part is not None for part in parts):
            return "/".join(part.strip("/") for part in parts)  # type: ignore[union-attr]
    return None


def _is_test_path(rel: str) -> bool:
    # Only an explicit tests/ directory is treated as fixtures; a test_*.py
    # basename does NOT hide a production reader.
    return "/tests/" in rel or rel.startswith("tests/")


def _catalog_refs(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp, ast.Call)):
            folded = _fold(node)
            if folded and folded.startswith(CATALOG_PREFIX) and folded.endswith(".yaml"):
                yield folded, getattr(node, "lineno", 0)


def find_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    checked = 0
    for path in sorted((repo / SCAN_DIR).rglob("*.py")):
        rel = path.relative_to(repo).as_posix()
        if rel == FIXTURE_OWNER or _is_test_path(rel):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        seen: set[tuple[str, int]] = set()
        for folded, lineno in _catalog_refs(tree):
            if (folded, lineno) in seen:  # nested fold double-count
                continue
            seen.add((folded, lineno))
            checked += 1
            if not (repo / folded).is_file():
                violations.append(
                    f"{rel}:{lineno}: reader names catalog file '{folded}' which does "
                    f"not exist (a catalog restructure moved/renamed it without syncing "
                    f"this reader)"
                )
    return sorted(set(violations)), checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every catalog-file path a support/ code "
            "reader names (literal or statically constructed) resolves to an "
            "existing file. Does not prove file content correctness, nor source "
            "truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        violations, checked = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"catalog reader sync rejected: {exc}")
        return 1

    if violations:
        print("catalog reader sync rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that reader catalog file paths "
            "resolve to existing files; it does not prove the file content is "
            "correct, nor source truth, success, quality, or Movement authority."
        )
        return 1

    print(
        "catalog reader sync passed: "
        f"{checked} catalog-file path reference(s) in support/ readers resolve."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
