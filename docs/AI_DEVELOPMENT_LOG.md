# 🤖 MINH CHỨNG SỬ DỤNG AI KHI LẬP TRÌNH (AI DEVELOPMENT LOG)

> Tài liệu ghi nhận chi tiết quá trình ứng dụng **Trí tuệ Nhân tạo (AI Assistant)** vào việc phân tích nghiệp vụ (BA), thiết kế kiến trúc, sinh mã nguồn, rà soát bảo mật và kiểm thử hệ thống **Personal Expense AI**.

---

## 📌 1. KHUNG CHUẨN PROMPT 5 THÀNH PHẦN

Mọi câu lệnh Prompt trong dự án đều được thiết kế theo chuẩn **5 thành phần**:

1. **Instructions (Chỉ dẫn)**: Dùng động từ hành động rõ ràng (*“Viết”*, *“Phân tích”*, *“Thiết kế”*, *“Trích xuất”*).
2. **Context (Ngữ cảnh)**: Thiết lập vai trò (*Business Analyst, Senior Backend/AI Engineer*), môi trường kỹ thuật (*FastAPI, React 19, MySQL 8, Gemini Vision*).
3. **Input Data / Constraints (Dữ liệu đầu vào & Ràng buộc)**: Dữ liệu mẫu, giới hạn hiệu năng, bất biến số dư không âm, chống Race-condition.
4. **Examples (Ví dụ mẫu - Few-Shot)**: Đưa ra mẫu đầu vào/đầu ra mong muốn để AI hiểu đúng ngữ cảnh.
5. **Output Format (Định dạng đầu ra)**: Chỉ định định dạng phản hồi (*Markdown, Gherkin syntax, Code Python có type hints*).

---

## 📋 2. MINH CHỨNG PHÂN TÍCH NGHIỆP VỤ (BUSINESS ANALYSIS)

---

### 🔹 Ca 1: Phân Tích Nghiệp Vụ CRUD Giao Dịch & Thùng Rác (Transactions & Trash)

#### 1. Prompt của Sinh viên (Chuẩn 5 thành phần):
```text
[Context]
Với vai trò là một Business Analyst (BA) chuyên sâu về mảng Fintech, tôi đang xây dựng phân hệ Quản lý Giao dịch Thu/Chi cho ứng dụng Personal Expense AI.

[Instructions]
Hãy phân tích nghiệp vụ và liệt kê chi tiết:
1. Những yêu cầu còn thiếu trong luồng CRUD Giao dịch và Thùng rác (Recycle Bin).
2. Các trường hợp biên (Edge cases) có thể xảy ra trong thực tế.
3. Tiêu chí chấp nhận (Acceptance Criteria) theo chuẩn Gherkin (Given - When - Then).
4. Các câu hỏi nghiệp vụ cần làm rõ với khách hàng / Stakeholders.

[Input Data / Constraints]
- Hỗ trợ 2 loại: Thu nhập (Income) và Chi tiêu (Expense).
- Mỗi giao dịch bắt buộc có: Số tiền, Ngày giao dịch, Danh mục (Category), Hình thức thanh toán (Tiền mặt / Chuyển khoản).
- Bất biến số dư: Số dư khả dụng = Tổng thu - Tổng chi - Tiền đã tích lũy vào mục tiêu tiết kiệm (Số dư này tuyệt đối không được âm).
- Thùng rác hỗ trợ: Chuyển vào thùng rác (Soft-delete), Khôi phục (Restore), Xóa vĩnh viễn (Permanent delete).

[Output Format]
Trình bày Markdown rõ ràng, có tiêu đề và bảng biểu trực quan.
```

#### 2. Phản hồi của AI:
* **Yêu cầu còn thiếu**: Cần bổ sung tính năng *“Nhân bản giao dịch” (Duplicate)* để người dùng tạo nhanh các khoản chi định kỳ.
* **Edge cases quan trọng**:
  * Người dùng xóa khoản Thu nhập 10 triệu, nhưng trước đó đã tiêu hết 8 triệu và gửi tiết kiệm 2 triệu $\rightarrow$ Xóa xong ví sẽ bị **âm tiền**.
  * Người dùng khôi phục giao dịch từ thùng rác nhưng danh mục cũ đã bị xóa vĩnh viễn trước đó.
