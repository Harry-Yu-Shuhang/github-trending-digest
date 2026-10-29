@echo off
setlocal
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo Installing uv from astral.sh...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"
  if errorlevel 1 goto failed
)
uv run --project "%~dp0app" --frozen --extra ui --python 3.12 python "%~dp0app\start.py" %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Startup failed. See the error above. For a busy fixed port, try --port 7861.
pause
exit /b 1
