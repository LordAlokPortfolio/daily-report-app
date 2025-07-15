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
DB_PATH = Path(r"M:\ALOK\Daily Reports\daily_reports.db")

# ------------------------------------------------------------------#
#                    DATABASE INITIALISATION                        #
# ------------------------------------------------------------------#


def init_db() -> None:
    """Create the `reports` table (if absent) and make sure the
    `subtasks` column exists for legacy databases."""
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
        existing_cols = [
            col[1] for col in conn.execute("PRAGMA table_info(reports)")
        ]
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
    """Generate a pretty PDF summary for the selected week."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(
        0,
        10,
        clean_text(f"Simarjit Kaur – Weekly Report (Week {week_no})"),
        ln=True,
        align="C",
    )
    pdf.ln(5)

    # One section per day
    for _, row in df.iterrows():
        pdf.set_font("Arial", style="B", size=11)
        pdf.cell(0, 8, clean_text(f"📅 {row['date']}  ({row['Day']})"), ln=True)

        # Try to pretty-print subtasks JSON
        try:
            subs_dict = json.loads(row.get("subtasks", "{}"))
            if isinstance(subs_dict, dict) and subs_dict:
                subs_text = "\n".join(
                    f"• {task}:\n    - " + "\n    - ".join(items)
                    for task, items in subs_dict.items()
                )
            else:
                subs_text = "—"
        except Exception:
            subs_text = "—"

        pdf.set_font("Arial", size=10)
        pdf.multi_cell(
            0,
            6,
            clean_text(
                f"✅ Completed Tasks:\n{row['completed_tasks'] or '—'}\n\n"
                f"❌ Incomplete Tasks:\n{row['incomplete_tasks'] or '—'}\n\n"
                f"🧹 Organizing Details:\n{row['organizing_details'] or '—'}\n\n"
                f"📋 Sub-Tasks:\n{subs_text}\n\n"
                f"🗒️ Notes:\n{row['notes'] or '—'}"
            ),
        )

        # Divider
        pdf.ln(1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Page {pdf.page_no()}", 0, 0, "C")

    return pdf.output(dest="S").encode("latin1")


# ------------------------------------------------------------------#
#                     SCHEDULE (STATIC SAMPLE)                      #
# ------------------------------------------------------------------#
SCHEDULE: dict[str, list[str]] = {
    "Monday": [
        "Stock Screens",
        "Screen Mesh",
        "Spectra",
        "LTC",
        "Organizing Materials",
    ],
    "Tuesday": [
        "Vision",
        "RPM Punched",
        "RPM Stainless",
        "Organizing Materials",
    ],
    "Wednesday": [
        "SIL Plastic",
        "SIL Fastners",
        "Schelgal",
        "Shop Supplies",
        "Organizing Materials",
    ],
    "Thursday": [
        "Amesbury Truth",
        "Twin/Multipoint Keepers",
        "Stock Screens",
        "Foot Locks",
        "Organizing Materials",
    ],
    "Friday": [
        "Mini Blinds",
        "Foam Concept",
        "Cardboard",
        "Organizing Materials",
    ],
}

# ------------------------------------------------------------------#
#                        STREAMLIT LAYOUT                           #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly View"])

# ------------------------ TAB 1: SUBMIT ---------------------------#
with tab_submit:
    st.header("Daily Report – Simarjit Kaur")

    date_sel = st.date_input("Date", datetime.today())
    day_name = date_sel.strftime("%A")
    today_tasks = SCHEDULE.get(day_name, [])

    if not today_tasks:
        st.info(f"No predefined tasks for **{day_name}**.")
        st.stop()

    # ---------- form ----------#
    with st.form("report_form", clear_on_submit=True):
        completed: list[str] = []
        incomplete: dict[str, str] = {}
        task_subtasks: dict[str, list[str]] = {}

        st.subheader(f"Tasks for {day_name}")

        DEFAULT_SUBTASKS = [
            "Counted and recorded on Excel",
            "Sent file to managers via email",
            "Provided physical copies to managers",
            "Arranged material in its location",
        ]

        for task in today_tasks:
            choice = st.radio(
                f"{task} done?",
                ["Yes", "No"],
                key=task,
                horizontal=True,
            )

            if choice == "Yes":
                completed.append(task)
                selected_subs: list[str] = []
                flags: list[bool] = []

                st.markdown("✔️ **Confirm Sub-Tasks Completed**")
                for sub in DEFAULT_SUBTASKS:
                    checked = st.checkbox(sub, key=f"{task}_{sub}")
                    flags.append(checked)
                    if checked:
                        selected_subs.append(sub)

                task_subtasks[task] = selected_subs

                if not all(flags):
                    reason = st.text_area(
                        f"❗ Reason (some sub-tasks incomplete) – {task}",
                        key=f"{task}_reason",
                        height=80,
                    )
                    incomplete[task] = reason

                if task == "Organizing Materials":
                    st.text_area(
                        "🧹 Organizing Details",
                        key="organizing_details",
                        height=120,
                    )

            else:  # task not completed
                reason = st.text_area(
                    f"❗ Reason – {task} not completed",
                    key=f"{task}_reason",
                    height=80,
                )
                incomplete[task] = reason

        notes = st.text_area("🗒️ Notes (optional)", height=80)

        if st.form_submit_button("✅ Submit Report"):
            if any(not v.strip() for v in incomplete.values()):
                st.error("All unchecked tasks require a reason.")
                st.stop()

            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO reports
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
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

# ----------------------- TAB 2: WEEKLY VIEW -----------------------#
with tab_weekly:
    st.header("📅 Weekly Reports")

    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No records found.")
        st.stop()

    # Prepare summary columns like before:
    df["Date"] = pd.to_datetime(df["date"])
    df["Day"] = df["Date"].dt.strftime("%A")
    df["subtasks"] = df["subtasks"].apply(
        lambda x: json.dumps(json.loads(x or "{}"), indent=1)
    )

    st.dataframe(df.drop(columns=["date", "Day"]), use_container_width=True)

    # Excel export (all data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="AllReports", index=False)
    buf.seek(0)
    st.download_button("📥 Download Excel", data=buf,
                       file_name="Simarjit_All_Reports.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    
    # ------------- PDF download (last 7 days) -------------
    last_week = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=7)]
    pdf_bytes = generate_pdf(last_week, week_no=last_week["Date"].dt.isocalendar().week.max())
    st.download_button(
        "🖨️ Download PDF (last 7 days)",
        pdf_bytes,
        "Simarjit_LastWeek_Report.pdf",
        mime="application/pdf",
    )