# 💰 Hệ Thống Quản Lý Chi Tiêu Cá Nhân Tích Hợp AI (Personal Expense AI)

Hệ thống quản lý tài chính và chi tiêu cá nhân toàn diện, kết hợp trợ lý AI thông minh giúp theo dõi dòng tiền, lập ngân sách chi tiêu, quét hóa đơn tự động và phân tích tài chính cá nhân hóa.

---

## 📑 Mục Lục
1. [Giới Thiệu & Kiến Trúc Hệ Thống](#-giới-thiệu--kiến-trúc-hệ-thống)
2. [Các Tính Năng Chính](#-các-tính-năng-chính)
3. [Yêu Cầu Môi Trường](#-yêu-cầu-môi-trường)
4. [Hướng Dẫn Cài Đặt & Cấu Hình Chi Tiết](#-hướng-dẫn-cài-đặt--cấu-hình-chi-tiết)
5. [Hướng Dẫn Khởi Chạy Ứng Dụng](#-hướng-dẫn-khởi-chạy-ứng-dụng)
6. [Hướng Dẫn Kiểm Thử (Testing & Linting)](#-hướng-dẫn-kiểm-thử-testing--linting)
7. [Tóm Tắt Các Thay Đổi Mới Nhất (Changelog)](#-tóm-tắt-các-thay-đổi-mới-nhất-changelog)
8. [Quy Trình Phát Triển Với AI Agents](#-quy-trình-phát-triển-với-ai-agents)

---

## 🏛️ Giới Thiệu & Kiến Trúc Hệ Thống

Dự án được xây dựng theo kiến trúc Client-Server hiện đại, tách biệt hoàn toàn giữa Frontend và Backend qua RESTful API.

### Tech Stack
* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+ / 3.14), Pydantic v2, SQLAlchemy ORM, PyMySQL.
* **Frontend:** [React 19](https://react.dev/), [Vite](https://vitejs.dev/), React Router v7, Vanilla CSS (Glassmorphism & Micro-animations), Axios.
* **Cơ sở dữ liệu:** MySQL 8.0+.
* **AI & OCR Engine:** [Google Gemini API](https://ai.google.dev/) (`gemini-1.5-flash`), Tesseract / Vision OCR.
* **Kiểm thử tự động:** `pytest` (111 tests backend), `vitest` + `@testing-library/react` (24 tests frontend), `oxlint`.

---

## ✨ Các Tính Năng Chính

### 1. Xác thực & Quản lý Tài khoản (Authentication & Profile)
- Đăng ký tài khoản mới (tự động khởi tạo bộ danh mục Thu/Chi mặc định chuẩn).
- Đăng nhập bảo mật qua JSON Web Token (JWT Bearer).
- Quên mật khẩu & Đặt lại mật khẩu an toàn qua Email xác thực token một lần (dựa trên HMAC password version hash).
- Xem và chỉnh sửa hồ sơ cá nhân (Username, Email).
- Đổi mật khẩu có xác thực mật khẩu hiện tại.

### 2. Quản lý Danh mục Thu & Chi (Categories)
- Phân loại rõ ràng Danh mục **Chi tiêu (Expense)** và **Thu nhập (Income)**.
- Tùy biến linh hoạt Icon và Mã màu sắc nhận diện.
- Tính năng **Ẩn / Hiện danh mục** giúp tối ưu danh sách chọn khi không dùng đến.
- **Xóa mềm (Soft Delete)** bảo toàn nguyên vẹn lịch sử các giao dịch trong quá khứ.
- Thống kê tổng tiền và tỷ trọng chi tiêu trực tiếp theo từng danh mục.

### 3. Quản lý Giao dịch Tài chính (Transactions)
- Ghi nhận chi tiết: Số tiền, Ngày phát sinh, Loại (Thu/Chi), Danh mục, Phương thức thanh toán (Tiền mặt, Chuyển khoản, Thẻ tín dụng, Ví điện tử), Ghi chú.
- **Nhân bản nhanh (Duplicate Transaction):** Tự động điền dữ liệu giao dịch mẫu để ghi nhận chi tiêu định kỳ nhanh chóng.
- **Bộ lọc đa tiêu chí:** Lọc từ khóa ghi chú, khoảng ngày (Custom Date Picker), khoảng số tiền (Min-Max), loại giao dịch, danh mục, phương thức thanh toán.
- **Thùng rác giao dịch (Trash):** Khôi phục giao dịch đã xóa hoặc xóa vĩnh viễn.

### 4. Nhập liệu Thông minh & Tích hợp AI (Smart Import & AI)
- **Quét hóa đơn OCR (Receipt Scanner):** Chụp/Tải ảnh hóa đơn để AI tự động trích xuất số tiền, ngày giao dịch, nội dung và gợi ý danh mục phù hợp.
- **Nhập sao kê Excel hàng loạt (Excel Importer):** Tải file Excel sao kê ngân hàng (.xlsx, .xls). Hệ thống tự động nhận diện mẫu, gợi ý danh mục và **phát hiện giao dịch trùng lặp** trước khi xác nhận lưu.
- **Trợ lý AI Tài chính (FinAI Chatbot):** Trò chuyện trực tiếp cùng trợ lý ảo. AI phân tích số dư khả dụng, tổng thu chi thực tế trong tháng và đưa ra lời khuyên tài chính cá nhân hóa (đã tích hợp bộ lọc tự động che giấu số tài khoản / số thẻ ngân hàng để bảo vệ quyền riêng tư).

### 5. Quản lý Ngân sách & Cảnh báo Chi tiêu (Budgets & Alerts)
- Thiết lập ngân sách tối đa cho từng danh mục Chi tiêu theo tháng/năm.
- Tính toán tiến độ chi tiêu theo thời gian thực (Đã chi, Còn lại, % Đã sử dụng).
- **Hệ thống cảnh báo thông minh 3 cấp độ:**
  - 🟢 **Bình thường (Normal):** Chi tiêu `< 80%` hạn mức.
  - 🟡 **Cảnh báo (Warning):** Chi tiêu `≥ 80%` hạn mức.
  - 🔴 **Vượt hạn mức (Exceeded):** Chi tiêu `≥ 100%` hạn mức.
- Tự động tính toán **Hạn mức an toàn chi tiêu mỗi ngày** (Daily Safe Spend) dựa trên số tiền còn lại và số ngày còn lại trong tháng.
- Banner cảnh báo trực quan xuất hiện ngay tại Trang chủ (Dashboard) và Trang Ngân sách.

### 6. Bảng điều khiển Tổng quan & Thống kê (Dashboard & Analytics)
- Hiển thị Số dư khả dụng hiện tại, Tổng thu/chi trong tháng và toàn thời gian.
- Thanh tỷ trọng dòng tiền Thu / Chi sinh động.
- Danh sách 5 giao dịch gần nhất.
- Báo cáo thống kê trực quan dòng tiền theo chu kỳ thời gian.

---

## 💻 Yêu Cầu Môi Trường

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt:
- **Python:** Phiên bản `3.10` trở lên (Khuyến nghị 3.11 hoặc 3.12).
- **Node.js:** Phiên bản `18.x` trở lên (kèm `npm`).
- **MySQL Server:** Phiên bản `8.0` trở lên đang chạy cục bộ hoặc remote.
- **Git:** Để quản lý mã nguồn.

---

## 🛠️ Hướng Dẫn Cài Đặt & Cấu Hình Chi Tiết

### Bước 1: Clone mã nguồn từ GitHub
```bash
git clone https://github.com/Hoanglight2006/personal-expense-ai.git
cd personal-expense-ai
```

### Bước 2: Tạo Cơ Sở Dữ Liệu MySQL
Mở MySQL Workbench hoặc Command Line và tạo database:
```sql
CREATE DATABASE personal_expense CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### Bước 3: Cài đặt và Cấu hình Backend

1. **Di chuyển vào thư mục `backend`:**
   ```bash
   cd backend
   ```

2. **Tạo và kích hoạt môi trường ảo Python (Virtual Environment):**
   - **Trên Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Trên macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Cài đặt các gói phụ thuộc (Dependencies):**
   ```bash
   pip install -r requirements.txt
   ```

4. **Tạo file cấu hình môi trường `.env`:**
   Sao chép từ `.env.example`:
   - Trên Windows (PowerShell):
     ```powershell
     copy .env.example .env
     ```
   - Trên Linux/macOS:
     ```bash
     cp .env.example .env
     ```

5. **Chỉnh sửa file `backend/.env` phù hợp với máy của bạn:**
   ```env
   # Kết nối MySQL (thay root và mật khẩu của bạn)
   DATABASE_URL=mysql+pymysql://root:MatKhauCuaBan@localhost:3306/personal_expense

   # Khóa bí mật JWT (sinh một chuỗi ngẫu nhiên an toàn)
   SECRET_KEY=mot_chuoi_bi_mat_ngau_nhien_rat_dai_va_an_toan_123456

   # Cấu hình CORS & Frontend
   CORS_ORIGINS=["http://localhost:5173"]
   FRONTEND_BASE_URL=http://localhost:5173

   # Cấu hình AI Chatbot & OCR Scanner (Google Gemini)
   OCR_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSyD...Điền_API_Key_Gemini_Của_Bạn_Tại_Đây...
   GEMINI_MODEL=gemini-1.5-flash

   # Giới hạn kích thước upload (MB)
   MAX_IMAGE_SIZE_MB=10
   MAX_EXCEL_SIZE_MB=5

   # Cấu hình Email gửi link Reset Password (Tùy chọn - Gmail SMTP)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=email_cua_ban@gmail.com
   SMTP_PASSWORD=app_password_16_ky_tu
   SMTP_FROM_EMAIL=email_cua_ban@gmail.com
   ```

---

### Bước 4: Cài đặt và Cấu hình Frontend

1. **Mở một cửa sổ Terminal mới và di chuyển vào thư mục `frontend`:**
   ```bash
   cd frontend
   ```

2. **Cài đặt các thư viện Node.js:**
   ```bash
   npm install
   ```

3. **Tạo file cấu hình môi trường `.env` cho Frontend:**
   - Trên Windows (PowerShell):
     ```powershell
     copy .env.example .env
     ```
   - Trên Linux/macOS:
     ```bash
     cp .env.example .env
     ```

4. **Kiểm tra file `frontend/.env`:**
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

---

## 🚀 Hướng Dẫn Khởi Chạy Ứng Dụng

### 1. Khởi chạy Backend Server (FastAPI)
Từ thư mục gốc của dự án, mở Terminal và chạy lệnh sau (chú ý cờ `--reload-dir backend` để tránh lag do theo dõi `node_modules`):

```bash
# Đảm bảo đã kích hoạt môi trường ảo .venv
python -m uvicorn app.main:app --reload --reload-dir backend --app-dir backend --host 127.0.0.1 --port 8000
```
* Backend API Documentation (Swagger UI): **`http://127.0.0.1:8000/docs`**
* Health Check Endpoint: **`http://127.0.0.1:8000/health`**

### 2. Khởi chạy Frontend Dev Server (React Vite)
Mở một cửa sổ Terminal khác:

```bash
cd frontend
npm run dev
```
* Giao diện người dùng Web App: **`http://localhost:5173`**

---

## 🧪 Hướng Dẫn Kiểm Thử (Testing & Linting)

Dự án duy trì bộ kiểm thử tự động toàn diện để bảo đảm không xảy ra lỗi hồi quy (regression bugs).

### 1. Chạy Backend Unit & Integration Tests
```bash
cd backend
pytest
```
> **Kết quả chuẩn:** `110 passed, 1 skipped, 0 warnings` (Bao phủ Auth, Categories, Transactions, Budgets, OCR, Excel import).

### 2. Chạy Frontend Tests
```bash
cd frontend
npm test
```
> **Kết quả chuẩn:** `24 passed` (Bao phủ Categories, Budgets, Profile, PopupCoordination, Axios Interceptors).

### 3. Chạy Frontend Linter
```bash
cd frontend
npx oxlint
```
> **Kết quả chuẩn:** `0 errors, 0 warnings`.

---

## 📦 Tóm Tắt Các Thay Đổi Mới Nhất (Changelog)

### Nhánh: `feature/budgets-and-profile`
1. **Module Quản lý Ngân sách (Budgets):**
   - Bổ sung trọn bộ API CRUD ngân sách theo tháng/năm và danh mục.
   - Cơ chế tính toán số tiền đã tiêu, % sử dụng và trạng thái cảnh báo (`normal`, `warning`, `exceeded`).
   - Giao diện quản lý ngân sách trực quan với thanh tiến độ, bộ lọc trạng thái, chỉ số "Hạn mức chi an toàn mỗi ngày".
   - Tích hợp Banner cảnh báo vượt ngân sách tại Dashboard.
2. **Module Hồ sơ Người dùng (Profile):**
   - API & Giao diện xem/cập nhật thông tin tài khoản (Username, Email).
   - Chức năng đổi mật khẩu có kiểm tra bảo mật mật khẩu cũ.
3. **Tối ưu hóa AI Assistant & OCR:**
   - Chuẩn hóa model Google Gemini mặc định sang `gemini-1.5-flash` kèm cơ chế fallback thông minh.
   - Thêm bộ lọc bảo mật tự động che giấu số tài khoản, mã giao dịch, số thẻ ngân hàng trong mô tả trước khi gửi đến AI.
4. **Cải tiến Nhập liệu Excel & Khử trùng lặp (Duplicate Detection):**
   - Nâng cấp thuật toán phát hiện giao dịch trùng lặp khi import sao kê ngân hàng, xử lý chính xác các trường hợp không có mô tả (`description is None`).
5. **Đồng bộ & Chuẩn hóa Codebase:**
   - Chuẩn hóa HTTP Status Code `422_UNPROCESSABLE_CONTENT`.
   - Cung cấp đầy đủ file mẫu `.env.example` cho cả Frontend và Backend.
   - Khóa cuộn trang khi mở modal (`useModalLock`) và điều phối popup (`popupCoordinator`) chống tràn giao diện.

---

## 🤖 Quy Trình Phát Triển Với AI Agents

Dự án sử dụng mô hình pair-programming với **2 AI Agents** theo phân vai nghiêm ngặt:

* **`/agent-1-dev` (Full-stack Developer):** Chuyên trách triển khai mã nguồn Backend, Frontend, Cơ sở dữ liệu, viết Unit test và sửa lỗi.
* **`/agent-3-qa` (Senior QA & Security Reviewer):** Chuyên trách đọc, phân tích, kiểm thử bảo mật, review code độc lập và lập báo cáo phát hiện lỗi (không trực tiếp sửa file).

### Quy tắc an toàn dữ liệu:
* Tuyệt đối không commit file `.env` chứa API Key thật hoặc mật khẩu cơ sở dữ liệu lên GitHub.
* Mọi thay đổi lớn phải chạy qua bộ kiểm thử `pytest` và `npm test` trước khi tạo Pull Request vào nhánh `main`.

---
*Tài liệu được cập nhật tự động phục vụ bàn giao và phát triển dự án.*
