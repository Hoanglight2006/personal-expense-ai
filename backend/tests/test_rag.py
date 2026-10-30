"""Test suite for RAG (Retrieval-Augmented Generation) & Recursive Chunking Engine.

Covers:
- Recursive character text splitting (chunk_size=500, chunk_overlap=50, natural boundaries)
- Multi-chunk indexing across Markdown (.md) and PDF (.pdf) documents
- Chunk-level relevance scoring & sibling noise filtering on long raw articles
- Precision filtering for irrelevant and non-financial queries
- Source citation deduplication in AI Chat endpoint
- AI Monthly Report & AI Budget Recommendation benchmark integration
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.rag import (
    DEFAULT_CHUNK_SIZE,
    FINANCIAL_KNOWLEDGE_BASE,
    KnowledgeDocument,
    format_rag_context,
    get_benchmark_knowledge,
    load_knowledge_base,
    load_knowledge_chunks,
    recursive_split_text,
    retrieve_relevant_knowledge,
)
from app.models.enums import CategoryType
from tests.test_ai import create_cat, create_txn, create_user_and_auth
from tests.test_db import TestingSessionLocal


# ---------------------------------------------------------------------------
# 1. Recursive Chunking Engine Unit Tests (Chapter 7 Pipeline)
# ---------------------------------------------------------------------------


def test_recursive_chunking_splits_with_overlap():
    """Verify recursive_split_text enforces chunk_size<=500, preserves word boundaries, and carries overlap."""
    raw_article = (
        "# Phân tích chuyên sâu chiến lược quản trị dòng tiền cá nhân\n\n"
        "Trong bối cảnh chi phí sinh hoạt đô thị ngày càng gia tăng, việc thiết lập một hệ thống kiểm soát "
        "ngân sách bài bản giúp người lao động trẻ tránh rơi vào vòng xoáy thiếu hụt tiền mặt cuối tháng. "
        "Nhiều khảo sát tài chính cho thấy hơn 60% người đi làm không nắm rõ tiền lương thực tế đã trôi về đâu.\n\n"
        "Bước quan trọng đầu tiên là tách bạch hoàn toàn tài khoản nhận lương với tài khoản chi tiêu hàng ngày. "
        "Ngay khi nhận thu nhập ròng, hãy trích lập tự động tối thiểu 20% vào quỹ tích lũy an toàn trước khi "
        "thanh toán hóa đơn điện nước, tiền thuê nhà hay mua sắm tiêu dùng cá nhân.\n\n"
        "Đối với các khoản chi biến đổi như ăn uống bên ngoài, cà phê và giải trí cuối tuần, người dùng nên đặt "
        "ngưỡng cảnh báo sớm ở mức 80% hạn mức tháng. Khi chạm ngưỡng này trước ngày 20, cần kích hoạt ngay chế độ "
        "thắt chặt tiêu dùng để bảo toàn mục tiêu tiết kiệm dài hạn đã đề ra từ đầu năm."
    )
    assert len(raw_article) > 900

    chunks = recursive_split_text(raw_article, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) <= 500, f"Chunk exceeded 500 chars: {len(chunk)}"
        assert len(chunk.strip()) > 0

    # Verify consecutive chunks share overlapping boundary context without cutting words in half
    overlap_found = False
    for i in range(len(chunks) - 1):
        prev_words = chunks[i].split()[-4:]
        if any(w in chunks[i + 1] for w in prev_words if len(w) > 2):
            overlap_found = True
            break
    assert overlap_found, "Expected semantic word overlap between adjacent chunks"


def test_knowledge_base_multi_chunk_indexing():
    """Verify that repository documents are split into <=500-char chunks with full lineage metadata."""
    docs = load_knowledge_base()
    chunks = load_knowledge_chunks()

    assert len(docs) >= 8
    assert len(chunks) >= 40
    for ch in chunks:
        assert len(ch["content"]) <= DEFAULT_CHUNK_SIZE
        assert "chunk_id" in ch
        assert ch.get("chunk_index", 0) >= 1
        assert ch.get("total_chunks", 0) >= ch.get("chunk_index", 1)
        assert ch["title"]
        assert ch["source_name"]


def test_chunk_level_filtering_drops_irrelevant_sections():
    """Verify that given a long raw article with filler sections, ONLY the relevant chunk is retrieved."""
    raw_long_doc: KnowledgeDocument = {
        "id": "raw_mixed_article",
        "title": "Bản tin tổng hợp đời sống và tài chính cuối tuần",
        "category": "article",
        "source_name": "Tạp chí Kinh tế",
        "source_url": "https://vneconomy.vn/ban-tin-tong-hop-cuoi-tuan.htm",
        "keywords": ["lãi suất bậc thang", "tiết kiệm bậc thang"],
        "content": (
            "Sáng chủ nhật tại Hà Nội thời tiết dịu mát với nắng nhẹ, nhiều gia đình lựa chọn dạo phố đi bộ "
            "Hồ Gươm thưởng thức cà phê trứng và đọc sách thư giãn sau một tuần làm việc căng thẳng kéo dài. "
            "Các quán cà phê cổ trang trí nhiều hoa tươi thu hút đông đảo bạn trẻ chụp ảnh lưu niệm.\n\n"
            "Chuyển sang chuyên mục văn hóa ẩm thực, món phở bò truyền thống ninh từ xương ống trong mười hai giờ "
            "luôn giữ vị trí đặc biệt trong lòng thực khách quốc tế mỗi dịp ghé thăm khu phố cổ mùa thu.\n\n"
            "Trong lĩnh vực ngân hàng cá nhân, hình thức gửi tiết kiệm bậc thang cho phép người gửi hưởng mức "
            "lãi suất bậc thang lũy tiến tăng dần theo quy mô số tiền gửi: khoản tiền gửi từ 500 triệu VNĐ trở lên "
            "thường được cộng biên độ ưu đãi thêm 0,3% đến 0,5%/năm so với biểu lãi suất niêm yết thông thường.\n\n"
            "Cuối bản tin là lịch chiếu phim rạp cuối tuần và chương trình khuyến mãi đăng ký nhận bản tin "
            "qua thư điện tử dành cho độc giả thân thiết trên toàn quốc."
        ),
    }

    results = retrieve_relevant_knowledge(
        "Hình thức gửi tiết kiệm lãi suất bậc thang ưu đãi thế nào?",
        top_k=3,
        custom_docs=[raw_long_doc],
        enable_web_search=False,
    )

    assert len(results) == 1
    assert results[0]["id"] == "raw_mixed_article"
    assert "500 triệu VNĐ" in results[0]["content"]
    assert "Hồ Gươm" not in results[0]["content"]
    assert "lịch chiếu phim" not in results[0]["content"]


# ---------------------------------------------------------------------------
# 2. Retriever Accuracy & Precision Unit Tests
# ---------------------------------------------------------------------------


def test_rag_retrieve_50_30_20():
    """Verify that querying about 50/30/20 retrieves the Elizabeth Warren rule chunk."""
    results = retrieve_relevant_knowledge("Quy tắc 50/30/20 là gì?", enable_web_search=False)
    assert len(results) >= 1
    assert results[0]["id"] == "rule_50_30_20"
    assert "nhu cầu thiết yếu" in results[0]["content"].lower()
    assert any("50%" in r["content"] or "50-30-20" in r["content"] for r in results)


def test_rag_retrieve_6_jars():
    """Verify that querying about 6 jars retrieves the JARS system."""
    results = retrieve_relevant_knowledge("Tôi muốn chia tiền 6 chiếc lọ", enable_web_search=False)
    assert len(results) >= 1
    assert results[0]["id"] == "jars_system"
    assert "T. Harv Eker" in results[0]["title"]


def test_rag_retrieve_emergency_fund():
    """Verify that querying about emergency funds retrieves the emergency fund scale chunk."""
    results = retrieve_relevant_knowledge(
        "Quỹ khẩn cấp nên để bao nhiêu tháng chi tiêu?",
        enable_web_search=False,
    )
    assert len(results) >= 1
    assert results[0]["id"] == "emergency_fund"
    assert any(p in results[0]["content"] for p in ("3 đến 6 tháng", "3-6 tháng", "3 – 6 tháng"))


def test_rag_retrieve_tax_regulations():
    """Verify that querying specifically about family deduction retrieves the exact deduction chunk."""
    results = retrieve_relevant_knowledge(
        "Mức giảm trừ gia cảnh thuế thu nhập cá nhân là bao nhiêu?",
        enable_web_search=False,
    )
    assert len(results) >= 1
    assert results[0]["id"] == "vietnam_pit_regulations"
    assert any(p in results[0]["content"] for p in ("15,5 triệu", "11.000.000", "11 triệu", "giảm trừ gia cảnh"))


def test_rag_precision_avoids_irrelevant():
    """Verify that unrelated or generic personal-stats queries return no external RAG chunks."""
    irrelevant_queries = [
        "thời tiết hôm nay thế nào",
        "xin chào bạn ơi",
        "hôm nay ăn gì ngon",
        "tháng này tôi chi nhiều nhất vào đâu?",
        "Thống kê chi tiêu ăn uống tháng này",
        "Phương pháp quản lý tiền của người giàu nhất thế giới là gì?",
    ]
    for q in irrelevant_queries:
        results = retrieve_relevant_knowledge(q, min_score=1.0, enable_web_search=False)
        assert results == [], f"Expected empty result for query '{q}', got {[r['id'] for r in results]}"


def test_rag_comparison_retrieves_both_methods():
    """Verify that comparing 50/30/20 and 6 Jars retrieves chunks from both documents without unrelated noise."""
    results = retrieve_relevant_knowledge(
        "So sánh phương pháp 50/30/20 với phương pháp 6 chiếc lọ. Phương pháp nào phù hợp hơn với người mới đi làm?",
        enable_web_search=False,
    )
    doc_ids = {r["id"] for r in results}
    assert "rule_50_30_20" in doc_ids
    assert "jars_system" in doc_ids
    assert "debt_reduction" not in doc_ids


def test_rag_format_context():
    """Verify formatting of retrieved knowledge chunks into a grounded prompt block."""
    sample_chunks = load_knowledge_chunks()[:1]
    formatted = format_rag_context(sample_chunks)
    assert "TÀI LIỆU & NGUYÊN TẮC TÀI CHÍNH THAM KHẢO" in formatted
    assert sample_chunks[0]["title"] in formatted
    assert "[Đoạn 1/" in formatted
    assert "HƯỚNG DẪN KẾT HỢP:" in formatted


def test_rag_get_benchmark_knowledge():
    """Verify that benchmark knowledge is generated properly for all report focus options."""
    assert len(FINANCIAL_KNOWLEDGE_BASE) >= 8

    comp = get_benchmark_knowledge("comprehensive")
    assert "Khung Tiêu Chuẩn Đánh Giá Sức Khỏe Tài Chính" in comp
    assert "50/30/20" in comp

    risk = get_benchmark_knowledge("risk")
    assert "Quỹ Dự phòng Khẩn cấp" in risk

    saving = get_benchmark_knowledge("saving")
    assert "Kiểm soát chi tiêu ngẫu hứng" in saving


def test_pdf_loading_and_deep_chunk_retrieval():
    """Verify multi-page real downloaded PDF parsing and deep chunk retrieval."""
    docs = load_knowledge_base()
    pdf_docs = [d for d in docs if d["id"].startswith("pdf_")]
    assert len(pdf_docs) >= 2
    assert any("tai_chinh_ca_nhan_dh_mo_tphcm" in d["id"] for d in pdf_docs)
    assert all(len(d["content"]) > 5000 for d in pdf_docs)

    results = retrieve_relevant_knowledge(
        "Lập kế hoạch tài chính cá nhân và quản trị rủi ro tín dụng hưu trí tại Đại học Mở?",
        enable_web_search=False,
    )
    assert len(results) >= 1
    assert any(r["id"].startswith("pdf_") for r in results)


def test_web_search_retrieval_integration():
    """Verify that financial queries seeking live info fetch full web content, chunk it, and return the best chunk."""
    long_web_article = (
        "Bản tin tổng hợp buổi sáng về tình hình thời tiết và giao thông đô thị tại các thành phố lớn trên cả nước. "
        "Nhiều tuyến đường trung tâm ghi nhận lưu lượng phương tiện tăng cao vào khung giờ cao điểm buổi sáng đầu tuần "
        "khi học sinh và nhân viên văn phòng quay trở lại làm việc sau kỳ nghỉ lễ dài ngày.\n\n"
        "Khảo sát biểu lãi suất tiết kiệm ngân hàng hôm nay cho thấy kỳ hạn 12 tháng tại nhóm ngân hàng thương mại cổ phần "
        "dao động từ 5,2% đến 6,1%/năm đối với hình thức gửi tiết kiệm trực tuyến lãnh lãi cuối kỳ. Nhiều ngân hàng "
        "cộng thêm biên độ ưu đãi 0,2%/năm cho khách hàng gửi tiết kiệm online qua ứng dụng ngân hàng số.\n\n"
        "Chuyên mục văn hóa giải trí cuối tuần giới thiệu các bộ phim điện ảnh mới ra mắt tại rạp cùng lịch biểu diễn "
        "âm nhạc ngoài trời tại phố đi bộ."
    )
    assert len(long_web_article) > DEFAULT_CHUNK_SIZE
    mock_web_results = [
        {
            "title": "Lãi suất tiết kiệm ngân hàng mới nhất tháng này",
            "snippet": "Bảng cập nhật lãi suất tiền gửi tiết kiệm kỳ hạn 6 tháng và 12 tháng.",
            "content": long_web_article,
            "source_name": "VnExpress",
            "source_url": "https://vnexpress.net/lai-suat-ngan-hang-hom-nay.html",
        }
    ]
    with patch("app.core.rag.retriever.search_online_financial_knowledge", return_value=mock_web_results):
        results = retrieve_relevant_knowledge("lãi suất ngân hàng hôm nay", enable_web_search=True)
        assert len(results) >= 1
        web_chunks = [r for r in results if r.get("source_url", "").startswith("https://vnexpress.net/lai-suat")]
        assert len(web_chunks) >= 1
        assert "5,2% đến 6,1%/năm" in web_chunks[0]["content"]
        assert "phim điện ảnh" not in web_chunks[0]["content"]
        assert len(web_chunks[0]["content"]) <= DEFAULT_CHUNK_SIZE


# ---------------------------------------------------------------------------
# 3. API Integration Tests: Chat Deduplication, Monthly Report & Budgets
# ---------------------------------------------------------------------------


def test_chat_endpoint_with_deduplicated_rag_sources(client: TestClient):
    """Test that chat endpoint returns deduplicated rag_sources even when multiple chunks match."""
    db = TestingSessionLocal()
    _, token = create_user_and_auth(client, db, "rag_chat_user@example.com")

    with patch("app.core.ai_chat.genai.GenerativeModel") as mock_model_cls, \
         patch("app.core.ai_chat.settings.GEMINI_API_KEY", "test-key"):
        mock_instance = mock_model_cls.return_value
        mock_response = AsyncMock()
        mock_response.text = (
            "Theo quy tắc 50/30/20, với mức lương 15 triệu VNĐ bạn nên dành 50% (7,5 triệu) cho thiết yếu, "
            "30% (4,5 triệu) cho mong muốn và 20% (3 triệu) cho tiết kiệm."
        )
        mock_instance.generate_content_async = AsyncMock(return_value=mock_response)

        res = client.post(
            "/api/v1/chat/message",
            json={
                "message": "Quy tắc 50/30/20 là gì và áp dụng cho lương 15 triệu thế nào?",
                "conversation_history": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "reply" in data
        assert "rag_sources" in data
        assert len(data["rag_sources"]) >= 1
        assert "50/30/20" in data["rag_sources"][0]
        # Ensure no duplicate source strings when multiple chunks come from the same article
        assert len(data["rag_sources"]) == len(set(data["rag_sources"]))

    db.close()


def test_monthly_report_includes_rag_benchmarks(client: TestClient):
    """Test that monthly report includes RAG financial benchmark references."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "rag_report_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    create_txn(db, user.id, cat_food.id, Decimal("1200000"), CategoryType.EXPENSE, date.today())

    with patch("app.core.ai.gemini_client.settings.GEMINI_API_KEY", ""):
        res = client.post(
            "/api/v1/ai/monthly-report",
            json={
                "month": f"{date.today().year}-{date.today().month:02d}",
                "focus": "saving",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert "rag_benchmarks" in data
    assert len(data["rag_benchmarks"]) >= 2
    assert any("50/30/20" in bm for bm in data["rag_benchmarks"])

    db.close()


def test_budget_recommendations_includes_rag_benchmarks(client: TestClient):
    """Test that budget recommendations endpoint includes RAG financial benchmark references."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "rag_budget_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    create_txn(db, user.id, cat_food.id, Decimal("1500000"), CategoryType.EXPENSE, date.today())

    with patch("app.core.ai.gemini_client.settings.GEMINI_API_KEY", ""):
        res = client.get(
            f"/api/v1/ai/budget-recommendations?lookback_months=3",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert "rag_benchmarks" in data
    assert len(data["rag_benchmarks"]) >= 2
    assert any("50/30/20" in bm for bm in data["rag_benchmarks"])

    db.close()


def test_retrieve_contextual_report_knowledge():
    """Verify dynamic contextual RAG retrieval for monthly report based on financial metrics."""
    from app.core.rag import retrieve_contextual_report_knowledge

    summary = {
        "health_score": 50,
        "health_status": "Cần chú ý",
        "savings_rate": 5.0,
        "exceeded_budgets_count": 1,
        "budgets": [{"category": "Ăn uống", "is_exceeded": True}],
        "top_expenses": [{"name": "Ăn uống", "amount": 2000000}],
    }
    context, benchmarks = retrieve_contextual_report_knowledge(summary, focus="saving")
    assert context != ""
    assert len(benchmarks) >= 2
    assert any("50/30/20" in bm for bm in benchmarks)

    risk_summary = {
        "health_score": 40,
        "health_status": "Nguy cơ thâm hụt",
        "savings_rate": 0.0,
        "exceeded_budgets_count": 0,
        "budgets": [],
        "top_expenses": [],
    }
    risk_ctx, risk_bm = retrieve_contextual_report_knowledge(risk_summary, focus="risk")
    assert risk_ctx != ""
    assert any("phòng thân" in bm.lower() or "dự phòng" in bm.lower() or "50/30/20" in bm for bm in risk_bm)


def test_retrieve_contextual_budget_knowledge():
    """Verify dynamic contextual RAG retrieval for budget recommendations."""
    from app.core.rag import retrieve_contextual_budget_knowledge

    items = [
        {"id": 1, "name": "Tiền nhà", "avg_monthly_spent": 3000000},
        {"id": 2, "name": "Ăn uống", "avg_monthly_spent": 2500000},
    ]
    ctx, bm = retrieve_contextual_budget_knowledge(items, target_month=11, target_year=2026)
    assert ctx != ""
    assert len(bm) >= 1
    assert any("50/30/20" in b or "tài liệu" in b.lower() or "gia đình" in b.lower() for b in bm)
