#!/usr/bin/env python3
"""Guard BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0 catalog invariants.

This checker is support evidence only. It validates split catalog shape,
synthetic RED fixtures, and P8 active binding evidence; it does not choose
templates, Movement, quality, success, or source truth.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import re
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

from support.checkers.lib.yaml_subset import ProfileError, parse_yaml_subset


PROOF_LIMIT = (
    "proof limit: Brick template catalog restructure checker support evidence "
    "only; it does not prove source truth, success judgment, quality judgment, "
    "Movement authority, semantic template fitness, or P10 deletion closure."
)

OLD_REGISTRY_PATH = "brick/templates/shapes/registry.yaml"
SPLIT_CATALOG_PATHS = {
    "brick/templates/shapes/catalog.yaml",
    "brick/templates/shapes/shapes.yaml",
}
# U4/U6: the active step-template rows are sourced from the per-kind brick specs in
# bricks/<kind>/brick.md (step-templates.yaml retired). _catalog_documents wraps those
# specs as a synthetic step_template_catalog.rows document so the existing
# document-based step validators + the preset step_template_ref resolution read
# the bricks-sourced active step set unchanged.
BRICKS_SPEC_DIR = "brick/templates/bricks"
# U3 re-home: chain presets are authored as presets/<name>.md (frontmatter =
# the preset's former YAML keys verbatim + a `## Route` body the checker does NOT
# read). The Builder sources them here; this checker resolves chain-preset
# references against this directory's frontmatter rows.
PRESETS_SPEC_DIR = "brick/templates/presets"
SHAPES_SUBTREE_DIR = "brick/templates/shapes"
ADMITTED_PHYSICAL_TEMPLATE_DIRS = {
    "brick/templates/design",
    "brick/templates/do",
    "brick/templates/review",
    "brick/templates/closure",
    "brick/templates/tasks",
}
# T-FLATTEN (0611): the design/ + review/ kind folders retired; the two LIVING
# shared sheets re-homed as closed-form ROOT files (EXACT paths, no directory
# class opens up): the transition-concern complaint form every brick carries as
# its second return ref lives at the bricks/ family root, and the building-level
# human<->COO design-contract table lives at the brick/templates/ root. The old
# design/ + review/ dir names above stay admitted as PATH SHAPES so historical
# packet refs still parse (do/closure precedent); existence resolution for those
# old paths happens via the archive mirror fallback below.
ADMITTED_TEMPLATE_ROOT_FILES = {
    "brick/templates/bricks/transition-concern-return.yaml",
    "brick/templates/building-design-contract.yaml",
    "brick/templates/reroute-defaults.yaml",
}
ADMITTED_TEMPLATE_SUFFIXES = {".yaml", ".json"}
TASK_TEMPLATE_SUFFIXES = {".md"}
QA_STEP_TEMPLATE_REFS = {
    "building-step-template:axis-attack-qa",
    "building-step-template:code-attack-qa",
}
# CLEAN-YARD v3 (Smith 0611): the archive/brick-templates mirror left for the
# frozen museum repo and the ARCHIVE FALLBACK is PRUNED -- the product repo
# ships zero standing declaration packets, so a template ref resolves ONLY at
# its physical brick/templates path and a stale/retired ref REDs loudly (the
# missing-ref FIRE probes below stay RED-first).
BRICK_SPEC_FILENAME = "brick.md"
BRICK_RETURN_FILENAME = "return.yaml"
AGENT_INLINE_PAYLOAD_KEYS = {
    "prompt_refs",
    "skill_refs",
    "hook_refs",
    "tool_policy_refs",
    "discipline_refs",
    "adapter_refs",
    "callable_performer_refs",
}
AGENT_RETURN_FORBIDDEN_KEYS = {
    "adapter_refs",
    "agent_object_ref",
    "callable_performer_refs",
    "discipline_refs",
    "hook_refs",
    "performer",
    "prompt_refs",
    "selected_agent",
    "skill_refs",
    "tool_policy_refs",
}
LINK_RETURN_FORBIDDEN_KEYS = {
    "declared_gate_refs",
    "gate_ref",
    "movement",
    "movement_choice",
    "movement_literal",
    "next_movement_recommendation",
    "route_target",
    "selected_adapter_ref",
    "selected_model_ref",
    "selected_movement",
    "selected_target_ref",
    "target",
    "target_boundary_ref",
    "target_ref",
}
PROBLEM_CODES = {
    "missing_physical_binding",
    "invalid_physical_template_path",
    "step_ref_masquerades_as_brick_template_ref",
    "orphan_physical_template",
    "duplicate_conflicting_step_template_ref",
    "link_gate_token_drift",
    "agent_object_ref_payload_drift",
    "invalid_link_word",
    "gate_concept_used_as_live_gate_ref",
    "old_registry_active_dependency",
    "historical_ref_used_as_active_input",
    "missing_active_split_step_template_rows",
    "common_dogfood_preset_overlap",
    "legacy_compat_preset_refs",
    "dogfood_common_basis_missing",
    "invalid_chain_preset_catalog_scope",
    "preset_file_missing_frontmatter",
    "invalid_chain_brick_spec_ref",
    "declaration_expanded_brick_spec_ref_not_physical",
    "declaration_expanded_brick_template_ref_not_physical",
    "brick_template_axis_owned_return_field",
    "invalid_chain_step_template_ref",
    "invalid_chain_gate_concept_profile",
    "invalid_chain_target_word",
    "legacy_expanded_brick_template_ref_invalid",
    "shape_subtree_return_template_not_admitted",
}
GATE_REF_KEYS = {
    "gate_ref",
    "gate_refs",
    "declared_gate_ref",
    "declared_gate_refs",
    "default_gate_ref",
    "implicit_gate_ref",
    "live_gate_ref",
    "live_gate_refs",
}
# PROJECT-0 S1-C: historical/evidence roots generalized over EVERY project
# vessel (project/<id>/...), not only project #1 — building evidence under a
# new project must equally never be used as an active loader input.
HISTORICAL_ACTIVE_INPUT_ROOT_RE = re.compile(
    r"\Aproject/[^/]+/(?:buildings|building-evidence)/"
)


def _is_historical_active_input(path: str) -> bool:
    return bool(HISTORICAL_ACTIVE_INPUT_ROOT_RE.match(path))


@dataclass(frozen=True)
class CatalogViolation:
    problem_code: str
    location: str
    detail: str

    def render(self) -> str:
        return f"{self.problem_code}: {self.location}: {self.detail}"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _frontmatter_alias_value(
    mapping: Mapping[str, Any],
    canonical_key: str,
    legacy_key: str,
) -> Any:
    if canonical_key in mapping:
        return mapping.get(canonical_key)
    return mapping.get(legacy_key)


def _nested_value(document: Mapping[str, Any], dotted_key: str) -> Any:
    value: Any = document
    for part in dotted_key.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return parse_yaml_subset(text)


def _preset_frontmatter(text: str) -> Mapping[str, Any]:
    """Parse the YAML frontmatter mapping between the leading --- fences of a preset .md.

    The `## Route` body after the closing fence is author route-intent prose and is
    NOT parsed. Returns {} if the document has no well-formed frontmatter (a missing
    preset_ref then surfaces as the normal preset-validation violation).
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}
    block = parts[0][len("---"):]
    parsed = parse_yaml_subset(block)
    return parsed if isinstance(parsed, Mapping) else {}


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def _eval_ast_literal(node: ast.AST, values: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast_literal(item, values) for item in node.elts)
    if isinstance(node, ast.List):
        return [_eval_ast_literal(item, values) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _eval_ast_literal(key, values): _eval_ast_literal(value, values)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.Subscript):
        container = _eval_ast_literal(node.value, values)
        key = _eval_ast_literal(node.slice, values)
        return container[key]
    raise ValueError(f"unsupported AST literal: {type(node).__name__}")


