# 📋 BẢNG ĐẶC TẢ MA TRẬN TEST CASES HỆ THỐNG
> **Dự án**: Hệ thống Quản lý Chi tiêu Cá nhân Tích hợp AI (Personal Expense AI)  
> **Phiên bản tài liệu**: 1.0.0  
> **Tổng số ca kiểm thử tự động**: 189 Pytest (Backend) + 71 Vitest (14 Suites Frontend) = 260 Tests  
> **Tỷ lệ vượt qua (Pass Rate)**: 100% (Zero Regression)

---

## 🎯 1. TỔNG QUAN CHIẾN LƯỢC KIỂM THỬ (TEST STRATEGY)

Hệ thống áp dụng mô hình kim tự tháp kiểm thử (**Testing Pyramid**) kết hợp phương pháp phát triển hướng kiểm thử (**TDD/BDD**):
1. **Unit & Data Integrity Tests**: Kiểm tra tính đúng đắn của logic tính toán, xác thực Pydantic Schemas, bảo toàn tính bất biến số dư (`Balance Invariance`).
2. **Integration & Concurrency Tests**: Kiểm tra luồng gọi API, khóa bi quan hàng dữ liệu (`SELECT ... FOR UPDATE`), đồng bộ trạng thái giữa Thu nhập - Tiết kiệm - Ngân sách.
3. **Security & Authorization Tests**: Kiểm tra phân quyền đa người dùng (Multi-tenant IDOR), băm mật khẩu Bcrypt, xác thực JWT và bảo mật thông tin cá nhân (PII Masking).
4. **AI & Prompt Benchmark Tests**: Kiểm tra phản hồi của mô hình ngôn ngữ lớn (Gemini), tuân thủ định dạng JSON Schema, bẻ lái hành vi tiêu dùng và kích hoạt cơ chế dự phòng (Fallback).
5. **Frontend Component & UI Integration Tests**: Kiểm tra trạng thái giao diện, bắt sự kiện, điều phối modal/popup và xử lý Interceptor Axios.

---

## 📑 2. MA TRẬN CA KIỂM THỬ BACKEND (PYTEST MATRIX)

### 🔐 Phân hệ 1: Xác thực, Bảo mật & Người dùng (Authentication & Security)
*File kiểm thử*: [`backend/tests/test_auth.py`](../backend/tests/test_auth.py)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-AUTH-01** | Đăng ký tài khoản thành công | Email chưa tồn tại trong CSDL | Gửi POST `/api/v1/auth/register` với email hợp lệ, mật khẩu >= 6 ký tự | HTTP 201 Created; Mật khẩu được băm Bcrypt trong DB; trả về thông tin User (không lộ password) | Integration |
| **TC-AUTH-02** | Chặn đăng ký trùng Email | Email đã được đăng ký | Gửi POST `/api/v1/auth/register` với email đã có | HTTP 400 Bad Request, thông báo lỗi email đã tồn tại | Validation |
| **TC-AUTH-03** | Chặn mật khẩu yếu / sai định dạng | Không | Gửi POST `/api/v1/auth/register` với password < 6 ký tự hoặc email sai RFC format | HTTP 422 Unprocessable Entity từ Pydantic | Validation |
| **TC-AUTH-04** | Đăng nhập hợp lệ nhận Access Token | Tài khoản đã kích hoạt | Gửi POST `/api/v1/auth/login` đúng email và mật khẩu | HTTP 200 OK, trả về `access_token` định dạng JWT và `token_type: bearer` | Integration |
| **TC-AUTH-05** | Chặn đăng nhập sai mật khẩu | Tài khoản đã tồn tại | Gửi POST `/api/v1/auth/login` với mật khẩu sai | HTTP 401 Unauthorized, thông báo sai thông tin đăng nhập | Security |
| **TC-AUTH-06** | Chặn truy cập Endpoint yêu cầu Auth | Không truyền Header Authorization | Gửi GET tới `/api/v1/transactions` hoặc `/api/v1/budgets` | HTTP 401 Unauthorized, chặn từ middleware FastAPI | Security |
| **TC-AUTH-07** | Chặn Token JWT giả mạo hoặc hết hạn | Token bị sửa chữ ký hoặc exp quá hạn | Gửi request kèm Token JWT không hợp lệ | HTTP 401 Unauthorized, yêu cầu đăng nhập lại | Security |
| **TC-AUTH-08** | Đổi mật khẩu thành công | Người dùng đã đăng nhập | Gửi POST `/api/v1/auth/change-password` với mật khẩu cũ đúng và mật khẩu mới | HTTP 200 OK; Đăng nhập lại bằng mật khẩu cũ bị từ chối, mật khẩu mới thành công | Integration |

