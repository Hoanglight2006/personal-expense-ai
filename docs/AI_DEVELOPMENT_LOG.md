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
* **Yêu cầu còn thiếu**: Cần bổ sung tính năng *“Nhân bản giao dịch” (Duplicate)* để người dùng tạo nhanh các khoản chi định kỳ, và *“Nhập sao kê hàng loạt từ Excel”*.
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

## 📊 4. BẢNG TỔNG HỢP CÁC PROMPT TRONG DỰ ÁN

| STT | Phân hệ / Nhiệm vụ | Vai trò (Role) | Kỹ thuật Prompt | Đóng góp & Tinh chỉnh của Sinh viên |
|:---:|---|---|---|---|
| **1** | **Xác thực JWT** | Security Engineer | Instructions + Constraints | Kiểm tra regex mật khẩu, chuẩn hóa email chữ thường, bắt lỗi 401 |
| **2** | **Quản lý Thùng rác** | Business Analyst | Instructions + Edge Cases + Gherkin AC | Viết logic kiểm tra số dư âm và chặn khôi phục khi danh mục đã bị xóa |
| **3** | **Khóa Concurrency DB** | Database Specialist | Context + Constraints (InnoDB `FOR UPDATE`) | Bổ sung tính toán hoàn tiền trích tiết kiệm (`released_savings`) |
| **4** | **AI OCR Hóa đơn** | AI Engineer | Few-Shot Examples + JSON Schema | Thêm lớp Regex kiểm tra JSON, validate số tiền dương và fallback an toàn |
| **5** | **Trợ lý ảo FinAI 3D** | UI/UX Specialist | Instructions + Constraints (`100dvh`) | Tối ưu responsive trên màn hình điện thoại và thêm tính năng ẩn mascot |
| **6** | **Tạo Dữ liệu mẫu (Seed)** | Backend Engineer | Context + Instructions + Constraints | Sửa lỗi encoding UTF-8 trên Windows console và nạp sẵn 74 giao dịch demo |

---

## 💡 5. ĐÁNH GIÁ VÀ BÀI HỌC KINH NGHIỆM

1. 🎯 **Làm chủ cấu trúc Prompt 5 thành phần**: Việc xác định rõ **Context**, **Constraints** và **Output Format** giúp AI hiểu chính xác yêu cầu, giảm thiểu tối đa các câu trả lời sai lệch (*hallucination*).
2. 🛡️ **Nguyên tắc "Zero Trust" khi tích hợp Code AI**: Không bao giờ sao chép nguyên văn mã nguồn AI sinh ra ở các phần xử lý tiền tệ và bảo mật. Lập trình viên phải luôn đọc hiểu, rà soát trường hợp biên và viết test tự động để nghiệm thu.
3. ⚡ **Tăng tốc độ phát triển**: Ứng dụng AI giúp giảm hơn **60%** thời gian viết các đoạn code lặp lại, cho phép sinh viên tập trung tối đa vào việc hoàn thiện logic nghiệp vụ và tối ưu hóa trải nghiệm người dùng.
