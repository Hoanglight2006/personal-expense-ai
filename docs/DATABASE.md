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

### `saving_goals` và `saving_contributions`

- `target_amount`, `current_amount`, contribution `amount` đều `NUMERIC(15,2)`.
- `current_amount` là giá trị denormalized phải nhất quán với contribution hiệu
  lực.
- Contribution `manual` có `transaction_id = NULL`.
- Contribution `income_allocation` liên kết income Transaction;
  `transaction_id -> transactions.id ON DELETE SET NULL` ở cấp model.
- Trash/restore Transaction điều chỉnh `current_amount`; xóa vĩnh viễn Transaction
  xóa contribution liên kết trước.

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
```

Không chạy các SQL này trên SQLite.

## Test migration MySQL bằng database dùng một lần

Test `backend/tests/test_category_migration_mysql.py`:

- Kết nối tới MySQL server từ `DATABASE_URL`.
- Tạo database ngẫu nhiên `category_migration_test_<suffix>`.
- Tạo schema legacy và dữ liệu trùng.
- Chạy `001_category_management.sql` hai lần để kiểm tra retry safety.
- Kiểm tra merge, budget roll-up và composite constraints.
- Drop database trong `finally`, kể cả khi test thất bại.

Tài khoản MySQL trong `DATABASE_URL` phải có quyền `CREATE DATABASE` và
`DROP DATABASE`. Tuyệt đối không trỏ test vào database chứa dữ liệu cần giữ.

PowerShell, từ repository root:

```powershell
$env:RUN_MYSQL_MIGRATION_TEST = '1'
pytest -q backend/tests/test_category_migration_mysql.py -p no:cacheprovider
Remove-Item Env:RUN_MYSQL_MIGRATION_TEST
```

Bash:

```bash
RUN_MYSQL_MIGRATION_TEST=1 pytest -q backend/tests/test_category_migration_mysql.py -p no:cacheprovider
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
