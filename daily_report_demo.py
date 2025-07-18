"""
Streamlit Daily Report App for Simarjit Kaur
-------------------------------------------
Creates / reads a SQLite database of daily reports and
lets the user generate weekly Excel + PDF summaries.
"""

from __future__ import annotations

import io
import json
import re
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
    """Create the `reports` table if it doesn't exist."""
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

init_db()

# ------------------------------------------------------------------#
#                         HELPER FUNCTIONS                          #
# ------------------------------------------------------------------#
def clean_text(text: str | None) -> str:
    """Strip non-ASCII characters (including emojis) for PDF output."""
    if not isinstance(text, str):
        return ""
    txt = unicodedata.normalize("NFKD", text)
    # remove common emoji/unicode ranges
    emoji_pattern = re.compile(
        "["                       
        "\U0001F600-\U0001F64F"  
        "\U0001F300-\U0001F5FF"  
        "\U0001F680-\U0001F6FF"  
        "\U0001F1E0-\U0001F1FF"  
        "\U00002700-\U000027BF"  
        "\U0001F900-\U0001F9FF"  
        "\U00002600-\U000026FF"  
        "\U00002B50-\U00002B55"  
        "]+",
        flags=re.UNICODE
    )
    txt = emoji_pattern.sub("", txt)
    # drop any remaining non-ASCII
    return txt.encode("ascii", "ignore").decode("ascii")

def generate_pdf(df: pd.DataFrame, week_no: int) -> bytes:
    """
    Generate a PDF summary for one ISO-week (or all weeks if week_no==0),
    with separators after each day and between weeks.
    """
    pdf = FPDF()
    pdf.add_page()

    # Title (use hyphen, not en-dash)
    pdf.set_font("Arial", "B", 16)
    title = "All Weeks" if week_no == 0 else f"Week {week_no}"
    header = clean_text(f"Simarjit Kaur - Weekly Report ({title})")
    pdf.cell(0, 12, header, ln=True, align="C")
    pdf.ln(8)

    last_week = None
    for _, row in df.iterrows():
        # insert week break if in “All Weeks” view
        this_week = row["Date"].isocalendar().week
        if week_no == 0 and last_week is not None and this_week != last_week:
            pdf.ln(5)
            pdf.set_draw_color(160, 160, 160)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(8)
        last_week = this_week

        # Day header
        date_str = row["Date"].strftime("%Y-%m-%d")
        day_str  = row["Day"]
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, clean_text(f"{date_str} ({day_str})"), ln=True)
        pdf.ln(2)

        # Completed Tasks
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, clean_text("Completed Tasks:"), ln=True)
        pdf.set_font("Arial", "", 11)
        try:
            completed = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
        except Exception:
            completed = []
        pdf.multi_cell(0, 6, clean_text(", ".join(completed) if completed else "-"))
        pdf.ln(2)

        # Incomplete Tasks
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, clean_text("Incomplete Tasks:"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, clean_text(row.get("incomplete_tasks") or "-"))
        pdf.ln(2)

        # Organizing Details
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, clean_text("Organizing Details:"), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, clean_text(row["organizing_details"] or "-"))
        pdf.ln(2)

        # Sub‑Tasks with ASCII “[x] ”
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, clean_text("Sub-Tasks:"), ln=True)
        pdf.set_font("Arial", "", 11)
        try:
            subs = json.loads(row["subtasks"] or "{}")
            if isinstance(subs, dict) and subs:
                for task, items in subs.items():
                    if items:
                        line = f"[x] {task}: {', '.join(items)}"
                        pdf.multi_cell(0, 6, clean_text(line))
            else:
                pdf.multi_cell(0, 6, "-")
        except Exception:
            pdf.multi_cell(0, 6, "-")
        pdf.ln(5)

        # Day separator
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

    # Final week separator
    pdf.ln(5)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.7)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Page {pdf.page_no()}", align="C")

    return pdf.output(dest="S").replace(b"\u2013", b"-").encode("latin-1")

# ------------------------------------------------------------------#
#                       STATIC TASK SCHEDULE                       #
# ------------------------------------------------------------------#
SCHEDULE: dict[str, list[str]] = {
    "Monday":    ["Stock Screens","Screen Mesh","Spectra","LTC","Organizing Materials"],
    "Tuesday":   ["Vision","RPM Punched","RPM Stainless","Organizing Materials"],
    "Wednesday": ["SIL Plastic","SIL Fastners","Schelgal","Shop Supplies","Organizing Materials"],
    "Thursday":  ["Amesbury Truth","Twin/Multipoint Keepers","Stock Screens","Foot Locks","Organizing Materials"],
    "Friday":    ["Mini Blinds","Foam Concept","Cardboard","Organizing Materials"],
}

# ------------------------------------------------------------------#
#                        STREAMLIT LAYOUT                           #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")

from datetime import datetime
import random

# Personal greeting based on time of day
now = datetime.now()
hour = now.hour
if hour < 12:
    greet = "Good morning"
elif hour < 18:
    greet = "Good afternoon"
else:
    greet = "Good evening"

# Motivational quotes
quotes = [
    "Success is the sum of small efforts repeated day in and day out.",
    "Focus on being productive instead of busy.",
    "Don't watch the clock; do what it does—keep going.",
    "Well done is better than well said.",
    "You don't have to be great to start, but you have to start to be great."
]
quote = random.choice(quotes)

