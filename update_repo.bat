@echo off
REM Update the VideoEnhancer repository by pulling the latest changes from GitHub.
REM Requires git and Python.

cd /d "%~dp0"

REM Ensure git is available
where git >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Git is not installed or not in PATH. Aborting update.
    goto :EOF
)

python update_repo.py
pause