* **Acceptance Criteria (Gherkin)**:
  * *Given*: Ví có số dư khả dụng là 1.000.000 đ và có 1 khoản thu nhập 5.000.000 đ.
  * *When*: Người dùng bấm xóa khoản thu nhập 5.000.000 đ.
  * *Then*: Hệ thống chặn lại, trả về mã lỗi `400 Bad Request` kèm thông báo: *“Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm.”*

#### 3. Phần Sinh viên kiểm tra, phát hiện lỗi và hoàn thiện mã nguồn:
* **Phát hiện**: AI chỉ tính `Tổng thu - Tổng chi` mà quên mất số tiền đã trích vào **Mục tiêu tiết kiệm** (`SavingContribution`).
* **Sinh viên đã làm**: Tự viết hàm `_ensure_projected_balance()` và cơ chế khóa hàng `_lock_user_balance()` trong [transactions.py](../backend/app/api/routes/transactions.py) để ngăn chặn hoàn toàn lỗi âm ví.

---

### 🔹 Ca 2: Phân Tích Nghiệp Vụ Ngân Sách & Tiết Kiệm (Budgets & Saving Goals)

#### 1. Prompt của Sinh viên (Chuẩn 5 thành phần):
```text
[Context]
Với vai trò là Business Analyst & Product Owner, tôi đang thiết kế phân hệ Ngân sách chi tiêu tháng (Budgets) và Mục tiêu tích lũy tài chính (Saving Goals).

[Instructions]
Hãy phân tích nghiệp vụ và liệt kê:
1. Những yêu cầu còn thiếu về luồng tiền giữa Ngân sách, Mục tiêu tiết kiệm và Giao dịch hàng ngày.
2. Các Edge cases liên quan đến nạp tiền, rút tiền và phân bổ thu nhập.
3. Acceptance criteria cho tính năng cảnh báo bội chi và nạp tiền tiết kiệm.
4. Câu hỏi cần hỏi khách hàng về quy tắc hoàn tiền khi hủy mục tiêu tiết kiệm.

[Input Data / Constraints]
- Ngân sách: Hạn mức theo từng danh mục trong 1 tháng (VD: Ăn uống tháng 09/2026 là 5.000.000 đ).
- Tiết kiệm: Cho phép nạp tiền thủ công (MANUAL) hoặc tự động trích tiền khi tạo giao dịch thu nhập (INCOME_ALLOCATION). Cho phép rút một phần hoặc toàn bộ.

[Output Format]
Trình bày Markdown trực quan, ngắn gọn, đi thẳng vào các trường hợp thực tế.
```

#### 2. Phản hồi của AI:
* **Yêu cầu còn thiếu**: Cần phân biệt rõ giữa *“Hủy mục tiêu”* (`CANCELLED` - hoàn tiền về ví) và *“Hoàn thành mục tiêu”* (`COMPLETED` - đã đạt mục tiêu mua sắm).
* **Edge cases**:
  * Người dùng đặt 2 mức ngân sách trùng nhau cho cùng 1 danh mục trong cùng 1 tháng.
  * Người dùng rút số tiền tiết kiệm vượt quá số dư đang có trong quỹ tích lũy.

#### 3. Phần Sinh viên kiểm tra và hoàn thiện mã nguồn:
* **Sinh viên đã làm**: 
  * Bổ sung ràng buộc `UniqueConstraint("user_id", "category_id", "month", "year")` trong Database để chống trùng lặp.
  * Viết bảng theo dõi lịch sử rút tiền `SavingWithdrawalAllocation` trong [saving_goals.py](../backend/app/api/routes/saving_goals.py).

---

## 💻 3. MINH CHỨNG PHÁT TRIỂN & TỐI ƯU KỸ THUẬT (TECHNICAL IMPLEMENTATION)

---

### 🔹 Ca 3: Khóa Bi Quan (Pessimistic Locking) Chống Race-Condition Khi Xóa Giao Dịch

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là một Senior Backend Developer chuyên về FastAPI, SQLAlchemy và MySQL 8.0 (InnoDB).

[Instructions]
Viết hàm xóa giao dịch thu nhập (chuyển vào thùng rác) đảm bảo an toàn tuyệt đối:
- Khóa dòng dữ liệu người dùng để chống lỗi Race-condition (nhiều request xóa/rút tiền cùng lúc).
- Đảm bảo số dư khả dụng (Available Balance) không bao giờ bị âm.

