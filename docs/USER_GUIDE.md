# 📖 HƯỚNG DẪN SỬ DỤNG HỆ THỐNG — PERSONAL EXPENSE AI (USER GUIDE)

> Tài liệu hướng dẫn chi tiết từng bước (Step-by-Step) cách cấu hình, đăng nhập và sử dụng toàn bộ các tính năng trên giao diện web của hệ thống **Quản lý Chi tiêu Cá nhân Tích hợp AI**.

---

## 📑 MỤC LỤC HƯỚNG DẪN

1. [Lộ Trình Đọc Tài Liệu & Chuẩn Bị Cài Đặt](#1-lộ-trình-đọc-tài-liệu--chuẩn-bị-cài-đặt)
2. [Cấu Hình Môi Trường (.env), Database & Gemini API Key](#2-cấu-hình-môi-trường-env-database--gemini-api-key)
3. [Đăng Nhập Bằng Tài Khoản Demo Sẵn Có (6 Tháng Dữ Liệu)](#3-đăng-nhập-bằng-tài-khoản-demo-sẵn-có-6-tháng-dữ-liệu)
4. [Quản Lý Giao Dịch Thu Chi & Thùng Rác](#4-quản-lý-giao-dịch-thu-chi--thùng-rác)
5. [Quét Hóa Đơn Tự Động Bằng AI (AI OCR Receipt)](#5-quét-hóa-đơn-tự-động-bằng-ai-ai-ocr-receipt)
6. [Theo Dõi 5 Chỉ Số Tài Chính & Bảng Thống Kê](#6-theo-dõi-5-chỉ-số-tài-chính--bảng-thống-kê)
7. [Thiết Lập Ngân Sách & Cảnh Báo Bội Chi (Email & In-App)](#7-thiết-lập-ngân-sách--cảnh-báo-bội-chi-email--in-app)
8. [Quản Lý Mục Tiêu Tiết Kiệm, Nạp/Rút & Cảnh Báo Hạn Chót](#8-quản-lý-mục-tiêu-tiết-kiệm-nạprút--cảnh-báo-hạn-chót)
9. [Trợ Lý Ảo FinAI & Báo Cáo Tài Chính AI Đa Trọng Tâm](#9-trợ-lý-ảo-finai--báo-cáo-tài-chính-ai-đa-trọng-tâm)
10. [Phân Hệ Quản Trị Hệ Thống Dành Cho Quản Trị Viên (Admin)](#10-phân-hệ-quản-trị-hệ-thống-dành-cho-quản-trị-viên-admin)

---

## 1. LỘ TRÌNH ĐỌC TÀI LIỆU & CHUẨN BỊ CÀI ĐẶT

Nếu bạn là người mới tiếp cận dự án hoặc là Giảng viên/Người chấm đồ án, hãy xem tài liệu theo thứ tự sau:

1. 🎯 **Bắt đầu từ file này ([docs/USER_GUIDE.md](USER_GUIDE.md))**: Để cấu hình môi trường, chạy demo và trải nghiệm các tính năng trên web.
2. 🏛️ **Đọc [docs/SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)**: Để đánh giá kiến trúc phần mềm, luồng xác thực JWT, sơ đồ ERD và cơ chế khóa dòng chống Race-condition.
3. 🤖 **Đọc [docs/AI_DEVELOPMENT_LOG.md](AI_DEVELOPMENT_LOG.md)**: Để chấm điểm tiêu chí sử dụng AI (nhật ký Prompt 5 thành phần, phân tích BA và phần code sinh viên rà soát).
4. 🚀 **Đọc [docs/DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)**: Để nắm toàn bộ tiến độ 7 Sprint phát triển theo Agile/Scrum.
5. 📡 **Tra cứu [docs/API.md](API.md) & [docs/DATABASE.md](DATABASE.md)**: Khi cần tra cứu chi tiết tham số API và bảng CSDL.

---

## 2. KHỞI CHẠY HỆ THỐNG VÀ CƠ SỞ DỮ LIỆU DOCKER

> 💡 **Điểm cốt lõi**: Toàn bộ hệ thống sử dụng **CSDL MySQL 8.0 chạy hoàn toàn trong Docker Container** (`expense_mysql`).  
> **Bạn KHÔNG CẦN phải cài đặt MySQL Server trên máy tính Windows!**

---

### 🌟 Cách 1 (Khuyên Dùng): Khởi chạy 1-Click bằng Docker Compose
Đây là cách nhanh nhất và thuận tiện nhất để trải nghiệm toàn bộ hệ thống:

1. **Khởi tạo file cấu hình .env**:
   `powershell
   Copy-Item .env.example .env    # Linux/Mac/Git Bash: cp .env.example .env
   `
2. **Khởi động 3 dịch vụ (MySQL 8.0, Backend FastAPI, Frontend React)**:
   `powershell
   docker compose up -d --build
   `
3. **Nạp sẵn 74 giao dịch demo 6 tháng**:
   `powershell
   docker compose exec backend python /app/database/seed_demo.py
   `
4. **Mở trình duyệt truy cập ngay**:
   * Giao diện Web: **http://localhost:5173**
   * Tài liệu API Swagger: **http://localhost:8000/docs**

---

### 💻 Cách 2: Chạy trực tiếp trên máy host (Dành cho Lập trình viên)
Nếu muốn chạy trực tiếp code Backend và Frontend để tiện debug, bạn vẫn sử dụng MySQL từ Docker (không cần cài MySQL trên Windows):

1. **Bật container MySQL trên Docker**:
   `powershell
   docker compose up -d mysql
   `
   *(Container MySQL tự động ánh xạ cổng 3307 ra máy của bạn).*

2. **Khởi tạo file cấu hình .env**:
   `powershell
   # Sao chép file cấu hình mẫu ra file .env duy nhất ở thư mục gốc
   Copy-Item .env.example .env    # Linux/Mac/Git Bash: cp .env.example .env
   `
   *(File .env duy nhất ở thư mục gốc được Backend FastAPI và Docker tự động nhận diện. Chuỗi kết nối mặc định đã trỏ sẵn vào MySQL Docker qua cổng 3307: mysql+pymysql://expense_user:expense_password@localhost:3307/personal_expense).*

3. **(Tùy chọn) Cấu hình Gemini API Key**:
   * Để trải nghiệm các tính năng AI (Quét hóa đơn, FinAI chat, Báo cáo tháng), dán key vào file .env ở thư mục gốc:
     ```env
     GEMINI_API_KEY=AIzaSy...ChuoiKeyCuaBan...
     ```
   * *(Nếu chưa có API Key, toàn bộ tính năng quản lý tài chính, ngân sách, tiết kiệm, biểu đồ vẫn hoạt động 100%).*

4. **Nạp dữ liệu mẫu và chạy Backend**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   python database/seed_demo.py
   python -m uvicorn app.main:app --reload --reload-dir backend --app-dir backend --host 127.0.0.1 --port 8000
   ```

5. **Khởi chạy Frontend React**:
   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

---

## 3. ĐĂNG NHẬP BẰNG TÀI KHOẢN DEMO SẴN CÓ (6 THÁNG DỮ LIỆU)

### 🔹 Cách 1: Sử dụng Tài khoản Demo có sẵn
1. Mở trình duyệt và truy cập: **`http://localhost:5173/login`**.
2. Nhập thông tin đăng nhập đã được nạp sẵn 74 giao dịch mẫu 6 tháng:
   * 📧 **Email**: `demo@example.com`
   * 🔒 **Mật khẩu**: `Password123@`
3. Nhấn **"Đăng nhập"** ➔ Hệ thống sẽ tự động chuyển hướng bạn vào màn hình **Dashboard Tổng quan**.

### 🔹 Cách 2: Đăng ký tài khoản mới của riêng bạn
1. Tại màn hình đăng nhập, bấm vào liên kết **"Đăng ký ngay"** (hoặc truy cập `http://localhost:5173/register`).
2. Điền đầy đủ: *Tên hiển thị*, *Email*, *Mật khẩu* (tối thiểu 8 ký tự).
3. Bấm **"Đăng ký"** ➔ Hệ thống sẽ tự động khởi tạo tài khoản cùng **12 danh mục thu chi chuẩn** (Ăn uống, Lương, Mua sắm, Nhà ở...).

---

## 4. QUẢN LÝ GIAO DỊCH THU CHI & THÙNG RÁC

### ➕ Thêm Giao Dịch Mới Thủ Công:
1. Vào mục **"Giao dịch"** trên menu bên trái (hoặc nhấn nút **"+ Thêm giao dịch"** ở Dashboard).
2. Điền các thông tin:
   * **Loại giao dịch**: Chọn *Chi tiêu (Expense)* hoặc *Thu nhập (Income)*.
   * **Số tiền**: Nhập số tiền (VD: `150000`).
   * **Danh mục**: Chọn danh mục phù hợp (Ăn uống, Đi lại, Mua sắm...).
   * **Ngày giao dịch**: Mặc định là ngày hôm nay, bạn có thể bấm vào lịch để chọn ngày trong quá khứ.
   * **Hình thức thanh toán**: *Tiền mặt* hoặc *Chuyển khoản*.
   * **Ghi chú**: Nhập mô tả chi tiết (VD: *"Ăn trưa cơm văn phòng"*).
3. Nhấn **"Lưu giao dịch"**.

### 🔄 Nhân Bản Nhanh Giao Dịch (Duplicate):
* Với các khoản chi định kỳ (như tiền nhà, tiền mạng), bấm vào nút **"Nhân bản" (biểu tượng Copy)** trên dòng giao dịch ➔ Hệ thống tự động điền sẵn form với ngày hôm nay, bạn chỉ cần bấm Lưu.

### 🗑️ Xóa Giao Dịch & Khôi Phục Từ Thùng Rác:
* **Chuyển vào thùng rác**: Nhấn nút **Xóa (Thùng rác)** ở giao dịch cần xóa $\rightarrow$ Bấm xác nhận.
  > *Lưu ý*: Nếu xóa khoản Thu nhập mà làm số dư ví bị âm, hệ thống sẽ cảnh báo ngăn chặn để bảo vệ an toàn luồng tiền.
* **Khôi phục**: Vào menu **"🗑️ Thùng rác"** $\rightarrow$ Tìm giao dịch cần lấy lại và bấm **"Khôi phục" (Restore)**.
* **Xóa vĩnh viễn**: Nhấn **"Xóa vĩnh viễn"** trong thùng rác để dọn sạch hoàn toàn khỏi CSDL.

---

## 5. QUÉT HÓA ĐƠN TỰ ĐỘNG BẰNG AI (AI OCR RECEIPT)

Thay vì ngồi gõ từng con số, bạn chỉ cần chụp ảnh hóa đơn hoặc ảnh chụp màn hình chuyển khoản ngân hàng:

1. Bấm nút **"+ Thêm giao dịch"** để mở form.
2. Tại khung **"📸 Quét hóa đơn bằng AI"**, bấm vào để tải ảnh lên (hoặc kéo thả file ảnh PNG/JPG).
3. Chờ 1-2 giây: Mô hình **Google Gemini Vision AI** sẽ tự động đọc ảnh và điền sẵn:
   * ✅ Số tiền chính xác từ hóa đơn.
   * ✅ Ngày in trên hóa đơn.
   * ✅ Tên quán / người nhận tiền.
   * ✅ Tự động chọn danh mục phù hợp nhất (VD: Hóa đơn Phúc Long tự động chọn *Ăn uống*).
4. Bạn kiểm tra lại thông tin và nhấn **"Lưu giao dịch"**.

---

## 6. THEO DÕI 5 CHỈ SỐ TÀI CHÍNH & BẢNG THỐNG KÊ

Tại trang **Thống kê** hoặc phần đầu của **Báo cáo Tài chính AI**, hệ thống tổng hợp bức tranh dòng tiền trực quan qua **5 ô thẻ chỉ số**:

1. ↗️ **Tổng Thu Nhập**: Tổng số tiền thu vào từ lương, thưởng, kinh doanh...
2. ↘️ **Tổng Chi Tiêu**: Tổng số tiền thực chi trong tháng.
3. ◆ **Tiết Kiệm Ròng (Net Savings)**: Tính theo công thức `Tổng Thu - Tổng Chi`. Phản ánh chính xác phần thặng dư tài chính thực tế.
4. % **Tỷ Lệ Tiết Kiệm (Savings Rate)**: Tỷ lệ phần trăm thặng dư trên tổng thu nhập. Mức an toàn được khuyến nghị từ **20% trở lên**.
5. 🎯 **Tích Lũy Mục Tiêu (Net Goal Saved)**: Phản ánh số tiền thực tế được đưa vào các hũ mục tiêu tiết kiệm trong tháng theo công thức chuẩn: `max(0, Đã Nạp - Đã Rút)`. Đảm bảo nếu người dùng nạp vào rồi rút ra chi dùng thì chỉ số sẽ không bị tính khống.

---

## 7. THIẾT LẬP NGÂN SÁCH & CẢNH BÁO BỘI CHI (EMAIL & IN-APP)

Tính năng giúp bạn kiểm soát chi tiêu, không bị "vung tay quá trán":

1. Vào mục **"Ngân sách"** trên thanh menu ➔ Bấm **"+ Đặt ngân sách mới"**:
   * Chọn **Danh mục** (VD: *Ăn uống*).
   * Nhập **Hạn mức tối đa** cho phép tiêu trong tháng (VD: `3.000.000 đ`).
2. **Theo dõi tiến độ chi tiêu trực quan**:
   * 🟢 **Màu xanh lá**: Chi tiêu an toàn (< 70% ngân sách).
   * 🟡 **Màu vàng**: Chi tiêu sắp chạm mức (70% - 99%).
   * 🔴 **Màu đỏ**: **Cảnh báo bội chi** (> 100% - Đã chi vượt mức cho phép).
3. **Cơ chế Cảnh báo Tự động qua Email**:
   * Khi bạn thêm một giao dịch chi tiêu khiến ngân sách chạm ngưỡng **≥ 80%** hoặc **vượt 100%**, hệ thống lập tức gửi một email cảnh báo chi tiết qua **Gmail SMTP** tới hòm thư cá nhân của bạn, nhắc nhở điều chỉnh chi tiêu kịp thời.

---

## 8. QUẢN LÝ MỤC TIÊU TIẾT KIỆM, NẠP/RÚT & CẢNH BÁO HẠN CHÓT

Giúp bạn tích lũy tiền mua sắm tài sản lớn (Laptop, Quỹ dự phòng, Du lịch...):

### 🎯 Tạo Mục Tiêu Tiết Kiệm:
1. Vào mục **"Mục tiêu tiết kiệm"** ➔ Bấm **"+ Tạo mục tiêu mới"**.
2. Nhập: *Tên mục tiêu* (VD: *"Mua Laptop"*), *Số tiền cần đạt* (VD: `30.000.000 đ`), *Hạn chót hoàn thành* (Deadline).

### 💰 Nạp & Rút Tiền Linh Hoạt:
* **Nạp tiền**: Bấm nút **"Nạp tiền"** trên thẻ mục tiêu để chuyển tiền từ số dư khả dụng vào quỹ; hoặc chọn **"Trích từ thu nhập"** khi ghi nhận khoản thu mới.
* **Rút tiền**: Bấm nút **"Rút tiền"** ➔ Nhập số tiền cần rút ➔ Tiền được giải phóng tức thì về số dư ví khả dụng. Cơ chế **Idempotency Key** bảo đảm không bị rút trùng khi mạng chập chờn.

### ⏰ Cảnh Báo Hạn Chót Mục Tiêu (In-App Alert Banner):
* Trên đầu trang Mục tiêu tiết kiệm và trang Dashboard, hệ thống tự động phát hiện các mục tiêu cận ngày:
  * ⚠️ **Quá hạn**: Mục tiêu chưa hoàn thành nhưng đã quá ngày hạn chót.
  * 🔥 **Hạn chót hôm nay**: Cần hoàn tất nạp tiền trong ngày.
  * ⚡ **Gấp (Còn ≤ 3 ngày)**: Nhắc nhở người dùng gấp rút tích lũy.

---

## 9. TRỢ LÝ ẢO FINAI & BÁO CÁO TÀI CHÍNH AI ĐA TRỌNG TÂM

### 🪙 Trò Chuyện Với Trợ Lý FinAI Mascot 3D:
* Nhấp vào nhân vật đồng xu 3D ở góc dưới màn hình để hỏi đáp thông minh:
  * *"Tháng này tôi tiêu nhiều nhất vào khoản nào?"*
  * *"Làm sao để tôi tiết kiệm thêm 2 triệu mỗi tháng?"*

### 📊 Báo Cáo Tài Chính AI Đa Trọng Tâm:
1. Vào mục **"Báo cáo thống kê"** ➔ Chuyển sang tab **"✨ Báo Cáo AI"**.
2. Lựa chọn **Tháng phân tích** và **1 trong 3 trọng tâm**:
   * 🌐 **Phân Tích Toàn Diện (360 Độ)**: Cân đối giữa thu chi, tỷ lệ tiết kiệm và phân bổ tài sản.
   * 💡 **Tối Ưu Tiết Kiệm**: Soi xét các khoản chi hao phí và đưa ra 3 biện pháp cắt giảm chi phí thực chiến.
   * 🛡️ **Cảnh Báo Rủi Ro & An Toàn**: Đánh giá nguy cơ thâm hụt dòng tiền, thanh khoản và lập quỹ khẩn cấp.
3. Bấm **"Xác Nhận & Sinh Báo Cáo AI"**:
   * **Nhận thức thời gian thực**: AI nhận diện chính xác ngày hiện tại trong tháng (ví dụ: ngày 26 cuối tháng ít dữ liệu vs đầu tháng) để đưa ra nhận định sắc bén.
   * **Bắt lỗi vượt ngân sách**: Nếu có danh mục bị vượt hạn mức (như *Ăn uống chi 3.450.000 đ / 3.000.000 đ*), AI sẽ chỉ đích danh tên danh mục, phân tích mức độ bội chi và yêu cầu cắt giảm khẩn cấp trong phần Khuyến nghị.

---

## 10. PHÂN HỆ QUẢN TRỊ HỆ THỐNG DÀNH CHO QUẢN TRỊ VIÊN (ADMIN)

Phân hệ dành riêng cho vai trò **Quản trị viên (System Administrator)** để vận hành hệ thống:

1. **Đăng nhập Tài khoản Admin**:
   * 📧 Email: `admin@example.com`
   * 🔒 Mật khẩu: `AdminPass123@`
2. **Dashboard Giám Sát Toàn Hệ Thống (`/admin`)**:
   * Theo dõi tổng số lượng người dùng trong hệ thống và trạng thái hoạt động.
   * Giám sát tổng số lượt gọi AI Gemini và tổng lượng Token API đã sử dụng để kiểm soát chi phí.
3. **Quản Trị Người Dùng & Khắc Phục Sự Cố**:
   * **Khóa / Mở khóa tài khoản**: Vô hiệu hóa quyền truy cập của tài khoản khi phát hiện dấu hiệu vi phạm hoặc theo yêu cầu bảo vệ người dùng.
   * **Cấp mật khẩu tạm thời**: Tạo mật khẩu tạm 8 ký tự hỗ trợ người dùng khi họ bị mất quyền truy cập email hoặc quên mật khẩu.
4. **Nguyên Tắc Bảo Vệ Quyền Riêng Tư (Zero-Knowledge Privacy)**:
   * Quản trị viên chỉ quản lý trạng thái tài khoản và tài nguyên kỹ thuật, tuyệt đối **không có quyền xem chi tiết các giao dịch thu/chi cá nhân** của người dùng.