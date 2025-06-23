import os
import subprocess
import sys


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
    remote = get_remote_url(repo_dir)
    if not remote:
        print("❌ No remote repository configured. Cannot update.")
        return

    print(f"🔄 Updating from {remote} ...")
    try:
        subprocess.run(["git", "-C", repo_dir, "pull", "--ff-only"], check=True)
        print("✅ Repository updated successfully.")
    except subprocess.CalledProcessError as e:
        print("❌ Failed to update repository:", e)
        sys.exit(1)


if __name__ == "__main__":
    update_repo()
