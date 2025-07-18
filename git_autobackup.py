# git_autobackup.py

import subprocess, os
from datetime import datetime

def backup_to_git(db_path="daily_reports.db"):
    """
    1. Configure author
    2. Stage the DB
    3. Commit if there are changes
    4. Push directly to tokenized URL (avoiding origin)
    """
    # 1. Git author
    subprocess.run(
        ["git", "config", "user.name", os.environ["GIT_USER"]], check=True
    )
    subprocess.run(
        ["git", "config", "user.email", os.environ["GIT_EMAIL"]], check=True
    )

    # 2. Stage the DB file
    subprocess.run(["git", "add", db_path], check=True)

    # 3. Only commit if there’s something to push
    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], check=False
    ).returncode
    if status == 0:
        print("🔔 No new DB changes to back up.")
        return

    commit_msg = f"Auto‑backup: {datetime.now():%Y‑%m‑%d %H:%M:%S}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Build tokenized push URL and push HEAD:main
    repo = os.environ["REPO_URL"]
    if not repo.endswith(".git"):
        repo += ".git"
    token = os.environ["GIT_TOKEN"]
    token_url = repo.replace("https://", f"https://{token}@")

    # Direct push, bypassing origin
    subprocess.run(
        ["git", "push", token_url, "HEAD:main"],
        check=True
    )
    print("🔄 Backup pushed to GitHub.")

if __name__ == "__main__":
    try:
        backup_to_git()
    except Exception as e:
        print("🛑 Backup failed:", e)
