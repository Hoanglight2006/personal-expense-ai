# Changelog

## Unreleased — 2026-08-18

### Added

- Transaction CRUD với filter, sort, pagination, duplicate prefill, thùng rác,
  restore và xóa vĩnh viễn.
- Category create/edit, default categories, thống kê, hide/restore và soft-delete.
- Summary `total_balance`, `available_balance`, `saving_balance` và dòng tiền
  tháng hiện tại.
- Phân bổ income Transaction vào Saving Goal và lịch sử contribution.
- Excel parse/preview, category suggestion, duplicate hint và bulk import từng
  dòng với database-backed idempotency key.
- Retry/error/empty states frontend, popup validation có focus về trường lỗi và
  tối ưu render trang Transaction.
- Composite ownership FK cho Transaction/Budget với Category.
- Test cho ownership, validation, balance, allocation, trash/restore,
  idempotency và stale frontend request.

### Security and data-integrity fixes

- Mọi Transaction/Category query được scope theo JWT user; resource của user khác
  không thể đọc hoặc sửa.
- Chặn Category của user khác, Category hidden/deleted hoặc Category sai loại khi
  tạo/import Transaction.
- Chặn đổi `Category.type` sau khi Category đã được dùng bởi Transaction/Budget.
- Dùng `NUMERIC(15,2)`/Decimal và kiểm tra giới hạn tiền thay cho float.
- Chặn Expense, Saving Goal deposit và các update làm `available_balance` âm.
- Tuần tự hóa thao tác thay đổi số dư bằng row lock User; khóa Goal theo thứ tự
  thống nhất.
- Không cho API contribution công khai giả mạo `income_allocation` hoặc
  `transaction_id`; chỉ Transaction service được tạo allocation liên kết.
- Bảo đảm allocation không vượt income nguồn hoặc phần còn thiếu của Goal.
- Đồng bộ `current_amount` khi trash/restore income allocation, kể cả Goal đang
  cancelled, để reactivation không làm sai số dư.
- Chống import lặp giữa worker bằng unique `(user_id, idempotency_key)`.
- Chặn response reload cũ ghi đè kết quả filter Transaction mới ở frontend.

### Verification

- Backend suite: 153 passed, 1 skipped tại lần xác minh gần nhất.
- Frontend suite: 53 passed tại lần xác minh gần nhất.
- Frontend lint và production build passed.
- `git diff --check` passed.

### Known limitations

- Full MySQL migration chain chưa được chạy trong môi trường hiện tại. Test mặc
  định dùng SQLite và không xác minh `SELECT ... FOR UPDATE`.
- Test MySQL tùy chọn hiện tập trung vào `001_category_management.sql`; cần chạy
  toàn bộ migration trên disposable/staging MySQL trước production.
- Vite vẫn cảnh báo main bundle lớn hơn 500 kB; build thành công nhưng route-level
  code splitting chưa được triển khai.
