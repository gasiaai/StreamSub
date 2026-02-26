@echo off
title StreamSub
cd /d "%~dp0"

echo ============================================
echo   StreamSub - Real-time Translation Overlay
echo ============================================
echo.

:: ========== Step 1: Check Python ==========
python --version >nul 2>&1
if errorlevel 1 goto :no_python

:: ========== Step 2: Check Ollama ==========
where ollama >nul 2>&1
if errorlevel 1 goto :install_ollama
goto :ollama_ok

:install_ollama
echo [!] Ollama not found. Downloading installer...
echo.
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe' -UseBasicParsing" >nul 2>&1
if errorlevel 1 goto :ollama_download_failed

echo     Download complete. Starting installer...
echo.
echo     *** Please complete the Ollama installation wizard ***
echo.
start /wait "" "%TEMP%\OllamaSetup.exe"
echo.

:: Re-check after install (add common install paths)
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
where ollama >nul 2>&1
if errorlevel 1 goto :ollama_install_failed
echo     Ollama installed successfully!
echo.

:ollama_ok

:: ========== Step 3: Ensure Ollama is running ==========
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3 | Out-Null } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :ollama_running

echo [*] Starting Ollama service...
start "" ollama serve
echo     Waiting for Ollama to start...
timeout /t 5 /nobreak >nul

:ollama_running

:: ========== Step 4: Pull translation model if needed ==========
ollama list 2>nul | findstr /i "typhoon-translate" >nul 2>&1
if not errorlevel 1 goto :model_ok

echo [*] Downloading translation model (first time only, ~2.5 GB)...
echo     Model: scb10x/typhoon-translate1.5-4b
echo.
ollama pull scb10x/typhoon-translate1.5-4b
if errorlevel 1 (
    echo.
    echo [WARN] Model download failed. The app will try again when you click Start.
) else (
    echo     Model ready!
)
echo.

:model_ok

:: ========== Step 5: Python venv + dependencies ==========
if not exist "venv\Scripts\activate.bat" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 goto :venv_failed
)

call venv\Scripts\activate.bat

echo [*] Installing Python dependencies...
pip install -q -r requirements.txt
if errorlevel 1 goto :pip_failed

:: ========== Step 6: Launch ==========
echo.
echo ============================================
echo   Starting StreamSub...
echo   Log: streamsub.log
echo ============================================
echo.
python main.py 2>&1

echo.
echo ============================================
echo   StreamSub exited.
echo ============================================
echo.
pause
exit /b 0

:: ========== Error handlers ==========
:no_python
echo [ERROR] Python not found!
echo.
echo   Please install Python 3.10+ from:
echo   https://www.python.org/downloads/
echo.
echo   Make sure to check "Add Python to PATH" during install.
echo.
pause
exit /b 1

:ollama_download_failed
echo     [ERROR] Download failed. Please install Ollama manually:
echo     https://ollama.com/
echo.
pause
exit /b 1

:ollama_install_failed
echo [ERROR] Ollama not found after installation.
echo         Please restart this script or install manually: https://ollama.com/
echo.
pause
exit /b 1

:venv_failed
echo [ERROR] Failed to create venv. Is Python installed correctly?
pause
exit /b 1

:pip_failed
echo.
echo [ERROR] pip install failed. See output above.
pause
exit /b 1