---

### 📂 Phân hệ 2: Danh mục Thu & Chi (Categories & Soft-Hide)
*File kiểm thử*: [`backend/tests/test_categories.py`](../backend/tests/test_categories.py), [`backend/tests/test_category_migration_mysql.py`](../backend/tests/test_category_migration_mysql.py)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-CAT-01** | Khởi tạo 12 danh mục mặc định | Người dùng mới đăng ký | Gọi GET `/api/v1/categories` | Trả về đủ 12 danh mục hệ thống chuẩn (Ăn uống, Nhà ở, Mua sắm, Lương, Thưởng...) | Unit |
| **TC-CAT-02** | Tạo danh mục tùy chỉnh hợp lệ | User đã đăng nhập | POST `/api/v1/categories` kèm name, type (`expense`/`income`), icon, color | HTTP 201 Created; Danh mục mới gán đúng `user_id` hiện tại | Integration |
| **TC-CAT-03** | Chặn tạo trùng tên danh mục | Đã có danh mục "Ăn uống" | POST `/api/v1/categories` với tên "Ăn uống" (cùng loại) | HTTP 400 Bad Request, báo lỗi trùng lặp danh mục | Validation |
| **TC-CAT-04** | Cơ chế Ẩn danh mục (Soft-Hide) | Danh mục đang hoạt động có chứa giao dịch | PUT `/api/v1/categories/{id}` đặt `is_active = false` | HTTP 200 OK; Danh mục chuyển sang trạng thái ẩn; Các giao dịch cũ vẫn giữ nguyên liên kết | Business Rule |
| **TC-CAT-05** | Chặn tạo giao dịch mới vào danh mục đã ẩn | Danh mục có `is_active = false` | POST `/api/v1/transactions` gán `category_id` bị ẩn | HTTP 400 Bad Request, yêu cầu chọn danh mục đang hoạt động | Integrity |
| **TC-CAT-06** | Cách ly dữ liệu danh mục (IDOR) | User A và User B | User A gửi PUT/DELETE tới `category_id` của User B | HTTP 404 Not Found hoặc 403 Forbidden, không cho sửa đổi danh mục người khác | Security |

---

