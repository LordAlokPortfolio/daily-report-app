"""
Migration script to fix completed_tasks column in daily_reports.db
- For rows where completed_tasks == 'All completed',
  set completed_tasks to a comma-separated list of keys from subtasks JSON.
Run this ONCE, then delete or comment it out.
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path("daily_reports.db")

def migrate_completed_tasks():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT rowid, completed_tasks, subtasks FROM reports")
        rows = cur.fetchall()
        updated = 0
        for rowid, completed, subtasks in rows:
            if completed == "All completed":
                try:
                    subs = json.loads(subtasks) if subtasks else {}
                    if isinstance(subs, dict) and subs:
                        new_completed = ", ".join(subs.keys())
                        cur.execute(
                            "UPDATE reports SET completed_tasks = ? WHERE rowid = ?",
                            (new_completed, rowid),
                        )
                        updated += 1
                except Exception as e:
                    print(f"Row {rowid}: Error parsing subtasks: {e}")
        conn.commit()
    print(f"Migration complete. Updated {updated} rows.")

if __name__ == "__main__":
    migrate_completed_tasks()
    print("Done.")
