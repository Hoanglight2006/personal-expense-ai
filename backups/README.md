# Thư mục lưu bản sao lưu cơ sở dữ liệu

Thư mục này chứa các file sao lưu CSDL (`.sql` cho MySQL hoặc `.db` cho SQLite).

### 1. Cách sao lưu
- Windows: Chạy file [scripts/backup.bat](../scripts/backup.bat)
- Dòng lệnh:
  ```powershell
  python scripts/backup_db.py
  ```

### 2. Cách khôi phục
- Windows: Chạy file [scripts/restore.bat](../scripts/restore.bat)
- Dòng lệnh:
  ```powershell
  # Khôi phục bản mới nhất
  python scripts/restore_db.py

  # Khôi phục file chỉ định
  python scripts/restore_db.py --file backups/backup_mysql_personal_expense_20261003_175051.sql
  ```
