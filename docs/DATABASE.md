# Database và migration

Ứng dụng dùng SQLAlchemy 2 và MySQL 8 trong môi trường thực tế. Test thông thường
dùng SQLite in-memory để chạy nhanh; SQLite không xác minh được hành vi
`SELECT ... FOR UPDATE` của MySQL.

## Schema liên quan tài chính

### `categories`

- PK: `id`.
- Ownership: `user_id -> users.id ON DELETE CASCADE`.
- Trường chính: `name`, `name_normalized`, `type`, `icon`, `color`, `is_active`,
  `is_default`, `created_at`, `updated_at`, `deleted_at`.
- Unique `(user_id, name_normalized)`.
- Unique `(id, user_id)` là candidate key cho composite FK.

`type` hiện là chuỗi `income`/`expense` và là một phần bắt buộc của nghiệp vụ
Category/Transaction hiện tại.

### `transactions`

- PK: `id`; ownership `user_id`.
- `amount NUMERIC(15,2)` với check `amount > 0`.
- `type`, `category_id`, `transaction_date`, `description`, `payment_method`.
- Soft delete: `is_deleted`, `deleted_at`.
- Composite FK:

```text
(category_id, user_id)
    -> categories(id, user_id)
    ON DELETE CASCADE
```

Composite FK ngăn một Transaction tham chiếu Category của user khác ngay cả khi
application validation bị bỏ qua.

### `budgets`

- `amount NUMERIC(15,2)` và check dương.
- Composite FK `(category_id, user_id) -> categories(id, user_id)`.
- Unique `(user_id, category_id, month, year)`.

### Saving Goal ledger

- `target_amount`, `current_amount`, contribution `amount` đều `NUMERIC(15,2)`.
- `current_amount` là giá trị denormalized bằng tổng phần chưa bị rút của các
  contribution hiệu lực và phải luôn không âm.
- Contribution `manual` có `transaction_id = NULL`.
- Contribution `income_allocation` liên kết income Transaction;
  `transaction_id -> transactions.id ON DELETE SET NULL` ở cấp model.
- Trash/restore Transaction điều chỉnh `current_amount`; xóa vĩnh viễn Transaction
  xóa contribution liên kết trước.
- Withdrawal lưu amount dương, note, `idempotency_key` và thời điểm trong
  `saving_withdrawals`; `saving_goal_id` dùng `ON DELETE CASCADE`.
- Unique `(saving_goal_id, idempotency_key)` chống retry trùng và request đồng
  thời. Goal đã thuộc duy nhất một user nên constraint này tương đương scope
  user/Goal.
- `saving_withdrawal_allocations` phân bổ amount của mỗi withdrawal vào đúng các
  `saving_contributions` đã bị tiêu thụ. Unique `(withdrawal_id, contribution_id)`;
  cả hai foreign key dùng `ON DELETE CASCADE`.
- Rút tiền giảm `current_amount` trong cùng transaction và giải phóng số dư khả
  dụng với Goal active/completed. Goal cancelled không cộng số dư lần hai.
- Khi trash/restore income nguồn, backend cộng phần còn lại của từng contribution:
  `max(contribution.amount - withdrawal_allocated, 0)`, rồi mới kiểm tra số dư
  dự kiến. Vì vậy allocation đã rút không bị giải phóng hoặc khôi phục thêm lần
  nữa, còn contribution nạp sau đó vẫn được tính đầy đủ.

### `import_idempotency_keys`

- `id`, `user_id`, `idempotency_key`, `created_at`.
- Unique `(user_id, idempotency_key)`.
- Key chỉ được ghi khi batch có ít nhất một dòng import thành công.
- Constraint database bảo vệ chống submit lặp giữa nhiều worker/process.

## Kiểu tiền

Mọi số tiền nghiệp vụ dùng `NUMERIC(15,2)`/`Decimal`, không dùng float. Giới hạn
schema Transaction là `9,999,999,999,999.99`; API chuẩn hóa về hai chữ số thập
phân và từ chối số âm, zero, NaN, infinity hoặc vượt giới hạn.

## Ownership và khóa đồng thời

- Query application luôn lọc theo `user_id` hiện tại.
- Composite FK bảo vệ ownership Category cho Transaction và Budget.
- Endpoint thay đổi số dư khóa hàng `users` bằng `SELECT ... FOR UPDATE` trước
  khi tính `available_balance`.
- Khi có Saving Goal, thứ tự khóa là User trước rồi Goal để giảm nguy cơ deadlock.
- SQLite unit/integration tests không chứng minh row-lock; cần MySQL integration
  test cho cạnh tranh thật.

## Soft-delete semantics

### Transaction

- Trash: `is_deleted=true`, đặt `deleted_at`.
- Transaction trong trash không tham gia list thường, summary, duplicate
  detection hoặc thống kê.
- Restore đặt lại `is_deleted=false`, `deleted_at=NULL` và khôi phục allocation.
- Xóa vĩnh viễn chỉ được phép khi đang ở trash.

### Category

- Hide chỉ đặt `is_active=false`; có thể restore.
- Delete đặt `deleted_at`, `is_active=false` và đổi `name_normalized` để giải phóng
  unique name. Đây là soft-delete không có endpoint restore.
- Category soft-deleted bị loại khỏi Category API nhưng record được giữ để bảo
  toàn lịch sử Transaction.

## Khởi tạo database mới

Tạo database MySQL UTF-8, cấu hình `backend/.env`, rồi khởi động backend. Hàm
`Base.metadata.create_all()` tạo bảng còn thiếu:

