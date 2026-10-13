@echo off
chcp 65001 >nul
echo [PERSONAL EXPENSE AI] Dang chay sao luu Co so du lieu...
cd /d "%~dp0\.."

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe scripts\backup_db.py
) else (
    python scripts\backup_db.py
)

pause