# Render greeting, date/time, and quote
st.markdown(f"### {greet}, Simarjit Kaur!")
st.markdown(f"#### Today is {now:%A, %B %d, %Y • %I:%M %p}")
st.markdown("> _" + quote + "_")
st.markdown("---")

# Define the two main tabs
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly View"])

# ------------------------ TAB 1: SUBMIT ---------------------------#
with tab_submit:
    st.header("Daily Report")
    date_sel = st.date_input("Date", datetime.today())
    day_name = date_sel.strftime("%A")
    tasks = SCHEDULE.get(day_name, [])
    if not tasks:
        st.info(f"No tasks scheduled for **{day_name}**.")
        st.stop()

    with st.form("report_form", clear_on_submit=True):
        completed: list[str] = []
        incomplete: dict[str,str] = {}
        task_subs: dict[str,list[str]] = {}
        default_subs = [
            "Counted and recorded on Excel",
            "Sent file to managers via email",
            "Provided physical copies to managers",
            "Arranged material in its location",
        ]

        for task in tasks:
            done = st.radio(f"{task} done?", ["Yes","No"], key=task, horizontal=True)
            if done == "Yes":
                completed.append(task)
                flags, chosen = [], []
                st.markdown("✔️ **Confirm Sub‑Tasks Completed**")
                for sub in default_subs:
                    chk = st.checkbox(sub, key=f"{task}_{sub}")
                    flags.append(chk)
                    if chk:
                        chosen.append(sub)
                task_subs[task] = chosen

                if not all(flags):
                    reason = st.text_area(f"❗ Reason – sub‑tasks missing ({task})",
                                          key=f"{task}_reason", height=80)
                    incomplete[task] = reason

                if task == "Organizing Materials":
                    st.text_area("🧹 Organizing Details", key="organizing_details", height=120)
            else:
                reason = st.text_area(f"❗ Reason – not done ({task})",
                                      key=f"{task}_reason", height=80)
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
                        st.session_state.get("organizing_details",""),
                        notes,
                        json.dumps(task_subs),
                    ),
                )
            st.success("✅ Report saved!")
            from git_autobackup import backup_to_git
            try:
                backup_to_git(db_path=str(DB_PATH))
                st.info("🔄 Database backed up to GitHub.")
            except Exception as e:
                st.error(f"Backup failed: {e}")

# ----------------------- TAB 2: WEEKLY VIEW -----------------------#
with tab_weekly:
    st.header("📅 Weekly View")
    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No records found.")
        st.stop()

    df["Date"] = pd.to_datetime(df["date"])
    df["Week"] = df["Date"].dt.isocalendar().week
    df["Day"]  = df["Date"].dt.strftime("%A")

    def pretty_completed(row):
        done = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
        subs = json.loads(row["subtasks"] or "{}")
        if not done:
            return "-"
        lines = []
        for t in done:
            lines.append(f"✔ {t}")
            for sub in subs.get(t, []):
                lines.append(f"    • {sub}")
        return "\n".join(lines)

    df_clean = df[(df["date"].notna()) & (df["day"].notna())]
    df_clean_disp = df_clean.copy()
    df_clean_disp["completed_tasks"] = df_clean_disp.apply(pretty_completed, axis=1)

    show_cols = ["Date","Day","name","completed_tasks","incomplete_tasks",
                 "organizing_details","notes"]
    st.dataframe(df_clean_disp[show_cols].reset_index(drop=True), use_container_width=True)

    # --- Delete Rows Section ---
    st.markdown("---")
    st.subheader("❌ Delete Report Rows")
    df_display = df_clean.reset_index()
    df_display["RowLabel"] = (
        "Row #" + df_display["index"].astype(str)
        + ": " + df_display["Date"].dt.strftime("%Y-%m-%d")
        + " (" + df_display["Day"] + ") - " + df_display["name"]
    )
    options = [{"label": r["RowLabel"], "value": r["index"]} for _,r in df_display.iterrows()]
    selected = st.multiselect(
        "Select rows to delete:",
        options=[o["value"] for o in options],
        format_func=lambda i: next(o["label"] for o in options if o["value"]==i)
    )
    if st.button("Delete Selected Rows") and selected:
        to_delete = df_clean.loc[selected]
        with sqlite3.connect(DB_PATH) as conn:
            for _,r in to_delete.iterrows():
                conn.execute(
                    "DELETE FROM reports WHERE date=? AND day=? AND name=?",
                    (r["date"],r["day"],r["name"])
                )
            conn.commit()
        st.success(f"Deleted {len(selected)} row(s). Refreshing…")
        st.rerun()

    # Excel download
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_clean_disp[show_cols].to_excel(writer, sheet_name="All_Reports", index=False)
    excel_buf.seek(0)
    st.download_button(
        "📥 Download Excel",
        data=excel_buf,
        file_name="Simarjit_All_Reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # PDF download (all weeks)
    pdf_bytes = generate_pdf(df_clean, week_no=0)
    st.download_button(
        "🖨️ Download PDF",
        data=pdf_bytes,
        file_name="Simarjit_All_Reports.pdf",
        mime="application/pdf"
    )