[Input Data / Constraints]
- Dữ liệu: User, Transaction, SavingGoal, SavingContribution.
- Sử dụng khóa hàng: SELECT ... FOR UPDATE.
- Mã lỗi trả về khi không đủ số dư: HTTP 400 Bad Request.

[Output Format]
Code Python chuẩn PEP 8 có type hints và xử lý ngoại lệ rõ ràng.
```

#### 2. Code ban đầu do AI sinh ra:
```python
# Code ban đầu do AI tạo:
def trash_transaction(transaction_id: int, db: Session, current_user: User):
    db.query(User).filter(User.id == current_user.id).with_for_update().first()
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    # AI kiểm tra số dư rất sơ sài:
    avail_balance = get_user_available_balance(db, current_user.id)
    if txn.type == "income" and avail_balance - txn.amount < 0:
        raise HTTPException(status_code=400, detail="Không đủ số dư")
    
    txn.is_deleted = True
    db.commit()
```

#### 3. Phần Sinh viên phát hiện lỗi & Tối ưu lại:
* **Lỗi phát hiện**: AI chỉ trừ đơn thuần `txn.amount` mà **bỏ quên số tiền tiết kiệm được giải phóng (`released_savings`)** khi xóa khoản thu đã trích quỹ.
* **Code sinh viên đã sửa lại hoàn chỉnh**:
```python
# Code hoàn chỉnh sau khi sinh viên chỉnh sửa:
released_savings = sum(
    (Decimal(str(goal.current_amount)) - projected_goal_amounts[goal.id]
     for goal in linked_goals if goal.status != GoalStatus.CANCELLED),
    Decimal("0")
)
_ensure_projected_balance(
    db,
    current_user.id,
    -_balance_effect(txn.type, Decimal(str(txn.amount))) + released_savings,
    "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm."
)
```

---

### 🔹 Ca 4: Tích Hợp AI OCR Quét Hóa Đơn Bằng Google Gemini Vision (Multi-modal)

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là một AI Engineer phát triển module OCR nhận diện hóa đơn cho ứng dụng quản lý chi tiêu cá nhân bằng Google Gemini 1.5 Flash Vision.

[Instructions]
Thiết kế System Prompt và hàm Python để phân tích hình ảnh hóa đơn/biên lai chuyển tiền:
- Tự động trích xuất: Tổng số tiền (amount), Ngày giao dịch (transaction_date), Tên người bán/mô tả (description), và Gợi ý danh mục phù hợp nhất (category).

[Input Data / Constraints]
- Danh mục hệ thống gồm: "Ăn uống", "Đi lại", "Mua sắm", "Nhà ở", "Sức khỏe", "Giáo dục", "Giải trí", "Khác".
- Định dạng ngày: YYYY-MM-DD.
- Số tiền: Số nguyên dương (VND).
- Nếu ảnh mờ hoặc không phải hóa đơn, trả về lỗi rõ ràng, không được bịa số liệu.

[Examples]
Input: Ảnh hóa đơn Highlands Coffee ngày 12/09/2026 tổng 85.000 đ.
Output: {"amount": 85000, "transaction_date": "2026-09-12", "description": "Highlands Coffee", "suggested_category": "Ăn uống"}

[Output Format]
Mô hình AI bắt buộc trả về định dạng JSON thuần túy (không kèm text markdown thừa).
```

#### 2. Phản hồi của AI:
AI cung cấp prompt trích xuất JSON và hàm xử lý `extract_receipt_data()` gọi Gemini Vision API.

#### 3. Phần Sinh viên kiểm tra, rà soát và tích hợp:
* **Sinh viên đã làm**:
  * Xử lý trường hợp ảnh mờ hoặc người dùng chụp ảnh không có hóa đơn: Thêm lớp Regex kiểm tra JSON đầu ra và gán giá trị mặc định (`fallback`) an toàn.
  * Tích hợp thanh tải Fintech Overlay mượt mà trên giao diện Frontend [TransactionFormModal.jsx](../frontend/src/components/TransactionFormModal.jsx) giúp người dùng xem trước và chỉnh sửa số tiền trước khi lưu vào CSDL.

