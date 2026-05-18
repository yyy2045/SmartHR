# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SmartHR 是一个多智能体协作招聘平台，采用 Java (Spring Boot) + Python (FastAPI) 双语言架构，结合 Redis、MySQL 和向量数据库实现智能招聘辅助系统。

## 技术架构

```
[前端 Vue3/React]
    |
[Java Spring Boot 主业务层] —— [MySQL] (业务数据)
    |                        —— [Redis] (会话记忆、上下文)
    |
[Python FastAPI AI服务层]   —— [向量数据库] (语义匹配)
    |                        —— [LangChain + LangGraph] (多智能体编排)
    |
[LLM 大模型 API]
```

- **Java 层**：负责认证授权 (JWT)、业务 REST API、会话管理、结果持久化
- **Python 层**：负责所有 AI 推理任务（RAG、多智能体协作）
- **Redis**：两层共享记忆中枢，存储智能体对话历史和用户偏好
- **向量数据库**：存储文本嵌入向量，实现语义级简历匹配

## 核心技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 后端主语言 | Java, Spring Boot | 业务接口、鉴权、会话管理 |
| 认证 | JWT | 无状态用户认证 |
| 缓存与记忆 | Redis | 多智能体对话历史、上下文 |
| 关系型数据库 | MySQL | 用户、岗位、简历、报告 |
| AI 服务语言 | Python, FastAPI | AI 推理接口 |
| LLM 编排 | LangChain, LangGraph | 多智能体协作状态图 |
| 向量存储 | Chroma | 语义匹配 |
| 前端 | Vue3 / React | HR 操作界面 |

## 项目模块

1. **系统管理** - 用户认证、权限、企业管理、系统配置
2. **岗位管理** - JD CRUD、AI 辅助标签提取
3. **简历管理** - 批量上传、解析、匹配度计算
4. **智能面试** - 多智能体协作（主面试官、技能评估、行为分析、报告生成）
5. **上下文记忆** - Redis 会话管理、断点续面
6. **企业知识库** - 文档上传、分块、向量化
7. **评估报告** - 结构化报告、导出

## 开发环境要求

- JDK 17+, Maven
- Node.js 18+
- Python 3.12+
- MySQL 8, Redis 7
- 向量数据库 (Chroma)

## 常用命令（待实现）

项目将采用 docker-compose 部署，主要服务启动命令：
```bash
docker-compose up -d
```

## 多智能体架构

面试系统基于 LangGraph 实现，包含四个智能体：
- **主面试官**：主导提问，从题库抽题或动态生成
- **技能评估智能体**：评估技术深度，调用向量检索核验事实
- **行为分析智能体**：分析软素质、逻辑性、协作倾向
- **报告生成智能体**：交叉验证，生成加权评分报告

智能体通过 Redis 共享状态，实现断点续面能力。