### 💰 Phân hệ 3: Giao dịch Thu Chi, Lọc, Phân trang & Thùng rác (Transactions & Recycle Bin)
*File kiểm thử*: [`backend/tests/test_transactions.py`](../backend/tests/test_transactions.py) *(65 test cases)*

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-TXN-01** | Tạo giao dịch chi tiêu hợp lệ | Ví có đủ số dư khả dụng | POST `/api/v1/transactions` (type: expense, amount: 50.000, category_id, date) | HTTP 201 Created; Số dư ví giảm tương ứng; Giao dịch lưu vào DB | Integration |
| **TC-TXN-02** | Tạo giao dịch thu nhập hợp lệ | User đăng nhập | POST `/api/v1/transactions` (type: income, amount: 10.000.000) | HTTP 201 Created; Số dư ví tăng tương ứng | Integration |
| **TC-TXN-03** | Chặn số tiền âm, bằng 0, NaN hoặc vô cực | User đăng nhập | POST `/api/v1/transactions` với `amount <= 0`, `NaN`, `Infinity` | HTTP 422 Unprocessable Entity từ Pydantic Validator | Validation |
| **TC-TXN-04** | Chặn phương thức thanh toán không hợp lệ | User đăng nhập | POST với payment_method không thuộc `cash`, `bank_transfer`, `credit_card`, `e_wallet` | HTTP 422 Unprocessable Entity | Validation |
| **TC-TXN-05** | Lệch loại danh mục (Type Mismatch) | Danh mục loại `income` | POST giao dịch loại `expense` trỏ vào danh mục thu nhập | HTTP 400 Bad Request, báo lỗi danh mục không tương thích | Integrity |
| **TC-TXN-06** | Chu trình Thùng rác: Xóa mềm (Soft Delete) | Giao dịch đang hoạt động | DELETE `/api/v1/transactions/{id}` | HTTP 200 OK; `is_deleted = true`; Không còn xuất hiện trong danh sách chính | Business Rule |
| **TC-TXN-07** | Xem danh sách Thùng rác (Trash List) | Đã có giao dịch bị xóa mềm | GET `/api/v1/transactions?is_deleted=true` | Trả về đúng các giao dịch đã bị đưa vào thùng rác | Integration |
| **TC-TXN-08** | Khôi phục giao dịch từ Thùng rác (Restore) | Giao dịch đang trong thùng rác | POST `/api/v1/transactions/{id}/restore` | HTTP 200 OK; `is_deleted = false`; Giao dịch xuất hiện lại trong danh sách | Business Rule |
| **TC-TXN-09** | Xóa vĩnh viễn (Permanent Delete) | Giao dịch phải nằm trong thùng rác | DELETE `/api/v1/transactions/{id}/permanent` | HTTP 200 OK; Bản ghi bị xóa hoàn toàn khỏi CSDL | Business Rule |
| **TC-TXN-10** | Chặn xóa vĩnh viễn giao dịch chưa vào thùng rác | Giao dịch có `is_deleted = false` | DELETE `/api/v1/transactions/{id}/permanent` | HTTP 400 Bad Request, bắt buộc phải đưa vào thùng rác trước | Security |
| **TC-TXN-11** | Nhân bản giao dịch (Duplicate) | Giao dịch hợp lệ tồn tại | POST `/api/v1/transactions/{id}/duplicate` | HTTP 200/201; Trả về dữ liệu nhân bản để mở sẵn Form chỉnh sửa nhanh | Feature |
| **TC-TXN-12** | Bộ lọc đa điều kiện | Có 50 giao dịch đa dạng | Lọc theo ngày bắt đầu/kết thúc, khoảng tiền, danh mục, loại thu/chi | HTTP 200 OK; Dữ liệu trả về khớp chính xác 100% với các mệnh đề filter | Query Test |
| **TC-TXN-13** | Phân trang và sắp xếp linh hoạt | Nhiều giao dịch | GET với `page=2&limit=10&sort_by=transaction_date&order=desc` | HTTP 200 OK; Phân trang đúng offset; Sắp xếp ngày giảm dần chuẩn xác | Performance |

---

### 🛡️ Phân hệ 4: Bảo Toàn Tính Bất Biến Số Dư (Balance Invariance & Concurrency)
*File kiểm thử*: [`backend/tests/test_transactions.py`](../backend/tests/test_transactions.py), [`backend/tests/test_saving_goals.py`](../backend/tests/test_saving_goals.py)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-BAL-01** | Chặn tạo khoản chi vượt số dư khả dụng | Số dư ví = 100.000 đ | Tạo khoản chi 500.000 đ | HTTP 400 Bad Request, báo lỗi số dư khả dụng không đủ | Critical Rule |
| **TC-BAL-02** | Chặn xóa thu nhập làm âm số dư ví | Thu 2.000.000 đ, sau đó chi 1.800.000 đ (Ví còn 200.000 đ) | Gửi yêu cầu xóa giao dịch thu 2.000.000 đ | HTTP 400 Bad Request, chặn xóa vì sẽ làm số dư ví bị âm (-1.800.000 đ) | Critical Rule |
| **TC-BAL-03** | Chặn sửa giảm thu nhập làm âm số dư ví | Số dư hiện tại = 100.000 đ từ khoản thu 1.000.000 đ | Sửa khoản thu giảm từ 1.000.000 đ xuống 500.000 đ | HTTP 400 Bad Request từ hàm `_ensure_projected_balance()` | Critical Rule |
| **TC-BAL-04** | Chống xung đột Race Condition khi giao dịch đồng thời | Người dùng có số dư 1.000.000 đ | 2 luồng đồng thời gửi yêu cầu rút tiền 800.000 đ | Áp dụng `with_for_update()`; 1 giao dịch thành công, 1 giao dịch bị chặn vì thiếu số dư | Concurrency |

