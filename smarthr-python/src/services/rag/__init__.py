"""Unified RAG services for SmartHR."""

__all__ = ["rag_pipeline"]


def __getattr__(name: str):
    if name == "rag_pipeline":
        from src.services.rag.pipeline import rag_pipeline

        return rag_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
