"""Hybrid Chunk-Level RAG Retrieval Engine for Personal Finance Knowledge.

Implements the GenAI RAG Retrieval Pipeline:
1. Recursive 500-char chunk indexing (with 50-char overlap) over local .md / .pdf / .txt documents
2. Chunk-level lexical + phrase scoring & sibling noise filtering (drops irrelevant paragraphs)
3. Hybrid live web expansion (DuckDuckGo) for market/real-time financial queries
4. Source-grounded prompt formatting with anti-hallucination guardrails
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.rag.document_loader import (
    DEFAULT_CHUNK_SIZE,
    KnowledgeDocument,
    chunk_document,
    load_knowledge_chunks,
)
from app.core.rag.web_search import search_online_financial_knowledge

# Keywords indicating that the user query is about finance / money management
_FINANCIAL_INTENT_KEYWORDS = [
    "tiền",
    "chi tiêu",
    "thu nhập",
    "tiết kiệm",
    "ngân sách",
    "lãi suất",
    "giá vàng",
    "thuế",
    "nợ",
    "đầu tư",
    "quỹ",
    "chi phí",
    "ngân hàng",
    "sổ tiết kiệm",
    "thẻ tín dụng",
    "50/30/20",
    "chiếc lọ",
    "tài chính",
    "sinh hoạt",
    "lương",
    "tài sản",
    "cẩm nang",
    "bảo hiểm",
    "quy tắc 72",
    "cic",
]

# Keywords indicating that the user is seeking recent online or market information
_WEB_SEARCH_TRIGGERS = [
    "hôm nay",
    "mới nhất",
    "lãi suất",
    "giá vàng",
    "thị trường",
    "ngân hàng nào",
    "tin tức",
    "bảng giá",
    "cập nhật",
    "tỷ giá",
]

# Keywords indicating that the user is asking about personal account transactions/statistics
_PERSONAL_STATS_PATTERNS = [
    "thống kê",
    "giao dịch gần",
    "số dư hiện tại",
    "số dư của tôi",
    "số dư khả dụng",
    "tổng chi tiêu tháng này",
    "tổng thu nhập tháng này",
    "tháng này tôi chi",
    "tháng này mình chi",
    "tháng này đã chi",
    "tôi đã tiêu",
    "mình đã tiêu",
    "chi bao nhiêu",
    "tiêu bao nhiêu",
    "chi nhiều nhất",
    "danh mục nào",
    "ăn uống tháng này",
    "đi lại tháng này",
    "mua sắm tháng này",
    "tiền nhà tháng này",
    "lịch sử giao dịch",
]

# Keywords indicating that the user explicitly asks for financial knowledge, methods, rules, or advice
_KNOWLEDGE_METHOD_SIGNALS = [
    "50/30/20",
    "50 30 20",
    "50-30-20",
    "chiếc lọ",
    "6 lọ",
    "sáu lọ",
    "jars",
    "harv eker",
    "elizabeth warren",
    "phương pháp",
    "quy tắc",
    "nguyên tắc",
    "chiến lược",
    "chiến thuật",
    "tuyết lở",
    "quả cầu tuyết",
    "snowball",
    "avalanche",
    "quỹ dự phòng",
    "quỹ khẩn cấp",
    "tiền phòng thân",
    "giảm trừ gia cảnh",
    "thuế tncn",
    "thuế thu nhập",
    "biểu thuế",
    "bậc thuế",
    "lũy tiến",
    "lãi suất",
    "giá vàng",
    "lạm phát",
    "trì hoãn 24",
    "mua sắm bốc đồng",
    "mua sắm ngẫu hứng",
    "định mức ngân sách",
    "sức khỏe tài chính",
    "đại học mở",
    "đại học huế",
    "tạp chí khoa học",
    "so sánh",
    "rủi ro",
    "ưu nhược điểm",
    "phù hợp hơn",
    "làm sao để tiết kiệm",
    "cách quản lý tiền",
    "cách chia tiền",
]

# Vietnamese grammar/conversational stopwords excluded from content discrimination
_STOPWORDS = {
    "là",
    "gì",
    "tôi",
    "bạn",
    "mình",
    "muốn",
    "của",
    "cho",
    "và",
    "hay",
    "hoặc",
    "như",
    "thế",
    "nào",
    "sao",
    "có",
    "không",
    "nên",
    "cần",
    "phải",
    "được",
    "với",
    "trong",
    "khi",
    "thì",
    "mà",
    "ở",
    "đâu",
    "về",
    "các",
    "những",
    "một",
    "bao",
    "nhiêu",
    "hãy",
    "này",
    "đó",
    "nhất",
    "vào",
    "ra",
    "đến",
    "từ",
    "theo",
    "để",
}


def _normalize_text(text: str) -> str:
    """Normalize text by lowering, removing punctuation, and stripping extra whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFC", text)
    # Keep alphanumeric characters and slashes (for 50/30/20)
    text = re.sub(r"[^\w\s/]", " ", text)
    return " ".join(text.split())