def _py_constant(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        try:
            values[target.id] = _eval_ast_literal(value, values)
        except (KeyError, TypeError, ValueError):
            continue
        if target.id == name:
            return values[target.id]
    raise ProfileError(f"{path}: missing Python constant {name}")


def _gate_registry_rows(repo: Path) -> tuple[tuple[str, str | None], ...]:
    """The Link-owned ordered gate rows, read from the SINGLE SOURCE.

    STRUCT-SURGERY (2) (0623): the gate vocabulary moved to the data table
    ``GATE_REGISTRY`` in ``link/spec.py`` (one ``GateRegistryRow`` per gate);
    ``link/gate.py``'s ``DECLARED_GATE_REFS`` is now DERIVED from it
    (``tuple(row.ref for row in GATE_REGISTRY)``), so it is no longer an inline
    literal ``_py_constant`` can evaluate. This anchor follows the rehome: it
    reads each row's ``ref=`` string in registry order from ``link/spec.py``.
    The ``gate_registry_single_source`` checker independently guarantees the
    vocabulary is not re-stated anywhere else, so this remains the one source.
    """
    path = repo / "link/spec.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    registry_value: ast.AST | None = None
    for node in tree.body:
        target: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "GATE_REGISTRY":
            registry_value = value
            break
    if not isinstance(registry_value, ast.Tuple):
        raise ProfileError(f"{path}: missing GATE_REGISTRY tuple of GateRegistryRow rows")
    rows: list[tuple[str, str | None]] = []
    for row in registry_value.elts:
        if not isinstance(row, ast.Call):
            raise ProfileError(f"{path}: GATE_REGISTRY row is not a GateRegistryRow(...) call")
        ref_value: Any = None
        concept_token: str | None = None
        for kw in row.keywords:
            if kw.arg == "ref" and isinstance(kw.value, ast.Constant):
                ref_value = kw.value.value
            elif kw.arg == "concept_token" and isinstance(kw.value, ast.Constant):
                if kw.value.value is not None and not isinstance(kw.value.value, str):
                    raise ProfileError(
                        f"{path}: GATE_REGISTRY row concept_token= must be a string or None"
                    )
                concept_token = kw.value.value
        if not isinstance(ref_value, str):
            raise ProfileError(f"{path}: GATE_REGISTRY row missing a string ref= keyword")
        rows.append((ref_value, concept_token))
    if not rows:
        raise ProfileError(f"{path}: GATE_REGISTRY enumerates no gate rows")
    return tuple(rows)


def _canonical_gate_refs(repo: Path) -> tuple[str, ...]:
    return tuple(ref for ref, _concept_token in _gate_registry_rows(repo))


def _compact_support_gate_indexes(repo: Path) -> tuple[int, ...]:
    rows = _gate_registry_rows(repo)
    concept_indexes = tuple(
        index for index, (_ref, concept_token) in enumerate(rows) if concept_token is not None
    )
    return (0, *concept_indexes)


def _gate_refs_from_gate_yaml(repo: Path) -> tuple[str, ...]:
    payload = _as_mapping(_load_structured(repo / "link/gate.yaml"))
    refs: list[str] = []
    for item in _as_list(payload.get("declared_gate_refs")):
        ref = _text(_as_mapping(item).get("gate_ref"))
        if ref:
            refs.append(ref)
    return tuple(refs)


def _gate_concepts_from_gate_yaml(repo: Path) -> set[str]:
    payload = _as_mapping(_load_structured(repo / "link/gate.yaml"))
    matrix = _as_mapping(payload.get("post_d_base_gate_matrix"))
    concepts = set()
    for item in _as_list(matrix.get("concepts")):
        concept = _text(_as_mapping(item).get("concept_ref"))
        if concept:
            concepts.add(concept)
    return concepts


def _gate_refs_from_agents(repo: Path) -> tuple[str, ...]:
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    return tuple(sorted(set(re.findall(r"link-gate:[a-z-]+", text))))


def _support_gate_refs(repo: Path) -> tuple[str, ...]:
    path = repo / "support/operator/building_operation_common.py"
    canonical = _canonical_gate_refs(repo)
    expected_indexes = list(_compact_support_gate_indexes(repo))
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    alias = ""
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "brick_protocol.link.gate":
            continue
        for imported in node.names:
            if imported.name == "DECLARED_GATE_REFS":
                alias = imported.asname or imported.name
    if not alias:
        raise ProfileError(
            f"{path}: compact Link gate refs must import Link-owned DECLARED_GATE_REFS"
        )

    def subscript_index(node: ast.AST) -> int | None:
        if not isinstance(node, ast.Subscript):
            return None
        if not isinstance(node.value, ast.Name) or node.value.id != alias:
            return None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            return node.slice.value
        return None

    default_index: int | None = None
    token_indexes: list[int] = []
    for node in tree.body:
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        if target.id == "DEFAULT_LINK_GATE_REF":
            default_index = subscript_index(value)
        elif target.id == "COMPACT_LINK_GATE_TOKENS":
            if not isinstance(value, ast.Dict):
                raise ProfileError(f"{path}: COMPACT_LINK_GATE_TOKENS must be a dict")
            token_indexes = [
                index
                for item in value.values
                if (index := subscript_index(item)) is not None
            ]
            if len(token_indexes) != len(value.values):
                raise ProfileError(
                    f"{path}: COMPACT_LINK_GATE_TOKENS values must read DECLARED_GATE_REFS"
                )
    observed_indexes = [default_index, *token_indexes]
    if observed_indexes != expected_indexes:
        raise ProfileError(
            f"{path}: compact Link gate refs must preserve default and concept-backed "
            f"DECLARED_GATE_REFS order "
            f"{expected_indexes}, observed {observed_indexes}"
        )
    return tuple(canonical[index] for index in observed_indexes if index is not None)


def _agent_object_refs(repo: Path) -> tuple[set[str], list[CatalogViolation]]:
    refs: set[str] = set()
    violations: list[CatalogViolation] = []
    for path in sorted((repo / "agent/objects").glob("*.yaml")):
        payload = _as_mapping(_load_structured(path))
        ref = _text(payload.get("object_ref"))
        if not ref:
            violations.append(
                CatalogViolation(
                    "agent_object_ref_payload_drift",
                    _rel(repo, path),
                    "Agent Object payload lacks object_ref",
                )
            )
            continue
        refs.add(ref)
        expected_tail = path.stem
        if ref.removeprefix("agent-object:") != expected_tail:
            violations.append(
                CatalogViolation(
                    "agent_object_ref_payload_drift",
                    _rel(repo, path),
                    f"filename does not match payload object_ref {ref}",
                )
            )
    return refs, violations


def _slug_part(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value))


def _composition_slug(value: str) -> str:
    cleaned = "".join(
        char.lower() if char.isalnum() else "-"
        for char in str(value).strip()
    ).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "node"


def _chain_step_identity_slug(step_ref: str, step_alias: str) -> str:
    if step_alias:
        return _composition_slug(step_alias)
    tail = step_ref.split(":", 1)[-1]
    return _composition_slug(tail.removeprefix("building-step-template-"))


def _is_brick_kind_template_dir(path: str) -> bool:
    parts = Path(path).parts
    return (
        len(parts) == 4
        and parts[:3] == ("brick", "templates", "bricks")
        and _slug_part(parts[3])
    )


def _bricks_step_template_rows(repo: Path) -> list[Mapping[str, Any]]:
    """Build active step_template_catalog.rows from bricks/<kind>/brick.md frontmatter.

    U4 retired step-templates.yaml; the active step set now lives in the per-kind
    brick specs. Active frontmatter names use Builder-selection terms; this
    helper still emits the historical synthetic row shape so existing validators
    read the active-step-ref source unchanged.
    """
    bricks_dir = repo / BRICKS_SPEC_DIR
    if not bricks_dir.is_dir():
        return []
    rows: list[Mapping[str, Any]] = []
    for path in sorted(bricks_dir.glob(f"*/{BRICK_SPEC_FILENAME}")):
        fm = _preset_frontmatter(path.read_text(encoding="utf-8"))
        kind = _text(fm.get("brick_kind"))
        path_kind = path.parent.name
        if not kind or kind != path_kind:
            continue
        return_template = _frontmatter_alias_value(
            fm,
            "required_return_template_refs",
            "return_template",
        )
        if isinstance(return_template, str):
            brick_template_refs = [return_template]
        else:
            brick_template_refs = [
                _text(item) for item in _as_list(return_template) if _text(item)
            ]
        rows.append(
            {
                "step_template_ref": f"building-step-template:{kind}",
                "agent_object_ref": _text(
                    _frontmatter_alias_value(fm, "agent_object_hint_ref", "default_agent")
                ),
                "link_word": _text(
                    _frontmatter_alias_value(fm, "link_movement_literal", "default_link")
                ),
                "brick_contract": _text(fm.get("brick_contract")),
                "brick_spec_ref": path.relative_to(repo).as_posix(),
                "brick_template_refs": brick_template_refs,
            }
        )
    return rows


def _catalog_documents(repo: Path) -> list[tuple[str, Mapping[str, Any], bool]]:
    documents: list[tuple[str, Mapping[str, Any], bool]] = []
    for rel in sorted(SPLIT_CATALOG_PATHS):
        path = repo / rel
        if path.is_file():
            documents.append((rel, _as_mapping(_load_structured(path)), False))
    # Active step rows are sourced from bricks/<kind>/brick.md (U4/U6) and wrapped as a
    # synthetic step_template_catalog.rows document keyed by the bricks dir, so the
    # existing document-based step validators read the bricks-sourced active step
    # set unchanged. The .md-dir rel path is informational for violation locations.
    bricks_rows = _bricks_step_template_rows(repo)
    if bricks_rows:
        documents.append(
            (
                f"{BRICKS_SPEC_DIR}/",
                {"step_template_catalog": {"rows": bricks_rows}},
                False,
            )
        )
    # Chain presets now live as presets/<name>.md frontmatter (U3 re-home). Wrap
    # each preset's frontmatter as a single-row chain_presets document so the
    # existing chain-preset split/reference validators read it unchanged. The .md
    # rel path is preserved so violation locations point at the real source file.
    presets_dir = repo / PRESETS_SPEC_DIR
    if presets_dir.is_dir():
        for path in sorted(presets_dir.glob("*.md")):
            fm = _preset_frontmatter(path.read_text(encoding="utf-8"))
            documents.append((_rel(repo, path), {"chain_presets": [fm]}, False))
    registry = repo / OLD_REGISTRY_PATH
    if registry.is_file():
        documents.append((OLD_REGISTRY_PATH, _as_mapping(_load_structured(registry)), True))
    return documents


