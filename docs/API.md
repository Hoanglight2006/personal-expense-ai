# API Transaction và Category

Base URL mặc định: `http://localhost:8000/api/v1`.

Ngoại trừ các endpoint đăng ký, đăng nhập và reset mật khẩu, API yêu cầu JWT:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Swagger UI tại `/docs` là nguồn tham chiếu tương tác cho toàn bộ schema hiện tại.

## Quy tắc ownership

- User hiện tại luôn được lấy từ JWT; payload Transaction/Category không có
  `user_id`.
- Mọi truy vấn đọc/sửa/xóa đều lọc đồng thời theo resource ID và `user_id`.
- Resource của user khác trả `404` thay vì tiết lộ rằng ID đó tồn tại.
- Category gắn vào Transaction phải thuộc cùng user. Database bảo vệ thêm bằng
  composite foreign key `(category_id, user_id)`.
- Saving Goal dùng trong allocation cũng phải thuộc user hiện tại.

## Transaction

### Endpoint

| Method | Path | Kết quả |
|---|---|---|
| `POST` | `/transactions` | Tạo Transaction; có thể phân bổ một phần income vào Saving Goal. |
| `GET` | `/transactions` | Danh sách active, filter/sort/pagination. |
| `GET` | `/transactions/trash` | Danh sách Transaction trong thùng rác. |
| `GET` | `/transactions/summary` | Tổng thu chi và số dư. |
| `GET` | `/transactions/{id}` | Chi tiết Transaction active thuộc user. |
| `PATCH` | `/transactions/{id}` | Cập nhật một hoặc nhiều trường cho phép. |
| `POST` | `/transactions/{id}/trash` | Soft-delete Transaction. |
| `POST` | `/transactions/{id}/restore` | Restore Transaction và contribution liên quan. |
| `DELETE` | `/transactions/{id}` | Xóa vĩnh viễn; Transaction phải ở trong thùng rác. |
| `POST` | `/transactions/{id}/duplicate` | Trả dữ liệu để prefill form; không tạo record mới. |

Query của `GET /transactions`:

- `search` tối đa 255 ký tự, tìm trong description.
- `date_start`, `date_end`: `YYYY-MM-DD`.
- `amount_min`, `amount_max`.
- `type`: `income` hoặc `expense`.
- `category_id`, `payment_method`: `cash` hoặc `bank_transfer`.
- `sort`: `date_desc`, `date_asc`, `amount_desc`, `amount_asc`.
- `page >= 1`, `page_size` từ 1 đến 100; mặc định 20.

### Tạo Transaction

```json
{
  "amount": "100000.00",
  "type": "income",
  "category_id": 12,
  "transaction_date": "2026-08-18",
  "description": "Lương tháng 8",
  "payment_method": "bank_transfer",
  "saving_goal_id": 5,
  "saving_goal_amount": "30000.00"
}
```

`saving_goal_id` và `saving_goal_amount` là tùy chọn nhưng chỉ hợp lệ với income.
Số tiền phân bổ phải dương, không vượt Transaction amount và không vượt phần còn
thiếu của Goal. Goal phải active, chưa hoàn thành và thuộc user.

Expense không được lớn hơn `available_balance`. API khóa hàng User trước khi đọc
và cập nhật các dữ liệu tác động số dư.

### Cập nhật Transaction

Payload là partial update và phải có ít nhất một trường:

```json
{
  "amount": "125000.00",
  "transaction_date": "2026-08-19",
  "description": "Điều chỉnh giao dịch",
  "payment_method": "cash"
}
```

Các trường cho phép: `amount`, `type`, `category_id`, `transaction_date`,
`description`, `payment_method`. Không được gửi null cho trường bắt buộc.

Nếu income đã có contribution, không thể đổi thành expense và không thể giảm
amount xuống thấp hơn tổng allocation. Khi đổi Category, Category mới phải active
và cùng loại với Transaction.

### Transaction response

