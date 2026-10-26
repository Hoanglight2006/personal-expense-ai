Hệ thống quản lý chi tiêu cá nhân có tích hợp AI
1. Mô tả bài toán
Người dùng cá nhân cần quản lý thu nhập, chi tiêu, ngân sách, mục tiêu tiết kiệm và báo cáo tài chính cá nhân. Việc ghi chép thủ công dễ thiếu sót và khó nhận ra xu hướng chi tiêu. Hệ thống cần quản lý chi tiêu cá nhân và tích hợp AI tóm tắt thói quen chi tiêu, gợi ý ngân sách tham khảo và sinh báo cáo tháng. Đồng thời, hệ thống cung cấp phân hệ Quản trị viên (Admin) để quản lý tài khoản, hỗ trợ khắc phục sự cố đăng nhập và giám sát tài nguyên sử dụng AI toàn hệ thống theo nguyên tắc bảo vệ quyền riêng tư (Zero-Knowledge Privacy).

2. Mục tiêu
- Quản lý khoản thu, khoản chi, danh mục, ngân sách, mục tiêu tiết kiệm của người dùng cá nhân.
- Tích hợp AI để sinh báo cáo chi tiêu, gợi ý ngân sách, tóm tắt xu hướng và giải đáp qua trợ lý FinAI.
- Cung cấp tác nhân Quản trị viên (Admin) vận hành hệ thống đa người dùng an toàn.
- Sử dụng AI trong SDLC và bảo vệ dữ liệu tài chính cá nhân (Admin không can thiệp chi tiết chi tiêu riêng tư).

3. Yêu cầu chức năng
3.1. Chức năng quản lý cá nhân (End User)
- Đăng nhập và quản lý tài khoản cá nhân.
- Quản lý danh mục thu/chi.
- Ghi nhận giao dịch thu nhập và chi tiêu.
- Thiết lập ngân sách theo tháng/danh mục.
- Quản lý mục tiêu tiết kiệm.
- Tìm kiếm/lọc giao dịch theo ngày, danh mục.
- Cảnh báo vượt ngân sách.
- Thống kê chi tiêu theo tháng, danh mục, xu hướng.

3.2. Chức năng Quản trị hệ thống (System Administrator)
- Quản lý danh sách tài khoản người dùng trong hệ thống.
- Khóa và mở khóa tài khoản khi phát hiện dấu hiệu vi phạm hoặc theo yêu cầu bảo vệ người dùng.
- Hỗ trợ tạo mật khẩu tạm thời cho người dùng khi gặp sự cố mất hoặc quên tài khoản.
- Giám sát tài nguyên hệ thống và tần suất gọi AI Gemini (báo cáo tháng, gợi ý ngân sách, trợ lý chat) nhằm kiểm soát chi phí token API.

3.3. Chức năng AI
- AI sinh báo cáo chi tiêu tháng.
- AI gợi ý ngân sách tham khảo dựa trên lịch sử chi tiêu.
- AI trả lời câu hỏi như "tháng này tôi chi nhiều nhất vào đâu?".

4. Yêu cầu kỹ thuật
- Backend FastAPI; frontend React.
- CSDL MySQL 8.0.
- AI Engine Gemini API (hoặc OpenAI/Claude/Ollama).
- Phân quyền RBAC (Role-Based Access Control: User / Admin).
- Có kiểm soát dữ liệu tài chính gửi AI (Data Minimization).
- Có test cho giao dịch, ngân sách, báo cáo, quản trị admin và AI.

5. Dữ liệu đầu vào, đầu ra và dữ liệu hệ thống
- Dữ liệu chính: người dùng (vai trò, trạng thái khóa), danh mục, giao dịch, ngân sách, mục tiêu, nhật ký AI.
- Đầu vào AI: dữ liệu chi tiêu đã tổng hợp, ngân sách, mục tiêu (đã ẩn danh).
- Đầu ra AI: báo cáo, gợi ý ngân sách, câu trả lời phân tích.
- Prompt mẫu:
  - System: Bạn là trợ lý chi tiêu cá nhân. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp.
  - User: Dữ liệu chi tiêu tháng: {{monthly_expense_summary}}. Hãy tóm tắt xu hướng và gợi ý 3 điểm cần điều chỉnh.

6. Hướng dẫn sử dụng AI trong từng giai đoạn SDLC
- KT1: Dùng AI phân tích thu/chi, ngân sách, mục tiêu; thiết kế ERD, tác nhân Admin và bảo mật RBAC.
- KT2: Dùng AI sinh CRUD giao dịch, danh mục, ngân sách, API admin; debug thống kê.
- KT3: Dùng AI thiết kế prompt báo cáo chi tiêu; test dữ liệu nhạy cảm, quyền truy cập Admin và thiếu.
- Cuối kỳ: Dùng AI viết README, báo cáo, slide và review quyền riêng tư.

7. Mức độ khó
Trung bình: Hệ thống dữ liệu không quá lớn nhưng có yếu tố riêng tư, quản trị đa người dùng và yêu cầu phân tích số liệu cá nhân.