def _active_split_step_template_count(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> int:
    count = 0
    for _rel, document, compat_old in documents:
        if compat_old:
            continue
        for item in _as_list(_nested_value(document, "step_template_catalog.rows")):
            if _as_mapping(item):
                count += 1
    return count


def _step_templates(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
    *,
    allow_compat_fallback: bool,
) -> list[tuple[str, Mapping[str, Any], bool]]:
    active_rows: list[tuple[str, Mapping[str, Any], bool]] = []
    compat_rows: list[tuple[str, Mapping[str, Any], bool]] = []
    for rel, document, compat_old in documents:
        row_values = _as_list(_nested_value(document, "step_template_catalog.rows"))
        if not row_values:
            row_values = _as_list(document.get("step_templates"))
        for item in row_values:
            mapping = _as_mapping(item)
            if not mapping:
                continue
            if compat_old:
                compat_rows.append((rel, mapping, compat_old))
            else:
                active_rows.append((rel, mapping, compat_old))
    if active_rows:
        return active_rows
    return compat_rows if allow_compat_fallback else []


def _brick_template_refs(step: Mapping[str, Any]) -> tuple[str, ...]:
    refs = step.get("brick_template_refs", [])
    if isinstance(refs, str):
        return (refs,)
    return tuple(_text(item) for item in _as_list(refs) if _text(item))


def _physical_files(repo: Path) -> set[str]:
    files: set[str] = set()
    for rel_dir in ADMITTED_PHYSICAL_TEMPLATE_DIRS:
        root = repo / rel_dir
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if not path.is_file() or path.name == ".DS_Store":
                continue
            suffix = path.suffix
            if suffix in ADMITTED_TEMPLATE_SUFFIXES or (
                rel_dir == "brick/templates/tasks" and suffix in TASK_TEMPLATE_SUFFIXES
            ):
                files.add(_rel(repo, path))
    bricks_root = repo / BRICKS_SPEC_DIR
    if bricks_root.is_dir():
        for path in sorted(bricks_root.glob(f"*/{BRICK_RETURN_FILENAME}")):
            if path.is_file() and _slug_part(path.parent.name):
                files.add(_rel(repo, path))
    # T-FLATTEN (0611): closed-form root-file sheets (exact paths only).
    for rel in sorted(ADMITTED_TEMPLATE_ROOT_FILES):
        if (repo / rel).is_file():
            files.add(rel)
    return files


def _archived_template_files(repo: Path) -> set[str]:
    """ARCHIVE FALLBACK PRUNED (CLEAN-YARD v3, 0611): always empty.

    The museum mirror left for the frozen history repo; the product repo holds
    no standing declaration packets, so no historical ref may resolve through
    an archive home. Kept as a seam so the resolver signature stays stable; a
    ref that exists at no physical brick/templates path REDs.
    """
    del repo
    return set()


def _brick_spec_files(repo: Path) -> set[str]:
    files: set[str] = set()
    bricks_root = repo / BRICKS_SPEC_DIR
    if not bricks_root.is_dir():
        return files
    for path in sorted(bricks_root.glob(f"*/{BRICK_SPEC_FILENAME}")):
        if path.is_file() and _slug_part(path.parent.name):
            files.add(_rel(repo, path))
    return files


def _physical_template_documents(repo: Path, physical_files: Iterable[str]) -> Mapping[str, Any]:
    documents: dict[str, Any] = {}
    for rel in sorted(set(physical_files)):
        suffix = Path(rel).suffix
        if suffix not in ADMITTED_TEMPLATE_SUFFIXES:
            continue
        documents[rel] = _load_structured(repo / rel)
    return documents


def _shape_subtree_extra_documents(repo: Path) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    root = repo / SHAPES_SUBTREE_DIR
    if not root.is_dir():
        return ()
    documents: list[tuple[str, Mapping[str, Any]]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        rel = _rel(repo, path)
        if rel in SPLIT_CATALOG_PATHS or rel == OLD_REGISTRY_PATH:
            continue
        if path.suffix not in ADMITTED_TEMPLATE_SUFFIXES:
            continue
        payload = _load_structured(path)
        mapping = _as_mapping(payload)
        if mapping:
            documents.append((rel, mapping))
    return tuple(documents)


def _classified_physical_templates(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> tuple[str, ...]:
    classification = _classified_physical_templates_by_category(documents)
    classified: list[str] = []
    for values in classification.values():
        for item in values:
            path = _text(_as_mapping(item).get("path"))
            if path:
                classified.append(path)
    return tuple(dict.fromkeys(classified))


def _classified_physical_templates_by_category(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> Mapping[str, tuple[Mapping[str, Any], ...]]:
    classified: dict[str, list[Mapping[str, Any]]] = {}
    for _rel_name, document, _compat_old in documents:
        classification = _as_mapping(document.get("physical_template_classification"))
        for category, values in classification.items():
            classified.setdefault(str(category), [])
            for item in _as_list(values):
                mapping = _as_mapping(item)
                if mapping:
                    classified[str(category)].append(mapping)
    return {key: tuple(value) for key, value in classified.items()}


def _catalog_gate_refs(document: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in ("compact_link_authoring", "compact_link_authoring_view"):
        compact = _as_mapping(document.get(key))
        default = _text(compact.get("implicit_gate_ref") or compact.get("default_gate_ref"))
        if default:
            refs.add(default)
        for item in _as_mapping(compact.get("allowed_gate_tokens")).values():
            ref = _text(item)
            if ref:
                refs.add(ref)
        for item in _as_mapping(compact.get("token_refs")).values():
            ref = _text(item)
            if ref:
                refs.add(ref)
    return refs


CHAIN_PRESET_CATALOG_SCOPES = ("common", "brick_protocol_dogfood")


def _chain_preset_rows(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> tuple[
    list[tuple[str, Mapping[str, Any]]],
    list[tuple[str, Mapping[str, Any]]],
    list[tuple[str, Mapping[str, Any]]],
]:
    common: list[tuple[str, Mapping[str, Any]]] = []
    dogfood: list[tuple[str, Mapping[str, Any]]] = []
    invalid_scope: list[tuple[str, Mapping[str, Any]]] = []
    for rel, document, compat_old in documents:
        if compat_old:
            continue
        rows = [
            _as_mapping(item)
            for item in _as_list(document.get("chain_presets"))
            if _as_mapping(item)
        ]
        if not rows:
            continue
        # presets/<name>.md carries catalog_scope on the preset ROW (one row per
        # file); a legacy wrapper document carries it once at the document level.
        # Classify by the row scope when present, else the document scope.
        doc_scope = _text(document.get("catalog_scope"))
        for row in rows:
            scope = _text(row.get("catalog_scope")) or doc_scope
            # [P1] catalog_scope is a closed enum (mirrors the loader reject in
            # plan_rendering._chain_presets_from_presets): a typo / unknown scope
            # must surface as a VIOLATION, not be silently bucketed as common
            # (the prior `elif rel.startswith(PRESETS_SPEC_DIR ...)` swallowed any
            # scope for a presets/*.md row, hiding a typo'd local route as common).
            if scope not in CHAIN_PRESET_CATALOG_SCOPES:
                invalid_scope.append((rel, row))
                continue
            # Classification is scope-driven: presets are authored as
            # presets/<name>.md carrying catalog_scope on the row (U3 re-home), and
            # scope is already validated as the closed CHAIN_PRESET_CATALOG_SCOPES
            # enum above. The former legacy-path OR-branches (chain-presets-brick-
            # protocol.yaml / brick/templates/buildings|portfolios) were dead and
            # were removed with the step-templates.yaml retirement (U4).
            if scope == "brick_protocol_dogfood":
                dogfood.append((rel, row))
            else:  # scope == "common"
                common.append((rel, row))
    return common, dogfood, invalid_scope


def _validate_chain_preset_split(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]]
) -> list[CatalogViolation]:
    documents = list(documents)
    common_rows, dogfood_rows, invalid_scope_rows = _chain_preset_rows(documents)
    violations: list[CatalogViolation] = []
    for rel, row in invalid_scope_rows:
        preset_ref = _text(row.get("preset_ref")) or "<missing-preset-ref>"
        scope = _text(row.get("catalog_scope")) or "<missing>"
        violations.append(
            CatalogViolation(
                "invalid_chain_preset_catalog_scope",
                f"{rel}:{preset_ref}",
                f"catalog_scope {scope!r} is not one of "
                f"{list(CHAIN_PRESET_CATALOG_SCOPES)}",
            )
        )
    violations.extend(_validate_preset_file_frontmatter(documents))
    common_refs = {
        _text(row.get("preset_ref"))
        for _rel, row in common_rows
        if _text(row.get("preset_ref"))
    }
    dogfood_refs = {
        _text(row.get("preset_ref"))
        for _rel, row in dogfood_rows
        if _text(row.get("preset_ref"))
    }
    for ref in sorted(common_refs & dogfood_refs):
        violations.append(
            CatalogViolation(
                "common_dogfood_preset_overlap",
                ref,
                "preset_ref appears in both common and Brick Protocol dogfood catalogs",
            )
        )

    # L legacy cut (0610): the compat_preset_refs alias grammar is RETIRED. Any
    # preset row (common or dogfood) still carrying the key is a violation -- the
    # loader (plan_rendering._chain_presets_from_presets) rejects it loudly, and
    # this checker surfaces the same fact on the stored file so it gets FIXED,
    # never silently ignored. The former alias-conflict rules
    # (dogfood_alias_conflict) retired together with the alias grammar.
    for rel, row in [*common_rows, *dogfood_rows]:
        if "compat_preset_refs" in row:
            preset_ref = _text(row.get("preset_ref"))
            violations.append(
                CatalogViolation(
                    "legacy_compat_preset_refs",
                    f"{rel}:{preset_ref or '<missing-preset-ref>'}",
                    "compat_preset_refs is retired legacy preset alias grammar; "
                    "remove the key (callers must use the canonical preset_ref)",
                )
            )
    for rel, row in dogfood_rows:
        preset_ref = _text(row.get("preset_ref"))
        location = f"{rel}:{preset_ref or '<missing-preset-ref>'}"
        basis = _text(row.get("common_basis_ref"))
        if not basis or basis not in common_refs:
            violations.append(
                CatalogViolation(
                    "dogfood_common_basis_missing",
                    location,
                    f"common_basis_ref {basis or '<missing>'} is absent from the common chain preset catalog",
                )
            )
    return violations


def _validate_chain_preset_references(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
    *,
    step_refs: set[str],
    step_ref_to_spec: Mapping[str, str],
    brick_spec_files: set[str],
    gate_concepts: set[str],
    movement_literals: set[str],
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = []
    common_rows, dogfood_rows, _invalid_scope_rows = _chain_preset_rows(documents)
    for rel, row in [*common_rows, *dogfood_rows]:
        preset_ref = _text(row.get("preset_ref")) or "<missing-preset-ref>"
        location = f"{rel}:{preset_ref}"
        # U5/D5: the invalid_chain_selected_shape_ref rule (requiring each active
        # chain preset's selected_shape_ref to be explicit AND a shape-catalog
        # member) was removed -- selected_shape_ref is now an optional recorded tag,
        # not a constraint. The shape_refs parameter is gone with it.

        for gate_concept in _as_list(row.get("gate_concept_profile")):
            concept = _text(gate_concept)
            if concept and concept not in gate_concepts:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_gate_concept_profile",
                        location,
                        f"gate_concept_profile item {concept} is absent from link/gate.yaml concepts",
                    )
                )
            elif not concept:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_gate_concept_profile",
                        location,
                        "gate_concept_profile entries must be non-empty text",
                    )
                )

        steps = _as_list(row.get("steps"))
        if not steps:
            violations.append(
                CatalogViolation(
                    "invalid_chain_step_template_ref",
                    location,
                    "chain preset must declare at least one step",
                )
            )
        if any(
            _text(_as_mapping(step).get("step_template_ref")) in QA_STEP_TEMPLATE_REFS
            for step in steps
        ):
            budgets = row.get("node_reroute_budgets")
            if not isinstance(budgets, Mapping) or not budgets:
                violations.append(
                    CatalogViolation(
                        "qa_preset_missing_reroute_policy",
                        location,
                        "QA-bearing chain presets must declare non-empty node_reroute_budgets "
                        "so transition_concern_evidence can reland within a bounded budget",
                    )
                )
        step_template_rows: dict[str, list[tuple[str, bool]]] = {}
        identity_rows: dict[str, list[str]] = {}
        for index, raw_step in enumerate(steps):
            step = _as_mapping(raw_step)
            step_location = f"{location}.steps[{index}]"
            step_ref = _text(step.get("step_template_ref"))
            step_alias = _text(step.get("step_alias"))
            has_step_alias = "step_alias" in step and bool(step_alias)
            if "step_alias" in step and not step_alias:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_step_alias",
                        step_location,
                        "step_alias must be non-empty text when present",
                    )
                )
            step_template_rows.setdefault(step_ref, []).append(
                (step_location, has_step_alias)
            )
            identity_slug = _chain_step_identity_slug(step_ref, step_alias)
            identity_rows.setdefault(identity_slug, []).append(step_location)
            if step_ref not in step_refs:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_step_template_ref",
                        step_location,
                        f"step_template_ref {step_ref or '<missing>'} is absent from active step templates",
                    )
                )
            expected_spec_ref = _text(step_ref_to_spec.get(step_ref))
            brick_spec_ref = _text(step.get("brick_spec_ref"))
            if step_ref in step_refs and not brick_spec_ref:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_brick_spec_ref",
                        step_location,
                        "brick_spec_ref must point to the selected single-Brick brick.md",
                    )
                )
            elif brick_spec_ref:
                problem = _validate_brick_spec_path(brick_spec_ref, brick_spec_files)
                if problem:
                    violations.append(
                        CatalogViolation(
                            "invalid_chain_brick_spec_ref",
                            step_location,
                            f"brick_spec_ref {brick_spec_ref}: {problem}",
                        )
                    )
                elif expected_spec_ref and brick_spec_ref != expected_spec_ref:
                    violations.append(
                        CatalogViolation(
                            "invalid_chain_brick_spec_ref",
                            step_location,
                            f"brick_spec_ref {brick_spec_ref} does not match {step_ref} source {expected_spec_ref}",
                        )
                    )
            target_word = _text(step.get("target_word"))
            if not target_word:
                violations.append(
                    CatalogViolation(
                        "invalid_chain_target_word",
                        step_location,
                        "target_word must be explicit local preset vocabulary",
                    )
                )
            elif (
                target_word in movement_literals
                or target_word.startswith(("link-gate:", "building-step-template:"))
                or any(token in target_word for token in (" or ", " and ", ",", "|", "/"))
            ):
                violations.append(
                    CatalogViolation(
                        "invalid_chain_target_word",
                        step_location,
                        f"target_word {target_word!r} looks like Movement, gate, step identity, or multiple targets",
                    )
                )
        for step_ref, rows in sorted(step_template_rows.items()):
            if not step_ref or len(rows) <= 1:
                continue
            missing_alias_rows = [
                step_location for step_location, has_alias in rows if not has_alias
            ]
            if missing_alias_rows:
                violations.append(
                    CatalogViolation(
                        "chain_step_alias_required_for_repeated_template",
                        location,
                        f"step_template_ref {step_ref} appears multiple times; "
                        "each repeated row must carry a distinguishing step_alias "
                        f"(missing on {missing_alias_rows})",
                    )
                )
        for identity_slug, rows in sorted(identity_rows.items()):
            if len(rows) <= 1:
                continue
            violations.append(
                CatalogViolation(
                    "duplicate_chain_step_identity",
                    location,
                    f"step_alias/template slug {identity_slug!r} collides across rows {rows}",
                )
            )
    return violations


