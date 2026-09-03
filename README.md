# 💰 PERSONAL EXPENSE AI — HỆ THỐNG QUẢN LÝ TÀI CHÍNH CÁ NHÂN TÍCH HỢP AI

> **Hệ thống Quản lý Chi tiêu và Hoạch định Tài chính Thông minh** được xây dựng trên nền tảng **FastAPI (Python)**, **React 19 (Vite)**, **MySQL** và **Google Gemini AI**.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Bundler-Vite_8-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![MySQL](https://img.shields.io/badge/Database-MySQL_8.0-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com)
[![Tests](https://img.shields.io/badge/Tests-219%20Passed-success.svg)](docs/DEVELOPMENT_PROCESS.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🧭 LỘ TRÌNH ĐỌC TÀI LIỆU (READING ROADMAP)

Để thuận tiện nhất cho việc theo dõi, chấm điểm hoặc trải nghiệm dự án, hãy đọc các tài liệu theo thứ tự khuyên nghị dưới đây:

```mermaid
graph LR
    Step1["1. USER_GUIDE.md<br/>(Hướng dẫn dùng & Demo)"] --> Step2["2. SYSTEM_ARCHITECTURE.md<br/>(Kiến trúc, JWT & ERD)"]
    Step2 --> Step3["3. AI_DEVELOPMENT_LOG.md<br/>(Minh chứng Prompt AI)"]
    Step3 --> Step4["4. DEVELOPMENT_PROCESS.md<br/>(Quy trình 5 Sprint)"]
    Step4 --> Step5["5. API & DATABASE.md<br/>(Tra cứu kỹ thuật)"]
```

1. 🎯 **Bước 1 — Dành cho mọi người (Xem hướng dẫn & Trải nghiệm giao diện)**:
   👉 Đọc **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**: Hướng dẫn đăng nhập tài khoản Demo có sẵn 74 giao dịch, thao tác quét hóa đơn AI, nhập Excel và quản lý ngân sách.
2. 🏛️ **Bước 2 — Đánh giá Kiến trúc Hệ thống & Cơ sở Dữ liệu**:
   👉 Đọc **[docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)**: Thiết kế phân tầng, cơ chế xác thực JWT, khóa bi quan (`FOR UPDATE`) chống Race-condition và sơ đồ ERD.
3. 🤖 **Bước 3 — Đánh giá Minh chứng Ứng dụng AI khi Lập trình**:
   👉 Đọc **[docs/AI_DEVELOPMENT_LOG.md](docs/AI_DEVELOPMENT_LOG.md)**: Tổng hợp Prompt chuẩn 5 thành phần, phân tích BA, phần code AI sinh ra và phần sinh viên trực tiếp rà soát, sửa lỗi.
4. 🚀 **Bước 4 — Đánh giá Kế hoạch & Quy trình Phát triển Phần mềm**:
   👉 Đọc **[docs/DEVELOPMENT_PROCESS.md](docs/DEVELOPMENT_PROCESS.md)**: Báo cáo 5 Sprint theo mô hình Agile/Scrum và kết quả kiểm thử 55/55 test cases.
5. 📡 **Bước 5 — Tra cứu Kỹ thuật Chuyên sâu**:
   👉 Xem **[docs/API.md](docs/API.md)** (Đặc tả RESTful API) và **[docs/DATABASE.md](docs/DATABASE.md)** (Cấu trúc bảng CSDL & Migration).

---

## 📑 BẢNG MỤC LỤC TÀI LIỆU DỰ ÁN

| Tài liệu | Đối tượng & Mục đích |
|---|---|
| 📖 [**USER_GUIDE.md**](docs/USER_GUIDE.md) | **Hướng dẫn sử dụng chi tiết A-Z**: Thao tác từng bước trên giao diện, quét hóa đơn AI, nhập Excel, nạp/rút tiết kiệm, cấu hình API Key. |
| 🏛️ [**SYSTEM_ARCHITECTURE.md**](docs/SYSTEM_ARCHITECTURE.md) | **Kiến trúc hệ thống toàn diện**: Phân tầng, luồng bảo mật JWT, sơ đồ ERD, cơ chế khóa dòng chống Race-condition. |
| 🤖 [**AI_DEVELOPMENT_LOG.md**](docs/AI_DEVELOPMENT_LOG.md) | **Minh chứng sử dụng AI**: Nhật ký Prompt 5 thành phần, phân tích BA, code AI sinh ra, quá trình rà soát và kiểm thử của sinh viên. |
| 🚀 [**DEVELOPMENT_PROCESS.md**](docs/DEVELOPMENT_PROCESS.md) | **Quy trình & Lộ trình phát triển**: Kế hoạch 5 Sprint Agile/Scrum, quản lý rủi ro và kết quả kiểm thử. |
| 📡 [**API.md**](docs/API.md) | Đặc tả chi tiết toàn bộ các RESTful API endpoints, request/response models. |
| 🗄️ [**DATABASE.md**](docs/DATABASE.md) | Thiết kế bảng cơ sở dữ liệu, quan hệ khóa ngoại, index và hướng dẫn migration. |
| 📝 [**CHANGELOG.md**](CHANGELOG.md) | Lịch sử cập nhật và các mốc phát hành tính năng. |

---

## ✨ TÍNH NĂNG NỔI BẬT

### 1. 📊 Quản lý Thu Chi & Thùng Rác Đa Năng
* **CRUD Giao dịch**: Thêm/Sửa/Xem giao dịch thu và chi, phân loại theo danh mục và hình thức thanh toán (Tiền mặt / Chuyển khoản).
* **Bộ lọc & Tìm kiếm**: Tìm kiếm nhanh có Debounce, lọc theo khoảng ngày, danh mục, loại thu chi, sắp xếp đa tiêu chí.
* **Thùng rác & Khôi phục**: Cơ chế Soft-delete an toàn, cho phép khôi phục hoặc xóa vĩnh viễn.
* **Nhân bản & Import Excel**: Nhân bản giao dịch chỉ với 1 cú click; nhập sao kê hàng loạt từ file Excel.

### 2. 🎯 Ngân Sách & Mục Tiêu Tiết Kiệm Thông Minh
* **Hạn mức Ngân sách**: Thiết lập định mức chi tiêu theo tháng cho từng danh mục, thanh tiến độ trực quan kèm cảnh báo bội chi.
* **Mục tiêu Tiết kiệm**: Tạo mục tiêu tích lũy (Mua laptop, Quỹ du lịch...), hỗ trợ nạp tiền thủ công hoặc **tự động trích từ nguồn thu nhập**.
* **Bảo vệ toàn vẹn luồng tiền**: Khóa bi quan (`FOR UPDATE`) ngăn chặn Race-condition và không bao giờ cho phép số dư ví khả dụng bị âm.

### 3. 🤖 Trí Tuệ Nhân Tạo & Trợ Lý FinAI
* **Trợ lý ảo FinAI Mascot 3D**: Nhân vật đồng xu hoạt hình chuyển động mượt mà, hỗ trợ tư vấn tài chính trực tiếp qua chatbox.
* **AI OCR Quét Hóa Đơn**: Tự động nhận diện số tiền, ngày mua và danh mục từ ảnh chụp hóa đơn (Google Gemini Vision).
* **Báo cáo Tài chính AI**: Tự động phân tích thói quen chi tiêu, chấm điểm sức khỏe tài chính hàng tháng.
* **Đề xuất Ngân sách AI**: Tự động tính toán và gợi ý hạn mức chi tiêu tối ưu cho tháng tiếp theo.

---

## 🏗️ CẤU TRÚC THƯ MỤC DỰ ÁN (5 PHÂN HỆ TIÊU CHUẨN)

```text
personal-expense-ai/
├── 🌐 frontend/                # [FRONTEND] Giao diện React 19, Vite, 28 file CSS module hóa
│   ├── src/
│   │   ├── api/                # Axios API client modules
│   │   ├── components/         # Reusable UI components & Mascot 3D
│   │   ├── pages/              # Màn hình chức năng (Dashboard, Budgets, Trash...)
│   │   ├── styles/             # Hệ thống 28 file CSS Module hóa
│   │   ├── App.jsx             # React Router & shell
│   │   └── index.css           # Master CSS Hub (53 dòng)
│   └── package.json
│
├── ⚙️ backend/                 # [BACKEND] Máy chủ FastAPI (Python)
│   ├── app/
│   │   ├── api/routes/         # REST API routers (/auth, /transactions...)
│   │   ├── core/               # Bảo mật, JWT, hashing, AI logic
│   │   ├── models/             # SQLAlchemy ORM Models
│   │   ├── schemas/            # Pydantic validation schemas
│   │   ├── services/           # AI OCR & Excel services
│   │   ├── config.py           # Quản lý cấu hình môi trường
│   │   └── main.py             # FastAPI App entry point
│   ├── tests/                  # Bộ test tự động pytest (167 test cases)
│   └── requirements.txt
│
├── 🗄️ database/                # [DATABASE] Toàn bộ mã DDL, Migration & Seed data
│   ├── migrations/             # Các file SQL Migration (001 -> 004)
│   ├── schema.sql              # File DDL toàn vẹn CSDL MySQL 8.0
│   ├── seed_demo.py            # Script khởi tạo 74 giao dịch demo 6 tháng
│   └── README.md               # Hướng dẫn quản trị và migration CSDL
│
├── 🔧 config/                  # [CONFIG] Quản lý cấu hình & biến môi trường
│   ├── .env.example            # Master environment configuration template
│   └── README.md               # Hướng dẫn chi tiết từng biến môi trường
│
├── 📖 docs/                    # [DOCS] Toàn bộ tài liệu kiến trúc, quy trình, hướng dẫn & AI
│   ├── USER_GUIDE.md           # Hướng dẫn sử dụng chi tiết A-Z
│   ├── SYSTEM_ARCHITECTURE.md  # Kiến trúc hệ thống, bảo mật JWT & ERD
│   ├── DEVELOPMENT_PROCESS.md  # Kế hoạch phát triển 5 Sprint Agile/Scrum
│   ├── AI_DEVELOPMENT_LOG.md   # Minh chứng Prompt AI 5 thành phần & BA
│   ├── API.md                  # Đặc tả RESTful API chi tiết
│   └── DATABASE.md             # Thiết kế CSDL & quy tắc khóa dòng
│
└── README.md                   # Hướng dẫn tổng quan & cài đặt nhanh
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN (QUICK START)

### Yêu cầu môi trường:
* **Python**: Phiên bản 3.11 trở lên.
* **Node.js**: Phiên bản 18+ (khuyên dùng Node 20+ hoặc 22).

---

### Bước 1: Khởi tạo file cấu hình môi trường (.env)

Mở terminal tại thư mục gốc dự án:
```powershell
# Sao chép file cấu hình mẫu từ thư mục config
Copy-Item config/.env.example backend/.env
```

#### ⚙️ TÙY CHỌN 1: CẤU HÌNH DATABASE (Chọn 1 trong 2 cách):
Mở file `backend/.env` và chọn kiểu Database bạn muốn dùng:

* **Cách A — Dùng SQLite (Khuyên dùng để Chạy Thử Ngay Không Cần Cài MySQL)**:
  ```env
  DATABASE_URL=sqlite:///./personal_expense.db
  ```
  *(Hệ thống sẽ tự động tạo file database cục bộ, không cần tài khoản hay mật khẩu nào).*

* **Cách B — Dùng MySQL (Môi trường Database chuẩn)**:
  ```env
  DATABASE_URL=mysql+pymysql://root:MAT_KHAU_MYSQL_CUA_BAN@localhost:3306/personal_expense
  ```
  *(Thay `MAT_KHAU_MYSQL_CUA_BAN` bằng mật khẩu root MySQL trên máy của bạn).*

#### ⚙️ TÙY CHỌN 2: CẤU HÌNH GEMINI API KEY (Dành cho tính năng AI):
* Nếu bạn muốn sử dụng **Quét hóa đơn AI**, **Chatbot FinAI**, **Báo cáo tài chính AI**:
  1. Lấy API Key miễn phí tại [Google AI Studio](https://aistudio.google.com/).
  2. Dán vào dòng `GEMINI_API_KEY` trong file `backend/.env`:
     ```env
     GEMINI_API_KEY=AIzaSy...ChuoiKeyCuaBan...
     ```
* *(Nếu chưa có API Key, bạn vẫn sử dụng được 100% các tính năng CRUD Thu chi, Ngân sách, Tiết kiệm, Biểu đồ và Import Excel bình thường).*

---

### Bước 2: Khởi động Máy Chủ Backend & Nạp Dữ Liệu Demo

```powershell
# 1. Tạo và kích hoạt môi trường ảo Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện phụ thuộc
python -m pip install -r backend/requirements.txt

# 3. Nạp sẵn dữ liệu mẫu 6 tháng sống động để trải nghiệm
python backend/seed_demo.py

# 4. Khởi chạy server FastAPI
python -m uvicorn app.main:app --reload --reload-dir backend --app-dir backend --host 127.0.0.1 --port 8000
```
* **API Swagger UI**: Truy cập `http://127.0.0.1:8000/docs` để xem và test API.

---

### Bước 3: Khởi động Giao Diện Web Frontend

Mở một cửa sổ Terminal mới:
```powershell
# 1. Di chuyển vào thư mục frontend
Set-Location frontend

# 2. Cài đặt packages
npm ci

# 3. Khởi chạy dev server
npm run dev
```
* **Giao diện Web**: Mở trình duyệt truy cập ngay **`http://localhost:5173`**.

---

## 🔑 THÔNG TIN ĐĂNG NHẬP TÀI KHOẢN DEMO

Sau khi chạy lệnh `python backend/seed_demo.py`, bạn hãy dùng tài khoản sau để đăng nhập:

* 📧 **Email**: `demo@example.com`
* 🔒 **Mật khẩu**: `Password123@`

*(Tài khoản này chứa sẵn **74 giao dịch** trải dài 6 tháng, 12 danh mục chuẩn, 2 mục tiêu tiết kiệm và 4 ngân sách tháng có đầy đủ biểu đồ sống động).*

---

## 🧪 KIỂM THỬ TỰ ĐỘNG (TESTING)

Hệ thống đạt tỷ lệ kiểm thử thành công **100% (162 Backend + 57 Frontend = 219 Tests Passed)**:

```powershell
# Chạy kiểm thử Frontend (Vitest)
cd frontend
npm test

# Chạy kiểm thử Backend (Pytest)
pytest backend/tests
```

---

## 🛡️ BẢO MẬT & BẢN QUYỀN

* Mật khẩu được mã hóa một chiều bằng thuật toán **Bcrypt** với Salt ngẫu nhiên.
* Xác thực phiên làm việc an toàn với chuẩn **JWT (JSON Web Token)**.
* Dự án được phát hành theo giấy phép mã nguồn mở [MIT License](LICENSE).
