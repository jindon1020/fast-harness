# Wiki Generation — Full Generation Guide

## Pre-flight

Before scanning any code, confirm with user:
- Project root directory path
- Any directories to exclude (e.g. `node_modules`, `dist`, `migrations`)
- Primary language/framework (if not obvious from files)
- Whether a `.wiki/` already exists (if yes, switch to update mode)

---

## Step 1: Structure Scan

Read these files first (do not skip):
```
- Directory tree (2 levels deep)
- package.json / pyproject.toml / pom.xml / go.mod (whatever applies)
- Main entry point files (main.py, app.py, index.ts, Application.java, etc.)
- Router/controller files (they reveal the API surface)
- Config files (.env.example, config/, settings.py)
- Existing README if present
```

Output a mental model:
- What type of system is this? (API server, CLI tool, worker, frontend, monorepo...)
- What is the primary tech stack?
- What are the top-level modules/packages?
- Where does execution start?

---

## Step 2: Dependency Graph

Read import/require statements across the codebase to build a module dependency map.

Focus on:
- Which modules import which other modules (internal deps only, ignore stdlib/vendor)
- Which modules are imported by many others → these are "core/shared" modules
- Which modules import nothing internal → these are "leaf" modules (pure domain logic)
- Circular dependencies (flag these explicitly)

Produce a mental graph like:
```
drama-module → [common/auth, common/asset, common/team]
marketing-module → [common/auth, common/asset, common/workflow]
common/auth → [db/models]
common/asset → [db/models, storage/client]
```

This graph drives everything else. Don't skip it.

---

## Step 3: Module Deep-Dives

For each top-level module identified in Step 2, read:
- The module's own router/controller files
- Its service layer files
- Its model/schema definitions
- Any module-specific config or constants

For each module, capture:
1. **Single-sentence responsibility** — what does this module own?
2. **Public interface** — what endpoints/functions does it expose?
3. **Dependencies** — what does it need from other modules?
4. **Key business logic** — any non-obvious decisions or rules
5. **Data it owns** — which DB tables/collections belong to this module?

---

## Step 4: Cross-Cutting Concerns

Scan for patterns that appear across multiple modules:

- **Authentication/Authorization**: how is identity verified and permissions checked?
- **Error handling**: is there a common error format? global exception handlers?
- **Logging**: what gets logged, in what format?
- **Validation**: where does input validation happen (middleware vs service layer)?
- **Shared utilities**: what lives in utils/ or helpers/ and is widely used?
- **External integrations**: third-party APIs, queues, storage — how are they abstracted?

---

## Step 5: Write Wiki Files

Write all files to `.wiki/`. Use the templates in `references/templates/`.

### Writing rules (critical for AI consumption accuracy):

1. **Every claim must cite a source file**
   ```markdown
   <!-- Good -->
   Auth token validation happens in `common/auth/middleware.py:validate_token()`.
   
   <!-- Bad -->
   Auth token validation happens in the middleware layer.
   ```

2. **Use explicit section markers** so incremental updates can target sections:
   ```markdown
   <!-- SECTION: auth-flow | sources: common/auth/middleware.py,common/auth/service.py -->
   ... content ...
   <!-- END SECTION: auth-flow -->
   ```

3. **State boundaries explicitly** — what a module does NOT do is as important as what it does:
   ```markdown
   ## drama-module
   **Owns:** Canvas management, interactive sessions, approval workflows
   **Does NOT own:** User identity, asset storage, billing — delegates to common-module
   ```

4. **Flag uncertainty** — if you inferred something, say so:
   ```markdown
   > ⚠️ INFERRED: This appears to handle rate limiting based on the middleware order,
   > but no explicit rate limit config was found. Verify with team.
   ```

5. **Keep each file under 300 lines** — if a module is complex, give it its own file (`06-drama-module.md`) and link from `01-modules.md`.

---

## Step 6: Write MANIFEST.json

```json
{
  "generated_at": "2025-11-20T10:00:00Z",
  "generator": "code-wiki-gen v1",
  "sections": [
    {
      "wiki_file": ".wiki/00-overview.md",
      "section_id": "tech-stack",
      "source_files": ["package.json", "src/main.py"],
      "source_hash": "a1b2c3d4",
      "last_verified_commit": "abc123"
    },
    {
      "wiki_file": ".wiki/01-modules.md",
      "section_id": "drama-module",
      "source_files": [
        "src/drama/router.py",
        "src/drama/service.py",
        "src/drama/canvas_manager.py"
      ],
      "source_hash": "e5f6g7h8",
      "last_verified_commit": "abc123"
    }
  ]
}
```

`source_hash` is an MD5/SHA of the concatenated content of all source files for that section. Used later to detect staleness without needing git.

---

## Step 7: Write CLAUDE.md

Create or update `CLAUDE.md` in the project root:

```markdown
## Code Knowledge Base

This project has an AI-maintained wiki in `.wiki/`. Read relevant files before
writing or modifying any code.

### Reading order for common tasks:

**Starting a new feature:**
1. `.wiki/00-overview.md` — understand system boundaries
2. `.wiki/01-modules.md` — find which module owns the feature area
3. `.wiki/02-interfaces.md` — check existing internal contracts

**Fixing a bug:**
1. `.wiki/03-data-flow.md` — trace the request path
2. `.wiki/05-patterns.md` — understand error handling conventions

**Touching shared/common code:**
1. `.wiki/04-shared-code.md` — understand what belongs here vs domain modules
2. `.wiki/01-modules.md` — understand who depends on what you're changing

### Wiki freshness
Check `.wiki/MANIFEST.json` for `stale: true` markers before trusting a section.
Stale sections are marked with ⚠️ in the wiki files themselves.
```