@echo off
chcp 65001 >nul
echo ======================================================
echo    XEBERLER YENILENIR (APA.AZ ve REPORT.AZ)
echo ======================================================

set PYTHON_CMD="C:\Users\IKTEX\AppData\Local\Programs\Python\Python312\python.exe"

echo.
echo [1/2] APA.AZ yenilenir...
%PYTHON_CMD% apa_az\main.py

echo.
echo [2/2] REPORT.AZ yenilenir...
%PYTHON_CMD% report_az\fix_and_refresh_az.py

echo.
echo ======================================================
echo    BUTUN SAYTLAR UGURLA YENILENDI!
echo ======================================================
pause

