@echo off
chcp 65001 >nul

set PYTHON_CMD="C:\Users\IKTEX\AppData\Local\Programs\Python\Python312\python.exe"

if exist %PYTHON_CMD% (
    %PYTHON_CMD% "%~dp0refresh.py"
) else (
    python "%~dp0refresh.py"
)

pause
