# git_autobackup.py

import subprocess
import os
from datetime import datetime

def backup_to_git(db_path="daily_reports.db"):
    """
    0. Sync down any remote commits (rebase local on top)
    1. Configure author
    2. Stage the SQLite DB
    3. Commit with timestamp if there are changes
    4. Push back to GitHub via tokenized URL
    """
    # 0. Pull & rebase to incorporate upstream changes
    subprocess.run(
        ["git", "pull", "--rebase", "origin", "main"],
        check=True,
    )

    # 1. Configure author
    subprocess.run(
        ["git", "config", "user.name", os.environ["GIT_USER"]],
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", os.environ["GIT_EMAIL"]],
        check=True,
    )

    # 2. Stage the DB
    subprocess.run(["git", "add", db_path], check=True)

    # 3. Only commit if there are staged changes
    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"],
        check=False,
    )
    if result.returncode == 0:
        # no changes to commit
        print("🔔 No new changes to back up.")
        return

    commit_msg = f"Auto‑backup: {datetime.now():%Y‑%m‑%d %H:%M:%S}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Push via tokenized URL
    # ensure REPO_URL is like https://github.com/you/repo.git
    repo_url = os.environ["REPO_URL"].replace(
        "https://",
        f"https://{os.environ['GIT_TOKEN']}@"
    )
    subprocess.run(
        ["git", "push", repo_url, "HEAD:main"],
        check=True,
    )

if __name__ == "__main__":
    try:
        backup_to_git()
    except subprocess.CalledProcessError as e:
        print("🛑 Git command failed:", e)
    except KeyError as e:
        print(f"🛑 Missing environment variable: {e}")
    except Exception as e:
        print("🛑 Unexpected error during backup:", e)
