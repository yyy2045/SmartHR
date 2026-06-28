# SmartHR · 智能招聘平台

> **面向 HR 的多 Agent 智能招聘辅助系统** —— 把"岗位 → 知识库 → 简历 → 匹配 → 面试 → 报告 → RAG 评测"串成一条带证据的闭环。

[![Java](https://img.shields.io/badge/Java-17-ED8B00?logo=openjdk&logoColor=white)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2-6DB33F?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Docker Compose](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED?logo=docker&logoColor=white)](#-快速开始)

---

## ✨ 为什么是 SmartHR

传统 ATS 只做"存和搜",HR 真正难的是**判断这个人行不行、为什么行 / 不行、面试该问什么**。SmartHR 把这条判断链路交给多 Agent + RAG,每一步都给 HR 看得到证据:

- **匹配有依据**:分数、命中技能、缺口、风险点、证据片段,全部回写到候选人档案。
- **面试有锚点**:问题基于岗位 + 简历 + 知识库生成,不靠模板。
- **报告可回溯**:录用建议、能力评分、追问依据都能点回原文片段。
- **评测可量化**:内置本地启发式评测,可切 RAGas 完整模式跑 faithfulness / answer relevancy 等指标。

---

## 🎯 核心能力

| 模块 | 能力 |
| --- | --- |
| **岗位管理** | 结构化维护岗位职责、任职要求、技能标签 |
| **知识库** | 上传 PDF / Word / TXT / MD,解析后进入统一 RAG 索引(支持 BM25 + 向量混合检索) |
| **简历管理** | 上传 PDF / DOCX,自动解析文本与候选人信息 |
| **简历匹配** | 输出匹配分、匹配理由、技能命中、技能缺口、风险点、证据来源 |
| **RAG 面试** | 基于岗位 + 简历 + 匹配证据 + 知识库,LangGraph 多 Agent 生成带依据的问题 |
| **面试报告** | 录用建议、能力评分、风险点、追问依据,全部可回溯到原文 |
| **RAG 评测** | 默认本地启发式快速评测;可切 RAGas + LLM 完整评测(faithfulness / answer relevancy / context precision / context recall) |
| **系统安全(P0)** | 注册角色白名单、JWT 弱密钥启动校验、上传白名单 + 魔数校验、LLM Key 脱敏、Swagger 默认关闭、对外只暴露 80/443 |

---

## 🧱 技术栈

| 层 | 选型 |
| --- | --- |
| **前端** | Vue 3 · Vite 5 · Element Plus · Pinia · Vue Router · ECharts · vue-quill |
| **Java 业务后端** | Spring Boot 3.2 · Spring Security · Spring Data JPA · Spring Data Redis · JJWT 0.12 · SpringDoc OpenAPI |
| **Python AI 服务** | FastAPI · LangChain · **LangGraph**(多 Agent 编排)· RAGas · Sentence-Transformers(BGE) |
| **数据** | MySQL 8 · Redis 7 · **Chroma 0.5**(向量库) |
| **Embedding** | 本地 `bge-base-zh-v1.5`(768 维,通过 volume 挂载,不进镜像) |
| **LLM** | DeepSeek(默认,OpenAI-compatible 接口,可替换) |
| **部署** | Docker Compose · Nginx 反代 · Certbot(HTTPS) |

---

## 🏗️ 架构

```text
                    ┌─────────────────────────────────┐
                    │   宿主机 Nginx :80/:443 (HTTPS) │
                    │   反向代理 + 域名 + Certbot      │
                    └──────────────┬──────────────────┘
                                   │
                       ┌───────────▼───────────┐
                       │  frontend 容器 Nginx  │
                       │  Vue 3 静态文件 + API  │
                       │  反代 (/api → Java)    │
                       └───┬───────────────┬───┘
                           │               │
                ┌──────────▼──────┐   ┌────▼────────────┐
                │  java-backend   │   │  python-backend │  (内网)
                │  :8080          │◄──┤  :8001           │
                │  业务/鉴权/JPA  │   │  RAG/匹配/面试  │
                └─┬──────┬─────┬──┘   └─┬──────┬─────┬──┘
                  │      │     │        │      │     │
                  ▼      ▼     ▼        ▼      ▼     ▼
                MySQL  Redis  Chroma  (共享上述基础设施)
```

**对外只暴露 `80/443`**。MySQL / Redis / Chroma / Java / Python 全部走 Docker 内部网络,不映射公网端口。Python 也不再有 `/uploads/` 静态目录与前端 `/python/` 反代(P0 加固)。

---

## 📁 目录结构

```text
SmartHR/
├── smarthr-frontend/                 # Vue 3 前端 + 前端容器 Nginx
│   └── src/
│       ├── views/                    # auth / dashboard / job / knowledge
│       │                             # resume / interview / report / config
│       ├── api/ · components/ · router/ · stores/ · styles/
│
├── smarthr-java/                     # Spring Boot 业务后端
│   └── src/main/java/com/smarthr/
│       ├── config/                   # SecurityConfig · JwtTokenProvider
│       ├── controller/               # Auth / Job / Resume / Interview / Config …
│       ├── service/                  # 业务服务层
│       └── util/FileUploadValidator  # 上传白名单 + 魔数校验
│
├── smarthr-python/                   # FastAPI AI / RAG 服务
│   └── src/
│       ├── agents/                   # LangGraph 多 Agent:面试官 / 技能评估
│       │                             # 行为分析 / 报告生成 / 编排图
│       ├── services/rag/             # 切分 / 嵌入 / 检索 / 证据 / 评测
│       └── skills/ · tools/          # 工具与技能定义
│
├── init-scripts/schema.sql           # MySQL 初始化
├── models/bge-base-zh-v1.5/         # 本地 Embedding 模型(不进镜像)
├── docs/
│   ├── demo-data/                    # 可直接上传的示例知识库
│   └── IMPLEMENTATION_PROGRESS.md
├── nginx/                            # 前端容器 Nginx 配置
├── docker-compose.yml                # 本地开发 / 演示
├── docker-compose.example.yml        # 生产参考(ACR 镜像)
└── .env.example                      # 环境变量模板
```

---

## 🚀 快速开始

### 1. 准备

- Docker 24+ 与 Docker Compose v2
- 本地 BGE 中文 Embedding 模型放到 `models/bge-base-zh-v1.5/`
- 复制环境变量并填值:

```bash
cp .env.example .env
```

最少需要配置(`.env`):

```env
MYSQL_ROOT_PASSWORD=your_secure_root_password
MYSQL_USER=smarthr
MYSQL_PASSWORD=your_secure_mysql_password
JWT_SECRET=your_secure_jwt_secret_key_min_32_chars
DEEPSEEK_API_KEY=your_deepseek_api_key

EMBEDDING_PROVIDER=local_bge
LOCAL_BGE_MODEL_PATH=/opt/smarthr/models/bge-base-zh-v1.5
ALLOW_MOCK_EMBEDDING=false
EMBEDDING_DIMENSIONS=768
RAGAS_MODE=heuristic
```

> ⚠️ `JWT_SECRET` 必须 ≥32 字节且不能是已知默认值,启动时会 fail-closed 拒绝放行。

### 2. 构建并启动

```bash
docker compose build frontend java-backend python-backend
docker compose up -d
docker compose ps
```

### 3. 健康检查

```bash
curl http://localhost/api/health
curl http://localhost:8001/health/dependencies
```

Python 依赖健康检查应返回:

```json
{ "provider": "local_bge", "loaded": true, "mockAllowed": false, "actualDimensions": 768 }
```

### 4. 打开浏览器

```text
http://localhost
```

---

## 🌐 阿里云单机部署

### 1. 服务器初始化

```bash
mkdir -p /opt/smarthr/init-scripts
mkdir -p /opt/smarthr/models
cd /opt/smarthr
```

上传初始化脚本与 BGE 模型:

```bash
scp ./init-scripts/schema.sql root@<服务器IP>:/opt/smarthr/init-scripts/
scp -r ./models/bge-base-zh-v1.5 root@<服务器IP>:/opt/smarthr/models/
```

### 2. 推送镜像到 ACR(参考)

```bash
REG="<your-registry>.cn-beijing.personal.cr.aliyuncs.com"
NS="<your-namespace>"
TAG="v1"

docker login --username=<ACR 用户名> $REG

docker tag smarthr-frontend:latest       $REG/$NS/smarthr-frontend:$TAG
docker tag smarthr-java-backend:latest   $REG/$NS/smarthr-java-backend:$TAG
docker tag smarthr-python-backend:latest $REG/$NS/smarthr-python-backend:$TAG

docker push $REG/$NS/smarthr-frontend:$TAG
docker push $REG/$NS/smarthr-java-backend:$TAG
docker push $REG/$NS/smarthr-python-backend:$TAG
```

> 国内服务器访问 Docker Hub 不稳时,把基础镜像 `mysql:8` / `redis:7-alpine` / `chromadb/chroma:0.5.0` 也一并 retag 推送。

### 3. 服务器 `docker-compose.yml`

参考仓库根目录的 [`docker-compose.example.yml`](./docker-compose.example.yml),核心原则:

- 所有服务走同一 `smarthr-network`
- MySQL / Redis / Chroma / Java / Python 全部 `expose`(不映射公网)
- 前端只暴露到 `127.0.0.1:8088`,由宿主机 Nginx 提供 HTTPS

```bash
docker compose pull
docker compose up -d
```

### 4. 域名 + HTTPS

```text
smarthr.top      A    <服务器公网IP>
www.smarthr.top  A    <服务器公网IP>
```

宿主机 Nginx 最小示例(完整 HTTPS 配置请用 `certbot --nginx`):

```nginx
server {
    listen 443 ssl;
    server_name smarthr.top www.smarthr.top;

    ssl_certificate     /etc/letsencrypt/live/smarthr.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/smarthr.top/privkey.pem;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📚 演示数据

可直接上传到知识库的样本:

- [`docs/demo-data/ai_interview_question_bank.txt`](./docs/demo-data/ai_interview_question_bank.txt)
- [`docs/demo-data/hr_ai_interview_scoring_guide.txt`](./docs/demo-data/hr_ai_interview_scoring_guide.txt)

上传后:系统配置 → **重建 RAG 索引** → **RAG 评测**。

---

## ✅ 验收路径

```text
1. 注册 / 登录
2. 创建岗位并填写技能标签
3. 上传知识库文档(可用 docs/demo-data 演示数据)
4. 上传简历(PDF / DOCX)
5. 系统配置 → 重建 RAG 索引
6. 执行简历匹配,查看证据片段
7. 从匹配结果进入面试
8. 生成带依据的面试问题
9. 完成面试,查看证据化报告
10. 运行 RAG 评测(本地启发式 / RAGas 完整)
```

---

## 📊 RAG 评测

| 模式 | 触发 | 说明 |
| --- | --- | --- |
| **本地启发式** | `RAGAS_MODE=heuristic`(默认) | 不调用外部 LLM,基于检索命中与文本重叠做快速打分 |
| **完整 RAGas** | 系统配置页选择完整模式 | 调用 OpenAI-compatible LLM 跑 faithfulness / answer relevancy / context precision / context recall |

完整模式可选配置:

```env
RAGAS_MODE=full
RAGAS_LLM_PROVIDER=deepseek
RAGAS_LLM_API_KEY=<your_key>
RAGAS_LLM_BASE_URL=https://api.deepseek.com
RAGAS_LLM_MODEL=deepseek-chat
RAGAS_THRESHOLD=0.70
RAGAS_TIMEOUT_SECONDS=120
```

评测样本: [`smarthr-python/src/services/rag/evaluation_samples.json`](./smarthr-python/src/services/rag/evaluation_samples.json)

---

## 🔒 安全(P0 已加固)

- ✅ **对外暴露面**:删除前端 `/python/` 反代、删除 `/uploads/` 静态目录,Python 仅 Java 内网调用
- ✅ **上传校验**:扩展名白名单 + 文件头魔数(magic bytes)双重校验,阻止脚本伪装成 PDF/DOCX
- ✅ **LLM Key**:`/api/config/llm` 仅 ADMIN 可读写,读接口只返回掩码,写接口收到掩码不覆盖原值
- ✅ **注册越权**:注册角色仅允许 `HR` / `INTERVIEWER`,`ADMIN` 被降级,阻断垂直越权
- ✅ **JWT 弱密钥**:启动 fail-closed,拒绝空 / <32 字节 / 已知默认值的 `JWT_SECRET`
- ✅ **API 文档**:Swagger / Knife4j / OpenAPI 默认 `denyAll`,仅 `app.api-docs.public=true` 时放行
- ✅ **CORS**:Python 默认不放行跨域,`PYTHON_CORS_ORIGINS` 显式配置

部署侧请同样遵守:

- 不要提交 `.env`、API Key、数据库密码、证书私钥
- 生产服务器只开放 `80/443/22`
- BGE 模型走 volume 挂载,不要打进镜像
- 2 核 4G 建议开启 ≥2G swap

---

## 🛠️ 常用检查

```bash
docker compose ps
curl -I http://127.0.0.1:8088
docker compose exec python-backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health/dependencies').read().decode())"
```

---

## 📄 License

[MIT](./LICENSE)
