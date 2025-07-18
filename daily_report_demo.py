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
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Simarjit Kaur - Weekly Report (Week {week_no})", ln=True, align="C")
    pdf.ln(5)

    for _, row in df.iterrows():
        # Use the parsed datetime column here
        date_str = row["Date"].strftime("%Y-%m-%d")
        day_str = row["Day"]

        # Date header
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"{date_str} ({day_str})", ln=True)
        pdf.ln(2)

        pdf.set_font("Arial", "", 11)

        # Completed tasks
        pdf.cell(0, 6, "Completed Tasks:", ln=True)
        pdf.multi_cell(0, 6, row["completed_tasks"] or "-")
        pdf.ln(2)

        # Incomplete tasks
        pdf.cell(0, 6, "Incomplete Tasks:", ln=True)
        try:
            inc = json.loads(row["incomplete_tasks"])
            if isinstance(inc, dict) and inc:
                for task, reason in inc.items():
                    pdf.multi_cell(0, 6, f"- {task}: {reason}")
            else:
                pdf.multi_cell(0, 6, "-")
        except Exception:
            pdf.multi_cell(0, 6, "-")
        pdf.ln(2)

        # Organizing details
        pdf.cell(0, 6, "Organizing Details:", ln=True)
        pdf.multi_cell(0, 6, row["organizing_details"] or "-")
        pdf.ln(2)

        # Sub‑tasks
        pdf.cell(0, 6, "Sub-Tasks:", ln=True)
        try:
            subs = json.loads(row["subtasks"])
            if isinstance(subs, dict) and subs:
                for task, items in subs.items():
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(0, 6, f"{task}:", ln=True)
                    pdf.set_font("Arial", "", 11)
                    for item in items:
                        pdf.multi_cell(0, 6, f"   - {item}")
                    pdf.ln(1)
            else:
                pdf.multi_cell(0, 6, "-")
        except Exception:
            pdf.multi_cell(0, 6, "-")
        pdf.ln(2)

        # Notes
        pdf.cell(0, 6, "Notes:", ln=True)
        pdf.multi_cell(0, 6, row["notes"] or "-")
        pdf.ln(5)

        # Divider
        y = pdf.get_y()
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

# ------------------------------- TAB 2 ----------------------------#
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
            return json.dumps(json.loads(x or "{}"), indent=1)
        except Exception:
            return "{}"

    df["subtasks"] = df["subtasks"].apply(safe_json_pretty)

    # Filters
    col1, col2 = st.columns(2)
    week_no = col1.number_input("Select Week #", 1, 53, int(df["Week"].max()))
    day_filter = col2.selectbox("Select Day", ["All"] + sorted(df["Day"].unique()))

    df_week = df[df["Week"] == week_no]
    if day_filter != "All":
        df_week = df_week[df_week["Day"] == day_filter]

    st.dataframe(df_week.drop(columns=["Week"]), use_container_width=True)

    # Excel download
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_week.drop(columns=["Week"]).to_excel(writer, sheet_name=f"Week{week_no}", index=False)
    excel_buf.seek(0)
    st.download_button(
        "📥 Download Excel",
        data=excel_buf,
        file_name=f"Simarjit_Week{week_no}_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # PDF download
    pdf_bytes = generate_pdf(df_week, week_no)
    st.download_button(
        "🖨️ Download PDF",
        data=pdf_bytes,
        file_name=f"Simarjit_Week{week_no}_Report.pdf",
        mime="application/pdf",
    )
