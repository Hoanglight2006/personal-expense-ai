@echo off
chcp 65001 >nul
echo [PERSONAL EXPENSE AI] Dang chay khoi phuc Co so du lieu...
cd /d "%~dp0\.."

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe scripts\restore_db.py %*
) else (
    python scripts\restore_db.py %*
)

pause
