Hệ thống quản lý chi tiêu cá nhân có tích hợp AI
Mô tả bài toán
Người dùng cá nhân cần quản lý thu nhập, chi tiêu, ngân sách, mục tiêu tiết kiệm và báo cáo tài chính cá nhân. Việc ghi chép thủ công dễ thiếu sót và khó nhận ra xu hướng chi tiêu. Hệ thống cần quản lý chi tiêu cá nhân và tích hợp AI tóm tắt thói quen chi tiêu, gợi ý ngân sách tham khảo và sinh báo cáo tháng.
2. Mục tiêu
Quản lý khoản thu, khoản chi, danh mục, ngân sách, mục tiêu tiết kiệm.
Tích hợp AI để sinh báo cáo chi tiêu, gợi ý ngân sách, tóm tắt xu hướng.
Sử dụng AI trong SDLC và bảo vệ dữ liệu tài chính cá nhân.
Yêu cầu chức năng
3.1. Chức năng quản lý
Đăng nhập và quản lý tài khoản cá nhân.
Quản lý danh mục thu/chi.
Ghi nhận giao dịch thu nhập và chi tiêu.
Thiết lập ngân sách theo tháng/danh mục.
Quản lý mục tiêu tiết kiệm.
Tìm kiếm/lọc giao dịch theo ngày, danh mục.
Cảnh báo vượt ngân sách.
Thống kê chi tiêu theo tháng, danh mục, xu hướng.
3.2. Chức năng AI
AI sinh báo cáo chi tiêu tháng.
AI gợi ý ngân sách tham khảo dựa trên lịch sử chi tiêu.
AI trả lời câu hỏi như "tháng này tôi chi nhiều nhất vào đâu?".
Yêu cầu kỹ thuật
Backend FastAPI; frontend React.
CSDL MySQL.
AI Engine OpenAI/Gemini/Claude/Hugging Face/Ollama.
Có kiểm soát dữ liệu tài chính gửi AI.
Có test cho giao dịch, ngân sách, báo cáo và AI.
Dữ liệu đầu vào, đầu ra và dữ liệu hệ thống
Dữ liệu chính: người dùng, danh mục, giao dịch, ngân sách, mục tiêu.
Đầu vào AI: dữ liệu chi tiêu đã tổng hợp, ngân sách, mục tiêu.
Đầu ra AI: báo cáo, gợi ý ngân sách, câu trả lời phân tích.
Prompt mẫu:
System: Bạn là trợ lý chi tiêu cá nhân. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp.
User: Dữ liệu chi tiêu tháng: {{monthly_expense_summary}}. Hãy tóm tắt xu hướng và gợi ý 3 điểm cần điều chỉnh.
6. Hướng dẫn sử dụng AI trong từng giai đoạn SDLC
KT1: Dùng AI phân tích thu/chi, ngân sách, mục tiêu; thiết kế ERD và bảo mật.
KT2: Dùng AI sinh CRUD giao dịch, danh mục, ngân sách; debug thống kê.
KT3: Dùng AI thiết kế prompt báo cáo chi tiêu; test dữ liệu nhạy cảm và thiếu.
Cuối kỳ: Dùng AI viết README, báo cáo, slide và review quyền riêng tư.
Mức độ khó
Trung bình: Hệ thống dữ liệu không quá lớn nhưng có yếu tố riêng tư và yêu cầu phân tích số liệu cá nhân.