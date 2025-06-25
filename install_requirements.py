import os
import subprocess
import platform
import urllib.request
import zipfile
import json
import requests
import shutil


def get_latest_asset_url(repo: str, keyword: str) -> str | None:
    """Return download URL for the latest release asset matching keyword."""
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        resp = requests.get(api_url, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if keyword in name:
                return asset.get("browser_download_url")
    except Exception:
        return None
    return None


def download_and_extract(url: str, zip_name: str, folder_prefix: str, target: str) -> None:
    """Download a zip file and extract it to target folder."""
    print(f"⚡ Downloading from {url}...")
    urllib.request.urlretrieve(url, zip_name)
    with zipfile.ZipFile(zip_name, "r") as zip_ref:
        zip_ref.extractall(".")
    os.remove(zip_name)
    if not os.path.exists(target):
        for d in os.listdir('.'):
            if d.startswith(folder_prefix) and os.path.isdir(d):
                os.rename(d, target)
                break

REALSRCNN_EXECUTABLE = "realsr-ncnn-vulkan"
WAIFU2X_EXECUTABLE = "waifu2x-ncnn-vulkan"
REALESRGAN_EXECUTABLE = "realesrgan-ncnn-vulkan"
SWINIR_EXECUTABLE = "swinir-ncnn-vulkan"

REALSRCNN_REPO = "nihui/realsr-ncnn-vulkan"
WAIFU2X_REPO = "nihui/waifu2x-ncnn-vulkan"
REALESRGAN_REPO = "xinntao/Real-ESRGAN-ncnn-vulkan"
SWINIR_REPO = "nihui/swinir-ncnn-vulkan"

REALSRCNN_FOLDER = "realsr-ncnn-vulkan"
WAIFU2X_FOLDER = "waifu2x-ncnn-vulkan"
REALESRGAN_FOLDER = "realesrgan-ncnn-vulkan"
SWINIR_FOLDER = "swinir-ncnn-vulkan"

# Constants
RIFE_API_URL = "https://api.github.com/repos/nihui/rife-ncnn-vulkan/releases/latest"
RIFE_FOLDER = "rife-ncnn-vulkan"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_FOLDER = "ffmpeg"

def get_latest_rife_release():
    """Fetch the latest RIFE release URL from GitHub API."""
    print("🔎 Checking for the latest RIFE release...")
    response = requests.get(RIFE_API_URL)
    
    if response.status_code != 200:
        print("❌ Failed to fetch RIFE release info.")
        return None

    release_data = response.json()
    for asset in release_data.get("assets", []):
        if "windows.zip" in asset["name"]:  # Find the Windows ZIP file
            print(f"✅ Latest RIFE version found: {release_data['tag_name']}")
            return asset["browser_download_url"]
    
    print("❌ Could not find a valid Windows release!")
    return None

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✅ FFmpeg is already installed.")
        return True
    except FileNotFoundError:
        return False

def install_ffmpeg():
    """Download and install FFmpeg."""
    if check_ffmpeg():
        return

    print("⚡ Downloading FFmpeg...")
    ffmpeg_zip = "ffmpeg.zip"
    urllib.request.urlretrieve(FFMPEG_URL, ffmpeg_zip)

    print("🔄 Extracting FFmpeg...")
    with zipfile.ZipFile(ffmpeg_zip, "r") as zip_ref:
        zip_ref.extractall(".")

    extracted_folder = [f for f in os.listdir(".") if f.startswith("ffmpeg") and os.path.isdir(f)][0]
    os.rename(extracted_folder, FFMPEG_FOLDER)
    os.remove(ffmpeg_zip)

    # Add ffmpeg to PATH
    ffmpeg_bin = os.path.abspath(os.path.join(FFMPEG_FOLDER, "bin"))
    os.environ["PATH"] += os.pathsep + ffmpeg_bin
    print("✅ FFmpeg installed successfully.")

def move_rife_files():
    """Move extracted RIFE files into the correct folder."""
    extracted_dirs = [d for d in os.listdir(RIFE_FOLDER) if d.startswith("rife-ncnn-vulkan") and os.path.isdir(os.path.join(RIFE_FOLDER, d))]
    
    if not extracted_dirs:
        print("❌ No extracted RIFE folder found!")
        return False

    extracted_path = os.path.join(RIFE_FOLDER, extracted_dirs[0])

    for item in os.listdir(extracted_path):
        source = os.path.join(extracted_path, item)
        destination = os.path.join(RIFE_FOLDER, item)

        if os.path.exists(destination):
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            else:
                os.remove(destination)

        shutil.move(source, destination)

    # Clean up the empty extracted folder
    os.rmdir(extracted_path)

    print("✅ Moved RIFE files successfully.")
    return True

def check_rife():
    """Check if RIFE is installed."""
    return os.path.exists(os.path.join(RIFE_FOLDER, "rife-ncnn-vulkan.exe"))


def check_model_executable(name):
    """Check if an executable is available in PATH."""
    return shutil.which(name) is not None


def check_realsr():
    return os.path.exists(os.path.join(REALSRCNN_FOLDER, REALSRCNN_EXECUTABLE + ".exe"))


def check_realesrgan():
    return os.path.exists(os.path.join(REALESRGAN_FOLDER, REALESRGAN_EXECUTABLE + ".exe"))


def install_realsr():
    if check_realsr():
        print("✅ RealSR is already installed.")
        return

    url = get_latest_asset_url(REALSRCNN_REPO, "windows.zip")
    if not url:
        print("❌ Failed to fetch RealSR download URL.")
        return
    download_and_extract(url, "realsr.zip", "realsr-ncnn-vulkan", REALSRCNN_FOLDER)

    print("✅ RealSR installation completed.")


def install_realesrgan():
    if check_realesrgan():
        print("✅ RealESRGAN is already installed.")
        return
    url = get_latest_asset_url(REALESRGAN_REPO, "windows.zip")
    if not url:
        print("❌ Failed to fetch RealESRGAN download URL.")
        return
    download_and_extract(url, "realesrgan.zip", "realesrgan-ncnn-vulkan", REALESRGAN_FOLDER)

    print("✅ RealESRGAN installation completed.")


def check_waifu2x():
    return os.path.exists(os.path.join(WAIFU2X_FOLDER, WAIFU2X_EXECUTABLE + ".exe"))


def check_swinir():
    return os.path.exists(os.path.join(SWINIR_FOLDER, SWINIR_EXECUTABLE + ".exe"))


def install_waifu2x():
    if check_waifu2x():
        print("✅ Waifu2x is already installed.")
        return
      
    url = get_latest_asset_url(WAIFU2X_REPO, "windows.zip")
    if not url:
        print("❌ Failed to fetch Waifu2x download URL.")
        return
    download_and_extract(url, "waifu2x.zip", "waifu2x-ncnn-vulkan", WAIFU2X_FOLDER)

    print("✅ Waifu2x installation completed.")


def install_swinir():
    if check_swinir():
        print("✅ SwinIR is already installed.")
        return

    url = get_latest_asset_url(SWINIR_REPO, "windows.zip")
    if not url:
        print("❌ Failed to fetch SwinIR download URL.")
        return
    download_and_extract(url, "swinir.zip", "swinir-ncnn-vulkan", SWINIR_FOLDER)

    print("✅ SwinIR installation completed.")

def install_rife():
    """Download and install the latest RIFE ncnn Vulkan version."""
    if check_rife():
        print("✅ RIFE is already installed.")
        return

    rife_url = get_latest_rife_release()
    if not rife_url:
        print("❌ Could not determine RIFE download URL. Exiting.")
        return

    print(f"⚡ Downloading RIFE from {rife_url}...")
    rife_zip = "rife-ncnn-vulkan.zip"
    urllib.request.urlretrieve(rife_url, rife_zip)

    print("🔄 Extracting RIFE...")
    os.makedirs(RIFE_FOLDER, exist_ok=True)
    with zipfile.ZipFile(rife_zip, "r") as zip_ref:
        zip_ref.extractall(RIFE_FOLDER)

    os.remove(rife_zip)

    if move_rife_files():
        print("✅ RIFE installation completed successfully.")
    else:
        print("❌ RIFE installation failed!")

def verify_installation():
    """Verify all installations."""
    print("\n🔎 Verifying installations...")
    
    if check_ffmpeg():
        print("✅ FFmpeg is ready.")
    else:
        print("❌ FFmpeg is missing!")

    if check_rife():
        print("✅ RIFE is ready.")
    else:
        print("❌ RIFE installation failed!")

    if check_realsr():
        print("✅ RealSR is available.")
    else:
        print("❌ RealSR executable not found.")

    if check_waifu2x():
        print("✅ Waifu2x is available.")
    else:
        print("❌ Waifu2x executable not found.")

    if check_realesrgan():
        print("✅ RealESRGAN is available.")
    else:
        print("❌ RealESRGAN executable not found.")

    if check_swinir():
        print("✅ SwinIR is available.")
    else:
        print("❌ SwinIR executable not found.")

def main():
    if platform.system() != "Windows":
        print("❌ This script is designed for Windows only!")
        return

    print("🚀 Setting up video enhancement dependencies...\n")

    install_ffmpeg()
    install_rife()
    install_realsr()
    install_waifu2x()
    install_realesrgan()
    install_swinir()

    verify_installation()

    print("\n🎉 Setup complete! You can now use the video enhancer tools.")

if __name__ == "__main__":
    main()
