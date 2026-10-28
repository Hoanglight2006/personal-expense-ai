# 📡 ĐẶC TẢ TÀI LIỆU RESTFUL API — PERSONAL EXPENSE AI

> **Dự án**: Hệ thống Quản lý Chi tiêu Cá nhân Tích hợp AI (Personal Expense AI)  
> **Phiên bản API**: `v1`  
> **Base URL mặc định**: `http://localhost:8000/api/v1`  
> **Tài liệu trực quan Swagger UI**: `http://localhost:8000/docs`  
> **Tài liệu thay thế ReDoc**: `http://localhost:8000/redoc`  

---

## 🔐 1. NGUYÊN TẮC BẢO MẬT & XÁC THỰC (AUTHENTICATION & SECURITY)

Ngoại trừ các endpoint công khai (Đăng ký, Đăng nhập, Quên mật khẩu, Health check), toàn bộ các endpoint nghiệp vụ đều bắt buộc đính kèm JWT Access Token chuẩn RFC 7519 trong HTTP Header:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 1.1. Quy tắc Quyền sở hữu (Ownership & Data Isolation)
- **Cô lập dữ liệu tuyệt đối (Zero Cross-Tenant Leak)**: Người dùng hiện tại luôn được định danh an toàn từ chữ ký JWT (`current_user.id`). Payload request không chứa và không chấp nhận `user_id` từ client.
- **Che giấu tài nguyên không hợp lệ**: Khi truy vấn/sửa/xóa tài nguyên thuộc người dùng khác, hệ thống trả về mã lỗi `404 Not Found` (thay vì tiết lộ rằng ID đó đang tồn tại).
- **Ràng buộc toàn vẹn kép (Composite FK)**: Danh mục, ngân sách và giao dịch được bảo vệ thêm ở tầng CSDL bằng khóa ngoại kết hợp `(category_id, user_id)`.
- **Phân quyền vai trò (Role-Based Access Control)**:
  - `user`: Toàn quyền thao tác trên dữ liệu tài chính của chính mình.
  - `admin`: Quản trị tài khoản, cấp mật khẩu tạm và giám sát tài nguyên AI; **tuyệt đối không có quyền xem chi tiết chi tiêu riêng tư của người dùng** (Zero-Knowledge Privacy).

### 1.2. Chuẩn hóa Tiền tệ (Financial Invariance)
Mọi số tiền đều được lưu trữ và tính toán bằng kiểu `DECIMAL(15, 2)`, trả về dạng chuỗi định dạng (ví dụ: `"150000.00"`) để tránh lỗi làm tròn số thực (`float precision issue`).

---

## 👥 2. PHÂN HỆ XÁC THỰC & HỒ SƠ CÁ NHÂN (AUTHENTICATION & PROFILE)

Base URL: `/api/v1/auth`

| Method | Endpoint | Yêu cầu Auth | Mô tả nghiệp vụ |
|---|---|:---:|---|
| `POST` | `/auth/register` | Không | Đăng ký tài khoản mới, băm mật khẩu Bcrypt và tự động gán 12 danh mục mặc định. |
| `POST` | `/auth/login` | Không | Đăng nhập bằng email/password, nhận JWT Access Token (HS256). |
| `GET` | `/auth/me` | **Có** | Lấy thông tin hồ sơ tài khoản hiện tại, vai trò (role) và trạng thái xác thực. |
| `PATCH` | `/auth/me` | **Có** | Cập nhật thông tin hồ sơ (username, avatar_url). |
| `POST` | `/auth/avatar/upload` | **Có** | Upload ảnh đại diện người dùng (`multipart/form-data`). |
| `POST` | `/auth/change-password` | **Có** | Đổi mật khẩu cá nhân (yêu cầu mật khẩu cũ chính xác). |
| `POST` | `/auth/send-verification-email` | **Có** | Gửi mã OTP xác thực email qua Gmail SMTP. |
| `POST` | `/auth/verify-email` | **Có** | Xác thực mã OTP 6 chữ số để kích hoạt tích xanh verified. |
| `POST` | `/auth/forgot-password` | Không | Yêu cầu gửi mã khôi phục mật khẩu về email. |
| `POST` | `/auth/reset-password` | Không | Đặt lại mật khẩu mới bằng mã xác thực đặt lại. |
| `POST` | `/auth/dismiss-balance-guide` | **Có** | Đánh dấu đã đọc hướng dẫn thiết lập số dư ban đầu. |

