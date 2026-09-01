# 🗄️ TẦNG CƠ SỞ DỮ LIỆU — PERSONAL EXPENSE AI

Thư mục này quản lý toàn bộ cấu trúc DDL, các bản migration và script khởi tạo dữ liệu mẫu cho hệ thống **Personal Expense AI**.

---

## 📁 CẤU TRÚC THƯ MỤC DATABASE

```text
database/
├── migrations/                     # Các file SQL Migration theo phiên bản
│   ├── 001_category_management.sql # Migration danh mục & chuẩn hóa
│   ├── 002_transaction_management.sql # Migration giao dịch & thùng rác
│   ├── 003_category_soft_delete.sql # Migration soft delete danh mục
│   └── 004_saving_withdrawals.sql  # Migration nạp/rút tiền tiết kiệm
├── schema.sql                      # Toàn bộ mã DDL hợp nhất của CSDL (MySQL 8.0)
├── seed_demo.py                    # Script nạp 74 giao dịch demo 6 tháng
└── README.md                       # Tài liệu hướng dẫn tầng Database (File này)
```

---

## 🚀 CÁCH KHỞI TẠO VÀ NẠP DỮ LIỆU

### 1. Khởi tạo cấu trúc Database (Schema)
* **Khi dùng FastAPI Backend**: Server tự động khởi tạo các bảng còn thiếu thông qua SQLAlchemy Metadata khi khởi động.
* **Hoặc import thủ công bằng MySQL CLI**:
  ```bash
  mysql -u root -p < database/schema.sql
  ```

### 2. Nạp dữ liệu mẫu Demo (Seed Demo Data)
Chạy script từ thư mục gốc dự án:
```powershell
python database/seed_demo.py
```
* Tạo tài khoản: `demo@example.com` / `Password123@`.
* Nạp sẵn **74 giao dịch** thu chi thực tế trải dài 6 tháng gần nhất.
* Khởi tạo **2 Mục tiêu tiết kiệm** và **4 Ngân sách tháng**.
