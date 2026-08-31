@echo off
setlocal
set "LAUNCHER=%~dp0launch-workflow-configurator.ps1"

where pwsh.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  pwsh.exe -NoLogo -NoProfile -File "%LAUNCHER%" %*
) else (
  powershell.exe -NoLogo -NoProfile -File "%LAUNCHER%" %*
)
exit /b %ERRORLEVEL%