```json
{
  "id": 101,
  "amount": "100000.00",
  "type": "income",
  "category_id": 12,
  "category": {
    "id": 12,
    "name": "Lương",
    "icon": "salary",
    "color": "#4B9D67",
    "is_active": true
  },
  "transaction_date": "2026-08-18",
  "description": "Lương tháng 8",
  "payment_method": "bank_transfer",
  "is_deleted": false,
  "created_at": "2026-08-18T08:00:00",
  "updated_at": "2026-08-18T08:00:00",
  "deleted_at": null
}
```

List response:

```json
{
  "items": [],
  "total_count": 0,
  "page": 1,
  "page_size": 20
}
```

Restore response bọc Transaction trong trường `transaction` và có
`category_warning`. Nếu Category hiện hidden, restore vẫn thành công nhưng trả
cảnh báo để người dùng cập nhật Category.

### Thùng rác và contribution

- Trash đặt `is_deleted=true`, ghi `deleted_at` và loại Transaction khỏi mọi tổng
  thu chi.
- Nếu income có allocation, trash trừ contribution khỏi `goal.current_amount`.
- Restore cộng lại contribution kể cả Goal đang cancelled để lịch sử và
  `current_amount` nhất quán. Goal cancelled vẫn chưa được tính vào
  `saving_balance`; khi reactivate, allocation được giữ lại đúng.
- Xóa vĩnh viễn xóa contribution liên kết rồi mới xóa Transaction.

### Số dư

`GET /transactions/summary` trả:

```json
{
  "total_balance": "70000.00",
  "available_balance": "40000.00",
  "saving_balance": "30000.00",
  "all_time_income": "100000.00",
  "all_time_expense": "30000.00",
  "month_income": "100000.00",
  "month_expense": "30000.00",
  "month_net": "70000.00"
}
```

- `total_balance = all_time_income - all_time_expense`, chỉ tính Transaction chưa
  bị trash.
- `saving_balance = SUM(current_amount)` của Goal active/completed; Goal cancelled
  bị loại khỏi phép tính.
- `available_balance = total_balance - saving_balance`.
- `month_net = month_income - month_expense` trong tháng hiện tại.

## Category

### Endpoint

| Method | Path | Kết quả |
|---|---|---|
| `POST` | `/categories` | Tạo Category của user. |
| `POST` | `/categories/defaults` | Tạo các Category mặc định còn thiếu. |
| `GET` | `/categories` | Danh sách và thống kê theo kỳ. |
| `GET` | `/categories/statistics` | Thống kê mọi Category active/hidden. |
| `GET` | `/categories/{id}` | Chi tiết Category chưa soft-delete. |
| `PATCH` | `/categories/{id}` | Đổi name/type/icon/color. |
| `POST` | `/categories/{id}/hide` | Chuyển sang hidden. |
| `POST` | `/categories/{id}/restore` | Khôi phục hidden về active. |
| `DELETE` | `/categories/{id}` | Soft-delete Category; không có API restore. |

Query danh sách: `search`, `status=active|hidden|all`,
`sort=amount_desc|amount_asc|name_asc`, `start_date`, `end_date`. Nếu không truyền
kỳ, API dùng tháng hiện tại.

### Payload và response

```json
{
  "name": "Ăn uống",
  "type": "expense",
  "icon": "food",
  "color": "#E76452"
}
```

Name được NFKC, trim và casefold để tạo khóa uniqueness theo user. Màu phải có
dạng `#RRGGBB`; icon phải thuộc danh sách hỗ trợ. PATCH nhận ít nhất một trong
`name`, `type`, `icon`, `color`.

```json
{
  "id": 3,
  "name": "Ăn uống",
  "type": "expense",
  "icon": "food",
  "color": "#E76452",
  "is_active": true,
  "is_default": false,
  "created_at": "2026-08-18T08:00:00",
  "updated_at": "2026-08-18T08:00:00",
  "has_transactions": true,
  "total_amount": "45000.00",
  "income_amount": "0.00",
  "expense_amount": "45000.00",
  "transaction_count": 1,
  "expense_percentage": "100.00"
}
```

### Active, hidden và deleted

