# SmartHR - 智能招聘平台

SmartHR 是一个面向 HR 的智能招聘辅助系统，覆盖岗位、知识库、简历、匹配、面试、报告和 RAG 评测的闭环流程。

当前交付目标是单机 Docker Compose 演示部署：Java 负责业务 API，Python 负责 AI/RAG 能力，Vue 前端由 Nginx 托管，MySQL/Redis/Chroma 作为数据与检索基础设施。

## 核心能力

- 岗位管理：结构化维护岗位职责、任职要求和技能标签。
- 知识库：上传 PDF、Word、TXT、MD 文档，解析后进入统一 RAG 索引。
- 简历管理：上传简历、解析文本、索引候选人信息。
- 简历匹配：输出匹配分、匹配理由、技能命中、技能缺口、风险点和证据来源。
- RAG 面试：基于岗位、简历、匹配证据和知识库生成带依据的问题。
- 面试报告：输出录用建议、能力评分、风险点、追问依据和可回溯证据。
- RAG 评测：支持本地启发式快速评测，以及可选的 RAGas + LLM 完整评测。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Vue 3, Vite, Element Plus, Nginx |
| Java 后端 | Spring Boot 3.2, Spring Security, JWT, MyBatis/JPA |
| Python AI 服务 | FastAPI, LangChain, LangGraph, RAGas |
| 数据库 | MySQL 8 |
| 缓存 | Redis 7 |
| 向量库 | Chroma 0.5 |
| Embedding | 本地 `bge-base-zh-v1.5` |
| 部署 | Docker Compose, Nginx, Certbot |

## 架构

```text
浏览器
  -> 宿主机 Nginx: HTTPS / 域名 / 反向代理
  -> frontend 容器 Nginx: Vue 静态文件 / API 代理
  -> java-backend:8080: 业务 API、鉴权、数据持久化
  -> python-backend:8001: RAG、简历匹配、面试生成、评测
  -> mysql / redis / chroma
```

生产部署中只需要公网暴露 `80/443`。MySQL、Redis、Chroma、Java、Python 均通过 Docker 内部网络访问，不应直接暴露到公网。

## 目录结构

```text
SmartHR/
  smarthr-frontend/       Vue 前端和前端容器 Nginx 配置
  smarthr-java/           Spring Boot 业务后端
  smarthr-python/         FastAPI AI/RAG 服务
  init-scripts/           MySQL 初始化脚本
  docs/demo-data/         可上传的演示知识库文件
  docs/                   交付进度和项目文档
  docker-compose.yml      本地开发/演示 Compose
```

## 本地运行

准备本地 BGE 模型目录：

```text
models/bge-base-zh-v1.5
```

复制并配置环境变量：

```powershell
Copy-Item .env.example .env
```

至少配置：

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

构建并启动：

```powershell
docker compose build frontend java-backend python-backend
docker compose up -d
docker compose ps
```

健康检查：

```powershell
Invoke-RestMethod http://localhost/api/health
Invoke-RestMethod http://localhost:8001/health/dependencies
```

Python 依赖健康检查应看到：

```text
provider=local_bge
loaded=true
mockAllowed=false
actualDimensions=768
```

本地访问：

```text
http://localhost
```

## 镜像推送到阿里云 ACR

本地构建完成后，给镜像打阿里云 ACR 标签并推送。下面以个人版 ACR 为例，实际地址以控制台为准：

```powershell
$REG="crpi-xxxx.cn-beijing.personal.cr.aliyuncs.com"
$NS="your-namespace"
$TAG="v1"

docker login --username=你的阿里云镜像仓库用户名 $REG

docker tag smarthr-frontend:latest $REG/$NS/smarthr-frontend:$TAG
docker tag smarthr-java-backend:latest $REG/$NS/smarthr-java-backend:$TAG
docker tag smarthr-python-backend:latest $REG/$NS/smarthr-python-backend:$TAG

docker push $REG/$NS/smarthr-frontend:$TAG
docker push $REG/$NS/smarthr-java-backend:$TAG
docker push $REG/$NS/smarthr-python-backend:$TAG
```

如果服务器访问 Docker Hub 不稳定，建议把基础镜像也转推到 ACR：

```powershell
docker pull mysql:8
docker pull redis:7-alpine
docker pull chromadb/chroma:0.5.0

docker tag mysql:8 $REG/$NS/mysql:8
docker tag redis:7-alpine $REG/$NS/redis:7-alpine
docker tag chromadb/chroma:0.5.0 $REG/$NS/chroma:0.5.0

docker push $REG/$NS/mysql:8
docker push $REG/$NS/redis:7-alpine
docker push $REG/$NS/chroma:0.5.0
```

## 阿里云单机部署

服务器准备目录：

```bash
mkdir -p /opt/smarthr/init-scripts
mkdir -p /opt/smarthr/models
cd /opt/smarthr
```

上传初始化脚本和 BGE 模型：

```powershell
scp .\init-scripts\schema.sql root@服务器IP:/opt/smarthr/init-scripts/schema.sql
scp -r .\models\bge-base-zh-v1.5 root@服务器IP:/opt/smarthr/models/
```

服务器 `.env` 示例：

```env
MYSQL_ROOT_PASSWORD=换成强密码
MYSQL_DATABASE=smarthr
MYSQL_USER=smarthr
MYSQL_PASSWORD=换成强密码

JWT_SECRET=至少32位随机字符串
JWT_EXPIRATION=86400000

DEEPSEEK_API_KEY=你的DeepSeekKey
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

EMBEDDING_PROVIDER=local_bge
LOCAL_BGE_MODEL_PATH=/opt/smarthr/models/bge-base-zh-v1.5
ALLOW_MOCK_EMBEDDING=false
EMBEDDING_DIMENSIONS=768

RAGAS_MODE=heuristic
RAGAS_THRESHOLD=0.70
```

