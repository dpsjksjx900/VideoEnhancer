import os
import subprocess
import sys
import urllib.request
import zipfile
import shutil
import tempfile

DEFAULT_REMOTE = "https://github.com/dpsjksjx900/VideoEnhancer.git"
ZIP_URL = "https://codeload.github.com/dpsjksjx900/VideoEnhancer/zip/refs/heads/main"

def get_remote_url(repo_dir: str) -> str | None:
    """Return the URL of the remote named 'origin' for the given repo."""
    try:
        return (
            subprocess.check_output(
                ["git", "-C", repo_dir, "config", "--get", "remote.origin.url"],
                text=True,
            )
            .strip()
        )
    except subprocess.CalledProcessError:
        return None


def update_repo():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_dir = os.path.join(repo_dir, ".git")


    if os.path.exists(git_dir):
        remote = get_remote_url(repo_dir)
        if not remote:
            print(f"⚠️ No git remote configured. Setting to {DEFAULT_REMOTE}.")
            try:
                subprocess.run(
                    ["git", "-C", repo_dir, "remote", "add", "origin", DEFAULT_REMOTE],
                    check=True,
                )
                remote = DEFAULT_REMOTE
            except subprocess.CalledProcessError:
                print("❌ Failed to add git remote. Falling back to archive.")
                remote = None

        if remote:
            print(f"🔄 Updating from {remote} via git ...")
            try:
                subprocess.run(
                    ["git", "-C", repo_dir, "pull", "origin", "main", "--ff-only"],
                    check=True,
                )
                print("✅ Repository updated successfully.")
                return
            except subprocess.CalledProcessError as e:
                print("❌ Git pull failed:", e)

    # Fall back to downloading the archive
    print("📦 Downloading latest files from GitHub...")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "repo.zip")
        urllib.request.urlretrieve(ZIP_URL, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)
        extracted = os.path.join(tmpdir, "VideoEnhancer-main")
        if not os.path.isdir(extracted):
            extracted = next(
                os.path.join(tmpdir, d)
                for d in os.listdir(tmpdir)
                if d.startswith("VideoEnhancer")
            )
        for name in os.listdir(extracted):
            src = os.path.join(extracted, name)
            dst = os.path.join(repo_dir, name)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
    print("✅ Files updated from archive.")


if __name__ == "__main__":
    update_repo()