---

## 📂 3. PHÂN HỆ DANH MỤC THU / CHI (CATEGORIES)

Base URL: `/api/v1/categories`

### 3.1. Danh sách Endpoint
| Method | Endpoint | Mô tả nghiệp vụ |
|---|---|---|
| `GET` | `/categories` | Danh sách danh mục của user (hỗ trợ query `include_hidden=true/false`). |
| `POST` | `/categories` | Tạo danh mục tùy chỉnh mới (tên không được trùng lặp trong cùng user). |
| `POST` | `/categories/defaults` | Khởi tạo lại bộ 12 danh mục mặc định cho user. |
| `GET` | `/categories/statistics` | Thống kê số lượng giao dịch và tổng tiền theo từng danh mục. |
| `GET` | `/categories/{id}` | Chi tiết một danh mục cụ thể thuộc user. |
| `PATCH` | `/categories/{id}` | Cập nhật tên, icon, mã màu hoặc trạng thái của danh mục. |
| `POST` | `/categories/{id}/hide` | Ẩn danh mục (Soft-hide) — bảo toàn toàn bộ giao dịch lịch sử. |
| `POST` | `/categories/{id}/restore` | Khôi phục danh mục đã ẩn trở lại trạng thái hoạt động. |
| `DELETE` | `/categories/{id}` | Xóa mềm danh mục (`deleted_at = NOW()`). |

### 3.2. Quy tắc Danh mục (Category Rules)
- **Active**: Sẵn sàng chọn khi tạo giao dịch mới hoặc thiết lập ngân sách.
- **Hidden**: Ẩn khỏi danh sách chọn nhưng vẫn hiển thị trong lịch sử thu chi cũ. Có thể khôi phục bất cứ lúc nào qua `/restore`.
- **Deleted**: Xóa mềm khỏi danh sách hiển thị, bản ghi được lưu trữ để không làm mất lịch sử giao dịch.
- **Bất biến loại danh mục**: Không thể đổi `type` (income sang expense hoặc ngược lại) nếu danh mục đã phát sinh giao dịch hoặc đã gắn với ngân sách (trả mã `409 Conflict`).

---

## 💳 4. PHÂN HỆ GIAO DỊCH & THÙNG RÁC (TRANSACTIONS & TRASH)

Base URL: `/api/v1/transactions`

### 4.1. Danh sách Endpoint
| Method | Endpoint | Mô tả nghiệp vụ |
|---|---|---|
| `POST` | `/transactions` | Tạo giao dịch mới (hỗ trợ trích tự động vào Saving Goal khi là income). |
| `GET` | `/transactions` | Danh sách giao dịch active có phân trang, lọc và sắp xếp. |
| `GET` | `/transactions/trash` | Danh sách giao dịch đang nằm trong thùng rác. |
| `GET` | `/transactions/summary` | Thống kê tổng thu, tổng chi và số dư khả dụng thực tế. |
| `GET` | `/transactions/{id}` | Xem chi tiết một giao dịch active. |
| `PATCH` | `/transactions/{id}` | Cập nhật thông tin giao dịch (kiểm tra bất biến số dư không âm). |
| `POST` | `/transactions/{id}/trash` | Chuyển giao dịch vào thùng rác (Soft-delete). |
| `POST` | `/transactions/{id}/restore` | Khôi phục giao dịch và phân bổ tích lũy từ thùng rác. |
| `DELETE` | `/transactions/{id}` | Xóa vĩnh viễn giao dịch (bắt buộc giao dịch phải ở trong thùng rác). |
| `POST` | `/transactions/{id}/duplicate` | Trả dữ liệu giao dịch mẫu để prefill form tạo mới nhanh. |

### 4.2. Tham số Query của `GET /transactions`
- `search`: Tìm kiếm gần đúng trong trường diễn giải (`description`).
- `date_start`, `date_end`: Giới hạn khoảng thời gian phát sinh giao dịch (`YYYY-MM-DD`).
- `amount_min`, `amount_max`: Giới hạn khoảng số tiền.
- `type`: Loại giao dịch (`income` hoặc `expense`).
- `category_id`: Lọc theo danh mục cụ thể.
- `payment_method`: Hình thức thanh toán (`cash` hoặc `bank_transfer`).
- `sort`: Tiêu chí sắp xếp (`date_desc`, `date_asc`, `amount_desc`, `amount_asc`).
- `page`, `page_size`: Phân trang dữ liệu (mặc định page=1, page_size=20, tối đa 100).

