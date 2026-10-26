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

## 🚀 CƠ CHẾ VẬN HÀNH TRÊN DOCKER

> 💡 Hệ thống chuẩn hóa sử dụng **CSDL MySQL 8.0 chạy trong Docker Container** (`expense_mysql`). Không yêu cầu cài đặt MySQL Server trên máy tính.

### 1. Khởi tạo CSDL MySQL bằng Docker
```powershell
# Khởi động dịch vụ MySQL trong Docker (ánh xạ cổng 3307 ra máy host)
docker compose up -d mysql
```
* **Schema DDL**: Tự động được Docker nạp từ file `database/schema.sql` vào database `personal_expense` khi container khởi tạo lần đầu.
* **Tài khoản mặc định trong container**:
  * User ứng dụng: `expense_user` / `expense_password`
  * User quản trị: `root` / `rootpassword`

### 2. Nạp dữ liệu mẫu Demo (Seed Demo Data)
* **Cách 1 (Qua Docker Exec - Khuyên dùng)**:
  ```powershell
  docker compose exec backend python /app/database/seed_demo.py
  ```
* **Cách 2 (Chạy trực tiếp từ máy tính kết nối cổng 3307)**:
  ```powershell
  python database/seed_demo.py
  ```
* **Kết quả**:
  * Tạo tài khoản User Demo: `demo@example.com` / `Password123@`.
  * Tạo tài khoản Admin Demo: `admin@example.com` / `AdminPass123@`.
  * Nạp sẵn **74 giao dịch** thu chi thực tế trải dài 6 tháng gần nhất.
  * Khởi tạo **2 Mục tiêu tiết kiệm** và **4 Ngân sách tháng** với đầy đủ biểu đồ sống động.