# git_autobackup.py

import subprocess
import os
from datetime import datetime

def backup_to_git(db_path="daily_reports.db"):
    """
    1. Configure Git author
    2. Stage the DB
    3. Commit if there are changes
    4. Push to GitHub via tokenized URL
    """
    # 1. Author config
    subprocess.run(
        ["git", "config", "user.name", os.environ["GIT_USER"]], check=True
    )
    subprocess.run(
        ["git", "config", "user.email", os.environ["GIT_EMAIL"]], check=True
    )

    # 2. Stage the DB file
    subprocess.run(["git", "add", db_path], check=True)

    # 3. Only commit if staged changes exist
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        # nothing new
        print("🔔 No new DB changes to back up.")
        return

    commit_msg = f"Auto-backup: {datetime.now():%Y-%m-%d %H:%M:%S}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Push using token-authenticated URL
    repo_url = os.environ["REPO_URL"].replace(
        "https://",
        f"https://{os.environ['GIT_TOKEN']}@"
    )
    subprocess.run(["git", "push", repo_url, "HEAD:main"], check=True)

if __name__ == "__main__":
    try:
        backup_to_git()
    except Exception as e:
        print("🛑 Backup failed:", e)
