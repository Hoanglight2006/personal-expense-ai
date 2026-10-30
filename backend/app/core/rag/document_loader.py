"""Document Loader & Recursive Chunking Engine for RAG Knowledge Base.

Implements the GenAI Data Pipeline (Cleaning -> Recursive Character Splitting with Overlap ->
Metadata Lineage Preservation -> Caching) for raw Markdown (.md), PDF (.pdf), and Text (.txt) documents.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, NotRequired, TypedDict

logger = logging.getLogger(__name__)

# Standard RAG chunking hyperparameters (Chapter 7 - Section 7.4.8)
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class KnowledgeDocument(TypedDict):
    id: str
    title: str
    category: str
    source_name: str
    source_url: str
    keywords: list[str]
    content: str
    chunk_id: NotRequired[str]
    chunk_index: NotRequired[int]
    total_chunks: NotRequired[int]


# Built-in source lineage registry for raw downloaded files in backend/data/knowledge_base
# Allows files on disk to remain 100% pure raw text/PDF without requiring manual YAML headers
_RAW_FILE_METADATA_REGISTRY: dict[str, dict[str, Any]] = {
    "quy_tac_50_30_20": {
        "id": "rule_50_30_20",
        "title": "Quản lý tài chính cá nhân bằng quy tắc 50/30/20 (Elizabeth Warren)",
        "category": "budgeting",
        "source_name": "VnExpress Kinh Doanh",
        "source_url": "https://vnexpress.net/quan-ly-tien-bang-quy-tac-50-30-20-4282825.html",
        "keywords": [
            "50/30/20",
            "50 30 20",
            "50-30-20",
            "quy tắc 50",
            "nhu cầu thiết yếu",
            "mong muốn",
            "tiết kiệm",
            "phân bổ ngân sách",
            "cách chia tiền",
            "chia thu nhập",
            "elizabeth warren",
        ],
    },
    "he_thong_6_chiec_lo_jars": {
        "id": "jars_system",
        "title": "Phương pháp quản lý tiền 6 chiếc lọ tài chính (JARS System - T. Harv Eker)",
        "category": "budgeting",
        "source_name": "Techcombank Blog Tài Chính",
        "source_url": "https://techcombank.com/thong-tin/blog/6-chiec-lo-tai-chinh-ca-nhan",
        "keywords": [
            "6 chiếc lọ",
            "sáu chiếc lọ",
            "jars",
            "harv eker",
            "chia tiền 6 lọ",
            "hũ tài chính",
            "quỹ tự do tài chính",
            "phương pháp 6 lọ",
        ],
    },
    "quy_du_phong_khan_cap": {
        "id": "emergency_fund",
        "title": "Quỹ Dự phòng Khẩn cấp (Emergency Fund): Cần để dành bao nhiêu tiền phòng thân?",
        "category": "risk_management",
        "source_name": "VnExpress & Timo Digital Bank",
        "source_url": "https://vnexpress.net/can-de-danh-bao-nhieu-tien-phong-than-4908291.html",
        "keywords": [
            "quỹ khẩn cấp",
            "dự phòng",
            "tiền phòng thân",
            "rủi ro",
            "mất việc",
            "ốm đau",
            "an toàn tài chính",
            "quỹ dự phòng",
        ],
    },
    "bieu_thue_tncn_viet_nam": {
        "id": "vietnam_pit_regulations",
        "title": "Biểu thuế Thu nhập Cá nhân (TNCN) lũy tiến từng phần và Mức giảm trừ gia cảnh",
        "category": "regulations",
        "source_name": "Cổng TTĐT Chính phủ & Thư Viện Pháp Luật",
        "source_url": "https://xaydungchinhsach.chinhphu.vn/chi-tiet-bieu-thue-thu-nhap-ca-nhan-luy-tien-tung-phan-119260327091407544.htm",
        "keywords": [
            "thuế tncn",
            "thuế thu nhập",
            "giảm trừ gia cảnh",
            "lũy tiến",
            "tính thuế",
            "luật thuế",
            "bậc thuế",
            "người phụ thuộc",
        ],
    },
    "chien_luoc_tra_no": {
        "id": "debt_reduction",
        "title": "Chiến thuật trả nợ kiểu Tuyết lở (Avalanche) và Quả cầu tuyết (Snowball)",
        "category": "debt_management",
        "source_name": "Chứng khoán DNSE & Prudential",
        "source_url": "https://www.dnse.com.vn/hoc/phuong-phap-qua-cau-tuyet",
        "keywords": [
            "trả nợ",
            "xóa nợ",
            "nợ thẻ tín dụng",
            "lãi suất cao",
            "snowball",
            "avalanche",
            "quả cầu tuyết",
            "tuyết lở",
            "khoản nợ",
            "vay tiền",
        ],
    },
    "kiem_soat_chi_tieu_tri_hoan_24h": {
        "id": "spending_habits",
        "title": "Kiểm soát chi tiêu ngẫu hứng & Tâm lý tiêu dùng (Quy tắc trì hoãn 24 giờ / 30 ngày)",
        "category": "habits",
        "source_name": "Báo Dân Trí & CafeF",
        "source_url": "https://dantri.com.vn/kinh-doanh/meo-don-gian-giup-ban-tranh-mua-sam-boc-dong-giu-tien-trong-tui-20260725083137900.htm",
        "keywords": [
            "mua sắm ngẫu hứng",
            "mua sắm bốc đồng",
            "trì hoãn 24h",
            "trì hoãn 24 giờ",
            "tiết kiệm tiền",
            "cắt giảm chi phí",
            "thói quen chi tiêu",
            "trả cho mình trước",
        ],
    },
    "dinh_muc_ngan_sach_chuan": {
        "id": "financial_health_benchmarks",
        "title": "Khung Tiêu Chuẩn Đánh Giá Sức Khỏe Tài Chính & Định Mức Ngân Sách Gia Đình",
        "category": "benchmarks",
        "source_name": "VnExpress Kinh Doanh",
        "source_url": "https://vnexpress.net/quy-tac-chi-tieu-gia-dinh-trong-thoi-kho-khan-vnepre-4864535.html",
        "keywords": [
            "tiêu chuẩn tài chính",
            "tỷ lệ tiết kiệm",
            "định mức ngân sách",
            "sức khỏe tài chính",
            "hạn mức chi tiêu",
            "tỷ trọng danh mục",
            "chuẩn tài chính",
        ],
    },
    "tai_chinh_ca_nhan_dh_mo_tphcm": {
        "id": "pdf_tai_chinh_ca_nhan_dh_mo_tphcm",
        "title": "Đề cương & Tài liệu Tài chính Cá nhân (Personal Finance - Đại học Mở TP.HCM)",
        "category": "handbook",
        "source_name": "Trường Đại học Mở TP.HCM (PDF)",
        "source_url": "https://sdh.ou.edu.vn/asset/ckfinder/userfiles/5/files/FIN617_Tai%20chinh%20ca%20nhan_Personal%20finance.pdf",
        "keywords": [
            "tài chính cá nhân",
            "personal finance",
            "đại học mở",
            "lập kế hoạch tài chính",
            "quản trị rủi ro",
            "hưu trí",
            "tín dụng cá nhân",
            "pdf",
        ],
    },
    "tap_chi_khoa_hoc_quan_ly_tai_chinh_ca_nhan_dh_hue": {
        "id": "pdf_tap_chi_khoa_hoc_quan_ly_tai_chinh_ca_nhan_dh_hue",
        "title": "Nghiên cứu các yếu tố ảnh hưởng đến hành vi Quản lý Tài chính Cá nhân (Tạp chí Khoa học ĐH Huế)",
        "category": "handbook",
        "source_name": "Tạp chí Khoa học Đại học Huế (PDF)",
        "source_url": "https://jos.hueuni.edu.vn/index.php/hujos-ed/article/download/7911/2252/35807",
        "keywords": [
            "hành vi quản lý tài chính",
            "kiến thức tài chính",
            "thái độ tài chính",
            "tạp chí khoa học đại học huế",
            "kiểm soát chi tiêu",
            "pdf",
        ],
    },
}


_LOADED_CACHE: list[KnowledgeDocument] | None = None
_CACHE_MTIME: float = 0.0

_CHUNKED_CACHE: dict[tuple[int, int], list[KnowledgeDocument]] = {}
_CHUNKED_CACHE_MTIME: float = 0.0


def _find_knowledge_dir() -> Path | None:
    """Locate backend/data/knowledge_base relative to current file or workspace."""
    base_dir = Path(__file__).resolve()
    candidates = [
        base_dir.parents[3] / "data" / "knowledge_base",
        base_dir.parents[4] / "backend" / "data" / "knowledge_base",
        Path.cwd() / "data" / "knowledge_base",
        Path.cwd() / "backend" / "data" / "knowledge_base",
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _clean_extracted_text(text: str) -> str:
    """Clean raw document text before chunking (normalize newlines, strip noise & page numbers)."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in cleaned.split("\n"):
        line = re.sub(r"[ \t]{2,}", " ", raw_line).strip()
        # Drop standalone page number lines common in raw PDFs (e.g. "Trang 2/10", "Page 3", "- 4 -")
        if re.match(r"^(?:trang|page)?\s*[-–]?\s*\d+\s*(?:/\s*\d+)?\s*[-–]?$", line, flags=re.IGNORECASE):
            continue
        lines.append(line)

    joined = "\n".join(lines)
    # Collapse 3+ consecutive newlines into standard paragraph breaks
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def _extract_word_aligned_tail(text: str, max_len: int) -> str:
    """Extract a trailing slice of at most `max_len` characters aligned to a clean word boundary."""
    if max_len <= 0 or not text:
        return ""
    if len(text) <= max_len:
        return text.strip()

    raw_tail = text[-max_len:]
    # If cut occurred in the middle of a word, advance past the first whitespace
    if not text[-max_len - 1].isspace():
        ws_match = re.search(r"\s+", raw_tail)
        if ws_match:
            aligned = raw_tail[ws_match.end():].strip()
            if aligned:
                return aligned
    return raw_tail.strip()