- **Active:** dùng được cho Transaction mới, import và Budget.
- **Hidden:** vẫn tồn tại, giữ lịch sử và xuất hiện khi filter `hidden`/`all`.
  Không dùng được cho Transaction mới/import. Có thể gọi `/restore`.
- **Deleted:** `deleted_at` khác null, đồng thời `is_active=false`; bị loại khỏi
  mọi danh sách Category và không có endpoint restore. Delete là soft-delete để
  Transaction lịch sử không mất Category.
- Không thể đổi `type` nếu Category đã được dùng bởi bất kỳ Transaction nào
  (kể cả Transaction trong trash) hoặc Budget nào; API trả `409`.
- Tên normalized phải duy nhất theo user; conflict trả `409`.

## Mã lỗi

FastAPI trả lỗi dạng `{"detail": "..."}` hoặc danh sách validation detail.

| HTTP | Khi nào dùng |
|---:|---|
| `400 Bad Request` | Vi phạm nghiệp vụ: số dư âm, Goal cancelled/completed, allocation vượt giới hạn. |
| `401 Unauthorized` | Thiếu, hết hạn hoặc JWT không hợp lệ. |
| `404 Not Found` | Resource không tồn tại, đã bị loại khỏi scope endpoint, hoặc thuộc user khác. |
| `409 Conflict` | Trùng tên Category, đổi type Category đã được dùng, idempotency key đã xử lý hoặc database conflict. |
| `422 Unprocessable Content` | Payload/query sai schema, amount/date sai, Category hidden/type không khớp, thao tác trash/restore sai trạng thái. |


## Saving Goal contribution công khai

`POST /saving-goals/{goal_id}/contribute` chỉ nhận:

```json
{
  "amount": "50000.00",
  "note": "Nạp thủ công"
}
```

Schema dùng `extra="forbid"`: client không được gửi `source` hoặc
`transaction_id`. `income_allocation` chỉ do service Transaction tạo trong cùng
transaction database với income nguồn.

## Saving Goal withdrawal

`POST /saving-goals/{goal_id}/withdraw` rút một phần hoặc toàn bộ số tiền đang
tích lũy và lưu một bản ghi audit riêng:

```json
{
  "amount": "50000.00",
  "note": "Chi phí khẩn cấp",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440001"
}
```

Quy tắc:

- `amount` phải dương và không vượt `goal.current_amount`.
- `idempotency_key` dài 1–64 ký tự và ổn định cho một hành động rút. Retry cùng
  key và cùng payload trả kết quả hiện tại mà không tạo withdrawal mới. Dùng lại
  key với amount/note khác trả `409`.
- Không có prefix bị dành riêng; key như `legacy-2` vẫn là key công khai hợp lệ.
  Migration nhận diện dữ liệu draft bằng metadata database riêng, không suy luận
  từ nội dung key do client gửi.
- Frontend sinh key khi mở modal và giữ nguyên key nếu response bị timeout hoặc
  người dùng thử lại.
- Endpoint khóa User trước rồi Saving Goal để tuần tự hóa với Transaction và
  các thao tác số dư khác.
- Với Goal active/completed, phần tiền rút được giải phóng trở lại
  `available_balance` thông qua công thức số dư.
- Goal completed vẫn giữ trạng thái completed sau khi rút; trạng thái này ghi
  nhận mục tiêu đã từng hoàn thành, còn `current_amount` phản ánh số đang giữ.
- Goal cancelled vốn không nằm trong `saving_balance`; rút khi cancelled chỉ
  giảm số tích lũy và ghi lịch sử, không cộng số dư khả dụng lần hai.
- Goal phải thuộc user hiện tại; Goal của user khác trả `404`.
- Response là `SavingGoalResponse`, gồm cả `contributions` và `withdrawals`.
- Mỗi withdrawal được phân bổ vào các contribution mà nó đã tiêu thụ.
  Trash/restore chỉ cộng hoặc trừ phần contribution chưa từng được rút, không
  cộng/trừ trực tiếp toàn bộ allocation nguồn.


---

## Phân Hệ Trí Tuệ Nhân Tạo (AI Endpoints)

