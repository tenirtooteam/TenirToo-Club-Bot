"""Governance consolidation validation suite (feature 002).

Enforces specs/002-governance-consolidation/contracts/governance-contract.md.
Test names are binding (SC-006 mutation checks reference them).

No PyYAML dependency; plain-text/regex parsing only.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "RULES.md"
RULE_MAP = REPO / "docs" / "knowledge" / "rule-map.md"
AGENTS = REPO / "AGENTS.md"
CONSTITUTION = REPO / ".specify" / "memory" / "constitution.md"
INVENTORY = REPO / "tests" / "fixtures" / "rules_inventory_baseline.txt"
DISPOSITIONS = REPO / "tests" / "fixtures" / "imperative_dispositions.txt"
SHIMS = [REPO / "CLAUDE.md", REPO / "GEMINI.md"]
# PROJECT_LOGIC.md / CONTEXT_PROMPT.md deleted 2026-07-02: legacy anchors resolve
# via docs/knowledge/rule-map.md, so the duplicate-text scan covers only the two
# living governance files.
GOV_TEXT_FILES = [RULES, AGENTS]

RULE_ID_RE = re.compile(r"\bR-[A-Z]{2,4}-\d+\b")
LEGACY_ANCHOR_RE = re.compile(r"\b(?:PL|CP)-\d+(?:\.\d+)*\b")
IMPERATIVE_RE = re.compile(r"\bMUST\b|prohibited|forbidden|\bnever\b|strictly", re.IGNORECASE)


def _read(p):
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _rule_ids(text):
    return RULE_ID_RE.findall(text)


# --------------------------------------------------------------------------- #
def test_rule_ids_unique():
    assert RULES.is_file(), "RULES.md missing."
    text = RULES.read_text(encoding="utf-8")
    # An ID "definition" is a heading or list item that starts a rule entry.
    defs = re.findall(r"^\s*(?:#{2,4}\s*|[-*]\s*)(R-[A-Z]{2,4}-\d+)\b", text, re.MULTILINE)
    assert defs, "No rule entries found in RULES.md."
    dupes = {i for i in defs if defs.count(i) > 1}
    assert not dupes, f"Duplicate rule IDs defined: {sorted(dupes)}"


def test_no_duplicate_rule_text():
    """No >=20-word shingle repeats across governance files (single source of truth)."""
    shingles = {}
    collisions = []
    for f in GOV_TEXT_FILES:
        text = _read(f)
        # strip code/citation noise; work on prose words
        words = re.findall(r"[A-Za-z][A-Za-z_]+", text)
        for i in range(len(words) - 19):
            key = " ".join(w.lower() for w in words[i:i + 20])
            if key in shingles and shingles[key] != f.name:
                collisions.append((shingles[key], f.name, key[:60]))
            else:
                shingles.setdefault(key, f.name)
    assert not collisions, (
        "Duplicated >=20-word rule text across governance files: "
        + "; ".join(f"{a}<->{b}: '{s}...'" for a, b, s in collisions[:5])
    )


def test_rule_map_complete():
    """Every frozen legacy anchor resolves to an R-ID or a bundle file via rule-map.md."""
    assert RULE_MAP.is_file(), "docs/knowledge/rule-map.md missing."
    assert INVENTORY.is_file(), "frozen inventory fixture missing."
    map_text = RULE_MAP.read_text(encoding="utf-8")
    mapped = set(LEGACY_ANCHOR_RE.findall(map_text))
    frozen = set()
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        tag = line.split("\t", 1)[0]
        m = LEGACY_ANCHOR_RE.fullmatch(tag)
        if m:
            frozen.add(tag)
    missing = frozen - mapped
    assert not missing, f"Legacy anchors not covered by rule-map.md: {sorted(missing)[:15]}"


def test_tier_b_enforcement_exists():
    """Every Tier-B 'Enforced by' pointer names a mechanism that exists on disk/config."""
    text = _read(RULES)
    if not text:
        raise AssertionError("RULES.md missing.")
    # Lines declaring an enforcement mechanism after 'Enforced by' (tolerate markdown bold/colon)
    pointers = re.findall(r"Enforced by\**\s*:?\s*([^\n(]+)", text)
    assert pointers, "No Tier-B 'Enforced by' pointers found (expected >=15 demotions)."
    known_files = {
        "semgrep-rules.yaml", ".importlinter", ".ruff.toml", "docker-compose.yml",
        "local_scripts/prompt_linter.py",
    }
    for p in pointers:
        tokens = re.findall(r"[\w./\-]+", p)
        # at least one token must reference a real file OR a pytest test module OR a named tool
        ok = any(
            (REPO / t).exists()
            or t in known_files
            or t.startswith("test_")
            or t in {"semgrep", "import-linter", "ruff", "pytest", "AST", "FK", "init_db"}
            for t in tokens
        )
        assert ok, f"Tier-B enforcement pointer references nothing real: '{p.strip()}'"


def test_shims_are_pure():
    """CLAUDE.md / GEMINI.md are pointer-only: no imperative rule lines."""
    for shim in SHIMS:
        text = _read(shim)
        if not text:
            continue
        for line in text.splitlines():
            if line.strip().startswith(("@", ">", "#", "<!--")):
                continue
            assert not IMPERATIVE_RE.search(line), (
                f"{shim.name} contains normative content (must be a pure shim): '{line.strip()[:70]}'"
            )


def test_constitution_filled():
    """.specify/memory/constitution.md has no template placeholders."""
    text = _read(CONSTITUTION)
    assert text, "constitution.md missing."
    placeholders = re.findall(r"\[[A-Z_]+(?:_NAME|_DESCRIPTION|_CONTENT|_RULES|_VERSION|_DATE)?\]", text)
    assert not placeholders, f"constitution.md still has template placeholders: {set(placeholders)}"


def _rule_map_rows():
    """Parse docs/knowledge/rule-map.md's '| anchor | target |' table into a dict."""
    text = _read(RULE_MAP)
    rows = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*((?:PL|CP)-\d+(?:\.\d+)*)\s*\|\s*([^|]+?)\s*\|\s*$", line)
        if m:
            rows[m.group(1)] = m.group(2).strip()
    return rows


