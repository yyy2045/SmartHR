"""
Vector Store Service - Chroma DB wrapper
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from src.config import settings


class VectorStoreService:
    """Chroma vector database service"""

    def __init__(self):
        self.client = chromadb.Client(Settings(
            persist_directory=settings.chroma_persist_directory,
            anonymized_telemetry=False
        ))

    def create_collection(self, name: str, metadata: Optional[Dict] = None):
        """Create or get a collection"""
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
        """Add documents to collection"""
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
        """Search similar documents"""
        collection = self.client.get_collection(collection_name)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )

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
        """Delete documents from collection"""
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
        """Update documents in collection"""
        collection = self.client.get_collection(collection_name)
        collection.update(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadata
        )

    def delete_collection(self, name: str):
        """Delete a collection"""
        self.client.delete_collection(name)

    def list_collections(self) -> List[str]:
        """List all collections"""
        return [col.name for col in self.client.list_collections()]


# Global instance
vector_store_service = VectorStoreService()