Base URL: `/api/v1/ai` và `/api/v1/ocr`

### 1. Báo Cáo Tài Chính AI Tháng (`POST /ai/monthly-report`)
Sinh báo cáo phân tích chi tiêu chuyên sâu với 5 chỉ số tài chính, chấm điểm sức khỏe tài chính và 3 khuyến nghị điều chỉnh.

**Request Body:**
```json
{
  "month": "2026-10",
  "focus": "comprehensive"
}
```
* `month`: Định dạng `YYYY-MM`.
* `focus`: 1 trong 3 trọng tâm: `"comprehensive"` (Toàn diện 360 độ), `"saving"` (Tối ưu cắt giảm chi phí), `"risk"` (Cảnh báo rủi ro & an toàn).

**Response (200 OK):**
```json
{
  "month": "2026-10",
  "financial_health_score": 85,
  "health_status": "Xuất sắc",
  "total_income": "37500000.00",
  "total_expense": "14080000.00",
  "net_savings": "23420000.00",
  "savings_rate": 62.5,
  "total_saving_deposited": "0.00",
  "overview": "Tổng quan tài chính tháng 10/2026 duy trì thặng dư ấn tượng...",
  "trend_analysis": "Chi tiêu tập trung ở Nhà ở và Ăn uống...",
  "adjustments": [
    "Cắt giảm chi tiêu ở danh mục Ăn uống do đã vượt hạn mức ngân sách...",
    "Thiết lập quỹ dự phòng khẩn cấp...",
    "Tiếp tục duy trì tỷ lệ tiết kiệm trên 20%..."
  ],
  "conclusion": "Tiếp tục duy trì kỷ luật ghi chép...",
  "raw_markdown": "# Báo Cáo Phân Tích Chi Tiêu..."
}
```

### 2. Gợi Ý Ngân Sách AI (`POST /ai/budget-recommendations`)
Phân tích lịch sử chi tiêu trung bình và đề xuất hạn mức chi tiêu tối ưu cho từng danh mục cho tháng tới.

**Request Body:**
```json
{
  "target_month": 11,
  "target_year": 2026,
  "lookback_months": 3
}
```

### 3. Áp Dụng Ngân Sách Gợi Ý (`POST /ai/budget-recommendations/apply`)
Lưu hàng loạt các hạn mức ngân sách AI đề xuất vào cơ sở dữ liệu chỉ với 1 click.

### 4. Trợ Lý Chat FinAI Mascot (`POST /ai/chat`)
Trò chuyện và hỏi đáp thông minh với trợ lý chi tiêu FinAI.
```json
{
  "message": "Tháng này tôi tiêu nhiều nhất vào đâu?"
}
```

### 5. Quét Hóa Đơn AI OCR (`POST /ocr/receipt`)
Tải lên file ảnh hóa đơn (`multipart/form-data`) để trích xuất tự động số tiền, ngày giao dịch và gợi ý danh mục chi tiêu qua Gemini Vision.

---

## Phân Hệ Quản Trị Hệ Thống (System Admin Endpoints)

Base URL: `/api/v1/admin`  
Yêu cầu quyền: Người dùng phải có quyền Quản trị viên (`role = "admin"`). Trả về `403 Forbidden` nếu người dùng thông thường truy cập.

### 1. Tổng Quan Hệ Thống & Giám Sát Tài Nguyên (`GET /admin/overview`)
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

### 2. Danh Sách Người Dùng (`GET /admin/users`)
Hỗ trợ tìm kiếm theo username/email và lọc theo trạng thái (`status=all|active|locked`).

### 3. Khóa / Mở Khóa Tài Khoản (`POST /admin/users/{user_id}/status`)
```json
{
  "status": "locked",
  "reason": "Phát hiện đăng nhập bất thường"
}
```

### 4. Cấp Mật Khẩu Tạm Thời (`POST /admin/users/{user_id}/temp-password`)
Hỗ trợ cấp mật khẩu tạm thời 8 ký tự cho người dùng gặp sự cố quên/mất tài khoản.
