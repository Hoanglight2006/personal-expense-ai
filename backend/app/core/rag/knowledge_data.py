"""Financial Knowledge Base proxy for RAG.

Dynamically loads curated documents and chunks from local repository (backend/data/knowledge_base)
supporting Markdown (.md) articles, PDF (.pdf) handbooks, and plain text (.txt) files.
"""

from __future__ import annotations

from app.core.rag.document_loader import (
    KnowledgeDocument,
    load_knowledge_base,
    load_knowledge_chunks,
)


def get_knowledge_base() -> list[KnowledgeDocument]:
    """Retrieve all currently loaded full knowledge documents from repository."""
    return load_knowledge_base()


def get_knowledge_chunks() -> list[KnowledgeDocument]:
    """Retrieve all overlapping 500-character chunks across the knowledge repository."""
    return load_knowledge_chunks()


class _KnowledgeBaseProxy(list):
    """Dynamic list proxy that forwards calls to load_knowledge_base() for backward compatibility."""

    def __iter__(self):
        return iter(get_knowledge_base())

    def __len__(self):
        return len(get_knowledge_base())

    def __getitem__(self, index):
        return get_knowledge_base()[index]

    def __contains__(self, item):
        return item in get_knowledge_base()


FINANCIAL_KNOWLEDGE_BASE: list[KnowledgeDocument] = _KnowledgeBaseProxy()

__all__ = [
    "KnowledgeDocument",
    "FINANCIAL_KNOWLEDGE_BASE",
    "get_knowledge_base",
    "get_knowledge_chunks",
]
