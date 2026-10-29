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
uv run --frozen --extra ui --python 3.12 python start.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Startup failed. See the error above. Check your network and try again.
pause
exit /b 1
