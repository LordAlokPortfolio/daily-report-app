import io, json, sqlite3, unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# --- CONFIG ---
DB_PATH = Path(r"M:\ALOK\Daily Reports\daily_reports.db")

# --- DB INIT ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                date TEXT, day TEXT, name TEXT,
                completed_tasks TEXT, incomplete_tasks TEXT,
                organizing_details TEXT, notes TEXT,
                subtasks TEXT
            )
        """)

init_db()

# --- UI ---
SCHEDULE = {
    "Monday": ["Stock Screens","Screen Mesh","Spectra","LTC","Organizing Materials"],
    # ... (other days)
}

st.set_page_config(page_title="Daily Report", layout="wide")
tab_sub, tab_week = st.tabs(["📝 Submit", "📅 Weekly Reports"])

with tab_sub:
    st.header("Daily Report – Simarjit Kaur")
    date_sel = st.date_input("Date", datetime.today())
    day = date_sel.strftime("%A")
    tasks = SCHEDULE.get(day, [])
    if not tasks:
        st.warning(f"No tasks for {day}")
        st.stop()

    with st.form("form", clear_on_submit=True):
        completed, incomplete, task_subs = [], {}, {}
        for t in tasks:
            done = st.radio(f"{t} done?", ["Yes","No"], key=t, horizontal=True)
            # ... do subtasks and reasons like before ...
            if done=="Yes":
                completed.append(t)
            else:
                incomplete[t] = st.text_area(f"❗ Reason – {t}", key=f"{t}_reason", height=80)
        notes = st.text_area("🗒️ Notes", height=80)
        if st.form_submit_button("✅ Submit"):
            if any(not v.strip() for v in incomplete.values()):
                st.error("Unfinished tasks need reasons"); st.stop()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)", (
                    date_sel.strftime("%Y-%m-%d"), day, "Simarjit Kaur",
                    ", ".join(completed),
                    "All completed" if not incomplete else str(incomplete),
                    st.session_state.get("organizing_details",""),
                    notes, json.dumps(task_subs),
                ))
            st.success("✅ Saved")

with tab_week:
    st.header("Weekly Reports")
    df = pd.read_sql("SELECT * FROM reports", sqlite3.connect(DB_PATH))
    if df.empty:
        st.info("No data yet"); st.stop()

    df["Date"] = pd.to_datetime(df["date"])
    df["Day"] = df["Date"].dt.strftime("%A")
    df["subtasks"] = df["subtasks"].apply(lambda x: json.dumps(json.loads(x or "{}"), indent=1))

    st.dataframe(df.drop(columns=["date"]), use_container_width=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Reports", index=False)
    buf.seek(0)
    st.download_button("📥 Download Excel", data=buf,
                       file_name="Simarjit_All_Reports.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
