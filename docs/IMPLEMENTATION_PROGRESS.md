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
- [x] Phase 3: Add Ragas evaluation, optional MCP Client hooks, internal skills, and docs.
  - [x] Add sample-based RAG evaluation service with Ragas-first and local heuristic fallback.
  - [x] Add `/api/rag/evaluations/run` and `/api/rag/evaluations/latest`.
  - [x] Add optional MCP HTTP gateway client with silent fallback.
  - [x] Add project-internal recruitment skills and internal tool registry.
  - [x] Persist Java-triggered RAG evaluation runs in MySQL.
  - [x] Add compact RAG evaluation block to the System Config page.
  - [x] Validation passed: `python -m compileall smarthr-python/src`, `mvn -q -DskipTests package`, `npm run build`.
- [x] Phase 4: Make local Docker build runnable.
  - [x] Add China-friendly apt and PyPI mirror defaults to the Python Dockerfile.
  - [x] Add Python build tools for `chroma-hnswlib` on Python 3.12.
  - [x] Pin `datasets`, `fsspec`, and `numpy` to versions compatible with Ragas and Chroma.
  - [x] Local Docker validation passed: all six compose services are running and healthy.
  - [x] Frontend `http://localhost`, Java `http://localhost:8080/api/health`, Python `http://localhost:8001/health`, and Nginx `/api/health` checks passed.

## Phase 1 Tasks

- Unify Java/Python/frontend interview response contract.
- Route frontend interview operations through Java APIs.
- Fix knowledge-base vector metadata write bugs.
- Fix Java/Python AI service configuration and nginx `/python/` rewrite.
- Fix health checks and dependency manifest drift.

## Phase 3 Notes

- RAG evaluation defaults to `RAGAS_MODE=auto`: it uses Ragas only when dependencies and model configuration are available, otherwise it returns deterministic local metrics so the demo can run without API keys.
- Java exposes `POST /api/config/rag-evaluation/run` and `GET /api/config/rag-evaluation`; successful runs are saved to `rag_evaluation_runs`.
- Internal Agent skills are exposed under `/api/rag/skills` and `/api/rag/skills/call`.
- MCP is optional through `MCP_ENABLED`, `MCP_GATEWAY_URL`, and `MCP_TIMEOUT_SECONDS`; disabled or failed MCP calls fall back to internal tools.

## Phase 4 Notes

- Local Docker uses the ignored `docker-compose.yml`; the current local copy maps Docker MySQL to host port `3307` because the machine's native MySQL service still owns `3306`.
- The Docker MySQL/Redis/Chroma volumes were reset during validation so the database could be initialized with the current local `.env` credentials.
- Do not print expanded `docker compose config` output because it includes `.env` secrets.
