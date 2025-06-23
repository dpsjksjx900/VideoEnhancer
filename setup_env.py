import os
import sys
import subprocess

VENV_DIR = "venv"
REQ_FILE = "requirements.txt"


def create_venv():
    if not os.path.exists(VENV_DIR):
        print(f"🔧 Creating virtual environment in '{VENV_DIR}'...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    else:
        print(f"ℹ️ Virtual environment '{VENV_DIR}' already exists.")


def pip_path():
    return os.path.join(VENV_DIR, "Scripts" if os.name == "nt" else "bin", "pip")


def install_requirements():
    pip = pip_path()
    if not os.path.exists(pip):
        raise RuntimeError("pip not found in the virtual environment")
    print("📦 Installing requirements...")
    subprocess.run([pip, "install", "--upgrade", "pip"], check=True)
    if os.path.exists(REQ_FILE):
        subprocess.run([pip, "install", "-r", REQ_FILE], check=True)
    else:
        print(f"⚠️ '{REQ_FILE}' not found. Skipping package installation.")


def main():
    create_venv()
    install_requirements()
    print("✅ Environment setup complete. Activate it with:\n"
          f"  source {VENV_DIR}/bin/activate" if os.name != "nt" else
          f"  {VENV_DIR}\\Scripts\\activate.bat")


if __name__ == "__main__":
    main()
