"""RAG (Retrieval-Augmented Generation) package for personal finance knowledge."""

from app.core.rag.document_loader import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_SEPARATORS,
    KnowledgeDocument,
    chunk_document,
    load_knowledge_base,
    load_knowledge_chunks,
    recursive_split_text,
)
from app.core.rag.knowledge_data import (
    FINANCIAL_KNOWLEDGE_BASE,
    get_knowledge_base,
    get_knowledge_chunks,
)
from app.core.rag.retriever import (
    format_rag_context,
    get_benchmark_knowledge,
    retrieve_contextual_budget_knowledge,
    retrieve_contextual_report_knowledge,
    retrieve_relevant_knowledge,
)
from app.core.rag.web_search import (
    fetch_url_full_text,
    search_online_financial_knowledge,
)

__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_SEPARATORS",
    "FINANCIAL_KNOWLEDGE_BASE",
    "KnowledgeDocument",
    "chunk_document",
    "fetch_url_full_text",
    "get_knowledge_base",
    "get_knowledge_chunks",
    "load_knowledge_base",
    "load_knowledge_chunks",
    "recursive_split_text",
    "retrieve_relevant_knowledge",
    "format_rag_context",
    "get_benchmark_knowledge",
    "retrieve_contextual_budget_knowledge",
    "retrieve_contextual_report_knowledge",
    "search_online_financial_knowledge",
]
