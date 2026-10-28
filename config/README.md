# 🔧 TẦNG CẤU HÌNH HỆ THỐNG (CONFIG) — PERSONAL EXPENSE AI

Thư mục này quản lý toàn bộ các file mẫu cấu hình môi trường, biến bảo mật và thiết lập kết nối của hệ thống **Personal Expense AI**.

---

## 📁 CẤU TRÚC THƯ MỤC CONFIG

```text
config/
├── prompts.json    # Tập trung định nghĩa các AI system prompts và templates
└── README.md       # Giải thích ý nghĩa và hướng dẫn cấu hình (File này)

> 💡 **Lưu ý**: File cấu hình biến môi trường Master của toàn dự án được đặt tại thư mục gốc: [.env.example](../.env.example).
```

---

## ⚙️ CHI TIẾT CÁC BIẾN MÔI TRƯỜNG

| Tên biến | Bắt buộc | Mặc định / Ví dụ | Giải thích ý nghĩa |
|---|:---:|---|---|
| `DATABASE_URL` | **Có** | `mysql+pymysql://expense_user:expense_password@localhost:3307/personal_expense` | Chuỗi kết nối SQLAlchemy tới MySQL 8.0 chạy trong Docker Container qua cổng 3307. |
| `SECRET_KEY` | **Có** | `your-super-secret-key-32-chars` | Khóa bí mật dùng để ký và xác thực mã JWT Token. |
| `ALGORITHM` | Không | `HS256` | Thuật toán mã hóa JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | `30` | Thời hạn của Access Token (phút). |
| `CORS_ORIGINS` | **Có** | `["http://localhost:5173"]` | Danh sách domain Frontend được phép gọi API. |
| `GEMINI_API_KEY` | Tùy chọn | `AIzaSy...` | Khóa API Google Gemini AI (dùng cho tính năng OCR Hóa đơn & FinAI Chatbot). |
| `MAX_IMAGE_SIZE_MB` | Không | `10` | Dung lượng tối đa ảnh hóa đơn upload (MB). |

---

## 🚀 HƯỚNG DẪN THIẾT LẬP

Để khởi tạo cấu hình môi trường:
```powershell
# Sao chép file cấu hình mẫu Master ở thư mục gốc
Copy-Item .env.example .env    # Linux/Mac/Git Bash: cp .env.example .env
```
