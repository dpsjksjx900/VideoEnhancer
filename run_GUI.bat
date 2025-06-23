@echo off
REM Launch the VideoEnhancer GUI on Windows.
REM Requires Python with tkinter installed. Run install_requirements.py
REM to download FFmpeg and the RIFE models if they are missing.

cd /d "%~dp0"

REM Warn if FFmpeg is not installed
where ffmpeg >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo FFmpeg not found. Please install it before running the GUI.
)

REM Warn if RIFE models are missing
IF NOT EXIST "rife-ncnn-vulkan" (
    echo RIFE models not found. Run "python install_requirements.py" first.
)

python GUI.py
pause
