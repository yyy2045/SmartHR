# SmartHR RAG/Agent Optimization Progress

## Current Goal

Upgrade SmartHR into a portfolio-grade AI recruitment Agent project with a complete business loop:
knowledge base, jobs, resumes, interviews, reports, RAG evaluation, optional MCP client, and internal Agent skills.

## Execution Decisions

- Keep the Java + Python + Vue architecture.
- Allow major rewrites in the Python AI layer.
- Prioritize business loop over standalone benchmark scores or decorative Agent features.
- Rebuild RAG as a full pipeline with hybrid retrieval, rerank-ready interfaces, source tracing, and Ragas evaluation.
- Add project-internal skills, not Codex Skills.
- Add optional MCP Client support for file/material tools; failures degrade silently to internal RAG.
- Development reset may clear MySQL, Redis, and Chroma.

## Current Worktree Notes

- `smarthr-python/src/services/context_manager.py` already has pre-existing comment/documentation changes; do not overwrite unless directly required.
- `.claude/`, `.playwright-mcp/`, `CLAUDE.md`, upload directories, and this `docs/` directory are untracked at start of execution.

## Progress

- [x] Created this progress/context file.
- [ ] Phase 1: Fix blocking integration and deployment issues.
  - [x] Route frontend interview APIs through Java instead of direct Python calls.
  - [x] Make Java interview service compatible with camelCase Python responses.
  - [x] Preserve Python interview history with interviewer and candidate messages.
  - [x] Fix vector-store metadata argument mismatches.
  - [x] Pass company ID when deleting knowledge documents from Python AI service.
  - [x] Add AI service URL configuration for Docker and templates.
  - [x] Fix Java Docker healthcheck and root nginx Python rewrite.
  - [x] Align Python dependency manifests for current imports.
  - [x] Validation passed: `python -m compileall smarthr-python/src`, `mvn -q -DskipTests package`, `npm run build`.
- [ ] Phase 2: Rebuild the RAG pipeline.
  - [x] Add unified RAG schemas, embedding adapter, BM25 store, and hybrid search pipeline.
  - [x] Add `/api/rag/index` and `/api/rag/search`.
  - [x] Route knowledge document indexing and retrieval through the unified RAG pipeline.
  - [x] Add mock-by-default embedding configuration for API-key-free local validation.
  - [x] Validation passed: `python -m compileall smarthr-python/src`, `mvn -q -DskipTests package`, `npm run build`.
- [ ] Phase 3: Add Ragas evaluation, optional MCP Client hooks, internal skills, and docs.

## Phase 1 Tasks

- Unify Java/Python/frontend interview response contract.
- Route frontend interview operations through Java APIs.
- Fix knowledge-base vector metadata write bugs.
- Fix Java/Python AI service configuration and nginx `/python/` rewrite.
- Fix health checks and dependency manifest drift.