---

### 📊 Phân hệ 5: Quản Lý Ngân Sách (Budgets & Overspending Alerts)
*File kiểm thử*: [`backend/tests/test_budgets.py`](../backend/tests/test_budgets.py)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-BUD-01** | Thiết lập hạn mức ngân sách tháng | Danh mục chi tiêu hoạt động | POST `/api/v1/budgets` (category_id, month: "2026-09", amount: 3.000.000 đ) | HTTP 201 Created; Ngân sách được lưu đúng kỳ tháng/năm | Integration |
| **TC-BUD-02** | Cập nhật hạn mức ngân sách | Đã có ngân sách tháng này | PUT `/api/v1/budgets/{id}` sửa amount thành 4.000.000 đ | HTTP 200 OK; Hạn mức mới được cập nhật thành công | Integration |
| **TC-BUD-03** | Tính toán tỷ lệ chi tiêu và cảnh báo vượt ngưỡng | Ngân sách 2.000.000 đ; Đã chi 1.800.000 đ | Gọi GET `/api/v1/budgets/summary?month=2026-09` | Trả về `spent: 1.800.000`, `percentage: 90%`, `is_over_budget: false` | Calculation |
| **TC-BUD-04** | Kích hoạt cờ cảnh báo bội chi | Ngân sách 2.000.000 đ; Đã chi 2.100.000 đ | Gọi GET `/api/v1/budgets/summary` | Trả về `percentage: 105%`, `is_over_budget: true` kèm số tiền vượt mức | Business Rule |
| **TC-BUD-05** | Chặn thiết lập ngân sách âm hoặc sai format tháng | User đăng nhập | POST với `amount < 0` hoặc month `"09-2026"` | HTTP 422 Unprocessable Entity | Validation |

---

### 🎯 Phân hệ 6: Mục Tiêu Tiết Kiệm & Trích Phân Bổ (Saving Goals & Allocation)
*File kiểm thử*: [`backend/tests/test_saving_goals.py`](../backend/tests/test_saving_goals.py) *(28 test cases)*

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-SVG-01** | Tạo mục tiêu tiết kiệm mới | User đăng nhập | POST `/api/v1/saving-goals` (name: "Mua Laptop", target: 20.000.000 đ, deadline) | HTTP 201 Created; `current_amount = 0`, `status = active` | Integration |
| **TC-SVG-02** | Nạp tiền thủ công vào mục tiêu | Ví có đủ số dư khả dụng | POST `/api/v1/saving-goals/{id}/deposit` (amount: 2.000.000 đ) | HTTP 200 OK; Số dư ví giảm 2.000.000 đ; Mục tiêu tăng 2.000.000 đ | Transactional |
| **TC-SVG-03** | Tự động trích phần trăm từ thu nhập | Giao dịch thu nhập 10.000.000 đ | POST `/api/v1/transactions` kèm trích 20% vào Mục tiêu tiết kiệm | Tạo khoản thu 10 triệu; Tự động trích 2 triệu vào mục tiêu; Số dư ví tăng ròng 8 triệu | Integration |
| **TC-SVG-04** | Rút tiền từ mục tiêu tiết kiệm về ví | Mục tiêu có số dư tiết kiệm 5.000.000 đ | POST `/api/v1/saving-goals/{id}/withdraw` (amount: 3.000.000 đ) | HTTP 200 OK; Số dư mục tiêu giảm còn 2 triệu; Số dư ví tăng thêm 3 triệu | Transactional |
| **TC-SVG-05** | Chặn rút tiền vượt quá số tiền hiện có | Mục tiêu có 1.000.000 đ | Gửi yêu cầu rút 1.500.000 đ | HTTP 400 Bad Request, báo lỗi số tiền rút vượt quá số dư tích lũy | Validation |
| **TC-SVG-06** | Hoàn thành mục tiêu tiết kiệm | Mục tiêu đạt 100% hạn mức | Nạp số tiền đủ đạt `target_amount` | Mục tiêu tự động chuyển `status = completed`; ghi nhận ngày hoàn thành | Business Rule |

---

