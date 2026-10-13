"""Script khôi phục cơ sở dữ liệu (SQLite & MySQL) cho Personal Expense AI.

Hỗ trợ phục hồi dữ liệu từ file sao lưu trong thư mục backups/:
- Tự động nhận diện bản sao lưu mới nhất nếu không chỉ định file.
- SQLite: Sử dụng API sqlite3.backup() khôi phục an toàn.
- MySQL: Thực thi các câu lệnh SQL qua MySQL client hoặc PyMySQL.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT_DIR / "backups"

# Nạp DATABASE_URL từ backend/app/config.py hoặc .env
sys.path.insert(0, str(ROOT_DIR / "backend"))
try:
    from app.config import settings
    DATABASE_URL = settings.DATABASE_URL
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./personal_expense.db")


def find_latest_backup(pattern: str) -> Path | None:
    if not BACKUP_DIR.exists():
        return None
    backups = sorted(BACKUP_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


def restore_sqlite(backup_path: Path, db_url: str):
    raw_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    target_path = Path(raw_path)
    if not target_path.is_absolute():
        target_path = ROOT_DIR / "backend" / target_path

    print(f"[*] Dang khoi phuc CSDL SQLite tu: {backup_path.name}")
    print(f"    Dich den: {target_path}")

    # Đảm bảo thư mục cha tồn tại
    target_path.parent.mkdir(parents=True, exist_ok=True)

    src_conn = sqlite3.connect(str(backup_path))
    dst_conn = sqlite3.connect(str(target_path))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()

    print("[+] Khoi phuc CSDL SQLite thanh cong!")


def restore_mysql(backup_path: Path, db_url: str):
    cleaned = db_url.replace("mysql+pymysql://", "mysql://").replace("mysql+mysqldb://", "mysql://")
    parsed = urlparse(cleaned)

    user = parsed.username or "root"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    dbname = parsed.path.lstrip("/")

    print(f"[*] Dang khoi phuc MySQL database '{dbname}' tu: {backup_path.name}")

    mysql_bin = shutil.which("mysql")
    if mysql_bin:
        cmd = [
            mysql_bin,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
        ]
        if password:
            cmd.append(f"--password={password}")
        cmd.append(dbname)

        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                subprocess.run(cmd, stdin=f, check=True)
            print("[+] Khoi phuc CSDL MySQL thanh cong bang mysql client!")
            return
        except subprocess.CalledProcessError as e:
            print(f"[!] mysql client loi: {e}")
            print("    Chuyen sang thuc thi qua PyMySQL...")

    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            charset="utf8mb4",
            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS,
        )
        with open(backup_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        with conn.cursor() as cursor:
            cursor.execute(sql_content)
        conn.commit()
        conn.close()
        print("[+] Khoi phuc CSDL MySQL thanh cong qua PyMySQL!")
    except Exception as ex:
        print(f"[!] Loi khi khoi phuc MySQL: {ex}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Khôi phục CSDL Personal Expense AI")
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Đường dẫn tới file sao lưu (.sql hoặc .db). Nếu bỏ trống sẽ dùng bản mới nhất.",
    )
    args = parser.parse_args()

    print("--- Khoi phuc CSDL ---")

    is_sqlite = DATABASE_URL.startswith("sqlite")
    is_mysql = DATABASE_URL.startswith("mysql")

    if not is_sqlite and not is_mysql:
        print(f"[!] Khong ho tro database url: {DATABASE_URL}")
        sys.exit(1)

    backup_file: Path | None = None
    if args.file:
        backup_file = Path(args.file)
        if not backup_file.is_absolute():
            backup_file = ROOT_DIR / backup_file
    else:
        pattern = "backup_sqlite_*.db" if is_sqlite else "backup_mysql_*.sql"
        backup_file = find_latest_backup(pattern)
        if not backup_file:
            # Thu tim bat ky file hop le trong backups/
            all_files = list(BACKUP_DIR.glob("*.*")) if BACKUP_DIR.exists() else []
            if all_files:
                backup_file = sorted(all_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    if not backup_file or not backup_file.exists():
        print("[!] Khong tim thay file sao luu nao de khoi phuc!")
        print(f"    Vui long kiem tra thu muc: {BACKUP_DIR}")
        sys.exit(1)

    print(f"[i] File duoc chon: {backup_file}")
    confirm = input("Ban co chac chan muon khoi phuc de de du lieu hien tai? (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("[*] Da huy thao tac khoi phuc.")
        sys.exit(0)

    if is_sqlite:
        restore_sqlite(backup_file, DATABASE_URL)
    elif is_mysql:
        restore_mysql(backup_file, DATABASE_URL)



if __name__ == "__main__":
    main()
