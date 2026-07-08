"""Operator-only scaffold for a new brick KIND (make-a-brick skill helper).

Pure support mechanics: it WRITES the two per-kind template files
(``brick_protocol/brick/templates/bricks/<kind>/brick.md`` + ``return.yaml``) with the
body↔return invariant pre-satisfied, and REGISTERS the kind's primary return
template in the catalog ``active`` list so it is not an orphan. It authors no
Movement, casts no agent, and judges no success or quality. The made kind is
DATA, not a code enum — ``brick_protocol/brick/spec.BrickSpec`` needs no edit and a new casting
dial flows in through ``CASTING_FIELDS`` automatically.

The skill (brick_protocol/brick/templates/skills/make-a-brick) calls ``scaffold_brick_kind`` and
then runs the in-repo usability check (the bricks-spec + catalog profiles): green
on those profiles == the kind is Builder-resolvable.

This helper does NOT add a preset step (making the kind NEEDED is a separate,
deliberate authoring choice the skill documents); it only lands the kind + its
catalog registration so the checkers are green and the kind is loadable.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.support.recording.capture import REPO_ROOT

_BRICKS_DIR = "brick_protocol/brick/templates/bricks"
_CATALOG_REL = "brick_protocol/brick/templates/shapes/catalog.yaml"
_RETURN_FILENAME = "return.yaml"
_BRICK_FILENAME = "brick.md"
_TRANSITION_CONCERN_REF = "brick_protocol/brick/templates/bricks/transition-concern-return.yaml"
# The kernel admission gate keys NEW kind dirs on a CLOSED hand-list (a security
# allow-list, deliberately not disk-derived). A scaffolded kind dir is rejected by
# the `core` / `structure_template_integrity` profiles (and therefore by --all)
# until its slug is added to this set. The scaffold helper does NOT edit this kernel
# checker itself (an admission gate must stay human-reviewed, never auto-widened by
# the verb that creates admittable paths); it READS the set to report whether the
# operator still owes that one registration step.
_ADMISSION_CHECKER_REL = "brick_protocol/support/checkers/check_package_path_admission.py"
_ADMISSION_SET_NAME = "TEMPLATE0_BRICK_KINDS"

# A kind slug must be a lower-case [-a-z0-9] token (matches the bricks dir naming
# the bricks-spec checker keys on). Fail-closed before any write.
_KIND_SLUG = re.compile(r"^[a-z0-9][-a-z0-9]*$")


class BrickKindScaffoldError(ValueError):
    """A scaffold input was malformed or a target already exists."""


def scaffold_brick_kind(
    kind: str,
    *,
    brick_word: str,
    performer_word: str,
    requires_brick_write_scope: bool,
    performer_lane_need: str,
    link_movement_literal: str,
    brick_contract: str,
    required_return_shape: Sequence[str],
    body_paragraph: str,
    agent_object_hint_ref: str | None = None,
    carries_forward_fields: Sequence[str] | None = None,
    forbidden_return_keys: Sequence[str] | None = None,
    catalog_reason: str | None = None,
    repo_root: Path | str | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write a new brick kind's two template files and register its return template.

    Returns a record of what it wrote/registered (support evidence only). Raises
    ``BrickKindScaffoldError`` on a bad slug, an empty return shape, an existing
    target (unless ``overwrite``), or a body that omits a return-shape field.

    The body↔return invariant (check_bricks_spec_completeness): EVERY field in
    ``required_return_shape`` must appear (word-boundary token) in the ``##`` body.
    This helper APPENDS a "Return" line naming every field, so the invariant holds
    by construction even when ``body_paragraph`` omits some.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else Path(REPO_ROOT)
    slug = kind.strip()
    if not _KIND_SLUG.match(slug):
        raise BrickKindScaffoldError(
            f"kind must be a lower-case [-a-z0-9] slug (first char [a-z0-9]); got {kind!r}"
        )
    shape = [str(field).strip() for field in required_return_shape if str(field).strip()]
    if not shape:
        raise BrickKindScaffoldError("required_return_shape must be a non-empty field list")

    # Fail-closed on the Link Movement vocabulary BEFORE any write. The catalog
    # restructure checker (check_brick_template_catalog_restructure invalid_link_word)
    # rejects any kind whose link_movement_literal is not in the active Link Movement
    # set (MOVEMENT_LITERALS == forward / reroute). Without this guard the helper
    # would silently write a kind that REDs the catalog profile — violating the
    # make-a-brick contract that the scaffolded kind is checker-green / Builder-usable.
    movement_literal = link_movement_literal.strip()
    if movement_literal not in MOVEMENT_LITERALS:
        raise BrickKindScaffoldError(
            f"link_movement_literal must be one of {sorted(MOVEMENT_LITERALS)} "
            f"(the active Link Movement vocabulary); got {link_movement_literal!r}"
        )

    write_scope_literal = "yes" if requires_brick_write_scope else "no"
    primary_return_ref = f"{_BRICKS_DIR}/{slug}/{_RETURN_FILENAME}"
    forbidden = list(forbidden_return_keys) if forbidden_return_keys is not None else [
        "success",
        "failure",
        "approved",
        "quality",
        "movement_choice",
        "route_target",
    ]
    carries = (
        [str(f).strip() for f in carries_forward_fields if str(f).strip()]
        if carries_forward_fields is not None
        else []
    )
    bad_carry = [f for f in carries if f not in shape]
    if bad_carry:
        raise BrickKindScaffoldError(
            "carries_forward_fields must be a subset of required_return_shape; "
            f"not in shape: {', '.join(bad_carry)}"
        )

    kind_dir = repo / _BRICKS_DIR / slug
    brick_path = kind_dir / _BRICK_FILENAME
    return_path = kind_dir / _RETURN_FILENAME
    if not overwrite and (brick_path.exists() or return_path.exists()):
        raise BrickKindScaffoldError(
            f"kind '{slug}' already has template files (pass overwrite=True to replace): {kind_dir}"
        )

    brick_md = _render_brick_md(
        slug=slug,
        brick_word=brick_word.strip(),
        performer_word=performer_word.strip(),
        write_scope_literal=write_scope_literal,
        performer_lane_need=performer_lane_need.strip(),
        link_movement_literal=movement_literal,
        brick_contract=brick_contract.strip(),
        primary_return_ref=primary_return_ref,
        agent_object_hint_ref=(agent_object_hint_ref.strip() if agent_object_hint_ref else None),
        required_return_shape=shape,
        body_paragraph=body_paragraph.strip(),
        forbidden=forbidden,
    )
    return_yaml = _render_return_yaml(
        slug=slug,
        required_return_shape=shape,
        carries_forward_fields=carries,
        forbidden=forbidden,
    )

    kind_dir.mkdir(parents=True, exist_ok=True)
    brick_path.write_text(brick_md, encoding="utf-8")
    return_path.write_text(return_yaml, encoding="utf-8")

    registered = _register_active_template(
        repo / _CATALOG_REL,
        path_ref=primary_return_ref,
        reason=(
            catalog_reason
            or f"Canonical primary return template for building-step-template:{slug}."
        ),
    )

    # The one registration the helper CANNOT do for the operator: admit the new
    # kind dir in the kernel security gate. Report precisely whether it is owed so
    # the make-a-brick skill's usability check (which runs the REAL profiles, not
    # the standalone checker) does not false-green.
    admission = _admission_status(repo / _ADMISSION_CHECKER_REL, slug)

    return {
        "kind": slug,
        "brick_md_path": str(brick_path),
        "return_yaml_path": str(return_path),
        "primary_return_ref": primary_return_ref,
        "catalog_registered": registered,
        "required_return_shape": tuple(shape),
        "admission_registered": admission["admitted"],
        "admission_registration_required": admission["required_step"],
    }


def _admission_status(admission_checker_path: Path, slug: str) -> dict[str, object]:
    """READ-ONLY report on whether ``slug`` is admitted by the kernel gate.

    Returns ``admitted`` (the slug is already in ``TEMPLATE0_BRICK_KINDS``) and,
    when it is not, ``required_step`` — a precise instruction for the one manual
    registration the operator still owes before ``core`` / ``--all`` will accept the
    new kind dir. The helper never WRITES this kernel checker.
    """

    try:
        text = admission_checker_path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    block = ""
    marker = f"{_ADMISSION_SET_NAME} = {{"
    start = text.find(marker)
    if start != -1:
        end = text.find("}", start)
        block = text[start : end if end != -1 else len(text)]
    admitted = f'"{slug}"' in block
    if admitted:
        return {"admitted": True, "required_step": None}
    return {
        "admitted": False,
        "required_step": (
            f'Add "{slug}" to {_ADMISSION_SET_NAME} in {_ADMISSION_CHECKER_REL} '
            "(the kernel admission allow-list; a reviewed one-line registration), "
            "then the core + structure_template_integrity profiles accept the new "
            "kind dir. Without it --all rejects bricks/" + slug + " as unadmitted."
        ),
    }


def _render_brick_md(
    *,
    slug: str,
    brick_word: str,
    performer_word: str,
    write_scope_literal: str,
    performer_lane_need: str,
    link_movement_literal: str,
    brick_contract: str,
    primary_return_ref: str,
    agent_object_hint_ref: str | None,
    required_return_shape: list[str],
    body_paragraph: str,
    forbidden: list[str],
) -> str:
    refs = [primary_return_ref, _TRANSITION_CONCERN_REF]
    lines: list[str] = ["---"]
    lines.append(f"brick_kind: {slug}")
    lines.append(f"brick_word: {brick_word}")
    lines.append(f"performer_word: {performer_word}")
    lines.append(f"requires_brick_write_scope: {write_scope_literal}")
    lines.append(f"performer_lane_need: {performer_lane_need}")
    if agent_object_hint_ref:
        lines.append(f"agent_object_hint_ref: {agent_object_hint_ref}")
    lines.append("required_return_template_refs:")
    for ref in refs:
        lines.append(f"  - {ref}")
    lines.append(f"link_movement_literal: {link_movement_literal}")
    lines.append(f"brick_contract: {brick_contract}")
    lines.append("---")
    title = slug.replace("-", " ").title()
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")
    if body_paragraph:
        lines.append(body_paragraph)
        lines.append("")
    # The body↔return invariant line: name EVERY return-shape field so the
    # prose↔yaml drift checker passes by construction (word-boundary tokens).
    field_list = ", ".join(f"`{field}`" for field in required_return_shape)
    lines.append(
        f"Return: fill the `required_return_shape` from the return_template "
        f"(`{primary_return_ref}`): {field_list}."
    )
    lines.append("")
    forbidden_list = " / ".join(forbidden)
    lines.append(
        f"Do NOT return {forbidden_list} — sufficiency + movement are the Link "
        "gate's; quality/success are the human's."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_return_yaml(
    *,
    slug: str,
    required_return_shape: list[str],
    carries_forward_fields: list[str],
    forbidden: list[str],
) -> str:
    lines: list[str] = []
    lines.append(f"template_ref: brick-template:{slug}-return")
    lines.append("owner_axis: Brick")
    lines.append(f"template_kind: {slug.replace('-', '_')}_return_shape")
    lines.append("maps_to: AgentFact.returned")
    lines.append("step_template_refs:")
    lines.append(f"  - building-step-template:{slug}")
    lines.append("required_return_shape:")
    for field in required_return_shape:
        lines.append(f"  - {field}")
    lines.append("carries_forward_fields:")
    if carries_forward_fields:
        for field in carries_forward_fields:
            lines.append(f"  - {field}")
    else:
        lines.append("  []")
    lines.append("forbidden_return_keys:")
    for key in forbidden:
        lines.append(f"  - {key}")
    lines.append("proof_limits:")
    lines.append("  - Brick-owned return-shape data resource only")
    lines.append("  - not source truth")
    lines.append("  - not success judgment")
    lines.append("  - not quality judgment")
    lines.append("  - not Movement authority")
    lines.append("not_proven:")
    lines.append("  - semantic correctness of returned content")
    lines.append("  - complete coverage")
    return "\n".join(lines) + "\n"


def _register_active_template(catalog_path: Path, *, path_ref: str, reason: str) -> bool:
    """APPEND one ``active`` entry to the catalog, preserving comments/structure.

    Idempotent: returns False (no write) when ``path_ref`` is already classified
    anywhere in the catalog. Inserts the new ``- path:`` / ``  reason:`` pair at
    the END of the ``active:`` list (just before ``shared_base:``), preserving the
    file's comments by doing a TARGETED textual insert (not a YAML round-trip that
    would strip comments).
    """

    text = catalog_path.read_text(encoding="utf-8")
    if path_ref in text:
        return False

    lines = text.splitlines()
    active_idx = None
    for index, line in enumerate(lines):
        if line.rstrip() == "  active:":
            active_idx = index
            break
    if active_idx is None:
        raise BrickKindScaffoldError(
            f"catalog has no 'physical_template_classification.active:' list: {catalog_path}"
        )
    # Find the end of the active block: the next line at the SAME 2-space indent
    # that is not an active list entry (e.g. 'shared_base:').
    insert_at = len(lines)
    for index in range(active_idx + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= 2 and not line.lstrip().startswith("- ") and not line.lstrip().startswith("reason:"):
            insert_at = index
            break
    new_entry = [f"    - path: {path_ref}", f"      reason: {reason}"]
    lines[insert_at:insert_at] = new_entry
    catalog_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