def _validate_preset_file_frontmatter(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> list[CatalogViolation]:
    """[P2] A presets/<name>.md with no well-formed frontmatter (or no preset_ref)
    is a VIOLATION, not a silent skip.

    _catalog_documents wraps each presets/<name>.md as {"chain_presets": [fm]} where
    fm is _preset_frontmatter(...) == {} when the file has no leading --- fence block.
    Such an empty row is dropped by every downstream chain-preset validator, so a
    malformed preset file would otherwise escape ALL preset validation (and the
    loader plan_rendering._chain_presets_from_presets would later hard-fail on it).
    Mirror the loader: require at least one well-formed frontmatter row carrying a
    preset_ref per presets-dir file.
    """
    violations: list[CatalogViolation] = []
    for rel, document, compat_old in documents:
        if compat_old or not rel.startswith(PRESETS_SPEC_DIR + "/"):
            continue
        rows = [
            _as_mapping(item)
            for item in _as_list(document.get("chain_presets"))
            if _as_mapping(item)
        ]
        if not rows:
            violations.append(
                CatalogViolation(
                    "preset_file_missing_frontmatter",
                    rel,
                    "preset file has no well-formed --- frontmatter block "
                    "(parsed to no chain-preset row)",
                )
            )
            continue
        for row in rows:
            if not _text(row.get("preset_ref")):
                violations.append(
                    CatalogViolation(
                        "preset_file_missing_frontmatter",
                        rel,
                        "preset frontmatter is missing the required preset_ref key",
                    )
                )
    return violations


def _declaration_packets(repo: Path) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    packets: list[tuple[str, Mapping[str, Any]]] = []
    # PROJECT-0 S1-C: scan EVERY project vessel (project/<id>/buildings/*),
    # not only project #1 — a new project must never be silently unscanned.
    for path in sorted((repo / "project").glob("*/buildings/*/work/preset-expansion.json")):
        packets.append((_rel(repo, path), _as_mapping(_load_structured(path))))
    return tuple(packets)


def _has_p7_declaration_binding(packet: Mapping[str, Any]) -> bool:
    return any(
        key in packet
        for key in (
            "shape_catalog_ref",
            "chain_preset_catalog_source",
            "canonical_chain_preset_ref",
            "compat_chain_preset_ref",
            "chain_preset_catalog_scope",
            "common_basis_ref",
        )
    )


def _p7_marked_declaration_packet_count(
    packets: Iterable[tuple[str, Mapping[str, Any]]],
) -> int:
    return sum(1 for _rel, packet in packets if _has_p7_declaration_binding(packet))


def _validate_declaration_packets(
    packets: Iterable[tuple[str, Mapping[str, Any]]],
    physical_files: set[str],
    brick_spec_files: set[str],
    archived_template_files: set[str],
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = []
    for rel, packet in packets:
        for ref in _as_list(packet.get("expanded_brick_spec_refs")):
            ref_text = _text(ref)
            if not ref_text:
                continue
            if ref_text.startswith("building-step-template:"):
                problem = "step-template ref recorded as expanded Brick spec evidence"
            else:
                problem = _validate_brick_spec_path(ref_text, brick_spec_files)
            if problem:
                violations.append(
                    CatalogViolation(
                        "declaration_expanded_brick_spec_ref_not_physical",
                        rel,
                        f"{ref_text}: {problem}",
                    )
                )
        for ref in _as_list(packet.get("expanded_brick_template_refs")):
            ref_text = _text(ref)
            if not ref_text:
                continue
            if ref_text.startswith("building-step-template:"):
                problem = "step-template ref recorded as expanded Brick template evidence"
            else:
                problem = _validate_declared_template_ref(
                    ref_text, physical_files, archived_template_files
                )
            if problem:
                violations.append(
                    CatalogViolation(
                        "declaration_expanded_brick_template_ref_not_physical",
                        rel,
                        f"{ref_text}: {problem}",
                    )
                )
        for ref in _as_list(packet.get("legacy_expanded_brick_template_refs")):
            ref_text = _text(ref)
            if not ref_text:
                continue
            if ref_text.startswith("building-step-template:"):
                continue
            if ref_text.startswith("brick/templates/"):
                problem = _validate_declared_template_ref(
                    ref_text, physical_files, archived_template_files
                )
                if not problem:
                    continue
                detail = f"{ref_text}: {problem}"
            else:
                detail = f"{ref_text}: legacy expanded refs must be step refs or physical Brick template refs"
            violations.append(
                CatalogViolation(
                    "legacy_expanded_brick_template_ref_invalid",
                    rel,
                    detail,
                )
            )
    return violations


def _walk_values(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_values(child, f"{path}[{index}]")


def _normalized_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")


FORBIDDEN_RETURN_FIELD_LIST_KEYS = {
    "forbidden_return_keys",
    "forbidden_route_request_fields",
    "forbidden_transition_concern_fields",
}
RETURN_TEMPLATE_MARKER_KEYS = {
    "fields",
    "forbidden_return_keys",
    "forbidden_route_request_fields",
    "forbidden_transition_concern_fields",
    "maps_to",
    "next_link_input_sections",
    "required_return_shape",
    "returned_sections",
    "returned_shape",
    "review_return_sections",
}


def _is_forbidden_return_field_list_path(path: str) -> bool:
    for segment in path.split("."):
        key = segment.split("[", 1)[0]
        if key in FORBIDDEN_RETURN_FIELD_LIST_KEYS:
            return True
    return False


# Route-author DISPOSITION policy subtrees declared in the preset frontmatter are
# NOT Brick/Agent return-field declarations: closure_transition_target_policy is a
# caller / COO declaration (compose_building requires it from caller/COO and
# validates it against TRANSITION_CONCERN_KINDS + the explicit hold/target/reroute
# action vocabulary). Its action values (target / reroute / hold) and its
# target_step_template_ref / target_ref are the route author's own route
# disposition vocabulary, so this Brick-return-field scan must not treat them as
# Brick-declared Link-owned returned fields. Only this declared-policy subtree is
# excluded; everything else in the preset frontmatter is still scanned.
ROUTE_AUTHOR_POLICY_SUBTREE_KEYS = {
    "closure_transition_target_policy",
}


def _is_route_author_policy_path(path: str) -> bool:
    for segment in path.split("."):
        key = segment.split("[", 1)[0]
        if key in ROUTE_AUTHOR_POLICY_SUBTREE_KEYS:
            return True
    return False


def _return_field_declarations(document: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    for value_path, value in _walk_values(document):
        if _is_forbidden_return_field_list_path(value_path):
            continue
        if _is_route_author_policy_path(value_path):
            continue
        if isinstance(value, Mapping):
            for key in value:
                if isinstance(key, str):
                    yield f"{value_path}.{key}", key
        elif isinstance(value, str):
            yield value_path, value


def _validate_physical_template_content(
    template_docs: Mapping[str, Any],
    scan_paths: Iterable[str],
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = []
    forbidden = {
        _normalized_field_name(item): "Agent"
        for item in AGENT_RETURN_FORBIDDEN_KEYS
    }
    forbidden.update(
        {
            _normalized_field_name(item): "Link"
            for item in LINK_RETURN_FORBIDDEN_KEYS
        }
    )
    for rel in sorted(set(scan_paths)):
        document = _as_mapping(template_docs.get(rel))
        if not document:
            continue
        for value_path, field in _return_field_declarations(document):
            normalized = _normalized_field_name(field)
            owner = forbidden.get(normalized)
            if not owner:
                continue
            violations.append(
                CatalogViolation(
                    "brick_template_axis_owned_return_field",
                    f"{rel}{value_path}",
                    f"Brick return template declares {owner}-owned returned field/key {field!r}",
                )
            )
    return violations


def _looks_like_return_template(document: Mapping[str, Any]) -> bool:
    if any(key in document for key in RETURN_TEMPLATE_MARKER_KEYS):
        return True
    template_kind = _text(document.get("template_kind")).lower()
    maps_to = _text(document.get("maps_to"))
    return "return" in template_kind or maps_to == "AgentFact.returned"


def _validate_shape_subtree_extra_documents(
    documents: Iterable[tuple[str, Mapping[str, Any]]],
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = []
    forbidden = {
        _normalized_field_name(item): "Agent"
        for item in AGENT_RETURN_FORBIDDEN_KEYS
    }
    forbidden.update(
        {
            _normalized_field_name(item): "Link"
            for item in LINK_RETURN_FORBIDDEN_KEYS
        }
    )
    for rel, document in documents:
        if _looks_like_return_template(document):
            violations.append(
                CatalogViolation(
                    "shape_subtree_return_template_not_admitted",
                    rel,
                    "return-template shaped files must live under admitted physical template directories, not brick/templates/shapes",
                )
            )
        for value_path, field in _return_field_declarations(document):
            normalized = _normalized_field_name(field)
            owner = forbidden.get(normalized)
            if not owner:
                continue
            violations.append(
                CatalogViolation(
                    "brick_template_axis_owned_return_field",
                    f"{rel}{value_path}",
                    f"Brick shapes subtree declares {owner}-owned returned field/key {field!r}",
                )
            )
    return violations


def _is_admitted_catalog_binding_path(value_path: str, normalized: str) -> bool:
    return (
        (
            normalized == "agent_object_ref"
            and ".step_template_catalog.rows[" in value_path
            and value_path.endswith(".agent_object_ref")
        )
        or (
            normalized in {"selected_adapter_ref", "selected_model_ref"}
            and ".chain_presets[" in value_path
            and ".steps[" in value_path
            and value_path.endswith(f".{normalized}")
        )
    )


def _validate_shape_catalog_content(
    documents: Iterable[tuple[str, Mapping[str, Any], bool]],
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = []
    forbidden = {
        _normalized_field_name(item): "Agent"
        for item in AGENT_RETURN_FORBIDDEN_KEYS
    }
    forbidden.update(
        {
            _normalized_field_name(item): "Link"
            for item in LINK_RETURN_FORBIDDEN_KEYS
        }
    )
    for rel, document, compat_old in documents:
        if compat_old:
            continue
        for value_path, field in _return_field_declarations(document):
            normalized = _normalized_field_name(field)
            if _is_admitted_catalog_binding_path(value_path, normalized):
                continue
            owner = forbidden.get(normalized)
            if not owner:
                continue
            violations.append(
                CatalogViolation(
                    "brick_template_axis_owned_return_field",
                    f"{rel}{value_path}",
                    f"Brick shape catalog declares {owner}-owned returned field/key {field!r}",
                )
            )
    return violations


def _template_path_shape_problem(path: str) -> str | None:
    """Shared path-shape rules for ANY brick/templates ref (live or historical)."""
    if path.startswith("/") or ".." in Path(path).parts:
        return "physical template path must stay inside the repo"
    if not path.startswith("brick/templates/"):
        return "physical template path must stay under brick/templates"
    if path in ADMITTED_TEMPLATE_ROOT_FILES:
        # T-FLATTEN (0611): closed-form root-file sheets — exact paths only.
        return None
    parent = str(Path(path).parent)
    suffix = Path(path).suffix
    if parent not in ADMITTED_PHYSICAL_TEMPLATE_DIRS and not _is_brick_kind_template_dir(parent):
        return f"physical template path uses unadmitted directory {parent}"
    if suffix not in ADMITTED_TEMPLATE_SUFFIXES and not (
        parent == "brick/templates/tasks" and suffix in TASK_TEMPLATE_SUFFIXES
    ):
        return f"physical template path uses unadmitted suffix {suffix}"
    return None


def _validate_physical_path(path: str, physical_files: set[str]) -> str | None:
    """LIVE binding resolution: the file must exist in the live brick/templates tree.

    No archive fallback here on purpose — active catalog/step rows may only
    bind sheets that are live menu inventory.
    """
    problem = _template_path_shape_problem(path)
    if problem:
        return problem
    if path not in physical_files:
        return "physical template path does not exist"
    return None


def _validate_declared_template_ref(
    path: str,
    physical_files: set[str],
    archived_template_files: set[str],
) -> str | None:
    """Declaration-packet ref resolution (ARCHIVE FALLBACK PRUNED, 0611).

    A packet's template ref RESOLVES iff the file EXISTS at its physical
    brick/templates path. The 0610 archive-mirror fallback is pruned with the
    museum (CLEAN-YARD v3): retired sheets live only in the frozen history
    repo, and a ref to one REDs loudly here instead of resolving. All
    path-shape rules stay identical to live resolution.
    """
    problem = _template_path_shape_problem(path)
    if problem:
        return problem
    if path in physical_files or path in archived_template_files:
        return None
    return (
        "template file does not exist at its brick/templates path (no archive "
        "fallback in the product repo; retired sheets live in the frozen museum)"
    )


def _validate_brick_spec_path(path: str, brick_spec_files: set[str]) -> str | None:
    if path.startswith("/") or ".." in Path(path).parts:
        return "Brick spec path must stay inside the repo"
    parts = Path(path).parts
    if (
        len(parts) != 5
        or parts[0] != "brick"
        or parts[1] != "templates"
        or parts[2] != "bricks"
        or not _slug_part(parts[3])
        or parts[4] != BRICK_SPEC_FILENAME
    ):
        return f"Brick spec path must be {BRICKS_SPEC_DIR}/<kind>/{BRICK_SPEC_FILENAME}"
    if path not in brick_spec_files:
        return "Brick spec path does not exist"
    return None


def _validate_state(
    state: Mapping[str, Any],
    *,
    mode: str,
    require_physical_bindings: bool,
    enforce_orphans: bool,
) -> list[CatalogViolation]:
    violations: list[CatalogViolation] = list(_as_list(state.get("seed_violations")))
    canonical_gate_refs = tuple(state.get("declared_gate_refs_py", ()))
    canonical_gate_ref_set = set(canonical_gate_refs)
    movement_literals = set(state.get("movement_literals", ()))
    agent_refs = set(state.get("agent_object_refs", ()))
    physical_files = set(state.get("physical_files", ()))
    brick_spec_files = set(state.get("brick_spec_files", ()))
    archived_template_files = set(state.get("archived_template_files", ()))
    physical_template_docs = _as_mapping(state.get("physical_template_docs"))
    ref_map = _as_mapping(state.get("brick_template_ref_map"))
    gate_concepts = set(state.get("gate_concepts", ()))
    documents = list(state.get("catalogs", ()))
    if require_physical_bindings and _active_split_step_template_count(documents) == 0:
        violations.append(
            CatalogViolation(
                "missing_active_split_step_template_rows",
                f"{BRICKS_SPEC_DIR}/",
                "P8 active mode requires active step_template_catalog.rows "
                "(sourced from bricks/<kind>/brick.md since U6); old registry fallback is compat-only",
            )
        )
    steps = _step_templates(
        documents,
        allow_compat_fallback=not require_physical_bindings,
    )

    for source_name, observed in (
        ("link/gate.yaml declared_gate_refs", tuple(state.get("declared_gate_refs_yaml", ()))),
        ("AGENTS.md link-gate refs", tuple(state.get("declared_gate_refs_agents", ()))),
    ):
        if set(observed) != canonical_gate_ref_set:
            violations.append(
                CatalogViolation(
                    "link_gate_token_drift",
                    source_name,
                    f"observed {sorted(observed)} but link/gate.py declares {sorted(canonical_gate_refs)}",
                )
            )
    support_gate_refs = tuple(state.get("support_gate_refs", ()))
    expected_support_gate_refs = tuple(
        state.get("compact_support_gate_refs_expected", support_gate_refs)
    )
    if support_gate_refs != expected_support_gate_refs:
        violations.append(
            CatalogViolation(
                "link_gate_token_drift",
                "support compact Link gate tokens",
                "observed "
                f"{sorted(support_gate_refs)} but compact authoring requires "
                f"{sorted(expected_support_gate_refs)}",
            )
        )

    for rel, document, _compat_old in documents:
        catalog_gate_refs = _catalog_gate_refs(document)
        compact_gate_ref_set = set(
            state.get("compact_support_gate_refs_expected", support_gate_refs)
        )
        if catalog_gate_refs and catalog_gate_refs != compact_gate_ref_set:
            violations.append(
                CatalogViolation(
                    "link_gate_token_drift",
                    rel,
                    "compact_link_authoring gate refs drift from default/concept-backed "
                    "link/gate.py DECLARED_GATE_REFS",
                )
            )
        for value_path, value in _walk_values(document):
            key = value_path.rsplit(".", 1)[-1].split("[", 1)[0]
            if key not in GATE_REF_KEYS:
                continue
            values = value if isinstance(value, list) else [value]
            for candidate in values:
                text = _text(candidate)
                if text in gate_concepts and text not in canonical_gate_ref_set:
                    violations.append(
                        CatalogViolation(
                            "gate_concept_used_as_live_gate_ref",
                            f"{rel}{value_path}",
                            f"gate concept {text} used where a live link-gate:* ref is required",
                        )
                    )

    violations.extend(_validate_shape_catalog_content(documents))
    violations.extend(
        _validate_shape_subtree_extra_documents(
            state.get("shape_subtree_extra_documents", ())
        )
    )
    violations.extend(_validate_chain_preset_split(documents))

    seen_steps: dict[str, Mapping[str, Any]] = {}
    referenced_physical: set[str] = set()
    step_refs = {
        _text(step.get("step_template_ref"))
        for _rel, step, _compat_old in steps
        if _text(step.get("step_template_ref"))
    }
    step_ref_to_spec = {
        _text(step.get("step_template_ref")): _text(step.get("brick_spec_ref"))
        for _rel, step, _compat_old in steps
        if _text(step.get("step_template_ref"))
    }
    violations.extend(
        _validate_chain_preset_references(
            documents,
            step_refs=step_refs,
            step_ref_to_spec=step_ref_to_spec,
            brick_spec_files=brick_spec_files,
            gate_concepts=gate_concepts,
            movement_literals=movement_literals,
        )
    )
    for rel, step, _compat_old in steps:
        location = f"{rel}:{_text(step.get('step_template_ref')) or '<missing-step-ref>'}"
        step_ref = _text(step.get("step_template_ref"))
        if step_ref in seen_steps:
            previous = seen_steps[step_ref]
            for field in ("agent_object_ref", "link_word", "brick_contract"):
                if step.get(field) != previous.get(field):
                    violations.append(
                        CatalogViolation(
                            "duplicate_conflicting_step_template_ref",
                            location,
                            f"duplicate {step_ref} has conflicting {field}",
                        )
                    )
                    break
            else:
                if set(_brick_template_refs(step)) != set(_brick_template_refs(previous)):
                    violations.append(
                        CatalogViolation(
                            "duplicate_conflicting_step_template_ref",
                            location,
                            f"duplicate {step_ref} has conflicting brick_template_refs",
                        )
                    )
        elif step_ref:
            seen_steps[step_ref] = step

        agent_ref = _text(step.get("agent_object_ref"))
        if agent_ref and agent_ref not in agent_refs:
            violations.append(
                CatalogViolation(
                    "agent_object_ref_payload_drift",
                    location,
                    f"agent_object_ref {agent_ref} is absent from agent/objects payload object_ref values",
                )
            )
        inline_keys = sorted(AGENT_INLINE_PAYLOAD_KEYS & set(step))
        if inline_keys:
            violations.append(
                CatalogViolation(
                    "agent_object_ref_payload_drift",
                    location,
                    f"Brick catalog carries inline Agent payload key(s): {', '.join(inline_keys)}",
                )
            )

        link_word = _text(step.get("link_word"))
        if link_word and link_word not in movement_literals:
            violations.append(
                CatalogViolation(
                    "invalid_link_word",
                    location,
                    f"link_word {link_word!r} is not one of {sorted(movement_literals)}",
                )
            )

        refs = _brick_template_refs(step)
        if require_physical_bindings and not refs:
            violations.append(
                CatalogViolation(
                    "missing_physical_binding",
                    location,
                    "active step_template_ref lacks explicit brick_template_refs",
                )
            )
        for ref in refs:
            if ref.startswith("building-step-template:"):
                violations.append(
                    CatalogViolation(
                        "step_ref_masquerades_as_brick_template_ref",
                        location,
                        f"{ref} is a step template ref, not a physical Brick template ref",
                    )
                )
                continue
            physical_path = _text(ref_map.get(ref)) if ref.startswith("brick-template:") else ref
            if not physical_path:
                violations.append(
                    CatalogViolation(
                        "invalid_physical_template_path",
                        location,
                        f"{ref} does not resolve to a physical template path",
                    )
                )
                continue
            problem = _validate_physical_path(physical_path, physical_files)
            if problem:
                violations.append(
                    CatalogViolation("invalid_physical_template_path", location, f"{physical_path}: {problem}")
                )
            else:
                referenced_physical.add(physical_path)

    if enforce_orphans:
        classified = set(state.get("classified_physical_templates", ()))
        for path in sorted(physical_files - referenced_physical - classified):
            violations.append(
                CatalogViolation(
                    "orphan_physical_template",
                    path,
                    "active physical template is neither referenced nor classified shared/base/historical",
                )
            )

    classified_by_category = _as_mapping(state.get("classified_physical_templates_by_category"))
    content_scan_paths = set(referenced_physical)
    for category in ("active", "shared_base", "active_profile_pinned_compat"):
        content_scan_paths.update(
            _text(_as_mapping(item).get("path"))
            for item in _as_list(classified_by_category.get(category))
            if _text(_as_mapping(item).get("path"))
        )
    violations.extend(_validate_physical_template_content(physical_template_docs, content_scan_paths))

    # REHOME (objective_preservation_root closure delta-status invariant): the
    # standard-closure-with-parent-delta template's parent_goal_delta_status.allowed_fields
    # must be EXACTLY the five delta-ref buckets + evidence_refs. objective_preservation_root
    # only proved each NAME is present (text_contains); this asserts the closed SET so an
    # added/dropped bucket drifts RED. physical_template_docs already carries the live closure
    # template. Present-guarded: fires only when parent_goal_delta_status is declared (the
    # synthetic control fixture omits it; the live template always declares it). Field PRESENCE
    # itself stays pinned by objective_preservation_root path_exists + the template's
    # required_return_shape.
    closure_doc = _as_mapping(
        physical_template_docs.get(
            "brick/templates/bricks/closure/return.yaml"
        )
    )
    closure_delta_status = _as_mapping(closure_doc.get("parent_goal_delta_status"))
    if closure_delta_status:
        closure_allowed = {
            _text(item)
            for item in _as_list(closure_delta_status.get("allowed_fields"))
            if _text(item)
        }
        closure_canonical = {
            "matched_delta_refs",
            "closed_delta_refs",
            "open_delta_refs",
            "missing_delta_refs",
            "unknown_delta_refs",
            "evidence_refs",
        }
        if closure_allowed != closure_canonical:
            violations.append(
                CatalogViolation(
                    "closure_parent_delta_status_field_set_drift",
                    "brick/templates/bricks/closure/return.yaml",
                    "parent_goal_delta_status.allowed_fields must be exactly "
                    f"{sorted(closure_canonical)} but observed {sorted(closure_allowed)}",
                )
            )

    violations.extend(
        _validate_declaration_packets(
            state.get("declaration_packets", ()),
            physical_files,
            brick_spec_files,
            archived_template_files,
        )
    )

    active_inputs = tuple(state.get("active_inputs", ()))
    if mode == "p10-delete":
        for path in tuple(state.get("compat_inputs", ())):
            if path == OLD_REGISTRY_PATH:
                violations.append(
                    CatalogViolation(
                        "old_registry_active_dependency",
                        path,
                        "old registry still exists as a compatibility input in P10 deletion mode",
                    )
                )
        for path in active_inputs:
            if path == OLD_REGISTRY_PATH:
                violations.append(
                    CatalogViolation(
                        "old_registry_active_dependency",
                        path,
                        "old registry remains an active input in P10 deletion mode",
                    )
                )
    for path in active_inputs:
        if _is_historical_active_input(str(path)):
            violations.append(
                CatalogViolation(
                    "historical_ref_used_as_active_input",
                    str(path),
                    "historical/evidence path is used as active loader input",
                )
            )

    return violations


def _live_state(repo: Path) -> Mapping[str, Any]:
    agent_refs, agent_violations = _agent_object_refs(repo)
    documents = _catalog_documents(repo)
    physical_files = _physical_files(repo)
    brick_spec_files = _brick_spec_files(repo)
    return {
        "seed_violations": agent_violations,
        "catalogs": documents,
        "declared_gate_refs_py": _canonical_gate_refs(repo),
        "declared_gate_refs_yaml": _gate_refs_from_gate_yaml(repo),
        "declared_gate_refs_agents": _gate_refs_from_agents(repo),
        "support_gate_refs": _support_gate_refs(repo),
        "compact_support_gate_refs_expected": tuple(
            _canonical_gate_refs(repo)[index] for index in _compact_support_gate_indexes(repo)
        ),
        "movement_literals": tuple(_py_constant(repo / "link/movement.py", "MOVEMENT_LITERALS")),
        "gate_concepts": _gate_concepts_from_gate_yaml(repo),
        "agent_object_refs": agent_refs,
        "physical_files": physical_files,
        "brick_spec_files": brick_spec_files,
        "archived_template_files": _archived_template_files(repo),
        "physical_template_docs": _physical_template_documents(repo, physical_files),
        "brick_template_ref_map": {},
        "active_inputs": tuple(rel for rel, _document, compat_old in documents if not compat_old),
        "compat_inputs": tuple(rel for rel, _document, compat_old in documents if compat_old),
        "classified_physical_templates": _classified_physical_templates(documents),
        "classified_physical_templates_by_category": _classified_physical_templates_by_category(documents),
        "shape_subtree_extra_documents": _shape_subtree_extra_documents(repo),
        "declaration_packets": _declaration_packets(repo),
    }


def _synthetic_base(temp_root: Path) -> Mapping[str, Any]:
    physical_files = {
        "brick/templates/bricks/code-attack-qa/return.yaml",
        "brick/templates/bricks/work/return.yaml",
        "brick/templates/bricks/closure/return.yaml",
    }
    brick_spec_files = {
        "brick/templates/bricks/code-attack-qa/brick.md",
        "brick/templates/bricks/work/brick.md",
        "brick/templates/bricks/closure/brick.md",
    }
    for rel in physical_files:
        path = temp_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("template_ref: fixture\n", encoding="utf-8")
    for rel in brick_spec_files:
        path = temp_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nbrick_kind: fixture\n---\n", encoding="utf-8")
    # ARCHIVE FALLBACK PRUNED (CLEAN-YARD v3, 0611): the control packet
    # references only PHYSICAL sheets; the stale-ref FIRE probes
    # (missing_both_locations_*) assert a retired/archived ref REDs loudly
    # instead of resolving.
    archived_template_files = _archived_template_files(temp_root)
    catalog = {
        "compact_link_authoring_view": {
            "projection_only": True,
            "canonical_link_source": "link/gate.py DECLARED_GATE_REFS",
            "default_gate_ref": "link-gate:default-transition",
            "token_refs": {
                "strict": "link-gate:strict",
                "human": "link-gate:human",
                "coo": "link-gate:coo",
            },
        },
    }
    shapes_doc = {
        "shapes": [
            {
                "shape_ref": "building-shape:fixture",
                "intent": "fixture shape for checker control",
            }
        ]
    }
    # U4/U6: active step rows are sourced from bricks/<kind>/brick.md and wrapped by
    # _catalog_documents under the BRICKS_SPEC_DIR key (step-templates.yaml retired).
    # The FIRE harness mirrors that live shape so a broken bricks-sourced step row
    # trips the fixture, not the deleted file's old layout.
    step_templates_doc = {
        "step_template_catalog": {
            "rows": [
                {
                    "step_template_ref": "building-step-template:work",
                    "agent_object_ref": "agent-object:dev",
                    "link_word": "forward",
                    "brick_contract": "fixture work contract",
                    "brick_spec_ref": "brick/templates/bricks/work/brick.md",
                    "brick_template_refs": ["brick-template:work-return"],
                },
                {
                    "step_template_ref": "building-step-template:code-attack-qa",
                    "agent_object_ref": "agent-object:qa",
                    "link_word": "forward",
                    "brick_contract": "fixture code attack QA contract",
                    "brick_spec_ref": "brick/templates/bricks/code-attack-qa/brick.md",
                    "brick_template_refs": ["brick-template:code-attack-qa-return"],
                },
                {
                    "step_template_ref": "building-step-template:closure",
                    "agent_object_ref": "agent-object:coo",
                    "link_word": "forward",
                    "brick_contract": "fixture closure contract",
                    "brick_spec_ref": "brick/templates/bricks/closure/brick.md",
                    "brick_template_refs": ["brick-template:closure-return"],
                },
            ]
        },
    }
    # Chain presets are sourced from presets/<name>.md (U3 re-home): each .md is a
    # single-row chain_presets document with catalog_scope on the ROW. The FIRE
    # harness mirrors that shape so it exercises the real presets/ classification
    # and reference-resolution path (not a stale wrapper-document layout).
    common_chain_presets_doc = {
        "chain_presets": [
            {
                "preset_ref": "building-chain-preset:fixture-common",
                "catalog_scope": "common",
                "selected_shape_ref": "building-shape:fixture",
                "steps": [
                    {
                        "step_template_ref": "building-step-template:work",
                        "brick_spec_ref": "brick/templates/bricks/work/brick.md",
                        "target_word": "hold",
                    }
                ],
                "gate_concept_profile": ["default-transition"],
            }
        ],
    }
    dogfood_chain_presets_doc = {
        "chain_presets": [
            {
                "preset_ref": "building-chain-preset:brick-protocol-fixture",
                "catalog_scope": "brick_protocol_dogfood",
                "common_basis_ref": "building-chain-preset:fixture-common",
                "selected_shape_ref": "building-shape:fixture",
                "steps": [
                    {
                        "step_template_ref": "building-step-template:work",
                        "brick_spec_ref": "brick/templates/bricks/work/brick.md",
                        "target_word": "review",
                    }
                ],
            }
        ],
    }
    return {
        "seed_violations": [],
        "catalogs": [
            ("brick/templates/shapes/catalog.yaml", catalog, False),
            ("brick/templates/shapes/shapes.yaml", shapes_doc, False),
            (f"{BRICKS_SPEC_DIR}/", step_templates_doc, False),
            (f"{PRESETS_SPEC_DIR}/fixture-common.md", common_chain_presets_doc, False),
            (
                f"{PRESETS_SPEC_DIR}/brick-protocol-fixture.md",
                dogfood_chain_presets_doc,
                False,
            ),
        ],
        "declared_gate_refs_py": (
            "link-gate:default-transition",
            "link-gate:strict",
            "link-gate:human",
            "link-gate:coo",
        ),
        "declared_gate_refs_yaml": (
            "link-gate:default-transition",
            "link-gate:strict",
            "link-gate:human",
            "link-gate:coo",
        ),
        "declared_gate_refs_agents": (
            "link-gate:coo",
            "link-gate:default-transition",
            "link-gate:human",
            "link-gate:strict",
        ),
        "support_gate_refs": (
            "link-gate:default-transition",
            "link-gate:strict",
            "link-gate:human",
            "link-gate:coo",
        ),
        "compact_support_gate_refs_expected": (
            "link-gate:default-transition",
            "link-gate:strict",
            "link-gate:human",
            "link-gate:coo",
        ),
        "movement_literals": tuple("forward reroute".split()),
        "gate_concepts": {
            "default-transition",
            "strict-evidence",
            "fan-in-wait-all",
            "coo-review",
            "portfolio-policy",
            "human-review",
        },
        "agent_object_refs": {"agent-object:dev", "agent-object:qa", "agent-object:coo"},
        "physical_files": physical_files,
        "brick_spec_files": brick_spec_files,
        "archived_template_files": archived_template_files,
        "physical_template_docs": {
            "brick/templates/bricks/code-attack-qa/return.yaml": {
                "template_ref": "brick-template:code-attack-qa-return",
                "required_return_shape": ["observed_evidence", "not_proven"],
            },
            "brick/templates/bricks/work/return.yaml": {
                "template_ref": "brick-template:work-return",
                "required_return_shape": ["made_changes", "not_proven"],
                "forbidden_return_keys": ["movement_choice", "route_target"],
            },
            "brick/templates/bricks/closure/return.yaml": {
                "template_ref": "brick-template:closure-return",
                "required_return_shape": ["observed_evidence", "not_proven"],
            },
        },
        "brick_template_ref_map": {
            "brick-template:code-attack-qa-return": "brick/templates/bricks/code-attack-qa/return.yaml",
            "brick-template:work-return": "brick/templates/bricks/work/return.yaml",
            "brick-template:closure-return": "brick/templates/bricks/closure/return.yaml",
        },
        "active_inputs": ("brick/templates/shapes/catalog.yaml",),
        "compat_inputs": (),
        "classified_physical_templates": (),
        "classified_physical_templates_by_category": {},
        "shape_subtree_extra_documents": (),
        "declaration_packets": (
            (
                "project/brick-protocol/buildings/fixture/work/preset-expansion.json",
                {
                    "shape_catalog_ref": "brick-template-catalog:fixture",
                    "expanded_brick_spec_refs": [
                        "brick/templates/bricks/work/brick.md",
                    ],
                    "expanded_brick_template_refs": [
                        "brick/templates/bricks/work/return.yaml",
                    ],
                    "legacy_expanded_brick_template_refs": [
                        "brick/templates/bricks/work/return.yaml",
                    ],
                },
            ),
        ),
    }


def _mutable_step_rows(state: Mapping[str, Any]) -> list[Any]:
    for _rel, document, _compat_old in state["catalogs"]:  # type: ignore[index]
        if not isinstance(document, dict):
            continue
        rows = _nested_value(document, "step_template_catalog.rows")
        if isinstance(rows, list):
            return rows
        rows = document.get("step_templates")
        if isinstance(rows, list):
            return rows
    raise ProfileError("synthetic fixture lacks mutable step rows")


def _first_catalog_document(state: Mapping[str, Any]) -> dict[str, Any]:
    return state["catalogs"][0][1]  # type: ignore[index]


def _preset_row_by_scope(state: Mapping[str, Any], scope: str) -> dict[str, Any]:
    """First chain_preset row (from a presets/*.md fixture doc) with catalog_scope==scope."""
    for rel, document, _compat_old in state["catalogs"]:  # type: ignore[index]
        if not str(rel).startswith(PRESETS_SPEC_DIR + "/"):
            continue
        rows = document.get("chain_presets")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            if _text(rows[0].get("catalog_scope")) == scope:
                return rows[0]
    raise ProfileError(f"synthetic fixture lacks {scope} preset rows")


def _preset_document_by_scope(state: Mapping[str, Any], scope: str) -> dict[str, Any]:
    """The presets/*.md fixture DOCUMENT whose first chain_preset row has catalog_scope==scope."""
    for rel, document, _compat_old in state["catalogs"]:  # type: ignore[index]
        if not str(rel).startswith(PRESETS_SPEC_DIR + "/"):
            continue
        rows = document.get("chain_presets")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            if _text(rows[0].get("catalog_scope")) == scope:
                return document  # type: ignore[return-value]
    raise ProfileError(f"synthetic fixture lacks {scope} preset document")


def _first_dogfood_preset(state: Mapping[str, Any]) -> dict[str, Any]:
    return _preset_row_by_scope(state, "brick_protocol_dogfood")


def _first_common_preset(state: Mapping[str, Any]) -> dict[str, Any]:
    return _preset_row_by_scope(state, "common")


def _run_fire_fixtures() -> tuple[int, list[str]]:
    fixture_results: list[str] = []
    mutations: dict[str, tuple[str, str, Any]] = {
        "missing_physical_binding": ("missing_physical_binding", "remove_binding", None),
        "invalid_physical_template_path": (
            "invalid_physical_template_path",
            "set_binding",
            "brick/templates/shapes/not-a-physical-return.yaml",
        ),
        "step_ref_masquerades_as_brick_template_ref": (
            "step_ref_masquerades_as_brick_template_ref",
            "set_binding",
            "building-step-template:work",
        ),
        "orphan_physical_template": ("orphan_physical_template", "add_orphan", None),
        "duplicate_conflicting_step_template_ref": (
            "duplicate_conflicting_step_template_ref",
            "duplicate_conflict",
            None,
        ),
        "link_gate_token_drift": ("link_gate_token_drift", "gate_drift", None),
        "agent_object_ref_payload_drift": (
            "agent_object_ref_payload_drift",
            "agent_payload_drift",
            None,
        ),
        "invalid_link_word": ("invalid_link_word", "invalid_link_word", None),
        "gate_concept_used_as_live_gate_ref": (
            "gate_concept_used_as_live_gate_ref",
            "gate_concept_live",
            None,
        ),
        "old_registry_active_dependency": (
            "old_registry_active_dependency",
            "old_registry_active",
            None,
        ),
        "historical_ref_used_as_active_input": (
            "historical_ref_used_as_active_input",
            "historical_active_input",
            None,
        ),
        "missing_active_split_step_template_rows": (
            "missing_active_split_step_template_rows",
            "missing_active_split_rows",
            None,
        ),
        "common_dogfood_preset_overlap": (
            "common_dogfood_preset_overlap",
            "common_dogfood_overlap",
            None,
        ),
        "legacy_compat_preset_refs": (
            "legacy_compat_preset_refs",
            "legacy_compat_preset_refs",
            None,
        ),
        "dogfood_common_basis_missing": (
            "dogfood_common_basis_missing",
            "dogfood_common_basis_missing",
            None,
        ),
        "declaration_expanded_brick_template_ref_not_physical": (
            "declaration_expanded_brick_template_ref_not_physical",
            "bad_declaration_brick_template_ref",
            None,
        ),
        "declaration_expanded_brick_spec_ref_not_physical": (
            "declaration_expanded_brick_spec_ref_not_physical",
            "bad_declaration_brick_spec_ref",
            None,
        ),
        "declaration_expanded_brick_template_ref_not_physical_unmarked": (
            "declaration_expanded_brick_template_ref_not_physical",
            "bad_unmarked_declaration_brick_template_ref",
            None,
        ),
        # ARCHIVE FALLBACK negative probes (PRODUCT-TREE CLEANUP 0610): a ref
        # that exists at NEITHER brick/templates nor archive/brick-templates
        # must still RED. Mirrors the existing negative-probe convention; the
        # positive direction lives in the control packet's archive-only ref.
        "declaration_expanded_brick_template_ref_missing_both_locations": (
            "declaration_expanded_brick_template_ref_not_physical",
            "missing_both_locations_declaration_brick_template_ref",
            None,
        ),
        "legacy_expanded_brick_template_ref_missing_both_locations": (
            "legacy_expanded_brick_template_ref_invalid",
            "missing_both_locations_legacy_brick_template_ref",
            None,
        ),
        "brick_template_axis_owned_return_field": (
            "brick_template_axis_owned_return_field",
            "axis_owned_return_field",
            None,
        ),
        "brick_template_axis_owned_return_top_level_key": (
            "brick_template_axis_owned_return_field",
            "axis_owned_return_top_level_key",
            None,
        ),
        "brick_template_axis_owned_next_link_input_section": (
            "brick_template_axis_owned_return_field",
            "axis_owned_next_link_input_section",
            None,
        ),
        "brick_template_axis_owned_shape_catalog_field": (
            "brick_template_axis_owned_return_field",
            "axis_owned_shape_catalog_field",
            None,
        ),
        "brick_template_axis_owned_shapes_subtree_field": (
            "brick_template_axis_owned_return_field",
            "axis_owned_shapes_subtree_field",
            None,
        ),
        "shape_subtree_return_template_not_admitted": (
            "shape_subtree_return_template_not_admitted",
            "shape_subtree_return_template_not_admitted",
            None,
        ),
        "legacy_expanded_brick_template_ref_invalid": (
            "legacy_expanded_brick_template_ref_invalid",
            "bad_legacy_declaration_brick_template_ref",
            None,
        ),
        "invalid_chain_step_template_ref": (
            "invalid_chain_step_template_ref",
            "invalid_chain_step_template_ref",
            None,
        ),
        "chain_step_alias_required_for_repeated_template": (
            "chain_step_alias_required_for_repeated_template",
            "chain_step_alias_required_for_repeated_template",
            None,
        ),
        "duplicate_chain_step_identity": (
            "duplicate_chain_step_identity",
            "duplicate_chain_step_identity",
            None,
        ),
        "invalid_chain_gate_concept_profile": (
            "invalid_chain_gate_concept_profile",
            "invalid_chain_gate_concept_profile",
            None,
        ),
        "invalid_chain_target_word": (
            "invalid_chain_target_word",
            "invalid_chain_target_word",
            None,
        ),
        "qa_preset_missing_reroute_policy": (
            "qa_preset_missing_reroute_policy",
            "qa_preset_missing_reroute_policy",
            None,
        ),
        # presets/ source fixture (U3 re-home): a COMMON-scope presets/<name>.md
        # whose step_template_ref does not resolve must RED, proving the checker
        # validates the presets/ source rows (not only the dogfood ones).
        "presets_common_invalid_chain_step_template_ref": (
            "invalid_chain_step_template_ref",
            "presets_common_invalid_chain_step_template_ref",
            None,
        ),
        # [P1] a presets/<name>.md with a typo'd catalog_scope must RED (was silently
        # bucketed as common -> checker exit 0). Mirrors the loader enum reject.
        "invalid_chain_preset_catalog_scope": (
            "invalid_chain_preset_catalog_scope",
            "invalid_chain_preset_catalog_scope",
            None,
        ),
        # [P2] a presets/<name>.md with NO well-formed frontmatter must RED (was
        # silently skipped -> escaped ALL preset validation).
        "preset_file_missing_frontmatter": (
            "preset_file_missing_frontmatter",
            "preset_file_missing_frontmatter",
            None,
        ),
        "invalid_chain_brick_spec_ref": (
            "invalid_chain_brick_spec_ref",
            "invalid_chain_brick_spec_ref",
            None,
        ),
    }

    with tempfile.TemporaryDirectory(prefix="brick-template-catalog-fixtures-") as tmp:
        base = _synthetic_base(Path(tmp))
        control_violations = _validate_state(
            base,
            mode="p8-active",
            require_physical_bindings=True,
            enforce_orphans=True,
        )
        if control_violations:
            raise ProfileError(
                "synthetic control fixture rejected: "
                + "; ".join(violation.render() for violation in control_violations)
            )
        for fixture_name, (expected_code, mutation, value) in mutations.items():
            state = copy.deepcopy(base)
            step_rows = _mutable_step_rows(state)
            first_step = step_rows[0]
            if mutation == "remove_binding":
                first_step.pop("brick_template_refs", None)
            elif mutation == "set_binding":
                first_step["brick_template_refs"] = [value]
            elif mutation == "add_orphan":
                state["physical_files"] = set(state["physical_files"]) | {"brick/templates/review/orphan.yaml"}
            elif mutation == "duplicate_conflict":
                duplicate = copy.deepcopy(first_step)
                duplicate["agent_object_ref"] = "agent-object:coo"
                step_rows.append(duplicate)
            elif mutation == "gate_drift":
                state["declared_gate_refs_yaml"] = ("link-gate:default-transition", "link-gate:strict")
            elif mutation == "agent_payload_drift":
                first_step["agent_object_ref"] = "agent-object:missing"
            elif mutation == "invalid_link_word":
                first_step["link_word"] = "hold"
            elif mutation == "gate_concept_live":
                catalog = _first_catalog_document(state)
                catalog["compact_link_authoring_view"]["default_gate_ref"] = "fan-in-wait-all"
            elif mutation == "old_registry_active":
                state["active_inputs"] = (OLD_REGISTRY_PATH,)
            elif mutation == "historical_active_input":
                state["active_inputs"] = ("project/brick-protocol/buildings/old/work/preset-expansion.json",)
            elif mutation == "missing_active_split_rows":
                # U4/U6: active step rows are the bricks/<kind>/brick.md-sourced document
                # (wrapped under the BRICKS_SPEC_DIR key by _catalog_documents).
                # Empty THAT document so the missing-active-rows guard fires on the
                # live source, then add an old-registry compat doc that must NOT
                # satisfy the active-rows requirement.
                for rel, document, _compat_old in state["catalogs"]:  # type: ignore[index]
                    if str(rel) == f"{BRICKS_SPEC_DIR}/" and isinstance(document, dict):
                        document["step_template_catalog"]["rows"] = []
                state["catalogs"].append(
                    (
                        OLD_REGISTRY_PATH,
                        {
                            "step_templates": [
                                {
                                    "step_template_ref": "building-step-template:work",
                                    "agent_object_ref": "agent-object:dev",
                                    "link_word": "forward",
                                    "brick_contract": "old compat fixture",
                                    "brick_template_refs": [
                                        "brick-template:work-return"
                                    ],
                                }
                            ]
                        },
                        True,
                    )
                )
            elif mutation == "common_dogfood_overlap":
                _first_dogfood_preset(state)["preset_ref"] = "building-chain-preset:fixture-common"
            elif mutation == "legacy_compat_preset_refs":
                # L legacy cut (0610): ANY presence of the retired key is the
                # violation now (not just a conflicting alias target).
                _first_dogfood_preset(state)["compat_preset_refs"] = [
                    "building-chain-preset:fixture"
                ]
            elif mutation == "dogfood_common_basis_missing":
                _first_dogfood_preset(state)["common_basis_ref"] = "building-chain-preset:missing"
            elif mutation == "bad_declaration_brick_template_ref":
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet["expanded_brick_template_refs"] = ["building-step-template:work"]
            elif mutation == "bad_declaration_brick_spec_ref":
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet["expanded_brick_spec_refs"] = ["building-step-template:work"]
            elif mutation == "bad_unmarked_declaration_brick_template_ref":
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet.pop("shape_catalog_ref", None)
                packet["expanded_brick_template_refs"] = ["building-step-template:work"]
            elif mutation == "missing_both_locations_declaration_brick_template_ref":
                # NEGATIVE: exists at neither location -> must RED despite the
                # archive fallback (existence stays required).
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet["expanded_brick_template_refs"] = [
                    "brick/templates/review/never-existed-return.yaml"
                ]
            elif mutation == "missing_both_locations_legacy_brick_template_ref":
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet["legacy_expanded_brick_template_refs"] = [
                    "brick/templates/review/never-existed-return.yaml"
                ]
            elif mutation == "axis_owned_return_field":
                docs = state["physical_template_docs"]  # type: ignore[index]
                docs["brick/templates/bricks/work/return.yaml"]["required_return_shape"].append(
                    "movement_choice"
                )
            elif mutation == "axis_owned_return_top_level_key":
                docs = state["physical_template_docs"]  # type: ignore[index]
                docs["brick/templates/bricks/work/return.yaml"]["movement_choice"] = "reroute"
            elif mutation == "axis_owned_next_link_input_section":
                docs = state["physical_template_docs"]  # type: ignore[index]
                docs["brick/templates/bricks/work/return.yaml"]["next_link_input_sections"] = [
                    "performer"
                ]
            elif mutation == "axis_owned_shape_catalog_field":
                catalog = _first_catalog_document(state)
                catalog["performer"] = "agent-object:dev"
            elif mutation == "axis_owned_shapes_subtree_field":
                state["shape_subtree_extra_documents"] = (
                    (
                        "brick/templates/shapes/bad-return-template.yaml",
                        {
                            "template_ref": "brick-template:bad-shape-return",
                            "required_return_shape": ["movement_choice"],
                        },
                    ),
                )
            elif mutation == "shape_subtree_return_template_not_admitted":
                state["shape_subtree_extra_documents"] = (
                    (
                        "brick/templates/shapes/innocent-return-template.yaml",
                        {
                            "template_ref": "brick-template:innocent-shape-return",
                            "required_return_shape": ["observed_evidence"],
                        },
                    ),
                )
            elif mutation == "bad_legacy_declaration_brick_template_ref":
                packet = state["declaration_packets"][0][1]  # type: ignore[index]
                packet["legacy_expanded_brick_template_refs"] = ["/etc/passwd"]
            elif mutation == "invalid_chain_step_template_ref":
                _first_dogfood_preset(state)["steps"][0]["step_template_ref"] = "building-step-template:missing"
            elif mutation == "chain_step_alias_required_for_repeated_template":
                row = _first_dogfood_preset(state)
                row["steps"].append(copy.deepcopy(row["steps"][0]))
            elif mutation == "duplicate_chain_step_identity":
                row = _first_dogfood_preset(state)
                row["steps"][0]["step_alias"] = "work-lens"
                duplicate = copy.deepcopy(row["steps"][0])
                duplicate["step_alias"] = "work-lens"
                row["steps"].append(duplicate)
            elif mutation == "invalid_chain_brick_spec_ref":
                _first_dogfood_preset(state)["steps"][0]["brick_spec_ref"] = (
                    "brick/templates/bricks/closure/brick.md"
                )
            elif mutation == "invalid_chain_gate_concept_profile":
                _first_dogfood_preset(state)["gate_concept_profile"] = ["unknown-concept"]
            elif mutation == "invalid_chain_target_word":
                _first_dogfood_preset(state)["steps"][0]["target_word"] = "forward"
            elif mutation == "qa_preset_missing_reroute_policy":
                row = _first_common_preset(state)
                row["steps"] = [
                    {
                        "step_template_ref": "building-step-template:work",
                        "brick_spec_ref": "brick/templates/bricks/work/brick.md",
                        "target_word": "code_attack_qa",
                    },
                    {
                        "step_template_ref": "building-step-template:code-attack-qa",
                        "brick_spec_ref": "brick/templates/bricks/code-attack-qa/brick.md",
                        "target_word": "closure",
                    },
                ]
                row.pop("node_reroute_budgets", None)
            elif mutation == "presets_common_invalid_chain_step_template_ref":
                _first_common_preset(state)["steps"][0]["step_template_ref"] = "building-step-template:missing"
            elif mutation == "invalid_chain_preset_catalog_scope":
                _first_common_preset(state)["catalog_scope"] = "commmon"
            elif mutation == "preset_file_missing_frontmatter":
                # Mirror _catalog_documents wrapping a presets/<name>.md whose
                # _preset_frontmatter parsed to {} (no leading --- fence block):
                # the chain_presets row is empty, so the file yields no preset row.
                _preset_document_by_scope(state, "common")["chain_presets"] = [{}]

            mode = "p10-delete" if mutation == "old_registry_active" else "p8-active"
            violations = _validate_state(
                state,
                mode=mode,
                require_physical_bindings=True,
                enforce_orphans=True,
            )
            observed_codes = {violation.problem_code for violation in violations}
            if expected_code not in observed_codes:
                raise ProfileError(
                    f"FIRE fixture {fixture_name} expected {expected_code}, "
                    f"observed {sorted(observed_codes)}"
                )
            fixture_results.append(f"{fixture_name}:{expected_code}")

    return len(fixture_results), fixture_results


def run_check(repo: Path, mode: str) -> tuple[int, int, int]:
    if mode not in {"p3-staged", "p8-active", "p10-delete"}:
        raise ProfileError(f"unknown mode: {mode}")
    fixture_count, fixture_results = _run_fire_fixtures()
    state = _live_state(repo)
    violations = _validate_state(
        state,
        mode=mode,
        require_physical_bindings=mode in {"p8-active", "p10-delete"},
        enforce_orphans=mode in {"p8-active", "p10-delete"},
    )
    if violations:
        detail = "\n".join(f"- {violation.render()}" for violation in violations)
        raise ProfileError(f"Brick template catalog restructure rejected evidence:\n{detail}")
    catalog_count = len(state.get("catalogs", ()))
    print(
        "brick template catalog restructure guard passed: "
        f"{fixture_count} FIRE fixture(s) rejected; "
        f"{catalog_count} live catalog document(s) inspected in {mode} mode"
    )
    print("- fixtures: " + ", ".join(fixture_results))
    print(
        "- anchors: link/gate.py DECLARED_GATE_REFS; "
        "agent/objects/*.yaml payload object_ref; "
        "link/movement.py MOVEMENT_LITERALS; "
        "split catalog compact_link_authoring_view in P3-P10 drift scope"
    )
    p7_marked_count = _p7_marked_declaration_packet_count(
        state.get("declaration_packets", ())
    )
    print(f"- p7-marked declaration packets inspected: {p7_marked_count}")
    return fixture_count, catalog_count, len(state.get("physical_files", ()))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0 staged support-evidence "
            "guard. It runs synthetic RED fixtures and P3 live drift checks."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument(
        "--mode",
        choices=("p3-staged", "p8-active", "p10-delete"),
        default="p3-staged",
        help="Activation mode. P3 keeps real physical binding enforcement staged.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            raise ProfileError(f"--repo must be a directory: {repo}")
        run_check(repo, args.mode)
        print(PROOF_LIMIT)
        return 0
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        print(f"brick template catalog restructure checker rejected evidence: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
