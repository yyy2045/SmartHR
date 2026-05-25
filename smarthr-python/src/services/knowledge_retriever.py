"""
知识检索器 - 从 Chroma 企业知识库进行 RAG 检索
"""

from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from src.config import settings
from src.services.vector_store import vector_store_service


class KnowledgeRetriever:
    """基于企业知识库的 RAG 检索"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.collection_name = "knowledge_base"

    async def retrieve(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        在知识库中进行语义搜索
        返回 {content, metadata, score} 字典列表
        """
        # 获取查询嵌入向量
        query_embedding = await self.embeddings.aembed_query(query)

        # 搜索向量存储
        results = vector_store_service.search(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )

        return results

    async def add_knowledge(self, company_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """
        向向量存储添加知识条目
        返回 chunk ID
        """
        # 获取嵌入向量
        embedding = await self.embeddings.aembed_query(text)

        # 生成 ID
        import uuid
        chunk_id = str(uuid.uuid4())

        # 添加到向量存储
        vector_store_service.add(
            collection_name=self.collection_name,
            embeddings=[embedding],
            documents=[text],
            ids=[chunk_id],
            metadata=[{
                **metadata,
                "company_id": company_id,
                "type": "knowledge_entry"
            }]
        )

        return chunk_id

    async def search_by_company(self, company_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """在知识库中按公司搜索"""
        filters = {"company_id": company_id}
        return await self.retrieve(query, top_k, filters)

    async def search_by_doc_type(self, doc_type: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """在知识库中按文档类型搜索"""
        filters = {"doc_type": doc_type}
        return await self.retrieve(query, top_k, filters)

    async def get_context_for_agent(self, agent_type: str, query: str, company_id: str) -> str:
        """
        获取特定智能体类型的相关上下文
        agent_type: MAIN, SKILL, BEHAVIOR, REPORT
        """
        # 根据智能体类型自定义搜索
        if agent_type == "MAIN":
            # 主面试官需要公司价值观和面试指南
            search_query = f"{query} company values interview guidelines"
        elif agent_type == "SKILL":
            # 技能评估器需要技术知识
            search_query = f"{query} technical requirements skills"
        elif agent_type == "BEHAVIOR":
            # 行为分析器需要公司文化
            search_query = f"{query} company culture teamwork"
        else:
            search_query = query

        results = await self.search_by_company(company_id, search_query, top_k=3)

        # 格式化上下文
        if not results:
            return ""

        context_parts = []
        for r in results:
            content = r.get('document', '')
            metadata = r.get('metadata', {})
            source = metadata.get('title', 'Unknown')
            context_parts.append(f"[来源 {source}]: {content}")

        return "\n\n".join(context_parts)

    async def delete_knowledge(self, chunk_id: str) -> bool:
        """从向量存储中删除知识条目"""
        try:
            vector_store_service.delete(self.collection_name, [chunk_id])
            return True
        except Exception as e:
            print(f"[knowledge_retriever] delete_knowledge failed: {e}")
            return False

    async def update_knowledge(self, chunk_id: str, new_text: str, new_metadata: Dict[str, Any]) -> bool:
        """更新知识条目"""
        try:
            # 重新嵌入并更新
            embedding = await self.embeddings.aembed_query(new_text)
            vector_store_service.update(
                collection_name=self.collection_name,
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[new_text],
                metadata=[new_metadata]
            )
            return True
        except Exception as e:
            print(f"[knowledge_retriever] update_knowledge failed: {e}")
            return False


# 全局实例
knowledge_retriever = KnowledgeRetriever()