---

### 🔹 Ca 5: Xây Dựng Trợ Lý Ảo FinAI Mascot 3D & Chatbot Tư Vấn Tài Chính

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là một Frontend & UI/UX Specialist làm việc với React 19 và Vanilla CSS.

[Instructions]
Tạo component Trợ lý ảo FinAI Mascot hình đồng xu 3D nổi bật:
- Chuyển động lơ lửng bằng CSS Keyframes 100% GPU Hardware Accelerated.
- Nhấn vào nhân vật sẽ mở cửa sổ Chatbot Intercom-style kết nối với Gemini AI.
- Có hàng nút bấm gợi ý câu hỏi nhanh (Quick Prompt Chips) như: "Tháng này tôi tiêu nhiều nhất vào đâu?", "Tôi có thể tiết kiệm thêm tiền thế nào?".

[Constraints]
- Responsive hoàn hảo trên cả máy tính, tablet và mobile.
- Khi mở bàn phím ảo trên điện thoại (Mobile Keyboard), cửa sổ chat không bị tràn màn hình (sử dụng 100dvh).

[Output Format]
Component React JSX và file CSS module hóa tương ứng.
```

#### 2. Phản hồi của AI:
AI sinh ra các component `CoinAssistant.jsx`, `ChatPopup.jsx` và các keyframe `@keyframes float`.

#### 3. Phần Sinh viên kiểm tra và tối ưu:
* **Sinh viên đã làm**:
  * Thêm nút thu nhỏ/ẩn Mascot khi người dùng cần không gian làm việc.
  * Tối ưu hiển thị bong bóng thoại (`speech bubble`) tự động biến mất sau 6 giây để không gây rối mắt người dùng.

---

### 🔹 Ca 6: Thiết Kế Báo Cáo Tài Chính AI Đa Trọng Tâm, Nhận Thức Thời Gian Thực & Cảnh Báo Bội Chi

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là một Financial Analyst & AI Prompt Engineer cao cấp xây dựng module phân tích báo cáo tài chính hàng tháng cho ứng dụng Personal Expense AI.

[Instructions]
Thiết kế System Prompt và logic sinh báo cáo tài chính hàng tháng tự động với 3 chế độ trọng tâm (focus modes: comprehensive, savings, risk_alert):
- Nhận thức thời gian thực (Real-time Temporal Awareness): Phân biệt rõ thời điểm đầu tháng (mới có 1-3 ngày hoặc ít giao dịch ban đầu), giữa/cuối tháng (dữ liệu tích lũy đầy đủ), và tháng cũ (đã chốt sổ).
- Tự động đối chiếu ngân sách: Chỉ đích danh danh mục nào bị vượt hạn mức (overbudget) hoặc chạm ngưỡng cảnh báo, kèm hành động khẩn cấp.
- Đưa ra khuyến nghị chi tiêu cụ thể, khả thi thay vì các lời khuyên chung chung.

[Constraints]
- Tuyệt đối không phán xét vội vã là "người dùng tiêu ít/tiết kiệm vượt trội" khi thực chất họ chỉ mới bắt đầu 1-2 ngày đầu tháng.
- Định dạng xuất Markdown chuyên nghiệp, có icon, bảng tóm tắt và hành động khuyến nghị rõ ràng.
```

#### 2. Phản hồi của AI:
AI cung cấp prompt khung và hàm `generate_monthly_financial_report()` phân tích chi tiêu tổng quát theo tỉ lệ danh mục.

#### 3. Phần Sinh viên kiểm tra, rà soát và tối ưu:
* **Lỗi & Hạn chế phát hiện**:
  * Nếu chỉ cung cấp danh sách giao dịch mà không truyền ngữ cảnh ngày trong tháng (`day_of_month`), AI sẽ nhầm lẫn giữa người dùng chi tiêu tiết kiệm với người dùng mới đang ở những ngày đầu tháng (ảo giác phân tích).
  * AI ban đầu chỉ nhận xét tổng quan mà không bám sát ngân sách từng danh mục cụ thể mà người dùng đã thiết lập.
