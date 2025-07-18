# git_autobackup.py

import subprocess
import os
from datetime import datetime

def backup_to_git(db_path="daily_reports.db"):
    try:
        subprocess.run(["git", "config", "user.name", os.environ["GIT_USER"]], check=True)
        subprocess.run(["git", "config", "user.email", os.environ["GIT_EMAIL"]], check=True)
        subprocess.run(["git", "add", db_path], check=True)

        commit_msg = f"Auto-backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        repo_url = os.environ["REPO_URL"].replace("https://", f"https://{os.environ['GIT_TOKEN']}@")
        subprocess.run(["git", "push", repo_url], check=True)

    except subprocess.CalledProcessError as e:
        print("Git error:", e)
    except Exception as e:
        print("Backup failed:", e)
