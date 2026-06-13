# SmartHR 最终收尾进度

## Current Goal

将 SmartHR 收尾到可演示的 HR 闭环产品：岗位 -> 知识库 -> 简历 -> 匹配 -> 面试 -> 报告 -> RAG 评测。

## Execution Decisions

- 保持 Java + Python + Vue 架构。
- 部署由用户从零手动执行；仓库内不保留本轮新增的生产 Compose/Nginx/证书占位模板。
- 目标部署环境仍按阿里云轻量应用服务器/单机 Docker Compose，最低 2 核 4G 进行运行约束设计。
- embedding 固定使用宿主机挂载的本地 `/opt/smarthr/models/bge-base-zh-v1.5`。
- 2 核 4G 不常驻神经 reranker，使用 hybrid retrieval + embedding 相似度轻量排序。
- mock embedding 只允许开发模式；演示验收应显式设置 `ALLOW_MOCK_EMBEDDING=false`。
- 不做 MCP/skill 集成；已有内部入口默认隐藏，仅显式开启 `EXPOSE_INTERNAL_RAG_TOOLS=true` 时可访问。

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
- [x] Phase 5: Runtime baseline without keeping deployment artifacts.
  - [x] Removed the added `docker-compose.aliyun.yml`, `nginx/nginx.aliyun.conf`, and certificate placeholder at user request.
  - [x] Deployment will be performed manually by the user from scratch.
  - [x] Fixed Java Dockerfile JVM option placement and default heap limit.
  - [x] Added local BGE embedding provider, model health check, and `/health/dependencies` / `/api/health/dependencies`.
  - [x] Added `sentence-transformers` dependency for local `bge-base-zh-v1.5`.
  - [x] Hid MCP/internal skill HTTP entrypoints by default.
  - [x] Extended RAG search response with `evidence[]`, `retrievalScores`, and `rankScores`.
  - [x] Routed resume/job indexing through the unified RAG pipeline and returned evidence-backed match fields.
  - [x] Validation passed before deployment artifact removal: `python -m compileall smarthr-python/src`, `mvn -q -DskipTests package`, `npm.cmd run build`.
- [ ] Phase 6: Application evidence loop closeout.
  - [x] Added business-facing RAG evidence service for job, resume, knowledge and interview evidence.
  - [x] Added batch `/api/rag/rebuild` index rebuild endpoint.
  - [x] Added Java `POST /api/config/rag-index/rebuild` to rebuild job/resume indexes and trigger knowledge reindexing.
  - [x] Fixed knowledge reindexing to rebuild chunks from stored preview content and sync status/chunk IDs back to MySQL.
  - [x] Made BM25 and Chroma reindex delete old chunks by source before rewriting.
  - [x] Added RAG-driven interview evidence: every AI question carries `traceId`, `competency`, and `basisEvidence[]`.
  - [x] Indexed interview Q/A turns as `interview` evidence for report reuse.
  - [x] Extended reports with `risks`, `evidence`, `conclusionEvidence`, and `followUpBasis`.
  - [x] Added manually maintained RAG evaluation samples in `evaluation_samples.json`.
  - [x] Added frontend controls for manual RAG index rebuild and evidence display in matching, interview and report pages.
  - [x] Validation passed: `python -m compileall smarthr-python/src`, `mvn -q -DskipTests package`, `npm.cmd run build`.

## Phase 1 Tasks

- Unify Java/Python/frontend interview response contract.
- Route frontend interview operations through Java APIs.
- Fix knowledge-base vector metadata write bugs.
- Fix Java/Python AI service configuration and nginx `/python/` rewrite.
- Fix health checks and dependency manifest drift.

## Phase 3 Notes

- RAG evaluation should run as `RAGAS_MODE=heuristic` on 2 核 4G demo servers unless an external evaluator model is configured.
- Java exposes `POST /api/config/rag-evaluation/run` and `GET /api/config/rag-evaluation`; successful runs are saved to `rag_evaluation_runs`.
- Internal Agent skill and MCP HTTP routes are hidden by default and are not part of the final demo surface.

## Phase 4 Notes

- Local Docker uses the ignored `docker-compose.yml`; the current local copy maps Docker MySQL to host port `3307` because the machine's native MySQL service still owns `3306`.
- The Docker MySQL/Redis/Chroma volumes were reset during validation so the database could be initialized with the current local `.env` credentials.
- Do not print expanded `docker compose config` output because it includes `.env` secrets.

## Phase 5 Notes

- Deployment files added earlier were removed at user request.
- Local BGE model directory still must exist at `/opt/smarthr/models/bge-base-zh-v1.5` in the environment where Python runs.
- Final manual验收 requires `/python/health/dependencies` to report local BGE loaded and `actualDimensions=768`.