服务器 `docker-compose.yml` 使用 ACR 镜像，建议前端只暴露到本机端口，再由宿主机 Nginx 提供 HTTPS：

```yaml
services:
  mysql:
    image: registry.example.com/namespace/mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: smarthr
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    networks:
      - smarthr-network

  redis:
    image: registry.example.com/namespace/redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - smarthr-network

  chroma:
    image: registry.example.com/namespace/chroma:0.5.0
    platform: linux/amd64
    volumes:
      - chroma_data:/chroma/chroma
    networks:
      - smarthr-network

  java-backend:
    image: registry.example.com/namespace/smarthr-java-backend:v1
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/smarthr?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
      SPRING_DATASOURCE_USERNAME: ${MYSQL_USER}
      SPRING_DATASOURCE_PASSWORD: ${MYSQL_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      AI_SERVICE_URL: http://python-backend:8001
      JWT_SECRET: ${JWT_SECRET}
      JWT_EXPIRATION: ${JWT_EXPIRATION}
      JAVA_TOOL_OPTIONS: -Xms256m -Xmx768m
    depends_on:
      - mysql
      - redis
    networks:
      - smarthr-network

  python-backend:
    image: registry.example.com/namespace/smarthr-python-backend:v1
    environment:
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${MYSQL_USER}
      DB_PASSWORD: ${MYSQL_PASSWORD}
      DB_NAME: smarthr
      REDIS_HOST: redis
      REDIS_PORT: 6379
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      JAVA_BACKEND_URL: http://java-backend:8080
      ENVIRONMENT: production
      EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER}
      LOCAL_BGE_MODEL_PATH: ${LOCAL_BGE_MODEL_PATH}
      ALLOW_MOCK_EMBEDDING: ${ALLOW_MOCK_EMBEDDING}
      EMBEDDING_DIMENSIONS: ${EMBEDDING_DIMENSIONS}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      DEEPSEEK_BASE_URL: ${DEEPSEEK_BASE_URL}
      DEEPSEEK_MODEL: ${DEEPSEEK_MODEL}
      RAGAS_MODE: ${RAGAS_MODE}
      RAGAS_THRESHOLD: ${RAGAS_THRESHOLD}
    volumes:
      - /opt/smarthr/models/bge-base-zh-v1.5:/opt/smarthr/models/bge-base-zh-v1.5:ro
    depends_on:
      - mysql
      - redis
      - chroma
    networks:
      - smarthr-network

  frontend:
    image: registry.example.com/namespace/smarthr-frontend:v1
    ports:
      - "127.0.0.1:8088:80"
    depends_on:
      - java-backend
      - python-backend
    networks:
      - smarthr-network

volumes:
  mysql_data:
  redis_data:
  chroma_data:

networks:
  smarthr-network:
    driver: bridge
```

启动：

```bash
docker login --username=你的阿里云镜像仓库用户名 registry.example.com
docker compose pull
docker compose up -d
docker compose ps
```

## 域名和 HTTPS

DNS 添加 A 记录到服务器公网 IP：

```text
smarthr.top      A    服务器公网IP
www.smarthr.top  A    服务器公网IP
```

宿主机 Nginx 示例：

```nginx
server {
    listen 80;
    server_name smarthr.top www.smarthr.top;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name smarthr.top www.smarthr.top;

    ssl_certificate /etc/letsencrypt/live/smarthr.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/smarthr.top/privkey.pem;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

证书申请：

```bash
apt install -y nginx certbot python3-certbot-nginx
certbot --nginx -d smarthr.top -d www.smarthr.top
nginx -t
systemctl reload nginx
```

## 演示数据

可上传的知识库样本在：

```text
docs/demo-data/ai_interview_question_bank.txt
docs/demo-data/hr_ai_interview_scoring_guide.txt
```

上传后进入系统配置页，先执行 RAG 索引重建，再运行 RAG 评测。

## 验收路径

```text
注册/登录
创建岗位并填写技能标签
上传知识库
上传简历
系统配置 -> 重建 RAG 索引
执行简历匹配并查看证据
从匹配结果进入面试
生成带依据的问题
完成面试
查看证据化报告
运行 RAG 评测
```

## 常用检查命令

```bash
docker compose ps
curl -I http://127.0.0.1
curl -I https://smarthr.top
docker compose exec python-backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health/dependencies').read().decode())"
```

## RAG 评测说明

- 快速模式：`RAGAS_MODE=heuristic`，本地启发式评测，不调用外部 LLM。
- 完整模式：系统配置页选择完整 RAGas，使用 OpenAI-compatible LLM 评测 faithfulness、answer relevancy、context precision 和 context recall。
- 默认评测样本在 `smarthr-python/src/services/rag/evaluation_samples.json`。

完整 RAGas 可选配置：

```env
RAGAS_LLM_PROVIDER=deepseek
RAGAS_LLM_API_KEY=你的Key
RAGAS_LLM_BASE_URL=https://api.deepseek.com
RAGAS_LLM_MODEL=deepseek-chat
RAGAS_TIMEOUT_SECONDS=120
```

## 安全注意

- 不要提交 `.env`、API Key、数据库密码、证书私钥。
- 生产服务器只开放 `80/443/22`。
- MySQL、Redis、Chroma、Java、Python 不直接暴露公网。
- BGE 模型通过 volume 挂载，不打进镜像。
- 2 核 4G 服务器建议开启 2G 以上 swap。

## License

MIT