### 4.3. Payload Tạo Giao Dịch (`POST /transactions`)
```json
{
  "amount": "15000000.00",
  "type": "income",
  "category_id": 12,
  "transaction_date": "2026-10-15",
  "description": "Lương tháng 10/2026",
  "payment_method": "bank_transfer",
  "saving_goal_id": 3,
  "saving_goal_amount": "3000000.00"
}
```

---

## 📊 5. PHÂN HỆ NGÂN SÁCH CHI TIÊU (BUDGETS)

Base URL: `/api/v1/budgets`

### 5.1. Danh sách Endpoint
| Method | Endpoint | Mô tả nghiệp vụ |
|---|---|---|
| `POST` | `/budgets` | Thiết lập hạn mức ngân sách cho danh mục theo tháng/năm. |
| `GET` | `/budgets` | Lấy danh sách ngân sách tháng kèm tiến độ chi tiêu thực tế và cảnh báo. |
| `GET` | `/budgets/alerts` | Lấy danh sách danh mục chạm ngưỡng cảnh báo (>= 80%) hoặc bội chi (> 100%). |
| `GET` | `/budgets/{budget_id}` | Xem chi tiết hạn mức của một danh mục trong tháng. |
| `PATCH` | `/budgets/{budget_id}` | Cập nhật số tiền hạn mức ngân sách (`amount > 0`). |
| `DELETE` | `/budgets/{budget_id}` | Xóa bỏ hạn mức ngân sách đã thiết lập. |

### 5.2. Payload Thiết Lập Ngân Sách
```json
{
  "category_id": 5,
  "amount": "5000000.00",
  "month": 10,
  "year": 2026
}
```

---

## 🎯 6. PHÂN HỆ MỤC TIÊU TIẾT KIỆM (SAVING GOALS & LEDGER)

Base URL: `/api/v1/saving-goals`

### 6.1. Danh sách Endpoint
| Method | Endpoint | Mô tả nghiệp vụ |
|---|---|---|
| `GET` | `/saving-goals` | Danh sách mục tiêu tiết kiệm kèm tiến độ và cảnh báo hạn chót. |
| `POST` | `/saving-goals` | Tạo mục tiêu tích lũy mới. |
| `GET` | `/saving-goals/{goal_id}` | Chi tiết mục tiêu, danh sách các lần nạp (`contributions`) và rút (`withdrawals`). |
| `PATCH` | `/saving-goals/{goal_id}` | Cập nhật tên mục tiêu, hạn chót, số tiền kỳ vọng hoặc trạng thái. |
| `DELETE` | `/saving-goals/{goal_id}` | Xóa mục tiêu (hoàn trả số dư quỹ về ví khả dụng). |
| `POST` | `/saving-goals/{goal_id}/contribute` | Nạp tiền thủ công từ ví vào mục tiêu tiết kiệm. |
| `POST` | `/saving-goals/{goal_id}/withdraw` | Rút tiền từ mục tiêu về ví (áp dụng Idempotency Key & giải trừ FIFO). |

### 6.2. Nạp tiền thủ công (`POST /saving-goals/{goal_id}/contribute`)
```json
{
  "amount": "500000.00",
  "note": "Nạp thêm tiền thưởng dự án"
}
```

### 6.3. Rút tiền từ mục tiêu (`POST /saving-goals/{goal_id}/withdraw`)
```json
{
  "amount": "1000000.00",
  "note": "Chi tiêu khẩn cấp",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440001"
}
```

---

## 🤖 7. PHÂN HỆ TRÍ TUỆ NHÂN TẠO (AI & OCR ENDPOINTS)

Base URL: `/api/v1/ai` và `/api/v1/ocr`

### 7.1. Báo Cáo Tài Chính AI Tháng (`POST /ai/monthly-report`)
Sinh báo cáo phân tích chi tiêu với nhận thức thời gian thực, chấm điểm sức khỏe tài chính và 3 khuyến nghị hành động.
- **Request Body**:
  ```json
  {
    "month": "2026-10",
    "focus": "comprehensive"
  }
  ```
  *(Các trọng tâm `focus`: `"comprehensive"` - Toàn diện, `"saving"` - Tối ưu tiết kiệm, `"risk"` - Cảnh báo rủi ro).*