def _extract_meaningful_unigrams(text: str) -> set[str]:
    """Extract non-stopword unigrams of length >= 2."""
    normalized = _normalize_text(text)
    return {
        w for w in normalized.split()
        if len(w) > 1 and w not in _STOPWORDS
    }


def _extract_bigrams(text: str) -> set[str]:
    """Extract 2-word phrases where at least one token carries domain meaning."""
    normalized = _normalize_text(text)
    words = [w for w in normalized.split() if len(w) > 1]
    bigrams: set[str] = set()
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if w1 not in _STOPWORDS or w2 not in _STOPWORDS:
            bigrams.add(f"{w1} {w2}")
    return bigrams


def _prepare_candidate_chunks(custom_docs: list[KnowledgeDocument] | None) -> list[KnowledgeDocument]:
    """Load pre-chunked repository corpus or split oversized custom documents on the fly."""
    if custom_docs is None:
        return load_knowledge_chunks()

    prepared: list[KnowledgeDocument] = []
    for doc in custom_docs:
        if "chunk_id" not in doc and len(doc.get("content", "")) > DEFAULT_CHUNK_SIZE:
            prepared.extend(chunk_document(doc))
        else:
            prepared.append(doc)
    return prepared


def retrieve_relevant_knowledge(
    query: str,
    top_k: int = 3,
    min_score: float = 1.0,
    custom_docs: list[KnowledgeDocument] | None = None,
    enable_web_search: bool = True,
) -> list[KnowledgeDocument]:
    """Retrieve top-K most relevant knowledge chunks for a query.

    1. Splits long raw documents into ~500-char chunks with 50-char overlap.
    2. Scores each chunk individually and filters out irrelevant sibling chunks.
    3. Expands to live web search when the query asks for market/live financial updates
       or when no local document matches a financial query.
    """
    if not query or len(query.strip()) < 3:
        return []

    chunks = _prepare_candidate_chunks(custom_docs)
    query_norm = _normalize_text(query)
    query_unigrams = _extract_meaningful_unigrams(query)
    query_bigrams = _extract_bigrams(query)

    if not query_unigrams and not query_bigrams:
        return []

    has_financial_intent = any(kw in query_norm for kw in _FINANCIAL_INTENT_KEYWORDS)
    is_personal_stats_query = any(pat in query_norm for pat in _PERSONAL_STATS_PATTERNS)
    has_knowledge_signal = any(sig in query_norm for sig in _KNOWLEDGE_METHOD_SIGNALS)

    # Pure personal transaction/statistics lookups should answer directly from financial_context
    # without attaching external RAG articles or citations.
    if is_personal_stats_query and not has_knowledge_signal and custom_docs is None:
        return []

    raw_scored: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_norm = _normalize_text(chunk["content"])

        # 1. Document-level metadata matching
        matched_doc_kws = [
            kw for kw in chunk.get("keywords", [])
            if _normalize_text(kw) and _normalize_text(kw) in query_norm
        ]
        keyword_hit = len(matched_doc_kws) > 0

        title_unigrams = _extract_meaningful_unigrams(chunk["title"])
        title_bigrams = _extract_bigrams(chunk["title"])
        common_title_unigrams = query_unigrams.intersection(title_unigrams)
        common_title_bigrams = query_bigrams.intersection(title_bigrams)
        common_title = common_title_unigrams | common_title_bigrams
        title_coverage = len(common_title_unigrams) / max(1, len(query_unigrams))

        # 2. Chunk-level content matching (discriminates target paragraph vs filler paragraphs)
        chunk_unigrams = _extract_meaningful_unigrams(chunk["content"])
        chunk_bigrams = _extract_bigrams(chunk["content"])
        common_unigrams = query_unigrams.intersection(chunk_unigrams)
        common_bigrams = query_bigrams.intersection(chunk_bigrams)

        chunk_kw_hits = [
            kw for kw in matched_doc_kws
            if _normalize_text(kw) in chunk_norm
        ]

        content_score = (
            len(common_bigrams) * 0.9
            + len(common_unigrams) * 0.35
            + len(chunk_kw_hits) * 1.5
        )
        if len(query_norm) >= 8 and query_norm in chunk_norm:
            content_score += 1.5

        # 3. Precision Gate (supports both frontmatter-tagged articles AND raw untagged PDFs/articles)
        raw_content_match = (
            has_financial_intent
            and len(common_bigrams) >= 2
            and len(common_unigrams) >= 4
        )
        strong_title_match = len(common_title) >= 2 and title_coverage >= 0.45
        if not keyword_hit and not strong_title_match and not raw_content_match:
            continue
        if not keyword_hit and not strong_title_match and raw_content_match and not has_knowledge_signal and custom_docs is None:
            continue

        base_score = 0.0
        if keyword_hit:
            base_score += 2.0
        if strong_title_match:
            base_score += min(len(common_title) * 0.7, 2.1)
        elif len(common_title) >= 1 and keyword_hit:
            base_score += 0.5
        elif raw_content_match and base_score == 0.0:
            base_score += 1.0

        total_score = round(base_score + content_score, 3)
        if total_score >= min_score:
            raw_scored.append({
                "doc": chunk,
                "doc_id": chunk["id"],
                "chunk_index": chunk.get("chunk_index", 1),
                "keyword_hit": keyword_hit,
                "content_score": round(content_score, 3),
                "score": total_score,
            })

    # If at least one document matched via explicit domain keywords, drop weak non-keyword matches
    if any(item["keyword_hit"] for item in raw_scored):
        raw_scored = [item for item in raw_scored if item["keyword_hit"]]
    elif custom_docs is None:
        # Built-in repository documents are all indexed with domain keywords; require at least one keyword hit
        raw_scored = []

    # 4. Sibling Noise Filtering: drop filler chunks of a matched document when specific chunks hit
    max_content_by_doc: dict[str, float] = {}
    for item in raw_scored:
        did = item["doc_id"]
        max_content_by_doc[did] = max(max_content_by_doc.get(did, 0.0), item["content_score"])

    filtered_results: list[dict[str, Any]] = []
    for item in raw_scored:
        best_sibling = max_content_by_doc[item["doc_id"]]
        if best_sibling > 0.0:
            if item["content_score"] >= max(0.35, best_sibling * 0.25):
                filtered_results.append(item)
        else:
            # Synonym-only match in frontmatter: keep only the lead chunk (chunk_index == 1)
            if item["chunk_index"] == 1:
                filtered_results.append(item)

    filtered_results.sort(key=lambda x: (x["score"], -x["chunk_index"]), reverse=True)

    # Ensure multi-topic / comparison queries include chunks from distinct matched documents
    matched_chunks: list[KnowledgeDocument] = []
    seen_doc_ids: set[str] = set()
    distinct_doc_count = len({item["doc_id"] for item in filtered_results})

    if distinct_doc_count >= 2:
        for item in filtered_results:
            did = item["doc_id"]
            if did not in seen_doc_ids and len(matched_chunks) < top_k:
                matched_chunks.append(item["doc"])
                seen_doc_ids.add(did)
        for item in filtered_results:
            if len(matched_chunks) >= top_k:
                break
            if item["doc"] not in matched_chunks:
                matched_chunks.append(item["doc"])
    else:
        matched_chunks = [item["doc"] for item in filtered_results[:top_k]]

    # 5. Hybrid Live Web Search Expansion (Local-First with Web Fallback)
    needs_live_search = any(trigger in query_norm for trigger in _WEB_SEARCH_TRIGGERS)
    insufficient_local_matches = len(matched_chunks) < min(2, top_k)
    should_search_web = (
        enable_web_search
        and has_financial_intent
        and not is_personal_stats_query
        and custom_docs is None
        and (needs_live_search or insufficient_local_matches)
    )

    if should_search_web:
        try:
            web_results = search_online_financial_knowledge(query, max_results=top_k)
            live_web_chunks: list[KnowledgeDocument] = []
            for idx, wr in enumerate(web_results, 1):
                raw_web_text = wr.get("content") or wr["snippet"]
                web_doc: KnowledgeDocument = {
                    "id": f"web_{idx}",
                    "title": wr["title"],
                    "category": "online_article",
                    "source_name": wr["source_name"],
                    "source_url": wr["source_url"],
                    "keywords": [],
                    "content": raw_web_text,
                }
                if len(web_doc["content"]) > DEFAULT_CHUNK_SIZE:
                    web_chunks = chunk_document(web_doc)
                    best_web_chunk = max(
                        web_chunks,
                        key=lambda wc: (
                            len(query_bigrams.intersection(_extract_bigrams(wc["content"]))) * 0.9
                            + len(query_unigrams.intersection(_extract_meaningful_unigrams(wc["content"]))) * 0.35
                        ),
                    )
                    live_web_chunks.append(best_web_chunk)
                elif web_doc not in matched_chunks:
                    live_web_chunks.append(web_doc)

            if live_web_chunks:
                if needs_live_search and matched_chunks:
                    # Reserve slots for live web results when query explicitly asks for real-time/today info
                    keep_local = max(1, top_k - len(live_web_chunks))
                    matched_chunks = matched_chunks[:keep_local] + live_web_chunks
                else:
                    matched_chunks.extend(live_web_chunks)
        except Exception:
            pass

    return matched_chunks[:top_k]


