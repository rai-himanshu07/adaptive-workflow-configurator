@echo off
setlocal
set "INSTALLER=%~dp0install-workflow-configurator-launcher.ps1"

where pwsh.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  pwsh.exe -NoLogo -NoProfile -File "%INSTALLER%" %*
) else (
  powershell.exe -NoLogo -NoProfile -File "%INSTALLER%" %*
)
exit /b %ERRORLEVEL%
