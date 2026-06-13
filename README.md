# SmartHR - 多智能体协作招聘平台

## 项目简介

SmartHR 是一款面向企业 HR 和面试官的智能招聘辅助系统，采用 Java + Python 双语言架构，结合多智能体协作、RAG 和向量数据库实现全流程智能化招聘。

## 技术架构

```
[前端 Vue3/React]
    |
[Java Spring Boot 主业务层] —— [MySQL] (业务数据)
    |                        —— [Redis] (会话记忆、上下文)
    |
[Python FastAPI AI服务层]   —— [Chroma 向量数据库] (语义匹配)
    |                        —— [LangChain + LangGraph] (多智能体编排)
    |
[LLM 大模型 API (DeepSeek)]
```

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 后端主语言 | Java, Spring Boot 3.2 | 业务接口、鉴权、会话管理 |
| 认证 | JWT | 无状态用户认证与授权 |
| 缓存与记忆 | Redis | 存储多智能体对话历史、HR筛选上下文 |
| 关系型数据库 | MySQL 8 | 存储用户、岗位、简历、报告等业务数据 |
| AI 服务语言 | Python, FastAPI | 高性能异步 AI 推理接口 |
| LLM 编排 | LangChain, LangGraph | RAG 流程、多智能体协作 |
| 向量存储 | Chroma | 简历与岗位的语义匹配 |
| 检索增强生成 | RAG | 结合知识库与向量检索 |

## 项目结构

```
SmartHR/
├── smarthr-java/              # Java Spring Boot 主项目
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/smarthr/
│       │   ├── SmarthrApplication.java
│       │   ├── config/         # 配置类 (JWT, Security, Redis)
│       │   ├── controller/     # REST API (Auth, Company, Job, Health)
│       │   ├── service/        # 业务逻辑
│       │   ├── repository/     # 数据访问
│       │   ├── entity/         # 实体类 (User, Company, Job, Resume, InterviewSession, Report)
│       │   ├── dto/            # 数据传输对象
│       │   └── exception/      # 异常处理
│       └── resources/
│           └── application.yml
├── smarthr-python/            # Python FastAPI AI 服务
│   ├── pyproject.toml
│   └── src/
│       ├── main.py             # FastAPI 入口
│       ├── config.py           # 配置管理
│       ├── api/                # API 路由 (health, resume, interview, knowledge)
│       ├── services/           # LLM, VectorStore, Redis 服务
│       └── agents/             # 智能体实现
├── docker-compose.yml          # 容器编排 (MySQL, Redis, Chroma)
├── init-scripts/
│   └── schema.sql              # 数据库初始化脚本
└── README.md
```

## 快速开始

### 环境要求

- JDK 17+
- Maven 3.8+
- Python 3.10+
- Docker & Docker Compose
- DeepSeek API Key

### 1. 启动基础设施服务

```bash
cd SmartHR
docker-compose up -d
```

验证服务状态：
- MySQL: localhost:3306
- Redis: localhost:6379
- Chroma: localhost:8000

### 2. 配置文件

敏感配置使用环境变量管理，已从仓库中忽略。使用前请复制模板并配置：

```bash
# Java
cp smarthr-java/src/main/resources/application.yml.example \
   smarthr-java/src/main/resources/application.yml
# 编辑 application.yml 填入真实密码

# Python
cp smarthr-python/.env.example smarthr-python/.env
# 编辑 .env 填入 DeepSeek API Key
```

### 3. 启动 Java 后端

```bash
cd smarthr-java
mvn spring-boot:run
```

服务地址：http://localhost:8080

### 4. 启动 Python AI 服务

```bash
cd smarthr-python
poetry install
poetry run python src/main.py
```

服务地址：http://localhost:8001

## 阿里云轻量云服务器演示部署

目标环境：阿里云轻量应用服务器或单 ECS，最低 2 核 4G，CPU-only，Docker Compose 单机部署。生产演示只开放 `80/443` 和管理用 `22`，MySQL、Redis、Chroma、Java、Python、前端容器均不直接暴露公网端口。

### 1. 服务器准备

```bash
sudo mkdir -p /opt/smarthr/models
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

将本地 embedding 模型放到：

```bash
/opt/smarthr/models/bge-base-zh-v1.5
```

### 2. 域名和 HTTPS

域名需要解析到服务器公网 IP。中国大陆地域绑定域名通常需要 ICP 备案。证书文件放在：

```bash
deploy/certs/fullchain.pem
deploy/certs/privkey.pem
```

### 3. 配置和启动

```bash
cp .env.example .env
# 编辑 .env，填入 MySQL/JWT/DeepSeek/域名等真实配置
docker compose -f docker-compose.aliyun.yml up -d --build
```

生产模板固定使用本地 `bge-base-zh-v1.5`，`ALLOW_MOCK_EMBEDDING=false`。2 核 4G 下不启用神经 reranker，使用 hybrid retrieval + embedding 相似度排序。

### 4. 健康检查

```bash
curl https://你的域名/api/health
curl https://你的域名/python/health/dependencies
docker compose -f docker-compose.aliyun.yml ps
```

`/python/health/dependencies` 会检查 Redis、Chroma、本地 BGE 模型路径、加载状态、向量维度和一次测试 embedding。

### 5. 人工验收路径

1. 登录 `admin@smarthr.com / admin123` 或 `hr@smarthr.com / admin123`
2. 创建岗位
3. 录入或上传知识库文档
4. 上传简历并完成解析
5. 执行岗位匹配，查看总分、技能命中、技能缺口、风险点和证据来源
6. 从匹配结果进入面试
7. AI 生成问题并完成面试
8. 查看面试报告
9. 在系统配置页运行 RAGas/本地启发式评测

## API 接口

### 认证接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |

### 企业管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/companies | 创建企业 |
| GET | /api/companies | 获取企业列表 |
| GET | /api/companies/{id} | 获取企业详情 |
| PUT | /api/companies/{id} | 更新企业 |
| DELETE | /api/companies/{id} | 删除企业 |

### 岗位管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/jobs | 创建岗位 |
| GET | /api/jobs | 获取岗位列表 |
| GET | /api/jobs/{id} | 获取岗位详情 |
| PUT | /api/jobs/{id} | 更新岗位 |
| DELETE | /api/jobs/{id} | 删除岗位 |

### 健康检查

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/health | Java 后端健康检查 |
| GET | /health | Python AI 服务健康检查 |

## 核心功能

### 1. 简历智能匹配与解析

- PDF/Word 简历解析
- 结构化数据提取
- JD-简历语义匹配度计算

### 2. 智能面试系统

多智能体协作面试，包含：
- **主面试官**：主导提问流程
- **技能评估智能体**：评估技术深度
- **行为分析智能体**：分析软素质
- **报告生成智能体**：生成加权评分报告

### 3. 上下文记忆

- Redis 存储面试对话历史
- 断点续面能力
- HR 偏好学习

### 4. 企业知识库

- 文档上传与向量化
- 面试中检索企业知识

## 测试账号

| 邮箱 | 密码 | 角色 |
|------|------|------|
| admin@smarthr.com | admin123 | ADMIN |
| hr@smarthr.com | admin123 | HR |

## 开发阶段

- [x] 第0阶段：环境准备
- [x] 第1阶段：后端基础架构
- [ ] 第2阶段：简历匹配与解析
- [ ] 第3阶段：智能面试多智能体系统
- [ ] 第4阶段：上下文记忆与连续性
- [ ] 第5阶段：企业知识库
- [ ] 第6阶段：前端页面
- [ ] 第7阶段：集成测试
- [ ] 第8阶段：部署与文档

## License

MIT