def format_rag_context(documents: list[KnowledgeDocument]) -> str:
    """Format retrieved knowledge chunks into a prompt-ready context block with citations."""
    if not documents:
        return ""

    blocks = ["=== TÀI LIỆU & NGUYÊN TẮC TÀI CHÍNH THAM KHẢO (RAG KNOWLEDGE) ==="]
    for idx, doc in enumerate(documents, start=1):
        source_label = doc.get("source_name", "Tài liệu tham khảo")
        source_url = doc.get("source_url", "")
        url_part = f" - URL: {source_url}" if source_url and source_url != "local_pdf" else ""

        total_chunks = doc.get("total_chunks", 1)
        chunk_index = doc.get("chunk_index", 1)
        chunk_part = f" [Đoạn {chunk_index}/{total_chunks}]" if total_chunks and total_chunks > 1 else ""

        blocks.append(f"[{idx}] {doc['title']}{chunk_part} (Nguồn: {source_label}{url_part})")
        blocks.append(doc["content"])
        blocks.append("-" * 40)

    blocks.append("HƯỚNG DẪN KẾT HỢP:")
    blocks.append(
        "1. Ưu tiên sử dụng kiến thức, tỷ lệ phân bổ và quy tắc trong đoạn tài liệu trên để giải thích, phân tích hoặc so sánh cho người dùng.\n"
        "2. Trích dẫn tự nhiên tên nguyên tắc hoặc nguồn tham khảo khi sử dụng thông tin từ tài liệu.\n"
        "3. Nếu câu hỏi liên quan đến phương pháp tài chính mà tài liệu trên chưa đề cập trực tiếp, hãy nêu rõ kho tài liệu hiện tại chưa ghi nhận công thức cố định đó và tư vấn các nguyên tắc quản lý tài chính chuẩn mực."
    )
    blocks.append("=================================================================")
    return "\n".join(blocks)