* **Cải tiến sinh viên đã triển khai**:
  * Bổ sung trường `temporal_context` (`current_day_of_month`, `days_in_month`, `is_early_month`, `is_closed_month`) vào payload gửi tới Gemini AI, hướng dẫn AI nhận thức chính xác chu kỳ thời gian.
  * Tích hợp bảng đối chiếu ngân sách (`actual_spent` vs `budget_amount`) vào prompt, buộc AI phải cảnh báo danh mục vượt ngưỡng ngay phần đầu báo cáo.
  * Xây dựng giao diện Tab 3 chế độ (`AiReportTab.jsx`) cho phép người dùng chuyển đổi linh hoạt giữa Toàn diện, Tiết kiệm và Cảnh báo rủi ro.

---

### 🔹 Ca 7: Kiến Trúc RAG Tri Thức Tài Chính & Bộ Lọc Precision Gating

#### 1. Prompt của Sinh viên (Chuẩn 5 thành phần):
```text
[Context]
Bạn là Senior AI Architect chuyên về Retrieval-Augmented Generation (RAG) và NLP tiếng Việt.

[Instructions]
Thiết kế module truy xuất tri thức RAG (retriever.py) kết hợp giữa tài liệu nội bộ (.md, .pdf) và câu hỏi của người dùng:
1. Đảm bảo khi người dùng hỏi về phương pháp tài chính (50/30/20, 6 chiếc lọ, quỹ khẩn cấp), hệ thống trích xuất đúng tài liệu chuẩn và đính kèm nguồn tham khảo chính xác.
2. Thiết kế cơ chế phân loại ý định (Intent Gating): Nếu người dùng chỉ tra cứu số liệu cá nhân ("Thống kê ăn uống tháng này", "Số dư hiện tại"), tuyệt đối KHÔNG trích xuất RAG và KHÔNG gắn link bài viết ngoài lề.
3. Khi người dùng hỏi so sánh nhiều phương pháp, phải lấy đủ tài liệu từ các nhóm khác nhau, không bị chiếm chỗ bởi một tài liệu duy nhất.

[Constraints]
- Bộ nhớ ngữ cảnh ngắn gọn, tối ưu token đầu vào.
- Trả về danh sách KnowledgeDocument có độ liên quan cao (min_score threshold).

[Output Format]
Mã nguồn Python hoàn chỉnh cho module retriever.py kèm giải thích thuật toán tính điểm.
```

#### 2. Phản hồi của AI:
AI đề xuất hàm `retrieve_relevant_knowledge()` tính điểm theo Bigram/Unigram và gọi DuckDuckGo tìm kiếm trực tuyến khi thiếu dữ liệu.

#### 3. Phần Sinh viên kiểm tra, phát hiện lỗi và tối ưu hóa:
* **Lỗi & Hạn chế phát hiện**:
  * **Ô nhiễm nguồn tham khảo cá nhân**: Các từ tiếng Việt phổ biến như `"chi tiêu"`, `"ăn uống"`, `"tháng này"` bị AI kích hoạt tìm kiếm Web mẫu Excel ngoài lề, gắn link nguồn tham khảo lung tung khi người dùng chỉ hỏi số dư cá nhân.
  * **Thiên lệch tài liệu khi so sánh**: Khi người dùng hỏi *"So sánh 50/30/20 và 6 chiếc lọ"*, thuật toán chấm điểm của AI chỉ lấy 3 đoạn trích của bài 6 chiếc lọ mà bỏ quên bài 50/30/20.
* **Cải tiến sinh viên đã triển khai**:
  * Xây dựng danh sách mẫu truy vấn số liệu cá nhân `_PERSONAL_STATS_PATTERNS` kết hợp `_KNOWLEDGE_METHOD_SIGNALS` trong [`retriever.py`](../backend/app/core/rag/retriever.py): nếu người dùng chỉ hỏi tra cứu tài chính cá nhân, trả về ngay mảng rỗng `[]` để dùng trực tiếp `financial_context`.
  * Bổ sung cơ chế **Đa dạng hóa nguồn khi so sánh**: Đảm bảo phân bổ đều các đoạn trích từ các `doc_id` khác nhau.
  * Viết 22 ca kiểm thử chuyên sâu trong [`test_rag.py`](../backend/tests/test_rag.py) kiểm chứng độ chính xác 100%.

---

