# Wiki Update — Incremental Update Guide

The key principle: **never rewrite what hasn't changed.**
Use git diff to scope the blast radius, then surgically update only affected sections.

---

## Trigger Conditions

Run incremental update when:
- User mentions specific changed files/directories
- User says "merge了一个PR" / "刚改了X模块"
- Automated post-commit hook runs wiki-agent

Do NOT use incremental update when:
- Major architectural change (new modules, module merges, renamed services)
- MANIFEST.json is missing or corrupt
- User says "重新生成" / "全量更新"
→ Use full generation instead

---

## Step 1: Scope the Change

Get the list of changed files. Ask user if not provided, or run:
```bash
git diff --name-only HEAD~1 HEAD
# or for a specific PR:
git diff --name-only main...feature-branch
```

Classify each changed file:

| Changed file type | Impact scope |
|-------------------|-------------|
| Router / controller | `02-interfaces.md` + module section in `01-modules.md` |
| Service / business logic | Module section in `01-modules.md` + `03-data-flow.md` |
| Model / schema | `02-interfaces.md` + `03-data-flow.md` |
| Common/shared module | `04-shared-code.md` + any module that imports it |
| Config / env | `00-overview.md` tech stack section |
| New file in existing module | Module section in `01-modules.md` |
| New directory (new module) | Full generation for that module + update `01-modules.md` |

---

## Step 2: Cross-Reference MANIFEST.json

Load `.wiki/MANIFEST.json`. For each changed file, find all sections that list it in `source_files`.

Those sections need regeneration. Everything else stays untouched.

```python
# Pseudo-logic:
changed_files = ["src/drama/canvas_manager.py", "src/common/auth/service.py"]
sections_to_update = []

for section in manifest["sections"]:
    if any(f in section["source_files"] for f in changed_files):
        sections_to_update.append(section)
```

---

## Step 3: Read Changed Source Files

Read only the files identified as changed. Do not re-read the entire codebase.

For each changed file, understand:
- What changed functionally (new function? changed signature? new import?)
- Does this change the public interface or just internal implementation?
- Does this change affect any cross-cutting concern (auth, errors, data flow)?

---

## Step 4: Rewrite Affected Sections Only

Use the `<!-- SECTION: id -->` markers to locate and replace only the relevant block.

Example: updating the `drama-module` section in `01-modules.md`:

```markdown
<!-- SECTION: drama-module | sources: src/drama/router.py,src/drama/service.py -->
## drama-module
...updated content...
<!-- END SECTION: drama-module -->
```

Leave all other sections untouched.

---

## Step 5: Update MANIFEST.json

For each regenerated section:
1. Recompute `source_hash` from the new file contents
2. Update `last_verified_commit` to current HEAD
3. Remove `stale: true` if it was present

For sections NOT regenerated but whose source files changed indirectly
(e.g., a shared utility was modified but you only updated the shared module's wiki):
1. Add `"stale": true` to those sections
2. Add a note in the wiki file: `> ⚠️ POTENTIALLY STALE: dependency 'common/auth/service.py' was modified. Verify this section still applies.`

---

## Step 6: Staleness Propagation

When a shared/common module changes, all modules that depend on it may be affected.
Use the dependency graph from MANIFEST.json to identify downstream consumers.

Mark them as `stale: true` with a reason:
```json
{
  "wiki_file": ".wiki/01-modules.md",
  "section_id": "drama-module",
  "stale": true,
  "stale_reason": "dependency 'common/auth/service.py' changed at commit abc123"
}
```

This tells the next AI reading the wiki: "verify this before trusting it."

---

## Staleness Decay Rules

These rules prevent wiki rot by proactively flagging risk:

| Condition | Action |
|-----------|--------|
| Source file changed, section not updated | Mark `stale: true` immediately |
| Section not verified in > 20 commits | Add `⚠️ NOT VERIFIED RECENTLY` marker |
| Dependency of this section changed | Mark `stale: true` with reason |
| New file added to module directory | Flag module section for review |
| Interface file changed | Flag all consumers of that interface |

---

## Automated Git Hook (Optional)

Add to `.git/hooks/post-commit`:
```bash
#!/bin/bash
# Auto-update wiki on commit
CHANGED=$(git diff --name-only HEAD~1 HEAD)
if [ -n "$CHANGED" ]; then
  echo "Wiki: checking for stale sections..."
  # Mark stale sections based on changed files
  # Full regeneration of affected sections can be triggered manually
  python3 .wiki/scripts/mark_stale.py "$CHANGED"
fi
```

This doesn't auto-rewrite (that would be too slow), but it auto-marks stale sections
so the next developer opening the project sees accurate freshness indicators.