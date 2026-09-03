# 📖 HƯỚNG DẪN SỬ DỤNG HỆ THỐNG — PERSONAL EXPENSE AI (USER GUIDE)

> Tài liệu hướng dẫn chi tiết từng bước (Step-by-Step) cách cấu hình, đăng nhập và sử dụng toàn bộ các tính năng trên giao diện web của hệ thống **Quản lý Chi tiêu Cá nhân Tích hợp AI**.

---

## 📑 MỤC LỤC HƯỚNG DẪN

1. [Lộ Trình Đọc Tài Liệu & Chuẩn Bị Cài Đặt](#1-lộ-trình-đọc-tài-liệu--chuẩn-bị-cài-đặt)
2. [Cấu Hình Môi Trường (.env), Database & Gemini API Key](#2-cấu-hình-môi-trường-env-database--gemini-api-key)
3. [Đăng Nhập Bằng Tài Khoản Demo Sẵn Có (6 Tháng Dữ Liệu)](#3-đăng-nhập-bằng-tài-khoản-demo-sẵn-có-6-tháng-dữ-liệu)
4. [Quản Lý Giao Dịch Thu Chi & Thùng Rác](#4-quản-lý-giao-dịch-thu-chi--thùng-rác)
5. [Quét Hóa Đơn Tự Động Bằng AI (AI OCR Receipt)](#5-quét-hóa-đơn-tự-động-bằng-ai-ai-ocr-receipt)
6. [Nhập Sao Kê Giao Dịch Hàng Loạt Bằng File Excel](#6-nhập-sao-kê-giao-dịch-hàng-loạt-bằng-file-excel)
7. [Thiết Lập & Theo Dõi Ngân Sách Tháng](#7-thiết-lập--theo-dõi-ngân-sách-tháng)
8. [Quản Lý Mục Tiêu Tiết Kiệm & Trích Thu Nhập](#8-quản-lý-mục-tiêu-tiết-kiệm--trích-thu-nhập)
9. [Tương Tác Với Trợ Lý Ảo FinAI & Báo Cáo Tài Chính AI](#9-tương-tác-với-trợ-lý-ảo-finai--báo-cáo-tài-chính-ai)

---

## 1. LỘ TRÌNH ĐỌC TÀI LIỆU & CHUẨN BỊ CÀI ĐẶT

Nếu bạn là người mới tiếp cận dự án hoặc là Giảng viên/Người chấm đồ án, hãy xem tài liệu theo thứ tự sau:

1. 🎯 **Bắt đầu từ file này ([docs/USER_GUIDE.md](USER_GUIDE.md))**: Để cấu hình môi trường, chạy demo và trải nghiệm các tính năng trên web.
2. 🏛️ **Đọc [docs/SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)**: Để đánh giá kiến trúc phần mềm, luồng xác thực JWT, sơ đồ ERD và cơ chế khóa dòng chống Race-condition.
3. 🤖 **Đọc [docs/AI_DEVELOPMENT_LOG.md](AI_DEVELOPMENT_LOG.md)**: Để chấm điểm tiêu chí sử dụng AI (nhật ký Prompt 5 thành phần, phân tích BA và phần code sinh viên rà soát).
4. 🚀 **Đọc [docs/DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)**: Để nắm toàn bộ tiến độ 5 Sprint phát triển theo Agile/Scrum.
5. 📡 **Tra cứu [docs/API.md](API.md) & [docs/DATABASE.md](DATABASE.md)**: Khi cần tra cứu chi tiết tham số API và bảng CSDL.

---

## 2. CẤU HÌNH MÔI TRƯỜNG (.ENV), DATABASE & GEMINI API KEY

Trước khi chạy hệ thống và nạp dữ liệu mẫu, bạn cần tạo file cấu hình:

### Bước 1: Tạo file cấu hình từ file mẫu
```powershell
# Sao chép file cấu hình mẫu từ thư mục config
Copy-Item config/.env.example backend/.env
```

### Bước 2: Chọn kiểu Cơ sở Dữ liệu (Database) trong `backend/.env`
Mở file `backend/.env` và chọn **1 trong 2 tùy chọn**:

* **Tùy chọn A — Dùng SQLite (Khuyên dùng để chạy thử nghiệm 1-Click ngay)**:
  ```env
  DATABASE_URL=sqlite:///./personal_expense.db
  ```
  *(Không cần cài MySQL, không cần mật khẩu, hệ thống tự tạo file database cục bộ).*

* **Tùy chọn B — Dùng MySQL (Môi trường Database chuẩn)**:
  ```env
  DATABASE_URL=mysql+pymysql://root:MAT_KHAU_MYSQL_CUA_BAN@localhost:3306/personal_expense
  ```
  *(Thay `MAT_KHAU_MYSQL_CUA_BAN` bằng mật khẩu root MySQL trên máy của bạn).*

### Bước 3: Cấu hình Gemini API Key (Dành cho tính năng AI)
* Nếu bạn muốn dùng thử tính năng **Quét hóa đơn AI**, **Chatbot FinAI**, **Báo cáo tài chính AI**:
  1. Truy cập [Google AI Studio](https://aistudio.google.com/) $\rightarrow$ Đăng nhập Google $\rightarrow$ Bấm **"Get API key"** $\rightarrow$ Tạo key miễn phí.
  2. Dán key vào file `backend/.env`:
     ```env
     GEMINI_API_KEY=AIzaSy...ChuoiKeyCuaBan...
     ```
* *(Nếu chưa có API Key, toàn bộ tính năng CRUD Giao dịch, Thùng rác, Ngân sách, Tiết kiệm, Biểu đồ và Import Excel vẫn hoạt động 100%).*

### Bước 4: Nạp dữ liệu mẫu Demo
Chạy lệnh sau tại thư mục gốc để tự động tạo tài khoản và nạp sẵn 74 giao dịch:
```powershell
python backend/seed_demo.py
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

## 6. NHẬP SAO KÊ GIAO DỊCH HÀNG LOẠT BẰNG FILE EXCEL

1. Vào trang **"Giao dịch"** ➔ Nhấn nút **"📥 Import Excel"**.
2. Chọn file Excel sao kê ngân hàng (`.xlsx` hoặc `.xls`).
3. Màn hình **Xem trước (Preview)** sẽ hiện ra: Bạn có thể chọn ghép cột (Cột Ngày, Cột Số tiền, Cột Ghi chú).
4. Bấm **"Xác nhận nhập dữ liệu"** ➔ Hàng chục giao dịch sẽ được thêm vào hệ thống cùng lúc chỉ trong vài giây.

---

## 7. THIẾT LẬP & THEO DÕI NGÂN SÁCH THÁNG

Tính năng giúp bạn kiểm soát không bị "vung tay quá trán" trong tháng:

1. Vào mục **"Ngân sách"** trên thanh menu.
2. Bấm **"+ Đặt ngân sách mới"**:
   * Chọn **Danh mục** (VD: *Ăn uống*).
   * Nhập **Hạn mức tối đa** cho phép tiêu trong tháng (VD: `5.000.000 đ`).
3. **Theo dõi tiến độ chi tiêu trực quan**:
   * 🟢 **Màu xanh lá**: Chi tiêu an toàn (< 70% ngân sách).
   * 🟡 **Màu vàng**: Chi tiêu sắp chạm mức (70% - 99%).
   * 🔴 **Màu đỏ**: **Cảnh báo bội chi** (> 100% - Đã chi vượt mức cho phép).

---

## 8. QUẢN LÝ MỤC TIÊU TIẾT KIỆM & TRÍCH THU NHẬP

Giúp bạn tích lũy tiền mua sắm tài sản lớn (Laptop, Xe máy, Quỹ du lịch...):

### 🎯 Tạo Mục Tiêu Tiết Kiệm:
1. Vào mục **"Mục tiêu tiết kiệm"** ➔ Bấm **"+ Tạo mục tiêu mới"**.
2. Nhập: *Tên mục tiêu* (VD: *"Mua Macbook M3"*), *Số tiền cần đạt* (VD: `45.000.000 đ`), *Hạn chót hoàn thành*.

### 💰 Cách Nạp Tiền Vào Mục Tiêu:
* **Cách 1 (Nạp tiền thủ công)**: Bấm nút **"Nạp tiền"** trên thẻ mục tiêu ➔ Nhập số tiền muốn trích từ số dư khả dụng vào quỹ.
* **Cách 2 (Trích tự động khi có Lương/Thu nhập)**: Khi bạn tạo 1 giao dịch **Thu nhập** mới (VD: Lương 30 triệu), ở cuối form chọn mục *"Trích vào mục tiêu tiết kiệm"* $\rightarrow$ Nhập 5 triệu. Hệ thống sẽ tự động cộng 5 triệu vào quỹ tiết kiệm ngay khi thêm giao dịch.

### 💸 Rút Tiền Từ Mục Tiêu Về Ví:
* Khi cần dùng tiền, bấm nút **"Rút tiền"** trên thẻ mục tiêu ➔ Nhập số tiền cần rút ➔ Tiền sẽ ngay lập tức được hoàn trả về **Số dư khả dụng** trong ví của bạn.

---

## 9. TƯƠNG TÁC VỚI TRỢ LÝ ẢO FINAI & BÁO CÁO TÀI CHÍNH AI

### 🪙 Trò Chuyện Với Trợ Lý FinAI Mascot 3D:
1. Nhìn vào góc dưới cùng bên phải màn hình, bạn sẽ thấy **Nhân vật đồng xu 3D FinAI** đang bay lơ lửng.
2. Nhấp chuột vào nhân vật để mở cửa sổ chat.
3. Bạn có thể bấm các câu hỏi gợi ý nhanh hoặc tự gõ câu hỏi:
   * *"Tháng này tôi tiêu nhiều nhất vào khoản nào?"*
   * *"Làm sao để tôi tiết kiệm thêm 3 triệu mỗi tháng?"*
   * *"Đánh giá tình hình tài chính tháng này của tôi."*

### 📊 Xem Báo Cáo Phân Tích Tài Chính Tháng Do AI Tạo:
1. Vào mục **"Báo cáo thống kê"** hoặc trang **"Ngân sách"** ➔ Bấm nút **"✨ Tạo Báo cáo AI"**.
2. AI sẽ tự động phân tích toàn bộ dữ liệu thu chi trong tháng, chấm điểm sức khỏe tài chính và đưa ra các đề xuất điều chỉnh ngân sách cực kỳ thông minh.