### 🔹 Ca 8: Phân Hệ Quản Trị Hệ Thống (Admin) Bảo Vệ Dữ Liệu Riêng Tư (Zero-Knowledge Privacy)

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là Security & Software Architect thiết kế phân hệ Quản trị viên (System Administrator) cho ứng dụng tài chính cá nhân Personal Expense AI.

[Instructions]
Thiết kế kiến trúc RBAC và các API Admin đáp ứng 3 mục tiêu:
1. Quản lý tài khoản (khóa/mở khóa tài khoản khi có dấu hiệu vi phạm, cấp mật khẩu tạm thời khi người dùng mất tài khoản).
2. Giám sát tài nguyên hệ thống và chi phí gọi Gemini AI (tần suất gọi, tổng token sử dụng, tỉ lệ lỗi).
3. Đảm bảo nguyên tắc bảo mật Zero-Knowledge Privacy: Quản trị viên tuyệt đối không thể đọc lén giao dịch thu/chi, số dư hoặc nội dung chat riêng tư của bất kỳ người dùng nào.

[Constraints]
- Phân quyền chặt chẽ thông qua JWT Role-based Access Control (User / Admin).
- API Admin không bao giờ trả về trường Transaction.description, amount hoặc nội dung hội thoại cá nhân.

[Output Format]
Lược đồ API, Pydantic Schema và middleware kiểm tra quyền hạn.
```

#### 2. Phản hồi của AI:
AI sinh ra các endpoint trong router `/api/v1/admin` kèm bảng dữ liệu người dùng cơ bản.

#### 3. Phần Sinh viên kiểm tra và hoàn thiện:
* **Lỗi & Rủi ro phát hiện**: Code ban đầu của AI có endpoint trả về `user_stats` chứa tổng thu chi lũy kế của người dùng, vi phạm nguyên tắc Zero-Knowledge.
* **Sinh viên đã làm**: 
  * Loại bỏ triệt để mọi dữ liệu tài chính cá nhân khỏi phản hồi của Admin; thay vào đó chỉ thống kê `total_users`, `active_users`, `total_ai_requests` và bảng nhật ký ẩn danh `ai_usage_logs`.
  * Viết bộ kiểm thử bảo mật độc lập trong [`test_admin.py`](../backend/tests/test_admin.py) đảm bảo tài khoản quyền User thông thường khi truy cập endpoint Admin bị chặn ngay lập tức với mã lỗi `403 Forbidden`.

---

### 🔹 Ca 9: Tự Động Hóa Kiểm Thử & Kiểm Thử Hồi Quy (Test Generation & CI/CD Verification)

#### 1. Prompt của Sinh viên:
```text
[Context]
Bạn là Senior QA Automation Engineer làm việc với Pytest và FastAPI TestClient.

