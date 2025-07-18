'''Streamlit Daily Report App for Simarjit Kaur
-------------------------------------------
Creates / reads a SQLite database of daily reports and
lets the user generate weekly Excel + PDF summaries.
'''

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

# Log the absolute path of the database file for debugging
import os
st.info(f"[DEBUG] Using database at: {os.path.abspath(DB_PATH)}")

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

init_db()

# ------------------------------------------------------------------#
#                         HELPER FUNCTIONS                          #
# ------------------------------------------------------------------#
def clean_text(text: str | None) -> str:
    """Strip non-ASCII characters and emojis for PDF output."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove emojis\    
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
    pdf = FPDF()
    pdf.add_page()
    # … title setup …

    # Keep track of the current ISO‐week if you ever feed it multiple weeks at once
    last_week = None
    for _, row in df.iterrows():
        # If you’re doing “All Weeks” (week_no == 0), insert a week‐separator when the ISO‐week changes
        if week_no == 0:
            this_week = row["Date"].isocalendar().week
            if last_week is not None and this_week != last_week:
                pdf.ln(5)
                pdf.set_draw_color(200, 200, 200)
                pdf.set_line_width(0.5)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(8)
            last_week = this_week

        # … your per‐day header & tasks …
        date_str = row["Date"].strftime("%Y-%m-%d")
        day_str  = row["Day"]
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, clean_text(f"{date_str} ({day_str})"), ln=True)
        pdf.ln(2)
        # … completed/incomplete/organizing/sub‑tasks …

        # draw a light rule after every day
        pdf.ln(3)
        pdf.set_draw_color(200, 200, 200)     # light gray
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    # at the very end of the whole PDF (i.e. after all days/weeks), one more rule
    pdf.ln(5)
    pdf.set_draw_color(0, 0, 0)               # maybe a darker line for week‐end
    pdf.set_line_width(0.7)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
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
    "Monday": ["Stock Screens","Screen Mesh","Spectra","LTC","Organizing Materials"],
    "Tuesday": ["Vision","RPM Punched","RPM Stainless","Organizing Materials"],
    "Wednesday": ["SIL Plastic","SIL Fastners","Schelgal","Shop Supplies","Organizing Materials"],
    "Thursday": ["Amesbury Truth","Twin/Multipoint Keepers","Stock Screens","Foot Locks","Organizing Materials"],
    "Friday": ["Mini Blinds","Foam Concept","Cardboard","Organizing Materials"],
}

# ------------------------------------------------------------------#
#                        STREAMLIT LAYOUT                           #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly View"])

# TAB 1: Submit
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
                task_subtasks[task] = chosen

                if not all(flags):
                    reason = st.text_area(
                        f"❗ Reason – sub‑tasks missing ({task})",
                        key=f"{task}_reason", height=80
                    )
                    incomplete[task] = reason

                if task == "Organizing Materials":
                    st.text_area("🧹 Organizing Details", key="organizing_details", height=120)
            else:
                reason = st.text_area(
                    f"❗ Reason – not done ({task})",
                    key=f"{task}_reason", height=80
                )
                incomplete[task] = reason

        notes = st.text_area("🗒️ Notes (optional)", height=80)

        if st.form_submit_button("✅ Submit Report"):
            # validation
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
                        json.dumps(task_subtasks),
                    ),
                )
            st.success("✅ Report saved!")

            # auto-backup
            from git_autobackup import backup_to_git
            try:
                backup_to_git(db_path=str(DB_PATH))
                st.info("🔄 Database backed up to GitHub.")
            except Exception as e:
                st.error(f"Backup failed: {e}")

# TAB 2: Weekly View
with tab_weekly:
    st.header("📅 Weekly View")

    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No records found.")
        st.stop()

    df["Date"] = pd.to_datetime(df["date"])
    df["Week"] = df["Date"].dt.isocalendar().week
    df["Day"] = df["Date"].dt.strftime("%A")

    def pretty_completed(row):
        try:
            completed = [t.strip() for t in (row["completed_tasks"] or "").split(",") if t.strip()]
            subs = json.loads(row["subtasks"]) if row["subtasks"] else {}
        except Exception:
            completed, subs = [], {}
        if not completed:
            return "-"
        lines = []
        for task in completed:
            lines.append(f"✔ {task}")
            for item in subs.get(task, []):
                lines.append(f"    • {item}")
        return "\n".join(lines)

    df_clean = df[
        df["date"].notna() & df["day"].notna() & df["name"].notna()
    ]
    df_clean_disp = df_clean.copy()
    df_clean_disp["completed_tasks"] = df_clean_disp.apply(pretty_completed, axis=1)
    show_cols = ["Date","Day","name","completed_tasks","incomplete_tasks","organizing_details","notes"]
    st.dataframe(df_clean_disp[show_cols].reset_index(drop=True), use_container_width=True)

    # Excel & PDF downloads
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_clean_disp[show_cols].to_excel(writer, sheet_name="All_Reports", index=False)
    excel_buf.seek(0)
    st.download_button(
        "📥 Download Excel",
        data=excel_buf,
        file_name="Simarjit_All_Reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
# --- Delete Rows Section ---
    st.markdown("---")
    st.subheader("❌ Delete Report Rows")
    with st.expander("Delete rows by row number"):
        if not df_clean.empty:
            df_display = df_clean.reset_index()
            df_display["RowLabel"] = "Row #" + df_display["index"].astype(str) + ": " + df_display["Date"].dt.strftime("%Y-%m-%d") + " (" + df_display["Day"] + ") - " + df_display["name"]
            options = [
                {"label": row["RowLabel"], "value": row["index"]}
                for _, row in df_display.iterrows()
            ]
            selected = st.multiselect(
                "Select rows to delete:",
                options=[opt["value"] for opt in options],
                format_func=lambda idx: next(opt["label"] for opt in options if opt["value"] == idx)
            )
            if st.button("Delete Selected Rows") and selected:
                to_delete = df.iloc[selected]
                with sqlite3.connect(DB_PATH) as conn:
                    for _, r in to_delete.iterrows():
                        conn.execute(
                            "DELETE FROM reports WHERE date = ? AND day = ? AND name = ?",
                            (r["date"], r["day"], r["name"]),
                        )
                    conn.commit()

                st.success(f"Deleted {len(to_delete)} row(s). Table will refresh.")
                st.rerun()


    pdf_bytes = generate_pdf(df_clean_disp, 0)
    st.download_button(
        "🖨️ Download PDF",
        data=pdf_bytes,
        file_name="Simarjit_All_Reports.pdf",
        mime="application/pdf",
    )
# ------------------------------------------------------------------#
# End of Streamlit app
# ------------------------------------------------------------------#   