def _joined_units(units: list[tuple[str, str]]) -> str:
    """Join `(unit_text, trailing_separator)` pairs into a single string."""
    if not units:
        return ""
    parts: list[str] = []
    for idx, (u_text, u_sep) in enumerate(units):
        parts.append(u_text)
        if idx < len(units) - 1:
            parts.append(u_sep if u_sep else " ")
    return "".join(parts).strip()


def _decompose_to_units(
    segment: str,
    trailing_sep: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[tuple[str, str]]:
    """Recursively split an oversized text segment along natural boundaries."""
    segment = segment.strip()
    if not segment:
        return []
    if len(segment) <= chunk_size:
        return [(segment, trailing_sep)]

    chosen_sep = ""
    remaining_seps: list[str] = []
    for idx, sep in enumerate(separators):
        if sep == "":
            chosen_sep = ""
            remaining_seps = []
            break
        if sep in segment:
            chosen_sep = sep
            remaining_seps = separators[idx + 1:]
            break

    # Character-level fallback when no natural separator exists in an unbroken string
    if chosen_sep == "":
        step = max(1, chunk_size - chunk_overlap)
        slices: list[tuple[str, str]] = []
        pos = 0
        while pos < len(segment):
            piece = segment[pos : pos + step]
            pos += step
            this_sep = trailing_sep if pos >= len(segment) else ""
            slices.append((piece, this_sep))
        return slices

    if chosen_sep == ". ":
        raw_parts = segment.split(". ")
        parts = [p + "." for p in raw_parts[:-1]] + [raw_parts[-1]]
        inner_sep = " "
    else:
        parts = segment.split(chosen_sep)
        inner_sep = chosen_sep

    clean_parts = [p.strip() for p in parts if p.strip()]
    if len(clean_parts) <= 1:
        return _decompose_to_units(segment, trailing_sep, chunk_size, chunk_overlap, remaining_seps)

    result: list[tuple[str, str]] = []
    for idx, part in enumerate(clean_parts):
        part_sep = trailing_sep if idx == len(clean_parts) - 1 else inner_sep
        if len(part) <= chunk_size:
            result.append((part, part_sep))
        else:
            result.extend(
                _decompose_to_units(part, part_sep, chunk_size, chunk_overlap, remaining_seps)
            )
    return result


def recursive_split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    separators: list[str] | None = None,
) -> list[str]:
    """Split raw text recursively into semantic chunks with overlap.

    Priority order defaults to `["\\n\\n", "\\n", ". ", " ", ""]` so paragraphs,
    lines, sentences, and words stay intact before falling back to hard cuts.
    """
    cleaned = _clean_extracted_text(text)
    if not cleaned:
        return []

    chunk_size = max(50, int(chunk_size))
    chunk_overlap = max(0, min(int(chunk_overlap), chunk_size // 2))

    if len(cleaned) <= chunk_size:
        return [cleaned]

    active_seps = list(separators) if separators is not None else list(DEFAULT_SEPARATORS)
    if "" not in active_seps:
        active_seps.append("")

    units = _decompose_to_units(cleaned, "", chunk_size, chunk_overlap, active_seps)
    if not units:
        return []

    chunks: list[str] = []
    buffer: list[tuple[str, str]] = []

    for unit_text, unit_sep in units:
        if not buffer:
            buffer.append((unit_text, unit_sep))
            continue

        # Keep section/chapter headings (## / ### / Chương N) attached to their own body rather than the prior section
        is_new_section_heading = bool(re.match(r"^(?:#{1,4}\s+\S|Chương\s+\d+\s*[:.-])", unit_text))
        has_body_paragraph = any(
            not re.match(r"^(?:#{1,4}\s+|Nguồn trích dẫn:|---)", u[0], flags=re.IGNORECASE)
            for u in buffer
        )
        if is_new_section_heading and has_body_paragraph and len(_joined_units(buffer)) >= 120:
            emitted_section = _joined_units(buffer)
            if emitted_section:
                chunks.append(emitted_section)
            buffer = [(unit_text, unit_sep)]
            continue

        joiner = buffer[-1][1] if buffer[-1][1] is not None else " "
        candidate_len = len(_joined_units(buffer)) + len(joiner) + len(unit_text)
        if candidate_len <= chunk_size:
            buffer.append((unit_text, unit_sep))
            continue

        # Flush current buffer as a completed chunk
        emitted = _joined_units(buffer)
        if emitted:
            chunks.append(emitted)

        # Retain natural unit-level overlap where possible
        while buffer:
            rem_text = _joined_units(buffer)
            rem_joiner = buffer[-1][1] if buffer[-1][1] is not None else " "
            if len(rem_text) <= chunk_overlap and (len(rem_text) + len(rem_joiner) + len(unit_text) <= chunk_size):
                break
            buffer.pop(0)

        # If unit-level pop emptied buffer (e.g. previous paragraph > chunk_overlap), carry a word-aligned tail
        if not buffer and chunk_overlap > 0 and emitted:
            tail_sep = "" if unit_sep == "" and " " not in emitted else " "
            max_tail = min(chunk_overlap, chunk_size - len(unit_text) - len(tail_sep))
            if max_tail >= 8:
                tail = _extract_word_aligned_tail(emitted, max_tail)
                if tail and (len(tail) + len(tail_sep) + len(unit_text) <= chunk_size):
                    buffer.append((tail, tail_sep))

        buffer.append((unit_text, unit_sep))

    if buffer:
        final_chunk = _joined_units(buffer)
        if final_chunk and (not chunks or final_chunk != chunks[-1]):
            chunks.append(final_chunk)

    return chunks


def chunk_document(
    doc: KnowledgeDocument,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[KnowledgeDocument]:
    """Split a single KnowledgeDocument into metadata-enriched chunks."""
    pieces = recursive_split_text(
        doc.get("content", ""),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not pieces:
        return []

    total = len(pieces)
    doc_id = doc["id"]
    chunked_docs: list[KnowledgeDocument] = []
    active_source_name = doc["source_name"]
    active_source_url = doc["source_url"]

    for idx, piece in enumerate(pieces, start=1):
        # Track inline "Nguồn trích dẫn: <Name> - <URL>" markers across multi-article raw files
        src_match = re.search(
            r"Nguồn trích dẫn:\s*([^-\n]+?)\s*-\s*(https?://\S+)",
            piece,
            flags=re.IGNORECASE,
        )
        if src_match:
            active_source_name = src_match.group(1).strip()
            active_source_url = src_match.group(2).strip()

        chunked_docs.append({
            "id": doc_id,
            "chunk_id": f"{doc_id}#chunk_{idx}",
            "chunk_index": idx,
            "total_chunks": total,
            "title": doc["title"],
            "category": doc["category"],
            "source_name": active_source_name,
            "source_url": active_source_url,
            "keywords": list(doc.get("keywords", [])),
            "content": piece,
        })

    return chunked_docs


def _parse_markdown_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse optional YAML frontmatter enclosed in --- at top of markdown file."""
    metadata: dict[str, Any] = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        header = match.group(1)
        body = match.group(2).strip()

        for line in header.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if v.startswith("[") and v.endswith("]"):
                    try:
                        parsed_list = json.loads(v)
                        metadata[k] = parsed_list
                    except Exception:
                        items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                        metadata[k] = items
                else:
                    metadata[k] = v

    return metadata, _clean_extracted_text(body)


def _derive_auto_keywords(stem: str, title: str) -> list[str]:
    """Generate baseline search keywords for raw documents lacking YAML frontmatter."""
    clean_stem = stem.replace("_", " ").replace("-", " ").strip().lower()
    keywords = [clean_stem]
    title_words = [w.lower() for w in re.findall(r"\w+", title) if len(w) > 2]
    if len(title_words) >= 2:
        keywords.append(" ".join(title_words[:3]))
    return list(dict.fromkeys(k for k in keywords if k))


def _load_pdf_file(pdf_path: Path) -> KnowledgeDocument | None:
    """Extract text and metadata from a raw PDF document using pypdf."""
    try:
        import pypdf

        reader = pypdf.PdfReader(str(pdf_path))
        text_pages: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                cleaned_page = _clean_extracted_text(t)
                if cleaned_page:
                    text_pages.append(cleaned_page)
        content = "\n\n".join(text_pages).strip()
        if not content:
            return None

        reg = _RAW_FILE_METADATA_REGISTRY.get(pdf_path.stem, {})
        clean_stem = pdf_path.stem.replace("_", " ").replace("-", " ").title()
        pdf_meta_title = ""
        if reader.metadata and getattr(reader.metadata, "title", None):
            candidate_title = str(reader.metadata.title).strip()
            if candidate_title and candidate_title.lower() not in ("untitled", "none", "anonymous"):
                pdf_meta_title = candidate_title

        title = str(reg.get("title") or pdf_meta_title or f"Tài liệu PDF: {clean_stem}")
        doc_id = str(reg.get("id") or f"pdf_{pdf_path.stem}")
        source_name = str(reg.get("source_name") or f"Tài liệu PDF: {pdf_path.name}")
        source_url = str(reg.get("source_url") or "local_pdf")
        auto_kws = _derive_auto_keywords(pdf_path.stem, title)
        reg_kws = reg.get("keywords", [])
        base_kws = list(dict.fromkeys([*reg_kws, *auto_kws, "pdf", "cẩm nang", "tài chính"]))

        return {
            "id": doc_id,
            "title": title,
            "category": str(reg.get("category", "handbook")),
            "source_name": source_name,
            "source_url": source_url,
            "keywords": base_kws,
            "content": content,
        }
    except Exception as e:
        logger.warning("Failed to load PDF file %s: %s", pdf_path, e)
        return None


def _load_text_file(txt_path: Path) -> KnowledgeDocument | None:
    """Load a plain .txt article placed directly into the knowledge base directory."""
    try:
        raw_text = txt_path.read_text(encoding="utf-8")
        cleaned = _clean_extracted_text(raw_text)
        if not cleaned:
            return None

        reg = _RAW_FILE_METADATA_REGISTRY.get(txt_path.stem, {})
        first_line = cleaned.split("\n", 1)[0].lstrip("#").strip()
        clean_stem = txt_path.stem.replace("_", " ").replace("-", " ").title()
        title = str(reg.get("title") or (first_line if 5 <= len(first_line) <= 120 else clean_stem))
        doc_id = str(reg.get("id") or f"txt_{txt_path.stem}")

        return {
            "id": doc_id,
            "title": title,
            "category": str(reg.get("category", "article")),
            "source_name": str(reg.get("source_name") or f"Bài viết lưu trữ: {txt_path.name}"),
            "source_url": str(reg.get("source_url", "")),
            "keywords": list(reg.get("keywords") or _derive_auto_keywords(txt_path.stem, title)),
            "content": cleaned,
        }
    except Exception as e:
        logger.warning("Failed to load TXT file %s: %s", txt_path, e)
        return None


def load_knowledge_base(force_reload: bool = False) -> list[KnowledgeDocument]:
    """Load all full .md, .pdf, and .txt documents from knowledge base directory."""
    global _LOADED_CACHE, _CACHE_MTIME

    kb_dir = _find_knowledge_dir()
    if not kb_dir or not kb_dir.exists():
        logger.warning("Knowledge base directory not found.")
        return _LOADED_CACHE or []

    try:
        current_mtime = max((p.stat().st_mtime for p in kb_dir.iterdir() if p.is_file()), default=0.0)
    except Exception:
        current_mtime = 0.0

    if not force_reload and _LOADED_CACHE is not None and current_mtime == _CACHE_MTIME:
        return _LOADED_CACHE

    documents: list[KnowledgeDocument] = []

    for file_path in sorted(kb_dir.iterdir()):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext == ".md":
            try:
                raw_text = file_path.read_text(encoding="utf-8")
                meta, body = _parse_markdown_frontmatter(raw_text)
                if not body:
                    continue

                reg = _RAW_FILE_METADATA_REGISTRY.get(file_path.stem, {})
                inferred_title = file_path.stem.replace("_", " ").replace("-", " ").title()
                first_line = body.split("\n", 1)[0].strip()
                if first_line.startswith("#"):
                    heading_text = first_line.lstrip("#").strip()
                    if heading_text:
                        inferred_title = heading_text

                doc_id = str(meta.get("id") or reg.get("id") or file_path.stem)
                title = str(meta.get("title") or reg.get("title") or inferred_title)
                category = str(meta.get("category") or reg.get("category") or "general")
                source_name = str(meta.get("source_name") or reg.get("source_name") or f"Tài liệu: {file_path.name}")
                source_url = str(meta.get("source_url") or reg.get("source_url") or "")
                raw_keywords = meta.get("keywords") or reg.get("keywords")
                if isinstance(raw_keywords, str):
                    keywords = [raw_keywords]
                elif isinstance(raw_keywords, list):
                    keywords = [str(k) for k in raw_keywords]
                else:
                    keywords = _derive_auto_keywords(file_path.stem, title)

                documents.append({
                    "id": doc_id,
                    "title": title,
                    "category": category,
                    "source_name": source_name,
                    "source_url": source_url,
                    "keywords": keywords,
                    "content": body,
                })
            except Exception as e:
                logger.error("Error reading markdown doc %s: %s", file_path, e)

        elif ext == ".pdf":
            pdf_doc = _load_pdf_file(file_path)
            if pdf_doc:
                documents.append(pdf_doc)

        elif ext == ".txt":
            txt_doc = _load_text_file(file_path)
            if txt_doc:
                documents.append(txt_doc)

    _LOADED_CACHE = documents
    _CACHE_MTIME = current_mtime
    logger.info("Loaded %d full documents from %s", len(documents), kb_dir)
    return documents


def load_knowledge_chunks(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    force_reload: bool = False,
) -> list[KnowledgeDocument]:
    """Load and split all knowledge base documents into overlapping semantic chunks."""
    global _CHUNKED_CACHE, _CHUNKED_CACHE_MTIME

    docs = load_knowledge_base(force_reload=force_reload)
    cache_key = (chunk_size, chunk_overlap)

    if (
        not force_reload
        and _CHUNKED_CACHE_MTIME == _CACHE_MTIME
        and cache_key in _CHUNKED_CACHE
    ):
        return _CHUNKED_CACHE[cache_key]

    if _CHUNKED_CACHE_MTIME != _CACHE_MTIME or force_reload:
        _CHUNKED_CACHE.clear()
        _CHUNKED_CACHE_MTIME = _CACHE_MTIME

    all_chunks: list[KnowledgeDocument] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap))

    _CHUNKED_CACHE[cache_key] = all_chunks
    logger.info(
        "Indexed %d chunks (size=%d, overlap=%d) from %d documents",
        len(all_chunks),
        chunk_size,
        chunk_overlap,
        len(docs),
    )
    return all_chunks
