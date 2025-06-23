
#!/usr/bin/env bash
# Launch the VideoEnhancer GUI on Unix-like systems.
# Requires python3 with tkinter installed. Ensure ffmpeg and the
# RIFE models are available. Run 'python3 install_requirements.py'
# if the models or ffmpeg are missing.

# Change to the directory containing this script
cd "$(dirname "$0")"

# Warn if ffmpeg is not installed
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "FFmpeg not found. Please install it before running the GUI." >&2
fi

# Warn if the RIFE model directory is missing
if [ ! -d "rife-ncnn-vulkan" ]; then
    echo "RIFE models not found. Run 'python3 install_requirements.py' to download them." >&2
fi

python3 GUI.py
