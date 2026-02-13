@echo off
setlocal

REM Try to find python in standard locations
set PYTHON_CMD=python

where python >nul 2>nul
if %errorlevel% equ 0 (
    goto :FOUND
)

REM Check common installation paths
if exist "C:\Python310\python.exe" set PYTHON_CMD="C:\Python310\python.exe" & goto :FOUND
if exist "C:\Python311\python.exe" set PYTHON_CMD="C:\Python311\python.exe" & goto :FOUND
if exist "C:\Python312\python.exe" set PYTHON_CMD="C:\Python312\python.exe" & goto :FOUND
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :FOUND
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :FOUND
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :FOUND

echo Error: Python not found in PATH or standard locations.
echo Please install Python 3.10+ and add it to your PATH.
echo You can download it from https://www.python.org/downloads/
pause
exit /b 1

:FOUND
echo Using Python at: %PYTHON_CMD%
echo Installing dependencies...
%PYTHON_CMD% -m pip install -e .

echo Starting Dashboard...
%PYTHON_CMD% -m uvicorn dashboard.backend.main:app --reload --host 127.0.0.1 --port 8000
pause