### 🤖 Phân hệ 7: Trí Tuệ Nhân Tạo & Báo Cáo Thông Minh (AI Features & Prompts)
*File kiểm thử*: [`backend/tests/test_ai.py`](../backend/tests/test_ai.py), [`docs/PROMPT_BENCHMARK_REPORT.md`](PROMPT_BENCHMARK_REPORT.md)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-AI-01** | Gợi ý ngân sách thông minh (AI Budget Suggestion) | Có dữ liệu chi tiêu 1-3 tháng gần nhất | GET `/api/v1/ai/budget-recommendations?month=2026-10` | HTTP 200 OK; Trả về danh sách gợi ý từng danh mục kèm số tiền và lý do giải thích | AI Feature |
| **TC-AI-02** | Áp dụng hàng loạt ngân sách gợi ý (1-Click Apply) | Nhận được gợi ý từ AI | POST `/api/v1/ai/apply-budget-recommendations` danh sách `[{category_id, amount}]` | HTTP 200 OK; Lưu hoặc cập nhật hàng loạt vào bảng `budgets` của tháng mục tiêu | Integration |
| **TC-AI-03** | Sinh Báo cáo Tài chính Tháng chuẩn JSON Schema | Có giao dịch trong tháng | POST `/api/v1/ai/generate-report` cho tháng được chọn | HTTP 200 OK; JSON đủ 4 trường chuẩn: `overview`, `trend_analysis`, `adjustments`, `conclusion` | AI Contract |
| **TC-AI-04** | Cơ chế Dự phòng (Fallback) khi AI gặp sự cố | Ngắt mạng hoặc làm giả lỗi timeout API Gemini | Gọi API gợi ý ngân sách hoặc báo cáo tháng | Không bị crash; Hệ thống tự kích hoạt thuật toán Rule-based (+5% buffer, làm tròn 50.000 đ) | Resilience |
| **TC-AI-05** | Che giấu dữ liệu cá nhân (PII Masking) | Chuỗi đầu vào chứa STK, số thẻ, mã giao dịch | Đưa chuỗi vào hàm `mask_sensitive_data()` trước khi gửi Prompt | 100% thông tin nhạy cảm bị chuyển thành `[STK_ĐÃ_ẨN]`, `[MÃ_GD_ĐÃ_ẨN]` | Security |
| **TC-AI-06** | Bẻ lái hành vi tiêu dùng bốc đồng (Behavioral Nudge) | Chatbot FinAI nhận câu hỏi *"Có nên đi ăn lẩu đắt tiền không?"* | Gửi câu hỏi tới `/api/v1/ai/chat` | AI không từ chối thô lỗ, đồng cảm ngắn gọn rồi cảnh báo số dư ví thực tế | AI Behavior |

---

