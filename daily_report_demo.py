"""
Streamlit Daily Report App for Simarjit Kaur
-------------------------------------------
Creates / reads a local SQLite database of daily reports and
lets the user generate Excel summaries (vertical layout,
one Excel sheet per ISO‑week).
"""

from __future__ import annotations
import io, json, sqlite3, unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------#
# CONFIG                                                            #
# ------------------------------------------------------------------#
DB_PATH = Path(r"M:\ALOK\Daily Reports\daily_reports.db")

# ------------------------------------------------------------------#
# DB INIT                                                           #
# ------------------------------------------------------------------#
def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports(
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
        cols = [c[1] for c in conn.execute("PRAGMA table_info(reports)")]
        if "subtasks" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN subtasks TEXT")


init_db()

# ------------------------------------------------------------------#
# HELPERS                                                           #
# ------------------------------------------------------------------#
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", "ignore").decode("latin-1")


# ------------------------------------------------------------------#
# STATIC TASK SCHEDULE                                              #
# ------------------------------------------------------------------#
SCHEDULE: dict[str, list[str]] = {
    "Monday": [
        "Stock Screens",
        "Screen Mesh",
        "Spectra",
        "LTC",
        "Organizing Materials",
    ],
    "Tuesday": ["Vision", "RPM Punched", "RPM Stainless", "Organizing Materials"],
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
    "Friday": ["Mini Blinds", "Foam Concept", "Cardboard", "Organizing Materials"],
}

# ------------------------------------------------------------------#
# STREAMLIT UI                                                      #
# ------------------------------------------------------------------#
st.set_page_config(page_title="Daily Report", layout="wide")
tab_submit, tab_weekly = st.tabs(["📝 Submit Report", "📅 Weekly Reports"])

# ------------------------------- TAB 1 ----------------------------#
with tab_submit:
    st.header("Daily Report – Simarjit Kaur")

    date_sel = st.date_input("Date", datetime.today())
    day_name = date_sel.strftime("%A")
    tasks = SCHEDULE.get(day_name, [])
    if not tasks:
        st.info(f"No tasks scheduled for **{day_name}**.")
        st.stop()

    with st.form("report_form", clear_on_submit=True):
        completed: list[str] = []
        incomplete: dict[str, str] = {}
        task_subs: dict[str, list[str]] = {}

        default_subs = [
            "Counted and recorded on Excel",
            "Sent file to managers via email",
            "Gave physical copies to managers",
            "Arranged materials to its location",
        ]

        for task in tasks:
            done = st.radio(
                f"{task} done?", ["Yes", "No"], key=task, horizontal=True
            )
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
                    reason = st.text_area(
                        f"❗ Reason – sub‑tasks missing ({task})",
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
            else:
                reason = st.text_area(
                    f"❗ Reason – not done ({task})",
                    key=f"{task}_reason",
                    height=80,
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
                        json.dumps(task_subs),
                    ),
                )
            st.success("✅ Saved!")

# ------------------------------- TAB 2 ----------------------------#
with tab_weekly:
    st.header("📅 Weekly Reports")

    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No reports found.")
        st.stop()

    # tidy columns for display
    df["date"] = pd.to_datetime(df["date"])
    df["Day"] = df["date"].dt.strftime("%A")
    df["subtasks"] = df["subtasks"].apply(
        lambda x: json.dumps(json.loads(x or "{}"), indent=1)
    )

    st.dataframe(df.drop(columns=["day"]), use_container_width=True)

    # -------- Excel download (vertical layout, one sheet per ISO week) -----
    excel_buf = io.BytesIO()

    # add ISO calendar columns
    iso = df["date"].dt.isocalendar()
    df["iso_year"], df["iso_week"] = iso.year, iso.week

    with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
        for (yr, wk), grp in df.groupby(["iso_year", "iso_week"]):
            sheet = f"W{wk:02d}_{yr}"
            start_row = 0

            for _, row in grp.iterrows():
                # drop helper cols + duplicates
                clean = row.drop(labels=["iso_year", "iso_week"]).loc[
                    ~row.index.duplicated(keep="first")
                ]
                vertical = (
                    clean.to_frame(name="Value")
                    .reset_index()
                    .rename(columns={"index": "Field"})
                )
                vertical.to_excel(
                    writer,
                    sheet_name=sheet,
                    index=False,
                    header=start_row == 0,  # header only on first record
                    startrow=start_row,
                )
                start_row += len(vertical) + 1  # add blank spacer row

    excel_buf.seek(0)
    st.download_button(
        "📥 Download Weekly Workbook (vertical)",
        data=excel_buf,
        file_name="Simarjit_All_Reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
