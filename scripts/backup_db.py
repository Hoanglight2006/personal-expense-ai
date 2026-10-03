"""Script sao lưu cơ sở dữ liệu (SQLite & MySQL) cho Personal Expense AI.

Hỗ trợ sao lưu an toàn tự động nhận diện theo DATABASE_URL:
- SQLite: Sử dụng API sqlite3.backup() chống lock/hỏng dữ liệu.
- MySQL: Sử dụng mysqldump (nếu có trong PATH) hoặc PyMySQL fallback.
Lưu trữ tại thư mục backups/ với định danh thời gian timestamp.
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

# Tìm thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT_DIR / "backups"

# Nạp DATABASE_URL từ backend/app/config.py hoặc .env
sys.path.insert(0, str(ROOT_DIR / "backend"))
try:
    from app.config import settings
    DATABASE_URL = settings.DATABASE_URL
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./personal_expense.db")


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def backup_sqlite(db_url: str) -> Path:
    raw_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        candidate_backend = ROOT_DIR / "backend" / db_path
        candidate_root = ROOT_DIR / db_path
        if candidate_backend.exists():
            db_path = candidate_backend
        elif candidate_root.exists():
            db_path = candidate_root
        else:
            db_path = candidate_root

    if not db_path.exists():
        print(f"[!] File SQLite khong ton tai tai: {db_path}")
        print("    Vui long kiem tra lai CSDL truoc khi sao luu.")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = ensure_backup_dir() / f"backup_sqlite_{timestamp}.db"

    print(f"[*] Dang sao luu SQLite tu: {db_path}")
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(backup_file))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()

    size_kb = backup_file.stat().st_size / 1024
    print(f"[+] Sao luu thanh cong! File: {backup_file.name} ({size_kb:.2f} KB)")
    return backup_file


def backup_mysql(db_url: str) -> Path:
    # URL dang: mysql+pymysql://user:password@host:port/dbname
    cleaned = db_url.replace("mysql+pymysql://", "mysql://").replace("mysql+mysqldb://", "mysql://")
    parsed = urlparse(cleaned)

    user = parsed.username or "root"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    dbname = parsed.path.lstrip("/")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = ensure_backup_dir() / f"backup_mysql_{dbname}_{timestamp}.sql"

    print(f"[*] Dang sao luu MySQL database '{dbname}' tai {host}:{port}...")

    mysqldump_bin = shutil.which("mysqldump")
    if mysqldump_bin:
        cmd = [
            mysqldump_bin,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            "--single-transaction",
            "--quick",
            "--routines",
            "--triggers",
        ]
        if password:
            cmd.append(f"--password={password}")
        cmd.append(dbname)

        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
            size_kb = backup_file.stat().st_size / 1024
            print(f"[+] Sao luu thanh cong bang mysqldump! File: {backup_file.name} ({size_kb:.2f} KB)")
            return backup_file
        except subprocess.CalledProcessError as e:
            print(f"[!] mysqldump bao loi: {e.stderr}")
            print("    Chuyen sang phuong an xuat du lieu bang PyMySQL...")

    # Fallback bang PyMySQL neu khong co mysqldump trong PATH
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            charset="utf8mb4",
        )
        with conn.cursor() as cursor, open(backup_file, "w", encoding="utf-8") as f:
            f.write(f"-- Backup created by Personal Expense AI on {datetime.now()}\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

            for tbl in tables:
                cursor.execute(f"SHOW CREATE TABLE `{tbl}`")
                create_stmt = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{tbl}`;\n")
                f.write(f"{create_stmt};\n\n")

                cursor.execute(f"SELECT * FROM `{tbl}`")
                rows = cursor.fetchall()
                if rows:
                    cols = [f"`{desc[0]}`" for desc in cursor.description]
                    cols_str = ", ".join(cols)
                    for row in rows:
                        vals = []
                        for val in row:
                            if val is None:
                                vals.append("NULL")
                            elif isinstance(val, (int, float)):
                                vals.append(str(val))
                            else:
                                escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
                                vals.append(f"'{escaped}'")
                        f.write(f"INSERT INTO `{tbl}` ({cols_str}) VALUES ({', '.join(vals)});\n")
                    f.write("\n")

            f.write("SET FOREIGN_KEY_CHECKS=1;\n")
        conn.close()

        size_kb = backup_file.stat().st_size / 1024
        print(f"[+] Sao luu thanh cong qua PyMySQL! File: {backup_file.name} ({size_kb:.2f} KB)")
        return backup_file
    except Exception as ex:
        print(f"[!] Loi sao luu MySQL: {ex}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Sao lưu CSDL Personal Expense AI")
    parser.parse_args()

    print("--- Sao luu CSDL ---")

    if DATABASE_URL.startswith("sqlite"):
        backup_file = backup_sqlite(DATABASE_URL)
    elif DATABASE_URL.startswith("mysql"):
        backup_file = backup_mysql(DATABASE_URL)
    else:
        print(f"Loi: Khong ho tro URL database: {DATABASE_URL}")
        sys.exit(1)

    print(f"File luu tai: {backup_file}")


if __name__ == "__main__":
    main()
