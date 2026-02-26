@echo off
title StreamSub Updater
cd /d "%~dp0"

echo ============================================
echo   StreamSub Updater
echo ============================================
echo.

:: ========== Check if git repo ==========
if exist ".git" goto :git_update

:: ========== No git — download ZIP ==========
echo [*] No git repository detected (downloaded as ZIP).
echo.
echo     Downloading latest version...
echo.

:: Download latest ZIP
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip' -OutFile '%TEMP%\StreamSub-update.zip' -UseBasicParsing" >nul 2>&1
if errorlevel 1 goto :download_failed

echo     Extracting...
:: Extract to temp folder
powershell -Command "Remove-Item '%TEMP%\StreamSub-main' -Recurse -Force -ErrorAction SilentlyContinue; Expand-Archive -Path '%TEMP%\StreamSub-update.zip' -DestinationPath '%TEMP%' -Force" >nul 2>&1
if errorlevel 1 goto :extract_failed

:: Copy files (skip Model/, venv/, settings.json, .env, streamsub.log)
echo     Updating files...
powershell -Command ^
  "$src = '%TEMP%\StreamSub-main'; " ^
  "$dst = '%~dp0'; " ^
  "$exclude = @('Model','venv','.env','settings.json','streamsub.log','__pycache__'); " ^
  "Get-ChildItem -Path $src -Recurse | ForEach-Object { " ^
  "  $rel = $_.FullName.Substring($src.Length + 1); " ^
  "  $skip = $false; " ^
  "  foreach ($e in $exclude) { if ($rel -like \"$e*\") { $skip = $true; break } }; " ^
  "  if (-not $skip) { " ^
  "    $target = Join-Path $dst $rel; " ^
  "    if ($_.PSIsContainer) { New-Item -ItemType Directory -Path $target -Force | Out-Null } " ^
  "    else { Copy-Item $_.FullName -Destination $target -Force } " ^
  "  } " ^
  "}"
if errorlevel 1 goto :copy_failed

:: Cleanup temp
del "%TEMP%\StreamSub-update.zip" >nul 2>&1
powershell -Command "Remove-Item '%TEMP%\StreamSub-main' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo.
echo     [OK] Update complete!
goto :update_deps

:: ========== Git update ==========
:git_update
echo [*] Pulling latest changes from GitHub...
echo.
git pull
if errorlevel 1 goto :git_failed
echo.
echo     [OK] Code updated!

:: ========== Update Python dependencies ==========
:update_deps
echo.
if not exist "venv\Scripts\activate.bat" (
    echo [*] No venv found. Run run.bat first to set up.
    goto :done
)

call venv\Scripts\activate.bat
echo [*] Updating Python dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [WARN] pip install had issues. See output above.
) else (
    echo     [OK] Dependencies updated!
)

:: Show current version
echo.
python -c "from config import APP_VERSION; print(f'    Current version: v{APP_VERSION}')" 2>nul
goto :done

:: ========== Error handlers ==========
:download_failed
echo     [ERROR] Download failed. Check your internet connection.
echo     You can download manually: https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip
goto :done

:extract_failed
echo     [ERROR] Failed to extract update.
goto :done

:copy_failed
echo     [ERROR] Failed to copy updated files.
goto :done

:git_failed
echo     [ERROR] git pull failed. You may have local changes.
echo     Try: git stash ^&^& git pull ^&^& git stash pop
goto :done

:done
echo.
echo ============================================
echo   Done! Run run.bat to start StreamSub.
echo ============================================
echo.
pause
