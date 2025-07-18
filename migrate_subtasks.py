import sqlite3
import json

DB_PATH = "daily_reports.db"

def migrate_subtasks():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT rowid, subtasks FROM reports")
        for rowid, subtasks in cur.fetchall():
            if not subtasks or subtasks.strip().startswith("{"):
                continue  # Already JSON or empty
            # Parse the old format
            task_dict = {}
            for line in subtasks.splitlines():
                if ":" in line:
                    task, items = line.split(":", 1)
                    task = task.strip()
                    items_list = [i.strip() for i in items.split(",") if i.strip()]
                    task_dict[task] = items_list
            # Update with JSON
            cur.execute("UPDATE reports SET subtasks = ? WHERE rowid = ?", (json.dumps(task_dict), rowid))
        conn.commit()

if __name__ == "__main__":
    migrate_subtasks()
    print("Migration complete.")
