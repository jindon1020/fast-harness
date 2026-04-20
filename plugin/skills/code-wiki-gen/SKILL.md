---
name: code-wiki-gen
description: Generate a comprehensive, AI-optimized code knowledge base (.wiki/) for any local codebase. Use this skill whenever the user wants to: generate a code wiki, create a project knowledge base for AI coding, document an existing codebase, set up long-term AI memory for a project, update or refresh an existing wiki, or says things like "生成代码知识库", "给项目建wiki", "让AI理解我的代码", "更新wiki", "代码知识库腐坏了". Also trigger when the user mentions "harness + wiki", "AI context files", "CLAUDE.md + wiki", or wants to improve AI code generation accuracy on an existing project.
---

# Code Wiki Generator

Generate a structured, source-linked, AI-optimized code knowledge base from a local codebase. Inspired by Google Code Wiki's knowledge graph approach and DeepWiki's RAG architecture — adapted to run entirely inside Claude Code with no external dependencies.

The output is a `.wiki/` directory in the project root. Claude Code, Cursor, and other AI tools automatically read these files as project context before generating code.

---

## Core Design Principles

**From Code Wiki:**
- Knowledge graph first: understand relationships before writing docs
- Source-linked: every claim anchors to a specific file/line
- Incremental updates: only regenerate what changed, not the whole wiki

**From DeepWiki:**
- Layered analysis: structure → dependencies → modules → cross-cutting
- Machine-readable format: AI tools consume this, not humans primarily
- Manifest-tracked: know exactly what generated what, enables safe updates

**Anti-rot strategy:**
- `MANIFEST.json` maps every wiki section to its source files + git hash
- Staleness markers automatically applied when source files change
- Surgical update mode: `git diff` tells you exactly what to regenerate

---

## When to Run What

| Situation | Command to tell Claude |
|-----------|----------------------|
| New project, first wiki | "为这个项目生成完整wiki" |
| After a big refactor | "重新生成wiki" |
| After a small PR merge | "更新wiki，变更文件: src/auth/" |
| Wiki feels stale | "检查wiki健康度" |
| Before starting a feature | "wiki是否覆盖了 X 模块" |

---

## Phase 1 — Full Generation

Read the reference file before starting:
→ `references/generation.md`

High-level steps:
1. **Structure scan** — directory tree, entry points, config, tech stack
2. **Dependency graph** — import chains, module boundaries, shared code
3. **Module deep-dives** — per-module: responsibility, interfaces, key logic
4. **Cross-cutting concerns** — auth, error handling, data flow, shared patterns
5. **Write wiki files** — structured markdown + MANIFEST.json
6. **Write CLAUDE.md** — instruct AI tools to read the wiki

Expected output: `.wiki/` directory with 5–12 files depending on project size.

---

## Phase 2 — Incremental Update

Read the reference file before starting:
→ `references/update.md`

Triggered when: code changed but wiki exists. Use git diff to scope changes, then surgically update only affected sections. Never rewrite the whole wiki for a small change.

---

## Phase 3 — Health Check

Read the reference file before starting:
→ `references/health.md`

Checks MANIFEST.json against current git hashes. Reports stale sections. User decides what to regenerate.

---

## Output Structure

```
project-root/
├── CLAUDE.md                    ← tells AI tools to read .wiki/
├── .wiki/
│   ├── MANIFEST.json            ← source-to-doc mapping + git hashes
│   ├── 00-overview.md           ← architecture, tech stack, entry points
│   ├── 01-modules.md            ← every module: purpose + boundaries
│   ├── 02-interfaces.md         ← internal APIs, contracts, shared types
│   ├── 03-data-flow.md          ← request lifecycle, data transformations
│   ├── 04-shared-code.md        ← what's in common modules and why
│   ├── 05-patterns.md           ← conventions, error handling, auth patterns
│   └── [06-domain-X.md ...]     ← one file per complex domain if needed
```

See `references/templates/` for the exact format of each file.