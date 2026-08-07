## 🤖 Hướng dẫn làm việc với AI Agents trong dự án

Hệ thống này sử dụng kiến trúc Team Agent nội bộ để hỗ trợ quy trình phát triển (SDLC). Mọi cấu hình AI được lưu tại thư mục `.agents`. Để đảm bảo luồng công việc thông suốt và không rò rỉ dữ liệu, toàn bộ thành viên cần tuân thủ các hướng dẫn sau.

### 1. Yêu cầu môi trường
*   **IDE bắt buộc:** Antigravity IDE (để tương thích chuẩn với thư mục `.agents`).
*   **API Key:** Mỗi thành viên tự cấu hình API Key (OpenAI/Gemini/Claude) trong cài đặt LLM của IDE cá nhân. Tuyệt đối không hardcode API key vào bất kỳ file nào trong source code.
*   **Đồng bộ Rule:** IDE sẽ tự động nạp các quy tắc toàn cục (Global Rules) từ `.agents/rules`. AI sẽ mặc định tuân thủ file `REQUIREMENTS.md` để giới hạn phạm vi tính năng.

### 2. Danh sách AI Agents
Nhóm sử dụng 3 Agents chuyên biệt. Trong cửa sổ chat của IDE, gõ `/` để gọi đúng Agent cần thiết:

*   `/agent-1-backend`: Chuyên trách CSDL, API (FastAPI/Flask/Django) và xử lý luồng dữ liệu giao dịch/danh mục.
*   `/agent-2-frontend`: Chuyên trách UI/UX (React/Vue), biểu đồ thống kê và quản lý state ngân sách.
*   `/egent-3-qa` (hoặc `/agent-3-qa`): Chuyên trách Review code, viết Test (Unit/Integration) và kiểm soát rủi ro bảo mật (Data masking, SQL Injection).

### 3. Quy trình vận hành chuẩn (SOP)
Để tránh hiện tượng AI bị "rối loạn ngữ cảnh" (Context Bleeding), bắt buộc áp dụng quy trình 4 bước:

1.  **Dev Phase:** Mở luồng chat MỚI. Gọi `/agent-1-backend` (hoặc frontend) để sinh/sửa code tính năng.
2.  **Test Phase:** Khi code chạy được, mở một luồng chat MỚI hoàn toàn. Gọi `/egent-3-qa` kèm đoạn code vừa làm để rà soát lỗi bảo mật và logic.
3.  **Human-in-the-loop:** Lập trình viên tự đánh giá lỗi do QA chỉ ra. Chọn lọc các lỗi thực sự cần sửa.
4.  **Fix Phase:** Quay lại luồng chat của Agent 1/2, cung cấp phản hồi từ QA để AI Dev tiến hành sửa lại code.

**⚠️ Lưu ý quan trọng:**
*   Một tính năng = Một luồng chat. Xóa hoặc mở chat mới khi chuyển sang làm tính năng khác.
*   Chỉ gọi Agent QA để kiểm tra, tuyệt đối không dùng Agent QA để sinh code tính năng mới.
*   Bảo mật dữ liệu: Luôn kiểm tra kỹ để đảm bảo dữ liệu test gửi cho AI không chứa thông tin định danh cá nhân thật.

*   **Đừng chat quá dài (Quy tắc 1 Task = 1 Chat):** Cửa sổ chat càng dài, AI càng dễ quên các rule và yêu cầu ban đầu. Ngay khi giải quyết xong một tính năng nhỏ (ví dụ: test xong API thêm giao dịch), hãy mở **New Chat** ngay lập tức.
*   **Không gọi chéo Agent:** Tuyệt đối không gọi `/agent-1-backend` rồi lại gọi `/egent-3-qa` trong cùng một phiên chat. Điều này làm AI bị "rối loạn nhân cách" và sinh ra code sai tiêu chuẩn. Đã đổi Agent là phải đổi luồng chat.
*   **Tag đúng file cần thiết:** Đừng bắt AI tự đọc toàn bộ project. Hãy chủ động tag chính xác file đang làm việc (ví dụ `@transaction.py`) và chỉ định rõ hàm đang lỗi để tiết kiệm token và tăng độ chính xác.
*   **KHÔNG nhắm mắt Copy-Paste:** AI sinh code rất nhanh nhưng có thể dùng sai thư viện hoặc xử lý sai logic (đặc biệt là các vòng lặp tính toán thống kê). Phải đọc hiểu dòng code đó làm gì trước khi đưa vào file chính.
*   **Dữ liệu Fake 100%:** Khi nhờ AI viết test hoặc sinh báo cáo mẫu, bắt buộc dùng dữ liệu giả (Mock data). Tuyệt đối không đưa số liệu tài chính thật hoặc thông tin cá nhân vào cửa sổ chat.

### 5. Quy chuẩn quản lý mã nguồn (Git Workflow)

Tuyệt đối tuân thủ luồng làm việc sau để tránh mất code và dễ dàng tích hợp AI vào khâu viết báo cáo cuối kỳ:

*   **Bảo vệ nhánh chính (`main`):** Nhánh `main` chỉ chứa code ĐÃ TEST THÀNH CÔNG. Tuyệt đối không ai được phép code hoặc push trực tiếp lên nhánh `main`.
*   **Chia nhánh theo tính năng (Feature Branch):** Không tạo nhánh theo tên người. Khi nhận việc, hãy tạo nhánh mới từ `main` với cú pháp rõ ràng. 
    *   Ví dụ Thành viên 1: `feature/api-transaction`, `feature/ai-report-prompt`.
    *   Ví dụ Thành viên 2: `feature/ui-dashboard`, `feature/budget-chart`.
*   **Quy tắc Commit Message:** Agent 3 (QA) sẽ tự động đọc lịch sử commit để hỗ trợ viết file Báo cáo cuối kỳ. Bắt buộc viết commit rõ ràng theo cú pháp: `[Loại thao tác] Mô tả ngắn gọn`.
    *   *Đúng:* `[Add] API tạo mới giao dịch thu chi`, `[Fix] Lỗi hiển thị sai số dư budget`.
    *   *Sai:* `update`, `fix bug`, `code cua tui`.
*   **Không commit code rác từ AI:** Chỉ thực hiện lệnh `git commit` khi đoạn code AI sinh ra đã được chạy thử thành công trên máy (local). Không commit những đoạn code đang lỗi dở dang.
*   **Quy trình Gộp code (Merge):** Xong tính năng nào, gộp tính năng đó. Trước khi gộp nhánh `feature` vào `main`, phải `git pull origin main` về nhánh của mình trước để xử lý conflict (nếu có). Khi xảy ra conflict lớn, 2 người phải trao đổi trực tiếp, không tự ý ghi đè code của người kia.