"""
向量存储服务 - Chroma DB 封装
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from src.config import settings


class VectorStoreService:
    """Chroma 向量数据库服务"""

    def __init__(self):
        self.client = chromadb.Client(Settings(
            persist_directory=settings.chroma_persist_directory,
            anonymized_telemetry=False
        ))

    def create_collection(self, name: str, metadata: Optional[Dict] = None):
        """创建或获取集合"""
        return self.client.get_or_create_collection(
            name=name,
            metadata=metadata or {}
        )

    def add(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None
    ):
        """向集合添加文档"""
        collection = self.create_collection(collection_name)
        collection.add(
            embeddings=embeddings,
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            collection = self.client.get_collection(collection_name)
        except Exception:
            # 集合不存在时返回空结果
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )

        # 处理空结果
        if not results["ids"] or not results["ids"][0]:
            return []

        return [
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else None,
                "metadata": results["metadatas"][0][i] if "metadatas" in results else None
            }
            for i in range(len(results["ids"][0]))
        ]

    def delete(self, collection_name: str, ids: List[str]):
        """从集合中删除文档"""
        collection = self.client.get_collection(collection_name)
        collection.delete(ids=ids)

    def update(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadata: Optional[List[Dict]] = None
    ):
        """更新集合中的文档"""
        collection = self.client.get_collection(collection_name)
        collection.update(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadata
        )

    def delete_collection(self, name: str):
        """删除集合"""
        self.client.delete_collection(name)

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return [col.name for col in self.client.list_collections()]


# 全局实例
vector_store_service = VectorStoreService()