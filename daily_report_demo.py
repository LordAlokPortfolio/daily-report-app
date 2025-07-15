"""
Streamlit Daily Report App for Simarjit Kaur
-------------------------------------------

Creates/reads a local SQLite database of daily reports and
lets the user generate Excel + PDF summaries.
"""

from __future__ import annotations
import io, json, sqlite3, unicodedata
from datetime import datetime, timedelta
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
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
        """)
        existing = [col[1] for col in conn.execute("PRAGMA table_info(reports)")]
        if "subtasks" not in existing:
            conn.execute("ALTER TABLE reports ADD COLUMN subtasks TEXT")


init_db()

# ------------------------------------------------------------------#
#                         HELPER FUNCTIONS                          #
# ------------------------------------------------------------------#
def clean_text(text: str | None) -> str:
    """Strip any character that the built‑in Latin‑1 PDF font can’t encode."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", "ignore").decode("latin-1")


def generate_pdf(df: pd.DataFrame, title: str = "Weekly Summary") -> bytes:
    """Return a PDF (bytes) built only with Latin‑1‑safe characters."""
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    # header
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, clean_text(f"Simarjit Kaur – {title}"), ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)

    for _, row in df.iterrows():
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, clean_text(f"{row['date']}  ({row['Day']})"), ln=True)

        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, clean_text(f"✅ Completed:\n{row['completed_tasks'] or '—'}"))
        pdf.multi_cell(0, 6, clean_text(f"❌ Incomplete:\n{row['incomplete_tasks'] or '—'}"))

        if row["organizing_details"]:
            pdf.multi_cell(0, 6, clean_text(f"🧹 Organizing:\n{row['organizing_details']}"))

        try:
            subs = json.loads(row.get("subtasks", "") or "{}")
        except Exception:
            subs = {}
        if subs:
            pdf.multi_cell(0, 6, "📋 Sub‑Tasks:")
            for task, items in subs.items():
                pdf.multi_cell(0, 6, clean_text(f"• {task}"))
                for it in items:
                    pdf.multi_cell(0, 6, clean_text(f"    – {it}"))

        if row["notes"]:
            pdf.multi_cell(0, 6, clean_text(f"🗒️ Notes:\n{row['notes']}"))

        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 6, f"Generated {datetime.now():%d %b %Y %H:%M}", 0, 0, "L")
    pdf.cell(0, 6, f"Page {pdf.page_no()}", 0, 0, "R")

    return pdf.output(dest="S").encode("latin-1",'replace')

# ------------------------------------------------------------------#
#                    STATIC TASK SCHEDULE                          #
# ------------------------------------------------------------------#
SCHEDULE: dict[str, list[str]] = {
    "Monday": ["Stock Screens", "Screen Mesh", "Spectra", "LTC", "Organizing Materials"],
    "Tuesday": ["Vision", "RPM Punched", "RPM Stainless", "Organizing Materials"],
    "Wednesday": ["SIL Plastic", "SIL Fastners", "Schelgal", "Shop Supplies", "Organizing Materials"],
    "Thursday": ["Amesbury Truth", "Twin/Multipoint Keepers", "Stock Screens", "Foot Locks", "Organizing Materials"],
    "Friday": ["Mini Blinds", "Foam Concept", "Cardboard", "Organizing Materials"],
}

# ------------------------------------------------------------------#
#                        STREAMLIT UI                               #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly Reports"])

# -- TAB 1: Submission --
with tab_submit:
    st.header("Daily Report – Simarjit Kaur")

    date_sel = st.date_input("Date", datetime.today())
    day = date_sel.strftime("%A")
    tasks = SCHEDULE.get(day, [])
    if not tasks:
        st.warning(f"No tasks scheduled for **{day}**.")
        st.stop()

    with st.form("report_form", clear_on_submit=True):
        completed, incomplete, task_subs = [], {}, {}

        st.subheader(f"Tasks – {day}")
        default_subs = [
            "Counted and recorded on Excel",
            "Sent file to managers via email",
            "Gave physical copies to managers",
            "Arranged materials to its location",
        ]

        for task in tasks:
            done = st.radio(f"{task} done?", ["Yes", "No"], key=task, horizontal=True)
            if done == "Yes":
                completed.append(task)
                flags, selected = [], []
                st.markdown("✔️ **Confirm Sub-Tasks Completed**")
                for sub in default_subs:
                    ch = st.checkbox(sub, key=f"{task}_{sub}")
                    flags.append(ch)
                    if ch:
                        selected.append(sub)
                task_subs[task] = selected

                if not all(flags):
                    reason = st.text_area(f"❗ Reason – incomplete subs ({task})", key=f"{task}_reason", height=80)
                    incomplete[task] = reason
                if task == "Organizing Materials":
                    st.text_area("🧹 Organizing Details", key="organizing_details", height=120)
            else:
                reason = st.text_area(f"❗ Reason – not done ({task})", key=f"{task}_reason", height=80)
                incomplete[task] = reason

        notes = st.text_area("🗒️ Notes (optional)", height=80)

        if st.form_submit_button("✅ Submit Report"):
            if any(not v.strip() for v in incomplete.values()):
                st.error("Unfinished tasks require reasons.")
                st.stop()
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)
            """, (
                date_sel.strftime("%Y-%m-%d"),
                day,
                "Simarjit Kaur",
                ", ".join(completed),
                "All completed" if not incomplete else str(incomplete),
                st.session_state.get("organizing_details", ""),
                notes,
                json.dumps(task_subs),
            ))
            conn.commit()
            conn.close()
            st.success("✅ Saved!")

# -- TAB 2: Weekly Reports --
with tab_weekly:
    st.header("📅 Weekly Reports")

    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No reports found.")
        st.stop()

    df["Date"] = pd.to_datetime(df["date"])
    df["Day"] = df["Date"].dt.strftime("%A")
    df["subtasks"] = df["subtasks"].apply(lambda x: json.dumps(json.loads(x or "{}"), indent=1))

    st.dataframe(df.drop(columns=["date"]), use_container_width=True)

    # Excel Export
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="All Reports", index=False)
    buf.seek(0)
    st.download_button("📥 Download Excel", data=buf,
                       file_name="Simarjit_All_Reports.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # PDF Export (last 7 days)
    last = df[df["Date"] >= datetime.now() - timedelta(days=7)]
    if not last.empty:
        pdf_bytes = generate_pdf(last, title="Last 7‑Day Summary")
        st.download_button("🖨️ Download PDF (last 7 days)",
                           data=pdf_bytes,
                           file_name="Last7Days_Report.pdf",
                           mime="application/pdf")