### 📚 Phân hệ 9: Tri Thức Tài Chính RAG & Tra Cứu Trực Tuyến (RAG & Live Web Search)
*File kiểm thử*: [`backend/tests/test_rag.py`](../backend/tests/test_rag.py) *(18 test cases)*

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-RAG-01** | Phân đoạn văn bản đệ quy (Recursive Chunking) | Tài liệu dài > 500 ký tự | Chia văn bản với chunk_size=500, overlap=50 | Các đoạn cắt đúng ranh giới đoạn văn / câu, giữ độ gối đầu 50 ký tự | Unit |
| **TC-RAG-02** | Bảo toàn Metadata nguồn gốc văn bản | File raw .md / .pdf | Nạp tài liệu qua `load_knowledge_chunks()` | Mỗi chunk lưu đủ `id`, `title`, `source_name`, `source_url`, `chunk_index` | Data Pipeline |
| **TC-RAG-03** | Lọc nhiễu Sibling Chunks (Sibling Noise Filter) | Văn bản có nhiều đoạn | Query khớp trực tiếp đoạn 2 | Đoạn 2 có điểm số cao nhất, các đoạn râu ria điểm thấp bị loại bỏ | Precision |
| **TC-RAG-04** | Truy xuất chuẩn quy tắc 50/30/20 | Query: "Làm sao chia tiền theo quy tắc 50 30 20" | Gọi `retrieve_relevant_knowledge()` | Trả về trích đoạn từ bài viết Elizabeth Warren VnExpress | Retrieval |
| **TC-RAG-05** | Truy xuất chuẩn 6 chiếc lọ JARS | Query: "Cách chia tiền 6 chiếc lọ JARS Harv Eker" | Gọi `retrieve_relevant_knowledge()` | Trả về trích đoạn 6 chiếc lọ Techcombank Blog | Retrieval |
| **TC-RAG-06** | Truy xuất Quỹ dự phòng khẩn cấp | Query: "Cần chuẩn bị quỹ khẩn cấp bao nhiêu tiền phòng thân" | Gọi `retrieve_relevant_knowledge()` | Trả về tài liệu quỹ dự phòng VnExpress & Timo | Retrieval |
| **TC-RAG-07** | Truy xuất Biểu thuế TNCN & Giảm trừ gia cảnh | Query: "Biểu thuế thu nhập cá nhân lũy tiến và mức giảm trừ" | Gọi `retrieve_relevant_knowledge()` | Trả về thông tin biểu thuế Cổng TTĐT Chính Phủ | Retrieval |
| **TC-RAG-08** | Intent Gating: Chặn RAG khi chỉ hỏi số dư cá nhân | Query: "Tháng này tôi đã tiêu bao nhiêu tiền ăn uống" | Gọi `retrieve_relevant_knowledge()` | Trả về rỗng `[]`, không đính kèm bài viết ngoài lề | Security/Guardrail |
| **TC-RAG-09** | So sánh đa phương pháp tài chính | Query: "So sánh phương pháp 50/30/20 và 6 chiếc lọ" | Gọi `retrieve_relevant_knowledge(top_k=2)` | Trả về đủ 2 nguồn từ 2 phương pháp khác nhau, không bị chiếm chỗ | Diversity |
| **TC-RAG-10** | Trích xuất PDF chuyên sâu (ĐH Mở, ĐH Huế) | Query về nghiên cứu hành vi chi tiêu sinh viên | Gọi `retrieve_relevant_knowledge()` | Trích xuất chuẩn xác các chunk từ file PDF Tạp chí khoa học | PDF Ingestion |
| **TC-RAG-11** | Tự động mở rộng Live Web Search khi tra cứu thị trường | Query: "Giá vàng hôm nay", "Lãi suất tiết kiệm mới nhất" | Gọi `retrieve_relevant_knowledge(enable_web_search=True)` | Tự động kích hoạt DuckDuckGo, trích xuất bài viết và kèm URL trực tiếp | Live Web RAG |
| **TC-RAG-12** | RAG Động cho Báo cáo tài chính tháng | Metrics: tỷ lệ tiết kiệm thấp, bội chi ăn uống | Gọi `retrieve_contextual_report_knowledge()` | Trả về ngữ cảnh RAG và danh sách benchmark phù hợp đúng ngữ cảnh | Dynamic Context |
| **TC-RAG-13** | RAG Động cho Đề xuất ngân sách tháng | Categories: Ăn uống, Đi lại, Nhà ở | Gọi `retrieve_contextual_budget_knowledge()` | Trả về tài liệu định mức ngân sách chuẩn và quy tắc phân bổ | Dynamic Context |

---

### 📷 Phân hệ 8: Quét Hóa Đơn AI OCR
*File kiểm thử*: [`backend/tests/test_ocr.py`](../backend/tests/test_ocr.py)

| Mã TC | Tên Kịch Bản Kiểm Thử | Điều Kiện Tiên Quyết | Dữ Liệu Đầu Vào & Các Bước | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-OCR-01** | Nhận diện ảnh hóa đơn mua sắm thành công | File ảnh JPG/PNG hóa đơn rõ nét | POST `/api/v1/ocr/scan-receipt` đính kèm file ảnh | HTTP 200 OK; Trích xuất đúng số tiền, ngày phát sinh, tên người bán và danh mục | Integration |
| **TC-OCR-02** | Xử lý ảnh mờ hoặc không phải hóa đơn | File ảnh phong cảnh / ảnh lỗi | POST file ảnh không chứa thông tin thanh toán | HTTP 200/400; Trả về kết quả trích xuất rỗng kèm cảnh báo nhẹ nhàng, không sập server | Resilience |

---

## 🖥️ 3. MA TRẬN CA KIỂM THỬ FRONTEND (VITEST & REACT TESTING LIBRARY)