```sql
CREATE DATABASE personal_expense
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

`create_all()` không phải migration engine: nó không tự sửa đầy đủ bảng legacy đã
tồn tại. Với production database hiện hữu, luôn backup và chạy migration đã kiểm
chứng trước khi deploy code.

## SQL migration legacy

Các script MySQL 8 nằm tại `backend/migrations`:

1. `001_category_management.sql`: merge tên Category legacy trùng, repoint
   Transaction/Budget và thêm composite ownership constraints.
2. `002_transaction_management.sql`: thêm payment method, soft-delete fields và
   index Transaction.
3. `003_category_soft_delete.sql`: thêm `categories.deleted_at` và index.
4. `004_saving_withdrawals.sql`: thêm sổ lịch sử rút tiền cho Saving Goal. Script
   cũng nâng cấp bản draft đã có bảng withdrawal nhưng thiếu `idempotency_key`,
   backfill dữ liệu cũ bằng `legacy-<id>` rồi thêm unique constraint. Allocation
   suy luận được dựng và kiểm tra trong temporary table; chỉ publish vào bảng
   thật trong transaction sau khi toàn bộ preflight đạt. Exception handler sẽ
   rollback nên preflight lỗi không để lại allocation trung gian. Một bảng marker
   tạm thời ở cấp migration ghi lại đúng các row từng thiếu key; nội dung key API
   không được dùng để nhận diện legacy. Marker được giữ nếu migration lỗi để hỗ
   trợ retry và được drop sau khi migration thành công.

Script dùng stored procedure và `information_schema` guards để có thể retry sau
DDL bị gián đoạn. Việc merge Category trong `001` không rollback được; phải phục
hồi backup nếu cần quay lại.

`001` nhắm tới một schema legacy cụ thể và không phải script tạo schema mới. Code
hiện tại yêu cầu `categories.type`; hãy đối chiếu schema đích và kiểm chứng toàn bộ
chain trước khi dùng trên dữ liệu thật. Trong môi trường làm việc hiện tại, full
MySQL migration chain chưa được chạy; đây là giới hạn xác minh đã biết.

Ví dụ chạy thủ công bằng MySQL client sau khi backup:

```powershell
Get-Content -Raw backend/migrations/001_category_management.sql | mysql --host=localhost --user=root --password personal_expense
Get-Content -Raw backend/migrations/002_transaction_management.sql | mysql --host=localhost --user=root --password personal_expense
Get-Content -Raw backend/migrations/003_category_soft_delete.sql | mysql --host=localhost --user=root --password personal_expense
Get-Content -Raw backend/migrations/004_saving_withdrawals.sql | mysql --host=localhost --user=root --password personal_expense
```

Không chạy các SQL này trên SQLite.

## Test migration MySQL bằng database dùng một lần

Test `backend/tests/test_category_migration_mysql.py` kiểm tra migration 001:

- Kết nối tới MySQL server từ `DATABASE_URL`.
- Tạo database ngẫu nhiên `category_migration_test_<suffix>`.
- Tạo schema legacy và dữ liệu trùng.
- Chạy `001_category_management.sql` hai lần để kiểm tra retry safety.
- Kiểm tra merge, budget roll-up và composite constraints.
- Drop database trong `finally`, kể cả khi test thất bại.

Test `backend/tests/test_saving_withdrawal_migration_mysql.py` kiểm tra migration
004:

- Tạo schema mới rồi chạy migration hai lần.
- Nâng cấp schema draft có withdrawal cũ và backfill allocation FIFO.
- Giữ nguyên ledger của withdrawal mới có key công khai giống `legacy-<id>` khi
  chạy lại migration.
- Kiểm tra trash/restore vẫn giữ đúng phần contribution chưa bị rút.
- Xác nhận preflight dừng migration khi ledger suy luận không khớp
  `current_amount`, bảng allocation thật vẫn rỗng và có thể sửa dữ liệu rồi chạy
  migration lại an toàn.
- Mỗi test dùng database ngẫu nhiên và drop trong `finally`.

Tài khoản MySQL trong `DATABASE_URL` phải có quyền `CREATE DATABASE` và
`DROP DATABASE`. Tuyệt đối không trỏ test vào database chứa dữ liệu cần giữ.

PowerShell, từ repository root:

```powershell
$env:RUN_MYSQL_MIGRATION_TEST = '1'
pytest -q backend/tests/test_category_migration_mysql.py backend/tests/test_saving_withdrawal_migration_mysql.py -p no:cacheprovider
Remove-Item Env:RUN_MYSQL_MIGRATION_TEST
```

Bash:

```bash
RUN_MYSQL_MIGRATION_TEST=1 pytest -q backend/tests/test_category_migration_mysql.py backend/tests/test_saving_withdrawal_migration_mysql.py -p no:cacheprovider
```

Nếu `RUN_MYSQL_MIGRATION_TEST` khác `1`, test được skip. Nếu `DATABASE_URL` không
phải MySQL, test cũng skip.

## Checklist migration production

1. Backup và thử restore backup.
2. Chạy ownership preflight trên bản sao dữ liệu.
3. Chạy migration trên disposable/staging MySQL cùng version production.
4. Kiểm tra composite FK, indexes, `NUMERIC(15,2)` và row counts.
5. Chạy backend tests và smoke test CRUD/trash/restore/import.
6. Chỉ sau đó mới lên lịch migration production.
