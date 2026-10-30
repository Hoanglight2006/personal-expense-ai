# 💰 PERSONAL EXPENSE AI — HỆ THỐNG QUẢN LÝ TÀI CHÍNH CÁ NHÂN TÍCH HỢP AI

> **Hệ thống Quản lý Chi tiêu và Hoạch định Tài chính Thông minh** được xây dựng trên nền tảng **FastAPI (Python)**, **React 19 (Vite)**, **MySQL** và **Google Gemini AI**.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Bundler-Vite_8-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![MySQL](https://img.shields.io/badge/Database-MySQL_8.0-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com)
[![CI Pipeline](https://github.com/Hoanglight2006/personal-expense-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Hoanglight2006/personal-expense-ai/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Tests-260%20Passed-success.svg)](docs/DEVELOPMENT_PROCESS.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🧭 LỘ TRÌNH ĐỌC TÀI LIỆU (READING ROADMAP)

Để thuận tiện nhất cho việc theo dõi, chấm điểm hoặc trải nghiệm dự án, hãy đọc các tài liệu theo thứ tự khuyên nghị dưới đây:

```mermaid
graph LR
    Step1["1. USER_GUIDE.md<br/>(Hướng dẫn dùng & Demo)"] --> Step2["2. SYSTEM_ARCHITECTURE.md<br/>(Kiến trúc, JWT & ERD)"]
    Step2 --> Step3["3. AI_DEVELOPMENT_LOG.md<br/>(Minh chứng Prompt AI)"]
    Step3 --> Step4["4. DEVELOPMENT_PROCESS.md<br/>(Quy trình 6 Sprint)"]
    Step4 --> Step5["5. API & DATABASE.md<br/>(Tra cứu kỹ thuật)"]
```

1. 🎯 **Bước 1 — Dành cho mọi người (Xem hướng dẫn & Trải nghiệm giao diện)**:
   👉 Đọc **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**: Hướng dẫn đăng nhập tài khoản Demo có sẵn 74 giao dịch, thao tác quét hóa đơn AI, nạp/rút tiết kiệm và quản lý ngân sách.
2. 🏛️ **Bước 2 — Đánh giá Kiến trúc Hệ thống & Cơ sở Dữ liệu**:
   👉 Đọc **[docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)**: Thiết kế phân tầng, cơ chế xác thực JWT, khóa bi quan (`FOR UPDATE`) chống Race-condition và sơ đồ ERD.
3. 🤖 **Bước 3 — Đánh giá Minh chứng Ứng dụng AI khi Lập trình**:
   👉 Đọc **[docs/AI_DEVELOPMENT_LOG.md](docs/AI_DEVELOPMENT_LOG.md)**: Tổng hợp Prompt chuẩn 5 thành phần, phân tích BA, phần code AI sinh ra và phần sinh viên trực tiếp rà soát, sửa lỗi.
4. 🚀 **Bước 4 — Đánh giá Kế hoạch & Quy trình Phát triển Phần mềm**:
   👉 Đọc **[docs/DEVELOPMENT_PROCESS.md](docs/DEVELOPMENT_PROCESS.md)**: Báo cáo 6 Sprint theo mô hình Agile/Scrum và kết quả kiểm thử 260/260 test cases.
5. 📡 **Bước 5 — Tra cứu Kỹ thuật Chuyên sâu**:
   👉 Xem **[docs/API.md](docs/API.md)** (Đặc tả RESTful API) và **[docs/DATABASE.md](docs/DATABASE.md)** (Cấu trúc bảng CSDL & Migration).

---

## 📑 BẢNG MỤC LỤC TÀI LIỆU DỰ ÁN

| Tài liệu | Đối tượng & Mục đích |
|---|---|
| 📖 [**USER_GUIDE.md**](docs/USER_GUIDE.md) | **Hướng dẫn sử dụng chi tiết A-Z**: Thao tác từng bước trên giao diện, quét hóa đơn AI, nạp/rút tiết kiệm, thiết lập ngân sách, cấu hình API Key. |
| 🏛️ [**SYSTEM_ARCHITECTURE.md**](docs/SYSTEM_ARCHITECTURE.md) | **Kiến trúc hệ thống toàn diện**: Phân tầng, luồng bảo mật JWT, sơ đồ ERD, cơ chế khóa dòng chống Race-condition. |
| 🤖 [**AI_DEVELOPMENT_LOG.md**](docs/AI_DEVELOPMENT_LOG.md) | **Minh chứng sử dụng AI**: Nhật ký Prompt 5 thành phần, 10 Ca thực tế, code AI sinh ra, quá trình rà soát và kiểm thử của sinh viên. |
| 📑 [**AI_SDLC_INTEGRATION_REPORT.md**](docs/AI_SDLC_INTEGRATION_REPORT.md) | **Báo cáo thực hành Bài 5**: Tích hợp AI vào SDLC, sơ đồ trước/sau, ma trận kiểm soát Human Gate, đo lường định lượng và tự chấm 10/10 điểm. |
| 🚀 [**DEVELOPMENT_PROCESS.md**](docs/DEVELOPMENT_PROCESS.md) | **Quy trình & Lộ trình phát triển**: Kế hoạch 6 Sprint Agile/Scrum, quản lý rủi ro và kết quả kiểm thử. |
| 🧪 [**TEST_CASES.md**](docs/TEST_CASES.md) | **Ma trận kiểm thử tự động**: 260 bài test chi tiết (189 backend + 71 frontend) bao phủ toàn diện 7 phân hệ nghiệp vụ. |
| 📡 [**API.md**](docs/API.md) | Đặc tả chi tiết toàn bộ các RESTful API endpoints, request/response models. |
| 🗄️ [**DATABASE.md**](docs/DATABASE.md) | Thiết kế bảng cơ sở dữ liệu, quan hệ khóa ngoại, index và hướng dẫn migration. |
| 📝 [**CHANGELOG.md**](CHANGELOG.md) | Lịch sử cập nhật và các mốc phát hành tính năng. |

---

## ✨ TÍNH NĂNG NỔI BẬT

### 1. 📊 Quản lý Thu Chi & Thùng Rác Đa Năng
* **CRUD Giao dịch**: Thêm/Sửa/Xem giao dịch thu và chi, phân loại theo danh mục và hình thức thanh toán (Tiền mặt / Chuyển khoản).
* **Bộ lọc & Tìm kiếm**: Tìm kiếm nhanh có Debounce, lọc theo khoảng ngày, danh mục, loại thu chi, sắp xếp đa tiêu chí.
* **Thùng rác & Khôi phục**: Cơ chế Soft-delete an toàn, cho phép khôi phục hoặc xóa vĩnh viễn.
* **Nhân bản Giao dịch**: Nhân bản giao dịch chỉ với 1 cú click giúp ghi nhận nhanh các khoản chi định kỳ.

### 2. 🎯 Ngân Sách & Mục Tiêu Tiết Kiệm Thông Minh
* **Hạn mức Ngân sách**: Thiết lập định mức chi tiêu theo tháng cho từng danh mục, thanh tiến độ trực quan.
* **Cảnh báo Bội chi Ngân sách**: Hệ thống tự động gửi **Email thông báo qua Gmail SMTP** và gắn huy hiệu cảnh báo In-App ngay khi mức chi tiêu chạm hoặc vượt hạn mức đề ra.
* **Mục tiêu Tiết kiệm**: Tạo mục tiêu tích lũy (Mua laptop, Quỹ du lịch...), hỗ trợ nạp tiền thủ công hoặc **tự động trích từ nguồn thu nhập**.
* **Rút tiền Linh hoạt & An toàn**: Cho phép rút tiền từ mục tiêu về số dư khả dụng với cơ chế **Idempotency Key** chống trùng lặp.
* **Cảnh báo Hạn chót Mục tiêu (In-App Alert Banner)**: Hệ thống tự động tính số ngày còn lại (`days_remaining`) và hiển thị banner cảnh báo trực quan cho các mục tiêu: *Quá hạn*, *Hạn chót hôm nay*, hoặc *Sắp đến hạn trong 3 ngày*.
* **Bảo vệ toàn vẹn luồng tiền**: Khóa bi quan (`FOR UPDATE`) ngăn chặn Race-condition và không bao giờ cho phép số dư ví khả dụng bị âm.

### 3. 🤖 Trí Tuệ Nhân Tạo & Báo Cáo Tài Chính FinAI
* **Trợ lý ảo FinAI Mascot 3D**: Nhân vật đồng xu hoạt hình chuyển động mượt mà, hỗ trợ tư vấn tài chính trực tiếp qua chatbox.
* **AI OCR Quét Hóa Đơn**: Tự động nhận diện số tiền, ngày mua và danh mục từ ảnh chụp hóa đơn (Google Gemini Vision).
* **5 Chỉ số Sức khỏe Tài chính Toàn diện**: Tổng Thu Nhập, Tổng Chi Tiêu, Tiết Kiệm Ròng, Tỷ Lệ Tiết Kiệm, và **🎯 Tích Lũy Mục Tiêu (Nạp - Rút)**.
* **Báo cáo Tài chính AI Đa Trọng Tâm**: Hỗ trợ 3 tùy chọn phân tích chuyên sâu (*Toàn diện 360 độ*, *Tối ưu tiết kiệm & cắt giảm chi phí*, *Cảnh báo rủi ro & an toàn tài chính*).
* **Nhận thức Thời gian Thực & Bắt lỗi Vượt Hạn mức**: AI phân biệt chính xác thời gian thực (đầu tháng vs cuối tháng ít giao dịch vs tháng đã qua), tự động phát hiện và chỉ đích danh danh mục bị vượt trần ngân sách, đưa ra hành động cắt giảm khẩn cấp.
* **Đề xuất Ngân sách & Báo cáo Tích hợp RAG Lai**: Tự động tính toán và gợi ý hạn mức chi tiêu tối ưu bám sát thói quen tiêu dùng kết hợp hệ thống RAG tri thức tài chính lai (Local-First 500-char Chunking + Fallback Live Web Search DuckDuckGo thời gian thực) kèm trích dẫn nguồn chuẩn mực minh bạch.

### 4. 🛡️ Phân Hệ Quản Trị Hệ Thống (System Administration)
* **Giám sát Tài nguyên & Chi phí AI**: Dashboard quản trị viên theo dõi tổng người dùng, tổng giao dịch, tần suất gọi mô hình Gemini AI và lượng Token API tiêu thụ.
* **Quản trị Người dùng**: Xem danh sách tài khoản, Khóa / Mở khóa người dùng khi phát hiện bất thường, Hỗ trợ cấp mật khẩu tạm thời khi người dùng gặp sự cố đăng nhập.
* **Bảo vệ Quyền riêng tư (Zero-Knowledge Privacy)**: Quản trị viên chỉ quản lý trạng thái tài khoản và tài nguyên kỹ thuật, tuyệt đối không can thiệp và không thể xem chi tiết giao dịch thu chi cá nhân của người dùng.

---

## 🏗️ CẤU TRÚC THƯ MỤC DỰ ÁN (5 PHÂN HỆ TIÊU CHUẨN)

```text
personal-expense-ai/
├── 🌐 frontend/                # [FRONTEND] React 19 + Vite (Component & Page Architecture)
│   ├── src/
│   │   ├── api/                # Axios API client modules
│   │   ├── components/         # Reusable UI (Modals, Popups, DatePicker, FinAI Mascot 3D)
│   │   ├── constants/          # Application constants & presets
│   │   ├── context/            # Global Auth & App State Context
│   │   ├── hooks/              # Custom React Hooks
│   │   ├── pages/              # Màn hình ứng dụng & Co-located Unit Tests
│   │   │   ├── admin/          # AdminPage & Dashboard quản trị viên
│   │   │   ├── Budgets.jsx     # Quản lý ngân sách & tiến độ chi tiêu (+ Budgets.test.jsx)
│   │   │   ├── Categories.jsx  # Quản lý danh mục thu/chi (+ Categories.test.jsx)
│   │   │   ├── Dashboard.jsx   # Tổng quan số dư ví & biểu đồ
│   │   │   ├── Login.jsx, Register.jsx, ForgotPassword.jsx, ResetPassword.jsx # Xác thực
│   │   │   ├── Profile.jsx     # Quản lý thông tin & mật khẩu (+ Profile.test.jsx)
│   │   │   ├── SavingGoals.jsx # Mục tiêu tích lũy & nạp/rút (+ SavingGoals.test.jsx)
│   │   │   ├── Statistics.jsx  # Báo cáo & phân tích AI (+ Statistics.test.jsx)
│   │   │   └── Transactions.jsx, TransactionTrash.jsx # Quản lý giao dịch thu chi
│   │   ├── styles/             # Hệ thống 28 file CSS module hóa (base, components, layout, pages)
│   │   ├── test/               # Cấu hình kiểm thử Vitest & mocks
│   │   ├── utils/              # Helper functions (Định dạng tiền tệ, ngày tháng UTC+7)
│   │   ├── App.jsx             # React Router & ProtectedRoute
│   │   ├── index.css           # Master CSS Hub (@import)
│   │   └── main.jsx            # Entry point ứng dụng React
│   ├── .env.example            # Vite frontend environment template
│   ├── package.json            # Quản lý dependencies frontend (Vitest 71 tests)
│   └── vite.config.js          # Cấu hình Vite & proxy
│
├── ⚙️ backend/                 # [BACKEND] Kiến trúc 3 lớp (3-Tier) với FastAPI & SQLAlchemy
│   ├── app/
│   │   ├── api/routes/         # Thin Controllers: Tiếp nhận HTTP request & ủy quyền cho Service
│   │   │   ├── admin.py        # Router phân hệ quản trị viên (Admin Portal)
│   │   │   ├── ai.py, chat.py, ocr.py # Router AI Báo cáo, Trợ lý FinAI & Quét hóa đơn OCR
│   │   │   ├── auth.py         # Router xác thực JWT, OTP kích hoạt & đổi mật khẩu
│   │   │   ├── budgets.py      # Router quản lý ngân sách tháng
│   │   │   ├── categories.py   # Router danh mục thu/chi & Soft-hide
│   │   │   ├── saving_goals.py # Router mục tiêu tiết kiệm, nạp/rút tiền (FIFO)
│   │   │   └── transactions.py # Router giao dịch thu/chi, khóa dòng & thùng rác
│   │   ├── services/           # Service Layer: Đóng gói 100% nghiệp vụ tài chính & tính toán
│   │   │   ├── admin_service.py # Xử lý khóa tài khoản, cấp pass tạm, telemetry AI
│   │   │   ├── auth_service.py  # Xử lý đăng ký, đăng nhập, token, đổi mật khẩu
│   │   │   ├── budget_service.py # Xử lý ngân sách, cảnh báo ngưỡng 80%, bội chi
│   │   │   ├── category_service.py # Xử lý danh mục, gán preset icon, khôi phục
│   │   │   ├── email_service.py # Gửi email cảnh báo ngân sách & OTP qua SMTP Gmail
│   │   │   ├── financial_alert_service.py # Phát hiện cảnh báo hạn chót & vi phạm ngân sách
│   │   │   ├── saving_service.py # Xử lý tích lũy, nạp/rút tiền, kiểm tra số dư ví
│   │   │   └── transaction_service.py # Xử lý CRUD giao dịch, khóa dòng, phân bổ mục tiêu
│   │   ├── core/               # Bảo mật, JWT, hashing, AI prompt logic
│   │   │   └── rag/            # RAG Engine: loader, recursive chunking, retriever, live web search
│   ├── data/knowledge_base/    # Kho tri thức tài chính chuẩn mực (.md, .pdf)
│   │   │   └── rag/            # RAG Engine: loader, recursive chunking, retriever, live web search
│   ├── data/knowledge_base/    # Kho tri thức tài chính chuẩn mực (.md, .pdf)
│   │   ├── models/             # SQLAlchemy ORM Models (User, Transaction, Category...)
│   │   ├── schemas/            # Pydantic Schemas (Request/Response validation)
│   │   ├── config.py           # Quản lý biến môi trường Pydantic Settings
│   │   ├── database.py         # Kết nối DB Engine & Session factory
│   │   └── main.py             # FastAPI Application initialization
│   ├── tests/                  # Bộ kiểm thử tự động pytest (189 test cases: 18 RAG + 8 AI)
│   └── requirements.txt        # Danh sách thư viện Python
│
├── 🗄️ database/                # [DATABASE] Toàn bộ mã DDL, Migration & Seed data
│   ├── migrations/             # Các file SQL Migration (001 -> 006)
│   ├── schema.sql              # File DDL toàn vẹn của CSDL MySQL 8.0
│   ├── seed_demo.py            # Script khởi tạo 74 giao dịch demo 6 tháng
│   └── README.md               # Hướng dẫn quản trị và migration CSDL
│
├── 🔧 config/                  # [CONFIG] Quản lý cấu hình & tài liệu biến môi trường
│   ├── prompts.json            # Tập trung toàn bộ cấu hình Prompt AI & Guardrails
│   └── README.md               # Hướng dẫn chi tiết từng biến môi trường
│
├── 📖 docs/                    # [DOCS] Toàn bộ tài liệu kiến trúc, quy trình, hướng dẫn & AI
│   ├── USER_GUIDE.md           # Hướng dẫn sử dụng chi tiết A-Z
│   ├── SYSTEM_ARCHITECTURE.md  # Kiến trúc hệ thống, bảo mật JWT & ERD
│   ├── DEVELOPMENT_PROCESS.md  # Kế hoạch phát triển 6 Sprint Agile/Scrum
│   ├── TEST_CASES.md           # Kịch bản kiểm thử toàn diện (238 test cases: 168 backend + 70 frontend)
│   ├── AI_DEVELOPMENT_LOG.md   # Minh chứng Prompt AI 5 thành phần & BA
│   ├── API.md                  # Đặc tả RESTful API chi tiết
│   ├── DATABASE.md             # Thiết kế CSDL & quy tắc khóa dòng (001 -> 006)
│   ├── PROMPT_BENCHMARK_REPORT.md # Báo cáo benchmark prompt AI
│   └── reports/                # Thư mục chứa các tài liệu báo cáo học phần
│
├── 🐳 docker-compose.yml       # Điều phối triển khai trọn gói MySQL 8.0, Backend, Frontend
├── 📄 .env.example             # Master Environment Configuration Template duy nhất
├── 📜 CHANGELOG.md             # Lịch sử cập nhật và phát hành qua các Sprint
└── README.md                   # Hướng dẫn tổng quan & cài đặt nhanh
```

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG

> 💡 **Quan trọng về Cơ sở dữ liệu**: Toàn bộ hệ thống chuẩn hóa sử dụng **CSDL MySQL 8.0 chạy hoàn toàn trong Docker Container** (`expense_mysql`).  
> **Bạn KHÔNG CẦN phải cài đặt MySQL trên máy tính Windows!** Mọi cấu trúc bảng, ràng buộc toàn vẹn và dữ liệu mẫu đều được Docker tự động thiết lập và lưu trữ an toàn trong Docker Volume.

---

### 🌟 CÁCH 1 (KHUYÊN DÙNG) — Khởi Chạy 1-Click Trọn Gói Bằng Docker Compose
*Dành cho Giảng viên, Người chấm bài hoặc Người dùng muốn trải nghiệm ngay toàn bộ hệ thống mà không cần cài đặt Python, Node.js hay MySQL.*

**Yêu cầu duy nhất**: Máy tính đã cài đặt [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```powershell
# 1. (Khuyên dùng) Tạo file .env từ file mẫu để điền GEMINI_API_KEY nếu có
Copy-Item .env.example .env    # Linux/Mac/Git Bash: cp .env.example .env

# 2. Khởi động toàn bộ 3 dịch vụ: MySQL 8.0, Backend FastAPI và Frontend React
docker compose up -d --build

# 3. Nạp sẵn 74 giao dịch demo 6 tháng sống động vào hệ thống
docker compose exec backend python /app/database/seed_demo.py
```

* 🌐 **Giao diện Web Người Dùng**: **`http://localhost:5173`**
* 📡 **Tài liệu API Swagger**: **`http://localhost:8000/docs`**
* 🛑 **Dừng toàn bộ hệ thống**: `docker compose down`

---

### 💻 CÁCH 2 — Dành Cho Lập Trình Viên (Local Development)
*Dành cho trường hợp bạn muốn chỉnh sửa code Backend/Frontend trực tiếp trên máy tính. **CSDL MySQL 8.0 vẫn chạy trong Docker Container**, không cần cài MySQL trên Windows.*

#### Yêu cầu:
* **Docker Desktop** (để chạy MySQL container).
* **Python**: Phiên bản 3.11+.
* **Node.js**: Phiên bản 18+ (khuyên dùng Node 20+).

#### Bước 1: Khởi động CSDL MySQL trên Docker
```powershell
# Chỉ khởi chạy duy nhất container MySQL 8.0 (ánh xạ cổng 3307 ra máy host)
docker compose up -d mysql
```

#### Bước 2: Cấu hình môi trường (.env)
```powershell
# Sao chép file cấu hình mẫu ra file .env duy nhất ở thư mục gốc
Copy-Item .env.example .env    # Linux/Mac/Git Bash: cp .env.example .env
```
*(File .env duy nhất ở thư mục gốc được cả Backend FastAPI lẫn Docker Compose tự động nhận diện. File mẫu đã thiết lập sẵn chuỗi kết nối MySQL qua cổng 3307: mysql+pymysql://expense_user:expense_password@localhost:3307/personal_expense).*

#### Bước 3: Khởi động Backend FastAPI & Nạp Dữ Liệu Demo
```powershell
# 1. Tạo và kích hoạt môi trường ảo Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện backend
python -m pip install -r backend/requirements.txt

# 3. Nạp dữ liệu demo 74 giao dịch
python database/seed_demo.py

# 4. Khởi chạy server FastAPI
python -m uvicorn app.main:app --reload --reload-dir backend --app-dir backend --host 127.0.0.1 --port 8000
```

#### Bước 4: Khởi động Frontend React
Mở một cửa sổ Terminal mới:
```powershell
Set-Location frontend
npm ci
npm run dev
```
* Mở trình duyệt truy cập ngay **`http://localhost:5173`**.

---

### ⚙️ GIẢI THÍCH CHI TIẾT CÁC BIẾN MÔI TRƯỜNG (.ENV)

| Biến môi trường | Mục đích & Hướng dẫn | Giá trị khuyến nghị |
|---|---|---|
| `DATABASE_URL` | Chuỗi kết nối CSDL MySQL. Khi chạy ngoài máy host, kết nối qua cổng ánh xạ `3307` của Docker. | `mysql+pymysql://expense_user:expense_password@localhost:3307/personal_expense` |
| `SECRET_KEY` | Khóa bí mật dùng để mã hóa và ký JSON Web Token (JWT). | Chuỗi ngẫu nhiên tối thiểu 32 ký tự |
| `GEMINI_API_KEY` | Khóa API dịch vụ Google Gemini (dùng cho Chatbot FinAI, quét hóa đơn OCR và báo cáo tháng). Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey). *(Nếu để trống, các tính năng tài chính khác vẫn hoạt động 100%)*. | `AIzaSy...` |
| `SMTP_*` | Cấu hình gửi cảnh báo bội chi ngân sách qua Gmail SMTP *(Tùy chọn)*. | `smtp.gmail.com` (Port 587) |

---

### ⚠️ BẢNG KHẮC PHỤC SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

| Hiện tượng lỗi | Nguyên nhân gốc rễ | Cách xử lý trong 5 giây |
|---|---|---|
| `docker compose up` báo lỗi không kết nối được Docker daemon | Docker Desktop chưa được bật trên máy tính | Mở ứng dụng Docker Desktop lên và đợi biểu tượng góc dưới chuyển sang màu xanh lá (Engine running). |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Chính sách bảo mật PowerShell của Windows chặn script `.ps1` | Chạy lệnh này trên PowerShell trước khi kích hoạt venv:<br>`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Chạy `seed_demo.py` báo lỗi kết nối CSDL | Container MySQL chưa khởi động xong hoàn toàn | Đợi khoảng 5–10 giây cho MySQL hoàn tất khởi tạo ban đầu rồi chạy lại lệnh `python database/seed_demo.py`. |
| Chatbot AI hoặc Quét hóa đơn OCR báo lỗi | Chưa điền hoặc sai `GEMINI_API_KEY` | Vào [Google AI Studio](https://aistudio.google.com/app/apikey) tạo key miễn phí và dán vào dòng `GEMINI_API_KEY=...` trong file `.env`. |
| Port 3307 bị báo lỗi `address already in use` | Máy tính đã có ứng dụng khác chiếm cổng 3307 | Đổi số cổng phía trước trong `docker-compose.yml` (ví dụ `"3308:3306"`) và sửa số cổng tương ứng trong `.env`. |

---

## 🔑 THÔNG TIN ĐĂNG NHẬP TÀI KHOẢN DEMO

Sau khi nạp dữ liệu mẫu bằng `seed_demo.py`, bạn có thể đăng nhập bằng 2 tài khoản:

1. 👤 **Tài khoản Người Dùng (End-User)**:
   * 📧 **Email**: `demo@example.com`
   * 🔒 **Mật khẩu**: `Password123@`
   * *(Chứa sẵn **74 giao dịch** trải dài 6 tháng, 12 danh mục chuẩn, 2 mục tiêu tiết kiệm và 4 ngân sách tháng có đầy đủ biểu đồ sống động).*

2. 🛡️ **Tài khoản Quản Trị Viên (System Admin)**:
   * 📧 **Email**: `admin@example.com`
   * 🔒 **Mật khẩu**: `AdminPass123@`
   * *(Truy cập trang Quản trị `/admin`: Giám sát tài nguyên hệ thống, kiểm soát chi phí token AI Gemini, quản lý người dùng).*

---

## Sao lưu và khôi phục cơ sở dữ liệu

Dự án có sẵn script sao lưu và phục hồi cho cả SQLite và MySQL, dữ liệu lưu trong thư mục `backups/`:

* **Sao lưu**:
  * Windows: Chạy file [`scripts/backup.bat`](scripts/backup.bat)
  * Dòng lệnh: `python scripts/backup_db.py`
* **Khôi phục**:
  * Windows: Chạy file [`scripts/restore.bat`](scripts/restore.bat)
  * Dòng lệnh: `python scripts/restore_db.py` (hoặc `python scripts/restore_db.py --file <đường_dẫn_file>`)

---

## 🧪 KIỂM THỬ TỰ ĐỘNG (TESTING)

Hệ thống đạt tỷ lệ kiểm thử thành công **100% (168 Backend + 70 Frontend = 238 Tests Passed)**:

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
