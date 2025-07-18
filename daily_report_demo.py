"""
Streamlit Daily Report App for Simarjit Kaur
-------------------------------------------
Creates / reads a SQLite database of daily reports and
lets the user generate weekly Excel + PDF summaries.
"""

from __future__ import annotations

import io
import json
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from fpdf import FPDF

# ------------------------------------------------------------------#
#                             CONFIG                                #
# ------------------------------------------------------------------#
DB_PATH = Path("daily_reports.db")

# ------------------------------------------------------------------#
#                    DATABASE INITIALISATION                        #
# ------------------------------------------------------------------#
def init_db() -> None:
    """Create the `reports` table (if absent) and ensure `subtasks` exists."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                date               TEXT,
                day                TEXT,
                name               TEXT,
                completed_tasks    TEXT,
                incomplete_tasks   TEXT,
                organizing_details TEXT,
                notes              TEXT,
                subtasks           TEXT
            )
            """
        )
        existing_cols = [col[1] for col in conn.execute("PRAGMA table_info(reports)")]
        if "subtasks" not in existing_cols:
            conn.execute("ALTER TABLE reports ADD COLUMN subtasks TEXT")


init_db()

# ------------------------------------------------------------------#
#                         HELPER FUNCTIONS                          #
# ------------------------------------------------------------------#
def clean_text(text: str | None) -> str:
    """Strip non-ASCII characters and emojis for PDF output."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove emojis (unicode ranges for emoticons, symbols, pictographs, etc.)
    import re
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U00002600-\U000026FF"  # Misc symbols
        "\U00002B50-\U00002B55"  # Stars
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub(r"", text)
    return text.encode("ascii", "ignore").decode("ascii")


def generate_pdf(df: pd.DataFrame, week_no: int) -> bytes:
    """
    Create a PDF summary for one ISO week, using row['Date'] (datetime)
    so we can call strftime without errors.
    """
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    title_week = "All Weeks" if week_no == 0 else f"Week {week_no}"
    pdf.cell(0, 12, f"Simarjit Kaur - Weekly Report ({title_week})", ln=True, align="C")
    pdf.ln(8)

    for _, row in df.iterrows():
        if pd.isna(row["Date"]):
            continue
        date_str = row["Date"].strftime("%Y-%m-%d")
        day_str = row["Day"]

        # Date header
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, clean_text(f"{date_str} ({day_str})"), ln=True)
        pdf.ln(2)

        # Completed tasks with subtasks and check mark (use pretty_completed logic)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, clean_text("Completed Tasks:"), ln=True)
        pdf.set_font("Arial", "", 11)
        try:
            completed = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
            subs = json.loads(row["subtasks"]) if row["subtasks"] else {}
        except Exception:
            completed = []
            subs = {}
        if not completed:
            pdf.cell(0, 7, clean_text("-"), ln=True)
        else:
            for task in completed:
                pdf.cell(0, 7, clean_text(f"✔ {task}"), ln=True)
                items = subs.get(task, []) if isinstance(subs, dict) else []
                for item in items:
                    pdf.cell(10)
                    pdf.multi_cell(0, 7, clean_text(f"• {item}"))
        pdf.ln(1)

        # Organizing details (after completed tasks)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, clean_text("Organizing Details:"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, clean_text(row["organizing_details"] or "-"))
        pdf.ln(1)

        pdf.ln(5)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Page {pdf.page_no()}", align="C")

    return pdf.output(dest="S").encode("latin-1")
    
# ------------------------------------------------------------------#
#                     SCHEDULE (STATIC SAMPLE)                      #
# ------------------------------------------------------------------#
SCHEDULE: dict[str, list[str]] = {
    "Monday": [
        "Stock Screens", "Screen Mesh", "Spectra", "LTC", "Organizing Materials"
    ],
    "Tuesday": ["Vision", "RPM Punched", "RPM Stainless", "Organizing Materials"],
    "Wednesday": [
        "SIL Plastic", "SIL Fastners", "Schelgal", "Shop Supplies", "Organizing Materials"
    ],
    "Thursday": [
        "Amesbury Truth", "Twin/Multipoint Keepers", "Stock Screens", "Foot Locks", "Organizing Materials"
    ],
    "Friday": ["Mini Blinds", "Foam Concept", "Cardboard", "Organizing Materials"],
}

# ------------------------------------------------------------------#
#                        STREAMLIT LAYOUT                           #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly View"])

# ------------------------------- TAB 1 ----------------------------#
with tab_submit:
    st.header("Daily Report - Simarjit Kaur")

    date_sel = st.date_input("Date", datetime.today())
    day_name = date_sel.strftime("%A")
    tasks = SCHEDULE.get(day_name, [])
    if not tasks:
        st.info(f"No tasks scheduled for **{day_name}**.")
        st.stop()

    with st.form("report_form", clear_on_submit=True):
        completed: list[str] = []
        incomplete: dict[str, str] = {}
        task_subtasks: dict[str, list[str]] = {}
        default_subs = [
            "Counted and recorded on Excel",
            "Sent file to managers via email",
            "Provided physical copies to managers",
            "Arranged material in its location",
        ]

        for task in tasks:
            done = st.radio(f"{task} done?", ["Yes", "No"], key=task, horizontal=True)
            if done == "Yes":
                completed.append(task)
                flags, chosen = [], []
                st.markdown("✔️ **Confirm Sub‑Tasks Completed**")
                for sub in default_subs:
                    chk = st.checkbox(sub, key=f"{task}_{sub}")
                    flags.append(chk)
                    if chk:
                        chosen.append(sub)
                task_subtasks[task] = chosen

                if not all(flags):
                    reason = st.text_area(
                        f"❗ Reason – sub‑tasks missing ({task})",
                        key=f"{task}_reason",
                        height=80,
                    )
                    incomplete[task] = reason

                if task == "Organizing Materials":
                    st.text_area("🧹 Organizing Details", key="organizing_details", height=120)

            else:
                reason = st.text_area(
                    f"❗ Reason – not done ({task})", key=f"{task}_reason", height=80
                )
                incomplete[task] = reason

        notes = st.text_area("🗒️ Notes (optional)", height=80)

        if st.form_submit_button("✅ Submit Report"):
            # Validation: ensure all required fields are present
            required_fields = [date_sel, day_name, "Simarjit Kaur", completed, incomplete]
            if any(
                (isinstance(f, str) and not f.strip()) or (isinstance(f, list) and not f) or (isinstance(f, dict) and not f and f != {})
                for f in required_fields
            ):
                st.error("All required fields (date, day, name, completed/incomplete tasks) must be filled.")
                st.stop()
            if any(not v.strip() for v in incomplete.values()):
                st.error("Every unfinished task must have a reason.")
                st.stop()

            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)",
                    (
                        date_sel.strftime("%Y-%m-%d"),
                        day_name,
                        "Simarjit Kaur",
                        ", ".join(completed),
                        "All completed" if not incomplete else str(incomplete),
                        st.session_state.get("organizing_details", ""),
                        notes,
                        json.dumps(task_subtasks),
                    ),
                )
            st.success("✅ Report saved!")

            # auto‑backup
            from git_autobackup import backup_to_git

            try:
                backup_to_git(db_path=str(DB_PATH))
                st.info("🔄 Database backed up to GitHub.")
            except Exception as e:
                st.error(f"Backup failed: {e}")

# ------------------------------------------------------------------#
#                CLEANUP SCRIPT FOR BAD DATA (ONE-TIME)             #
# ------------------------------------------------------------------#
def cleanup_bad_data():
    """Remove rows from the database where date, day, or name is NULL or empty."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM reports
            WHERE date IS NULL OR TRIM(date) = ''
               OR day IS NULL OR TRIM(day) = ''
               OR name IS NULL OR TRIM(name) = ''
            """
        )
        conn.commit()

# Uncomment the next line and run the app ONCE to clean up existing bad data, then comment it again.
#cleanup_bad_data()

# ------------------------------- TAB 2 ----------------------------#
with tab_weekly:
    st.header("📅 Weekly View")

    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No records found.")
        st.stop()

    # Prepare datetime, ISO week, and pretty subtasks
    df["Date"] = pd.to_datetime(df["date"])
    df["Week"] = df["Date"].dt.isocalendar().week
    df["Day"] = df["Date"].dt.strftime("%A")

    def pretty_completed(row):
        try:
            completed = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
            subs = json.loads(row["subtasks"]) if row["subtasks"] else {}
        except Exception:
            completed = []
            subs = {}
        if not completed:
            return "-"
        lines = []
        for task in completed:
            lines.append(f"✔ {task}")
            items = subs.get(task, []) if isinstance(subs, dict) else []
            for item in items:
                lines.append(f" • {item}")
        return "\n".join(lines)

    # Filter out rows with empty date, day, or name
    df_clean = df[(df["date"].notna()) & (df["day"].notna()) & (df["name"].notna()) &
                  (df["date"].astype(str).str.strip() != "") & (df["day"].astype(str).str.strip() != "") & (df["name"].astype(str).str.strip() != "")]

    # Prepare display DataFrame with only relevant columns, no duplicates
    display_cols = [
        "date", "day", "name", "completed_tasks", "incomplete_tasks", "organizing_details", "notes", "subtasks", "Date", "Day"
    ]
    # Remove duplicate columns: keep only 'Date' and 'Day' (pretty), drop 'date' and 'day' (raw)
    display_cols = [c for c in display_cols if c not in ("date", "day")]  # remove raw
    # Add index for row deletion
    df_clean_disp = df_clean.copy()
    df_clean_disp["completed_tasks"] = df_clean_disp.apply(pretty_completed, axis=1)
    # Only show relevant columns
    show_cols = ["Date", "Day", "name", "completed_tasks", "incomplete_tasks", "organizing_details", "notes"]
    st.dataframe(df_clean_disp[show_cols].reset_index(), use_container_width=True)

    # --- Delete Rows Section ---
    st.markdown("---")
    st.subheader("❌ Delete Report Rows")
    with st.expander("Delete rows by row number"):
        if not df_clean.empty:
            df_display = df_clean.reset_index()
            df_display["RowLabel"] = "Row #" + df_display["index"].astype(str) + ": " + df_display["Date"].dt.strftime("%Y-%m-%d") + " (" + df_display["Day"] + ") - " + df_display["name"]
            options = df_display["RowLabel"].tolist()
            selected = st.multiselect("Select rows to delete:", options)
            if st.button("Delete Selected Rows") and selected:
                selected_indices = [int(label.split()[1].split(":")[0]) for label in selected]
                to_delete = df.iloc[selected_indices]
                with sqlite3.connect(DB_PATH) as conn:
                    for _, r in to_delete.iterrows():
                        conn.execute(
                            "DELETE FROM reports WHERE date = ? AND day = ? AND name = ?",
                            (r["date"], r["day"], r["name"]),
                        )
                    conn.commit()
                st.success(f"Deleted {len(to_delete)} row(s). Table will refresh.")
                st.rerun()