[Instructions]
Dựa trên các API Giao dịch, Ngân sách, Mục tiêu tiết kiệm và RAG AI Chatbot, hãy sinh bộ kiểm thử tự động toàn diện:
- Kiểm thử các ca biên (Edge cases): số dư âm, trùng lặp ngân sách, khôi phục từ thùng rác khi danh mục đã bị xóa.
- Mocking an toàn các dịch vụ bên thứ ba (Google Gemini API) để test suite chạy offline độc lập không phụ thuộc Internet.
- Đảm bảo tỷ lệ bao phủ mã nguồn cao và tốc độ thực thi nhanh.
```

#### 2. Phản hồi của AI:
AI cung cấp các hàm fixture pytest và mock `AsyncMock` cho Google GenerativeAI.

#### 3. Phần Sinh viên kiểm tra và tối ưu:
* **Lỗi phát hiện**: Mock của AI bị thiếu cấu trúc đối tượng `response.text`, gây ra lỗi `AttributeError` khi chạy test chat và report.
* **Sinh viên đã làm**: 
  * Chuẩn hóa mock response trả về đúng cấu trúc đối tượng `AsyncMock(text="...")`.
  * Xây dựng trọn bộ **190 tests backend và 71 tests frontend** chạy tự động qua luồng GitHub Actions CI, đảm bảo tỷ lệ vượt qua 100% (*Zero Regression*).

---

## 📊 4. BẢNG TỔNG HỢP CÁC PROMPT TRONG DỰ ÁN

| STT | Phân hệ / Nhiệm vụ | Vai trò (Role) | Kỹ thuật Prompt | Đóng góp & Tinh chỉnh của Sinh viên |
|:---:|---|---|---|---|
| **1** | **Xác thực JWT** | Security Engineer | Instructions + Constraints | Kiểm tra regex mật khẩu, chuẩn hóa email chữ thường, bắt lỗi 401 |
| **2** | **Quản lý Thùng rác** | Business Analyst | Instructions + Edge Cases + Gherkin AC | Viết logic kiểm tra số dư âm và chặn khôi phục khi danh mục đã bị xóa |
| **3** | **Khóa Concurrency DB** | Database Specialist | Context + Constraints (InnoDB `FOR UPDATE`) | Bổ sung tính toán hoàn tiền trích tiết kiệm (`released_savings`) |
| **4** | **AI OCR Hóa đơn** | AI Engineer | Few-Shot Examples + JSON Schema | Thêm lớp Regex kiểm tra JSON, validate số tiền dương và fallback an toàn |
| **5** | **Trợ lý ảo FinAI 3D** | UI/UX Specialist | Instructions + Constraints (`100dvh`) | Tối ưu responsive trên màn hình điện thoại và thêm tính năng ẩn mascot |
| **6** | **Tạo Dữ liệu mẫu (Seed)** | Backend Engineer | Context + Instructions + Constraints | Sửa lỗi encoding UTF-8 trên Windows console và nạp sẵn 74 giao dịch demo |
| **7** | **Báo cáo AI & Bội chi** | Financial Analyst | Temporal Awareness + Multi-focus Prompt | Thêm ngữ cảnh ngày đầu tháng, đối chiếu ngân sách từng danh mục, ngăn ảo giác phân tích |
| **8** | **RAG Tri thức tài chính** | RAG Architect | Intent Gating + Chunk Scoring + Precision Gate | Xây dựng bộ lọc rẽ nhánh: tra cứu cá nhân không gắn link ngoài; so sánh đa phương pháp |
| **9** | **Admin Zero-Knowledge** | Security Architect | Zero-Knowledge RBAC + Privacy by Design | Loại bỏ triệt để dữ liệu chi tiêu cá nhân khỏi API Admin; chỉ giám sát token hệ thống |
| **10** | **Kiểm thử tự động** | QA Automation Engineer | Test Generation + Pytest Mocking | Chuẩn hóa mock Gemini AsyncMock, bao phủ 190 test cases backend và 71 test frontend |

---

## ⏱️ 5. BẢNG ĐO LƯỜNG THỰC NGHIỆM ĐỊNH LƯỢNG SDLC (BÀI THỰC HÀNH 5)

> Bảng đối chứng thực tế giữa phương thức phát triển truyền thống (thủ công) và phương thức có AI hỗ trợ (AI-augmented SDLC) trên các nhóm tác vụ của dự án:

| Pha hoạt động SDLC | Tác vụ cụ thể | Thời gian thủ công (Ước lượng) | Thời gian có AI hỗ trợ (Thực tế) | Tiết kiệm (%) | Số lỗi AI sinh ra (Bị bắt ở Review) | Tỉ lệ Code Churn (Code phải sửa tay) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Phân tích (BA)** | Viết User Stories & Acceptance Criteria Gherkin | 8.0 giờ | 2.5 giờ | **68.8%** | 3 lỗi logic thiếu trường hợp biên | 15% bổ sung thêm điều kiện số dư âm |
| **Thiết kế CSDL** | Thiết kế ERD, Index, Unique Constraints | 6.0 giờ | 2.0 giờ | **66.7%** | 1 lỗi thiếu bảng trung gian nạp/rút | 20% chỉnh sửa kiểu dữ liệu Decimal |
| **Lập trình Backend** | Viết CRUD, Service layer, Schemas Pydantic | 22.0 giờ | 8.0 giờ | **63.6%** | 4 lỗi Race-condition & SQL Injection | 30% viết lại logic khóa hàng `with_for_update` |
| **Tích hợp AI & RAG** | Xây dựng Pipeline RAG chunking & Intent filter | 16.0 giờ | 5.5 giờ | **65.6%** | 5 lỗi trích dẫn sai và ảo giác nguồn | 25% viết lại bộ lọc `_PERSONAL_STATS_PATTERNS` |
| **Kiểm thử (QA/Testing)**| Viết 190 Unit/Integration test cases | 20.0 giờ | 6.0 giờ | **70.0%** | 6 lỗi mock response thiếu attribute | 18% chỉnh sửa fixture database |
| **Tài liệu kỹ thuật** | Viết API doc, Database doc, System Arch | 10.0 giờ | 2.5 giờ | **75.0%** | 2 lỗi mô tả sai port container | 10% đồng bộ lại thông số thực tế |
| **TỔNG CỘNG** | **Toàn bộ vòng đời phát triển dự án** | **82.0 giờ** | **26.5 giờ** | **67.7%** | **21 lỗi được chặn ở bước Review** | **Bình quân 19.6%** |

---

## 🔬 6. THỰC NGHIỆM ĐỐI CHỨNG TỐI ƯU PROMPT QUA 3 VÒNG LẶP (TIÊU CHÍ 4)

> Toàn bộ prompt của hệ thống được tách biệt hoàn toàn khỏi mã nguồn tại [`config/prompts.json`](../config/prompts.json) và được quản lý tập trung bởi module [`backend/app/core/prompts.py`](../backend/app/core/prompts.py).
> 
> Đã tiến hành thực nghiệm benchmark đối chứng tự động bằng script [`scripts/benchmark_prompts.py`](../scripts/benchmark_prompts.py). Xem chi tiết báo cáo tại: [**`docs/PROMPT_BENCHMARK_REPORT.md`**](PROMPT_BENCHMARK_REPORT.md).

### Bảng Tổng Hợp Kết Quả 3 Vòng Thử Nghiệm Prompt:

| Chỉ số / Tiêu chí | Vòng 1 (V1 - Naive) | Vòng 2 (V2 - Constrained) | Vòng 3 (V3 - Production Hiện tại) |
|---|---|---|---|
| **Cấu trúc Prompt** | Zero-shot thô, không ràng buộc | Thêm luật cấm ngoài lề & JSON cơ bản | Chuẩn 5 thành phần + Regex Masking + Schema |
| **Bảo vệ Dữ liệu Nhạy cảm (PII)** | ❌ Lộ STK ngân hàng và mã giao dịch | ⚠️ Chỉ nhắc bằng text, dễ bị AI bỏ qua | ✅ **100% che giấu STK, Thẻ, Mã GD qua Regex** |
| **Kiểm soát Phạm vi (Scope Guard)** | ❌ Trả lời lan man (thời tiết, làm thơ) | ✅ Từ chối câu hỏi ngoài lề | ✅ **Phản hồi vui vẻ + Nudge về số dư khả dụng** |
| **Độ tin cậy Định dạng (Format)** | ❌ Văn bản tự do, Frontend không parse được | ⚠️ JSON không theo schema, thiếu trường | ✅ **JSON Schema chuẩn 4 trường, parse 100%** |
| **Tối ưu Token & Thời gian** | ❌ Dài dòng (> 600 tokens), phản hồi chậm | ✅ Đã rút ngắn độ dài | ✅ **Tối đa 100 từ, phản hồi < 1.5s, tiết kiệm 50% token** |
| **Điểm Đánh giá Kỹ thuật** | **3.5 / 10** | **6.8 / 10** | **9.6 / 10 (ĐẠT CHUẨN XUẤT SẮC)** |

---

## 💡 7. ĐÁNH GIÁ VÀ BÀI HỌC KINH NGHIỆM

1. 🎯 **Làm chủ cấu trúc Prompt 5 thành phần**: Việc xác định rõ **Context**, **Constraints** và **Output Format** giúp AI hiểu chính xác yêu cầu, giảm thiểu tối đa các câu trả lời sai lệch (*hallucination*).
2. 🛡️ **Nguyên tắc "Zero Trust" khi tích hợp Code AI**: Không bao giờ sao chép nguyên văn mã nguồn AI sinh ra ở các phần xử lý tiền tệ và bảo mật. Lập trình viên phải luôn đọc hiểu, rà soát trường hợp biên và viết test tự động để nghiệm thu.
3. ⚡ **Tách biệt Prompt khỏi Code**: Lưu trữ cấu trúc prompt tập trung tại `config/prompts.json` giúp kiểm thử A/B testing và tinh chỉnh văn phong nhanh chóng mà không cần biên dịch lại hoặc sửa đổi logic mã nguồn Python.
