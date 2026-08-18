# Changelog

## Unreleased — 2026-08-18

### Added

- Transaction CRUD với filter, sort, pagination, duplicate prefill, thùng rác,
  restore và xóa vĩnh viễn.
- Category create/edit, default categories, thống kê, hide/restore và soft-delete.
- Summary `total_balance`, `available_balance`, `saving_balance` và dòng tiền
  tháng hiện tại.
- Phân bổ income Transaction vào Saving Goal và lịch sử contribution.
- Rút một phần/toàn bộ tiền Saving Goal, hoàn lại số dư khả dụng và lưu lịch sử
  withdrawal; Goal đã completed vẫn giữ mốc hoàn thành sau khi rút.
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
- Chặn rút vượt `current_amount` và không cộng số dư hai lần khi Goal đang
  cancelled.
- Không cho API contribution công khai giả mạo `income_allocation` hoặc
  `transaction_id`; chỉ Transaction service được tạo allocation liên kết.
- Bảo đảm allocation không vượt income nguồn hoặc phần còn thiếu của Goal.
- Đồng bộ `current_amount` khi trash/restore income allocation, kể cả Goal đang
  cancelled, để reactivation không làm sai số dư.
- Chống import lặp giữa worker bằng unique `(user_id, idempotency_key)`.
- Chống rút tiết kiệm lặp bằng unique `(saving_goal_id, idempotency_key)` và
  replay an toàn khi client retry cùng payload.
- Migration 004 nâng cấp an toàn bảng withdrawal draft, backfill idempotency key
  cho dữ liệu hiện có thay vì yêu cầu xóa hoặc tạo lại bảng; allocation ứng viên
  được preflight trong temporary table và chỉ publish transactionally để lỗi
  không để lại ledger trung gian. Marker migration riêng ngăn key công khai dạng
  `legacy-<id>` bị nhận nhầm là dữ liệu draft khi chạy lại script.
- Chặn response reload cũ ghi đè kết quả filter Transaction mới ở frontend.
- Cho phép mở modal thiết lập ngân sách thủ công ngay trong tab AI gợi ý; modal
  không còn bị loại khỏi cây render khi tab AI đang hoạt động.
- Tái tính Saving Goal từ contribution hiệu lực trừ withdrawal khi trash/restore
  income nguồn; withdrawal được gắn với contribution đã tiêu thụ để ngăn số dư
  âm, tránh khôi phục thừa và không ảnh hưởng khoản nạp mới về sau.

### Verification

- Backend suite mặc định: 162 passed, 5 skipped; các test MySQL được skip nếu
  chưa bật biến môi trường.
- Frontend suite: 57 passed tại lần xác minh gần nhất.
- Migration trên disposable MySQL: 5 passed (001: 1 test; 004: 4 test), gồm
  fresh schema, draft backfill/retry/trash-restore và preflight rollback rồi
  chạy lại an toàn.
- Frontend lint và production build passed.
- `git diff --check` passed.

### Known limitations

- Full MySQL migration chain chưa được chạy trong môi trường hiện tại. Test mặc
  định dùng SQLite và không xác minh `SELECT ... FOR UPDATE`.
- Test MySQL tùy chọn kiểm tra riêng migration 001 và 004. Migration 002/003 và
  toàn bộ chain liên tục vẫn cần chạy trên disposable/staging MySQL trước
  production.
- Vite vẫn cảnh báo main bundle lớn hơn 500 kB; build thành công nhưng route-level
  code splitting chưa được triển khai.
