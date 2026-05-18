"""
Knowledge Retriever - RAG retrieval from Chroma for enterprise knowledge base
"""

from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from src.config import settings
from src.services.vector_store import vector_store_service


class KnowledgeRetriever:
    """RAG-based retrieval from enterprise knowledge base"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.collection_name = "knowledge_base"

    async def retrieve(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Semantic search in knowledge base.
        Returns list of {content, metadata, score} dicts.
        """
        # Get query embedding
        query_embedding = await self.embeddings.aembed_query(query)

        # Search vector store
        results = vector_store_service.search(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )

        return results

    async def add_knowledge(self, company_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """
        Add a knowledge entry to the vector store.
        Returns the chunk ID.
        """
        # Get embedding
        embedding = await self.embeddings.aembed_query(text)

        # Generate ID
        import uuid
        chunk_id = str(uuid.uuid4())

        # Add to vector store
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
        """Search knowledge base filtered by company"""
        filters = {"company_id": company_id}
        return await self.retrieve(query, top_k, filters)

    async def search_by_doc_type(self, doc_type: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base filtered by document type"""
        filters = {"doc_type": doc_type}
        return await self.retrieve(query, top_k, filters)

    async def get_context_for_agent(self, agent_type: str, query: str, company_id: str) -> str:
        """
        Get relevant context for a specific agent type.
        agent_type: MAIN, SKILL, BEHAVIOR, REPORT
        """
        # Customize search based on agent type
        if agent_type == "MAIN":
            # Main interviewer needs company values and interview guidelines
            search_query = f"{query} company values interview guidelines"
        elif agent_type == "SKILL":
            # Skill evaluator needs technical knowledge
            search_query = f"{query} technical requirements skills"
        elif agent_type == "BEHAVIOR":
            # Behavior analyzer needs company culture
            search_query = f"{query} company culture teamwork"
        else:
            search_query = query

        results = await self.search_by_company(company_id, search_query, top_k=3)

        # Format context
        if not results:
            return ""

        context_parts = []
        for r in results:
            content = r.get('document', '')
            metadata = r.get('metadata', {})
            source = metadata.get('title', 'Unknown')
            context_parts.append(f"[From {source}]: {content}")

        return "\n\n".join(context_parts)

    async def delete_knowledge(self, chunk_id: str) -> bool:
        """Delete a knowledge entry from the vector store"""
        try:
            vector_store_service.delete(self.collection_name, [chunk_id])
            return True
        except Exception:
            return False

    async def update_knowledge(self, chunk_id: str, new_text: str, new_metadata: Dict[str, Any]) -> bool:
        """Update a knowledge entry"""
        try:
            # Re-embed and update
            embedding = await self.embeddings.aembed_query(new_text)
            vector_store_service.update(
                collection_name=self.collection_name,
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[new_text],
                metadata=[new_metadata]
            )
            return True
        except Exception:
            return False


# Global instance
knowledge_retriever = KnowledgeRetriever()