### 7.2. Gợi Ý Ngân Sách AI (`POST /ai/budget-recommendations`)
Phân tích lịch sử chi tiêu 3–6 tháng và quy tắc 50/30/20 để đề xuất ngân sách tháng tới.
- **Request Body**:
  ```json
  {
    "target_month": 11,
    "target_year": 2026,
    "lookback_months": 3
  }
  ```

### 7.3. Áp Dụng Ngân Sách Gợi Ý (`POST /ai/budget-recommendations/apply`)
Lưu hàng loạt các hạn mức ngân sách AI gợi ý vào CSDL chỉ với 1 cú click.

### 7.4. Trợ Lý Chat FinAI Mascot (`POST /ai/chat`)
Trò chuyện và hỏi đáp thông minh với trợ lý chi tiêu FinAI.
- **Request Body**:
  ```json
  {
    "message": "Tháng này tôi tiêu nhiều nhất vào đâu?"
  }
  ```

### 7.5. Quét Hóa Đơn AI OCR (`POST /ocr/receipt`)
Tải file ảnh hóa đơn (`multipart/form-data`) để trích xuất tự động số tiền, ngày giao dịch và gợi ý danh mục bằng Gemini Vision.

---

## 🛡️ 8. PHÂN HỆ QUẢN TRỊ HỆ THỐNG (SYSTEM ADMIN ENDPOINTS)

Base URL: `/api/v1/admin`  
*Yêu cầu quyền hạn*: Header Authorization của tài khoản có `role = "admin"`. Người dùng thông thường truy cập nhận mã lỗi `403 Forbidden`.

### 8.1. Tổng Quan Hệ Thống & Giám Sát Tài Nguyên (`GET /admin/overview`)
Trả về số liệu thống kê kỹ thuật toàn hệ thống:
```json
{
  "total_users": 25,
  "active_users": 23,
  "locked_users": 2,
  "total_transactions": 1420,
  "total_ai_tokens": 158420,
  "total_ai_requests": 340
}
```

### 8.2. Danh Sách Người Dùng (`GET /admin/users`)
Tìm kiếm theo username/email và lọc theo trạng thái (`status=all|active|locked`).

### 8.3. Khóa / Mở Khóa Tài Khoản (`POST /admin/users/{user_id}/status`)
```json
{
  "status": "locked",
  "reason": "Phát hiện dấu hiệu đăng nhập bất thường"
}
```

### 8.4. Cấp Mật Khẩu Tạm Thời (`POST /admin/users/{user_id}/temp-password`)
Cấp mật khẩu ngẫu nhiên an toàn 8 ký tự cho người dùng gặp sự cố quên/mất tài khoản.

---

## 🩺 9. KIỂM TRA TRẠNG THÁI HỆ THỐNG (HEALTH CHECK)

### `GET /health`
Kiểm tra khả năng phản hồi của Backend FastAPI:
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "app": "personal-expense-backend",
    "version": "1.0.0"
  }
  ```

---

## ⚠️ 10. BẢNG MÃ LỖI HTTP CHUẨN HÓA (ERROR RESPONSES)

FastAPI trả về lỗi chuẩn dạng `{"detail": "..."}`:

| Mã HTTP | Tên chuẩn | Khi nào hệ thống trả về |
|:---:|---|---|
| `400` | **Bad Request** | Vi phạm bất biến số dư (làm âm ví), số tiền <= 0, mục tiêu đã hủy/hoàn thành, hoặc cố tình tự khóa chính mình. |
| `401` | **Unauthorized** | Thiếu Header Authorization, Token JWT hết hạn hoặc chữ ký số không hợp lệ. |
| `403` | **Forbidden** | Người dùng thông thường cố tình truy cập vào phân hệ Quản trị viên (`/admin/*`). |
| `404` | **Not Found** | Bản ghi không tồn tại hoặc thuộc quyền sở hữu của người dùng khác. |
| `409` | **Conflict** | Trùng lặp dữ liệu duy nhất (email, tên danh mục trong cùng user, ngân sách trùng tháng), hoặc trùng Idempotency Key. |
| `422` | **Unprocessable Entity** | Dữ liệu đầu vào sai định dạng schema Pydantic (ví dụ: ngày sai chuẩn YYYY-MM-DD, email sai RFC). |
| `500` | **Internal Server Error** | Lỗi máy chủ chưa được bắt ngoại lệ (kèm log chi tiết ở backend). |
