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
    """Strip non-ASCII characters for PDF output."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
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
        pdf.cell(0, 10, f"{date_str} ({day_str})", ln=True)
        pdf.ln(2)

        # Completed tasks with subtasks and check mark
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Completed Tasks:", ln=True)
        pdf.set_font("Arial", "", 11)
        completed_tasks = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
        try:
            subs = json.loads(row["subtasks"])
        except Exception:
            subs = {}
        for task in completed_tasks:
            pdf.cell(0, 7, f"✔ {task}", ln=True)
            # Show subtasks for this completed task
            items = subs.get(task, []) if isinstance(subs, dict) else []
            for item in items:
                pdf.cell(10)
                pdf.multi_cell(0, 7, f"• {item}")
        if not completed_tasks:
            pdf.cell(0, 7, "-", ln=True)
        pdf.ln(1)

        # Organizing details (after completed tasks)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Organizing Details:", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, row["organizing_details"] or "-")
        pdf.ln(1)

        # Incomplete tasks (only if any subtasks are missing)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Incomplete Tasks:", ln=True)
        pdf.set_font("Arial", "", 11)
        try:
            inc = json.loads(row["incomplete_tasks"])
            if isinstance(inc, dict) and inc:
                for task, reason in inc.items():
                    pdf.multi_cell(0, 7, f"- {task}: {reason}")
            else:
                pdf.multi_cell(0, 7, "-")
        except Exception:
            pdf.multi_cell(0, 7, "-")
        pdf.ln(1)

        # Notes
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Notes:", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, row["notes"] or "-")
        pdf.ln(3)

        # Divider
        y = pdf.get_y()
        pdf.set_draw_color(150, 150, 150)
        pdf.line(10, y, 200, y)
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

    def safe_json_pretty(x):
        try:
            # Only pretty-print if it's valid JSON dict/list, else return as string
            val = x or "{}"
            obj = json.loads(val)
            return json.dumps(obj, indent=1)
        except Exception:
            return "{}"

    df["subtasks"] = df["subtasks"].apply(safe_json_pretty)

    # Show all records for all weeks and days
    st.dataframe(df.drop(columns=["Week"]), use_container_width=True)

    # Excel download (all data)
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df.drop(columns=["Week"]).to_excel(writer, sheet_name="All_Reports", index=False)
    excel_buf.seek(0)
    st.download_button(
        "📥 Download Excel",
        data=excel_buf,
        file_name="Simarjit_All_Reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # PDF download (all data, use week_no as 0 for label)
    pdf_bytes = generate_pdf(df, 0)
    st.download_button(
        "🖨️ Download PDF",
        data=pdf_bytes,
        file_name="Simarjit_All_Reports.pdf",
        mime="application/pdf",
    )