def _dispositions():
    """Parse tests/fixtures/imperative_dispositions.txt: anchor -> (verdict, justification)."""
    text = _read(DISPOSITIONS)
    out = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def test_imperatives_map_to_rules():
    """Every IMP-flagged legacy anchor resolves to a real R-ID, or is dispositioned.

    Content-level retention guard (feature 003, audit F-1/F-4): rule-map completeness
    (test_rule_map_complete) only proves an anchor has SOME row; it does not prove the
    row target actually carries the rule's content. This test closes that gap: an
    imperative anchor's target must be a rule ID defined in RULES.md, or the anchor
    must be explicitly dispositioned as 'descriptive'/'retired' in the curated
    overrides file (tests/fixtures/imperative_dispositions.txt) — never silently
    left pointing at a bundle/description file.
    """
    assert INVENTORY.is_file(), "frozen inventory fixture missing."
    assert RULE_MAP.is_file(), "docs/knowledge/rule-map.md missing."

    imperative_anchors = []
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1] == "IMP":
            imperative_anchors.append(parts[0])
    assert imperative_anchors, "No IMP-flagged anchors found in frozen inventory."

    map_rows = _rule_map_rows()
    dispositions = _dispositions()
    defined_rule_ids = set(re.findall(r"^### (R-[A-Z]{2,4}-\d+)\b", _read(RULES), re.MULTILINE))

    unresolved = []
    for anchor in imperative_anchors:
        target = map_rows.get(anchor)
        if target is None:
            unresolved.append(f"{anchor}: no rule-map row")
            continue
        rid_match = re.match(r"^(R-[A-Z]{2,4}-\d+)\b", target)
        if rid_match:
            if rid_match.group(1) not in defined_rule_ids:
                unresolved.append(f"{anchor}: maps to undefined {rid_match.group(1)}")
            continue
        verdict = dispositions.get(anchor)
        if verdict not in ("descriptive", "retired"):
            unresolved.append(f"{anchor}: target '{target}' is not an R-ID and has no disposition")

    assert not unresolved, (
        "Imperative anchors without a rule-ID resolution or curated disposition:\n  "
        + "\n  ".join(unresolved)
    )

    # Map hygiene: zero rows may point at the generic bundle index (a fallback
    # artifact of the 002 generator, not a real content destination).
    index_rows = [a for a, t in map_rows.items() if t == "docs/knowledge/index.md"]
    assert not index_rows, f"rule-map.md rows still fall back to index.md: {sorted(index_rows)}"
