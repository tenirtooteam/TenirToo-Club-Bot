"""Validation suite for the OKF-style reference bundle (docs/knowledge/).

Enforces the contract in specs/001-okf-docs-graphify/contracts/okf-bundle-contract.md.
Test names are binding (spec SC-003 mutation checks reference them).

PyYAML is intentionally NOT a dependency (see research D6); front matter is parsed
by a small regex-based fallback parser below.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / "docs" / "knowledge"
INDEX_FILE = BUNDLE_DIR / "index.md"
LOG_FILE = BUNDLE_DIR / "log.md"
# PROJECT_LOGIC.md / CONTEXT_PROMPT.md deleted 2026-07-02 (governance cleanup):
# the always-preread core is now RULES.md + AGENTS.md; legacy PL/CP anchors
# resolve via docs/knowledge/rule-map.md (a bundle concept file, so the
# anchor-survival union below covers them automatically).
CORE_FILES = [REPO_ROOT / "RULES.md", REPO_ROOT / "AGENTS.md"]
ANCHOR_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pl_anchors_baseline.txt"

REQUIRED_FRONTMATTER_FIELDS = ("type", "title", "description", "timestamp")
ANCHOR_RE = re.compile(r"PL-\d+(?:\.\d+)*")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _concept_files():
    """All bundle markdown files except the reserved index.md and log.md."""
    if not BUNDLE_DIR.is_dir():
        return []
    return sorted(
        p
        for p in BUNDLE_DIR.rglob("*.md")
        if p.name not in ("index.md", "log.md")
    )


def _parse_frontmatter(text):
    """Minimal YAML front-matter parser (no PyYAML dependency).

    Returns a dict of top-level scalar keys, or None if no front-matter block.
    Supports `key: value` pairs between the leading `---` fences.
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if not m:
        return None
    block = m.group(1)
    data = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            val = val.strip('"').strip("'")
            data[key] = val
    return data


def _all_anchors_in(paths):
    found = set()
    for p in paths:
        if p.is_file():
            found |= set(ANCHOR_RE.findall(p.read_text(encoding="utf-8")))
    return found


def _bundle_paths_referenced_by_core():
    """docs/knowledge/... paths mentioned inside core files."""
    ref_re = re.compile(r"docs/knowledge/[\w\-./]+\.md")
    refs = set()
    for p in CORE_FILES:
        if p.is_file():
            refs |= set(ref_re.findall(p.read_text(encoding="utf-8")))
    return refs


# --------------------------------------------------------------------------- #
# Contract tests
# --------------------------------------------------------------------------- #
def test_frontmatter_required_fields():
    """Every concept file has parseable front matter with non-empty required fields."""
    assert BUNDLE_DIR.is_dir(), f"Bundle directory missing: {BUNDLE_DIR}"
    concept_files = _concept_files()
    assert concept_files, "No concept files found in bundle."
    for cf in concept_files:
        fm = _parse_frontmatter(cf.read_text(encoding="utf-8"))
        assert fm is not None, f"{cf.name}: missing YAML front-matter block."
        for field in REQUIRED_FRONTMATTER_FIELDS:
            assert field in fm and fm[field], (
                f"{cf.name}: front-matter field '{field}' missing or empty."
            )


def test_index_matches_files():
    """index.md and the concept files on disk are in bidirectional agreement."""
    assert INDEX_FILE.is_file(), f"Bundle index missing: {INDEX_FILE}"
    index_text = INDEX_FILE.read_text(encoding="utf-8")
    # Concept files are listed as markdown-link targets: [label](target.md).
    # Plain prose mentions of core files (e.g. `PROJECT_LOGIC.md`) are NOT links
    # and are intentionally excluded. Links that escape the bundle (contain "../",
    # e.g. the RULES.md pointer) reference non-bundle files and are excluded too
    # (feature-002 adaptation: the bundle index may point out to the rulebook).
    raw_links = re.findall(r"\]\(([^)]+\.md)\)", index_text)
    listed = {
        Path(x).name
        for x in raw_links
        if "../" not in x and Path(x).name not in ("index.md", "log.md")
    }
    on_disk = {p.name for p in _concept_files()}
    missing_from_index = on_disk - listed
    dangling_in_index = listed - on_disk
    assert not missing_from_index, f"Concept files not listed in index.md: {missing_from_index}"
    assert not dangling_in_index, f"index.md lists non-existent files: {dangling_in_index}"


def test_pl_anchors_preserved():
    """Every pre-migration PL-x.y anchor resolves in union(core + bundle)."""
    assert ANCHOR_FIXTURE.is_file(), f"Frozen anchor fixture missing: {ANCHOR_FIXTURE}"
    frozen = {
        line.strip()
        for line in ANCHOR_FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    present = _all_anchors_in(CORE_FILES + _concept_files())
    lost = frozen - present
    assert not lost, f"PL anchors lost after migration (not in core or bundle): {sorted(lost)}"


def test_core_bundle_references_resolve():
    """Every docs/knowledge/... path cited by a core file exists on disk."""
    for ref in _bundle_paths_referenced_by_core():
        target = REPO_ROOT / ref
        assert target.is_file(), f"Core file references missing bundle path: {ref}"


def test_log_exists_nonempty():
    """Bundle change log exists and is non-empty."""
    assert LOG_FILE.is_file(), f"Bundle log missing: {LOG_FILE}"
    assert LOG_FILE.read_text(encoding="utf-8").strip(), "log.md is empty."
