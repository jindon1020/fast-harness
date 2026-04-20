# Wiki Health Check

Diagnose wiki freshness without regenerating anything.

---

## Step 1: Load MANIFEST.json

Read `.wiki/MANIFEST.json`. If it doesn't exist: wiki is missing, run full generation.

---

## Step 2: Check Each Section

For each section in the manifest:

1. **Read each source file** listed in `source_files`
2. **Recompute hash** of concatenated contents
3. **Compare** to stored `source_hash`

Result classification:
- Hash matches → `FRESH` ✅
- Hash differs → `STALE` ⚠️
- Source file missing (deleted/renamed) → `BROKEN` ❌
- Already marked `stale: true` → `KNOWN_STALE` 🔶

---

## Step 3: Report

Output a health report like:

```
Wiki Health Report
Generated: 2025-11-20 | Last full generation: 2025-11-01 | Commits since: 47

FRESH ✅ (8 sections)
  - 00-overview.md / tech-stack
  - 00-overview.md / entry-points
  - 02-interfaces.md / internal-api-contracts
  ... 

STALE ⚠️ (3 sections — source files changed)
  - 01-modules.md / drama-module
    Changed files: src/drama/canvas_manager.py (47 commits ago)
  - 03-data-flow.md / auth-flow
    Changed files: common/auth/service.py (12 commits ago)
  - 04-shared-code.md / asset-manager
    Changed files: common/asset/service.py, common/asset/models.py (3 commits ago)

BROKEN ❌ (1 section — source file no longer exists)
  - 01-modules.md / old-script-manager
    Missing: src/drama/script_manager.py (likely renamed or deleted)

Recommendation:
  Priority 1: Regenerate 'auth-flow' — auth changes affect all modules
  Priority 2: Regenerate 'drama-module' — 47 commits is a long time
  Priority 3: Fix or remove 'old-script-manager' broken reference
  Low priority: 'asset-manager' only changed 3 commits ago
```

---

## Step 4: Ask User What to Update

Present the stale/broken sections and ask:
- "要全部更新吗？" → run full generation
- "只更新优先级高的" → run incremental update on those sections
- "先不管，只标记一下" → add stale markers to wiki files without regenerating

Don't auto-regenerate without confirmation — regeneration takes time and
the user may want to batch it with other changes.