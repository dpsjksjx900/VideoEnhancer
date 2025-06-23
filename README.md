# VideoEnhancer

This project contains utilities for video interpolation using the RIFE engine and related tools.

## Running the GUI

Use the GUI to pick videos and configure interpolation parameters.

- **Windows:** run `run_GUI.bat`.
- **Linux/macOS:** execute `./run_GUI.sh`.

## Updating the Repository

To pull the latest version of this project from GitHub execute:

```bash
python update_repo.py
```

## Installing Requirements (Windows)

The script `install_requirements.py` downloads FFmpeg and the latest RIFE binaries:

```bash
python install_requirements.py
```

## Python Environment Setup

Create an isolated Python environment and install the required packages with:

```bash
python setup_env.py
```

The environment will be created in the `venv` folder. Activate it with `source venv/bin/activate` on Linux/macOS or `venv\\Scripts\\activate` on Windows.