def get_benchmark_knowledge(focus: str = "comprehensive") -> str:
    """Get standardized financial benchmark chunks for AI Monthly Report & Budget Suggestion."""
    all_chunks = load_knowledge_chunks()
    target_ids = ["financial_health_benchmarks", "rule_50_30_20"]
    if focus == "risk":
        target_ids.append("emergency_fund")
    elif focus == "saving":
        target_ids.append("spending_habits")

    # Select the lead benchmark chunk (chunk_index == 1) of each benchmark document to keep prompts concise
    benchmark_chunks = [
        c for c in all_chunks
        if c["id"] in target_ids and c.get("chunk_index", 1) == 1
    ]
    return format_rag_context(benchmark_chunks)


def retrieve_contextual_report_knowledge(
    summary: dict[str, Any],
    focus: str = "comprehensive",
    top_k: int = 2,
    enable_web_search: bool = True,
) -> tuple[str, list[str]]:
    """Dynamically retrieve RAG financial knowledge chunks tailored to the user's monthly spending state.
    
    Uses Local-First retrieval with Fallback to live web search when local repository is insufficient.
    """
    signals: list[str] = []
    if focus == "saving":
        signals.append("kiểm soát chi tiêu thói quen mua sắm ngẫu hứng trì hoãn 24 giờ tối ưu tiết kiệm")
    elif focus == "risk":
        signals.append("quỹ dự phòng khẩn cấp 3 đến 6 tháng rủi ro an toàn thanh khoản tài chính")
    else:
        # comprehensive
        if summary.get("savings_rate", 0.0) < 15.0:
            signals.append("quy tắc 50/30/20 phân bổ thu nhập gia tăng tỷ lệ tiết kiệm")
        else:
            signals.append("khung tiêu chuẩn sức khỏe tài chính định mức chi tiêu phân bổ ngân sách")

    if summary.get("exceeded_budgets_count", 0) > 0:
        over_names = [b["category"] for b in summary.get("budgets", []) if b.get("is_exceeded")]
        if over_names:
            signals.append(f"bội chi ngân sách kiểm soát hạn mức {' '.join(over_names)}")

    if summary.get("top_expenses"):
        top_name = summary["top_expenses"][0].get("name", "")
        if top_name:
            signals.append(f"hạn mức chi tiêu {top_name}")

    query = " ".join(signals)
    dynamic_docs = retrieve_relevant_knowledge(query, top_k=top_k, enable_web_search=enable_web_search)

    # Deduplicate dynamic chunks to distinct document IDs to ensure diverse reference benchmarks
    distinct_docs: list[KnowledgeDocument] = []
    seen_ids: set[str] = set()
    for d in dynamic_docs:
        did = d.get("id", "")
        if did not in seen_ids:
            distinct_docs.append(d)
            seen_ids.add(did)

    final_docs: list[KnowledgeDocument] = list(distinct_docs)

    all_chunks = load_knowledge_chunks()
    lead_50_30_20 = next((c for c in all_chunks if c["id"] == "rule_50_30_20" and c.get("chunk_index", 1) == 1), None)
    lead_benchmarks = next((c for c in all_chunks if c["id"] == "financial_health_benchmarks" and c.get("chunk_index", 1) == 1), None)

    if len(final_docs) < 2 and lead_50_30_20 and "rule_50_30_20" not in seen_ids:
        final_docs.append(lead_50_30_20)
        seen_ids.add("rule_50_30_20")
    if len(final_docs) < 2 and lead_benchmarks and "financial_health_benchmarks" not in seen_ids:
        final_docs.append(lead_benchmarks)
        seen_ids.add("financial_health_benchmarks")
    if len(final_docs) < 2:
        for c in all_chunks:
            if c.get("chunk_index", 1) == 1 and c.get("id") not in seen_ids:
                final_docs.append(c)
                seen_ids.add(c["id"])
                if len(final_docs) >= 2:
                    break

    rag_context = format_rag_context(final_docs)
    applied_benchmarks: list[str] = []
    for d in final_docs:
        src = d.get("source_name", "Tài liệu tham khảo")
        t = d.get("title", "")
        u = d.get("source_url", "")
        label = f"{src}: {t} ({u})" if u and u.startswith("http") else f"{src}: {t}"
        if label not in applied_benchmarks:
            applied_benchmarks.append(label)

    return rag_context, applied_benchmarks


