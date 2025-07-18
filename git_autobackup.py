import subprocess
import os
from datetime import datetime

def backup_to_git(db_path="daily_reports.db"):
    """
    1. Configure Git author
    2. Stage the DB
    3. Commit if there are changes
    4. Fetch & rebase remote changes
    5. Push to GitHub via tokenized URL
    """
    # 1. Git author
    subprocess.run(["git", "config", "user.name", os.environ["GIT_USER"]], check=True)
    subprocess.run(["git", "config", "user.email", os.environ["GIT_EMAIL"]], check=True)

    # 2. Stage the DB file
    subprocess.run(["git", "add", db_path], check=True)

    # 3. Only commit if there are staged changes
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        print("🔔 No new DB changes to back up.")
        return

    commit_msg = f"Auto‑backup: {datetime.now():%Y‑%m‑%d %H:%M:%S}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Build tokenized URL
    repo = os.environ["REPO_URL"]
    if not repo.endswith(".git"):
        repo += ".git"
    token_url = repo.replace("https://", f"https://{os.environ['GIT_TOKEN']}@")

    # 5. Grab any new remote commits and rebase
    subprocess.run(["git", "fetch", token_url, "main"], check=True)
    # rebase local HEAD onto remote/main
    subprocess.run(["git", "rebase", "FETCH_HEAD"], check=True)

    # 6. Push your commit on top
    subprocess.run(["git", "push", token_url, "HEAD:main"], check=True)
    print("🔄 Backup pushed to GitHub.")

if __name__ == "__main__":
    try:
        backup_to_git()
    except Exception as e:
        print("🛑 Backup failed:", e)
