"""
Document Processor - PDF/Word processing, chunking and vectorization
"""

import io
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from src.config import settings


class DocumentProcessor:
    """Process documents: extract text, chunk, and vectorize for knowledge base"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.chunk_size = 500
        self.chunk_overlap = 50

    async def process_document(self, file_path: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Process a document file: extract text, chunk, and vectorize.
        Returns list of chunk IDs stored in vector DB.
        """
        # Extract text from file
        text = self.extract_text_from_file(file_path)

        # Chunk the text
        chunks = self.chunk_text(text)

        # Vectorize and store
        chunk_ids = await self.vectorize_chunks(chunks, metadata)

        return chunk_ids

    async def process_file_content(self, content: bytes, filename: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Process uploaded file content directly without saving to disk.
        Returns list of chunk IDs.
        """
        # Extract text based on file type
        text = self.extract_text_from_bytes(content, filename)

        # Chunk the text
        chunks = self.chunk_text(text)

        # Vectorize and store
        chunk_ids = await self.vectorize_chunks(chunks, metadata)

        return chunk_ids

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF or Word file"""
        import os

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            return self._extract_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self._extract_word(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def extract_text_from_bytes(self, content: bytes, filename: str) -> str:
        """Extract text from file bytes"""
        ext = filename.lower().split('.')[-1]

        if ext == 'pdf':
            return self._extract_pdf_from_bytes(content)
        elif ext in ['docx', 'doc']:
            return self._extract_word_from_bytes(content)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)
        except ImportError:
            raise ImportError("PyPDF2 is required for PDF processing. Install with: pip install PyPDF2")

    def _extract_pdf_from_bytes(self, content: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)
        except ImportError:
            raise ImportError("PyPDF2 is required for PDF processing")

    def _extract_word(self, file_path: str) -> str:
        """Extract text from Word file"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            raise ImportError("python-docx is required for Word processing. Install with: pip install python-docx")

    def _extract_word_from_bytes(self, content: bytes) -> str:
        """Extract text from Word bytes"""
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            raise ImportError("python-docx is required for Word processing")

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """
        Split text into overlapping chunks.
        Uses simple character-based chunking with overlap.
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap

        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                for punct in ['.', '!', '?', '\n']:
                    last_punct = text.rfind(punct, start + chunk_size // 2, end)
                    if last_punct > start + chunk_size // 2:
                        end = last_punct + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    async def vectorize_chunks(self, chunks: List[str], metadata: Dict[str, Any]) -> List[str]:
        """Vectorize text chunks and store in Chroma"""
        from src.services.vector_store import vector_store_service

        if not chunks:
            return []

        # Get embeddings
        embeddings_list = await self.embeddings.aembed_documents(chunks)

        # Prepare documents for Chroma
        documents = []
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{metadata.get('doc_id', 'doc')}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)

        # Add to vector store
        collection_name = metadata.get('collection', 'knowledge_base')
        vector_store_service.add(
            collection_name=collection_name,
            embeddings=embeddings_list,
            documents=documents,
            ids=ids,
            metadata=[metadata] * len(chunks)
        )

        return ids

    async def process_multiple_documents(self, files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Process multiple documents.
        files: List of {path, metadata} dicts
        Returns: {filename: [chunk_ids]}
        """
        results = {}
        for file_info in files:
            path = file_info.get('path')
            metadata = file_info.get('metadata', {})
            try:
                chunk_ids = await self.process_document(path, metadata)
                results[path] = chunk_ids
            except Exception as e:
                results[path] = []
                print(f"Error processing {path}: {e}")
        return results


# Global instance
document_processor = DocumentProcessor()