def retrieve_contextual_budget_knowledge(
    prompt_items: list[dict[str, Any]],
    target_month: int,
    target_year: int,
    monthly_income: Any = 0,
    top_k: int = 2,
    enable_web_search: bool = True,
) -> tuple[str, list[str]]:
    """Dynamically retrieve RAG financial knowledge chunks tailored to the user's category budget setup.
    
    Uses Local-First retrieval with Fallback to live web search when local repository is insufficient.
    """
    cat_names = [item.get("name", "") for item in prompt_items if item.get("name")]
    top_cats = " ".join(cat_names[:3]) if cat_names else "ăn uống nhà ở đi lại"

    income_val = float(monthly_income or 0)
    if income_val >= 2000000:
        query = f"định mức ngân sách chuẩn {top_cats} quy tắc 50/30/20 phân bổ thu nhập quản lý chi tiêu"
    else:
        query = f"định mức ngân sách chuẩn chi phí sinh hoạt {top_cats} chi tiêu cá nhân hợp lý"

    dynamic_docs = retrieve_relevant_knowledge(query, top_k=top_k, enable_web_search=enable_web_search)

    # Deduplicate dynamic chunks to distinct document IDs to ensure diverse reference benchmarks
    distinct_docs: list[KnowledgeDocument] = []
    seen_ids: set[str] = set()
    for d in dynamic_docs:
        did = d.get("id", "")
        if did not in seen_ids:
            distinct_docs.append(d)
            seen_ids.add(did)

    final_docs: list[KnowledgeDocument] = list(distinct_docs)

    all_chunks = load_knowledge_chunks()
    lead_50_30_20 = next((c for c in all_chunks if c["id"] == "rule_50_30_20" and c.get("chunk_index", 1) == 1), None)
    lead_benchmarks = next((c for c in all_chunks if c["id"] == "financial_health_benchmarks" and c.get("chunk_index", 1) == 1), None)

    if len(final_docs) < 2 and lead_50_30_20 and "rule_50_30_20" not in seen_ids:
        final_docs.append(lead_50_30_20)
        seen_ids.add("rule_50_30_20")
    if len(final_docs) < 2 and lead_benchmarks and "financial_health_benchmarks" not in seen_ids:
        final_docs.append(lead_benchmarks)
        seen_ids.add("financial_health_benchmarks")
    if len(final_docs) < 2:
        for c in all_chunks:
            if c.get("chunk_index", 1) == 1 and c.get("id") not in seen_ids:
                final_docs.append(c)
                seen_ids.add(c["id"])
                if len(final_docs) >= 2:
                    break

    rag_context = format_rag_context(final_docs)
    applied_benchmarks: list[str] = []
    for d in final_docs:
        src = d.get("source_name", "Tài liệu tham khảo")
        t = d.get("title", "")
        u = d.get("source_url", "")
        label = f"{src}: {t} ({u})" if u and u.startswith("http") else f"{src}: {t}"
        if label not in applied_benchmarks:
            applied_benchmarks.append(label)

    return rag_context, applied_benchmarks