*Thư mục kiểm thử*: [`frontend/src/pages/`](../frontend/src/pages)

| Mã TC | Component / Màn Hình | Kịch Bản Kiểm Thử | Thao Tác Thực Hiện (User Actions) | Kết Quả Kỳ Vọng | Loại Test |
|:---:|---|---|---|---|:---:|
| **TC-FE-01** | `Budgets.test.jsx` | Chuyển tab AI Gợi ý Ngân sách | Người dùng click vào tab *"AI Gợi Ý Ngân Sách"* | Hiển thị form cấu hình tháng, thanh chọn và nút xác nhận sinh gợi ý | UI Component |
| **TC-FE-02** | `Budgets.test.jsx` | Mở Modal và Áp dụng Gợi ý Ngân sách | Click *"Xác Nhận & Sinh Gợi Ý"* -> Xem danh sách gợi ý -> Click *"Áp Dụng Vào Ngân Sách"* | Modal hiển thị danh sách thẻ ngân sách; gọi API `applyBudgetRecommendations`; đóng modal và reload ngân sách | Integration |
| **TC-FE-03** | `Transactions.test.jsx` | Hiển thị và Tìm kiếm Giao dịch | Nhập từ khóa tìm kiếm vào ô Search Bar | Bảng giao dịch tự động lọc sau thời gian debounce 300ms | UI Interaction |
| **TC-FE-04** | `Transactions.test.jsx` | Thao tác Thùng rác (Xóa & Khôi phục) | Click icon Xóa một dòng giao dịch -> Chuyển tab Thùng rác -> Click Khôi phục | Giao dịch biến mất khỏi bảng chính, xuất hiện trong thùng rác và được hoàn nguyên khi click khôi phục | UI Flow |
| **TC-FE-05** | `Categories.test.jsx` | Ẩn danh mục chi tiêu | Click nút chuyển trạng thái Ẩn/Hiện trên thẻ danh mục | Hiển thị nhãn *"Đã ẩn"*, danh mục không còn xuất hiện trong dropdown thêm giao dịch | UI State |
| **TC-FE-06** | `SavingGoals.test.jsx` | Hiển thị tiến độ thanh đo tiết kiệm | Nạp tiền vào mục tiêu tiết kiệm | Thanh Progress Bar cập nhật tỷ lệ % hoàn thành và đổi màu trực quan | UI State |
| **TC-FE-07** | `PopupCoordination.test.jsx` | Điều phối hiển thị Popup & Modal | Mở Modal thêm giao dịch trong khi Modal AI đang mở | Tự động đóng popup trước đó, ngăn chặn hiện tượng popups chồng chéo giao diện | UX Test |
| **TC-FE-08** | `axios.test.js` | Tự động đính kèm Token và xử lý 401 | Gọi API bất kỳ khi đã có token; giả lập token hết hạn | Request header tự có `Authorization: Bearer <token>`; khi nhận lỗi 401 tự động xóa token và chuyển hướng về `/login` | E2E Mock |

---

## 🚀 4. HƯỚNG DẪN THỰC THI KIỂM THỬ (EXECUTION GUIDE)

### 1. Chạy toàn bộ kiểm thử Backend (Pytest)
```bash
# Kích hoạt môi trường ảo Python
cd backend
source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows

# Chạy toàn bộ 189 bài test backend với thống kê chi tiết
pytest -v

# Chạy riêng phân hệ AI
pytest tests/test_ai.py -v

# Chạy kiểm tra bảo toàn số dư
pytest tests/test_transactions.py -k "balance" -v
```

### 2. Chạy toàn bộ kiểm thử Frontend (Vitest)
```bash
cd frontend

# Chạy test 1 lần (CI mode)
npm run test:run

# Chạy test ở chế độ theo dõi tương tác (Watch mode)
npm run test
```

### 3. Báo cáo Tóm tắt Kết quả Thực nghiệm
* **Tổng số bài test tự động**: 189 Pytest (Backend) + 71 Vitest trong 14 Suites (Frontend) = 260 Test Cases
* **Kết quả kiểm thử**: 100% PASSED (Không có bài test thất bại)
* **Thời gian thực thi trung bình**: ~4.5 giây (Backend) và ~2.1 giây (Frontend)
