import streamlit as st
import pandas as pd
import sqlite3, io, json
from datetime import datetime
from fpdf import FPDF
import unicodedata

DB_PATH = r"M:\ALOK\Daily Reports\daily_reports.db"

# Ensure database and required columns are created fresh
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports(
                date TEXT, day TEXT, name TEXT,
                completed_tasks TEXT, incomplete_tasks TEXT,
                organizing_details TEXT, notes TEXT,
                subtasks TEXT
            )
        """)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(reports)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        if "subtasks" not in existing_columns:
            cursor.execute("ALTER TABLE reports ADD COLUMN subtasks TEXT")
init_db()

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")

def generate_pdf(df, week_no):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, clean_text(f"Simarjit Kaur - Weekly Report (Week {week_no})"), ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", size=10)
    for _, r in df.iterrows():
        pdf.multi_cell(0, 7, clean_text(
            f"Date: {r['date']} | Day: {r['day']}\n"
            f"Completed Tasks: {r['completed_tasks']}\n"
            f"Incomplete Tasks: {r['incomplete_tasks']}\n"
            f"Organizing Details: {r['organizing_details']}\n"
            f"Sub-Tasks Done: {r.get('subtasks', '')}\n"
            f"Notes: {r['notes']}\n" + "-"*70))
        pdf.ln(1)
    return pdf.output(dest="S").encode("latin1")

schedule = {
    "Monday":    ["Stock Screens", "Screen Mesh", "Spectra", "LTC", "Organizing Materials"],
    "Tuesday":   ["Vision", "RPM Punched", "RPM Stainless", "Organizing Materials"],
    "Wednesday": ["SIL Plastic", "SIL Fastners", "Schelgal", "Shop Supplies", "Organizing Materials"],
    "Thursday":  ["Amesbury Truth", "Twin/Multipoint Keepers", "Stock Screens", "Foot Locks", "Organizing Materials"],
    "Friday":    ["Mini Blinds", "Foam Concept", "Cardboard", "Organizing Materials"],
}

st.set_page_config(page_title="Daily Report", layout="wide")
tab1, tab2 = st.tabs(["📝 Submit Report", "📅 Weekly View"])

with tab1:
    st.header("Daily Report – Simarjit Kaur")
    date_sel = st.date_input("Date", datetime.today())
    day = date_sel.strftime("%A")
    today_tasks = schedule.get(day, [])

    if not today_tasks:
        st.info(f"No tasks for {day}")
    else:
        with st.form("report_form"):
            completed = []
            incomplete = {}
            task_subtasks = {}
            st.subheader(f"Tasks for {day}")

            subtasks = [
                "Counted and recorded on Excel",
                "Sent file to managers through email",
                "Gave physical copies to managers",
                "Arranged the material to its location"
            ]

            for task in today_tasks:
                choice = st.radio(f"{task} done?", ["Yes", "No"], key=task, horizontal=True)
                if choice == "Yes":
                    completed.append(task)
                    subtask_flags = []
                    selected_subs = []
                    st.markdown("✔️ **Confirm Sub-Tasks Completed**")
                    for sub in subtasks:
                        is_checked = st.checkbox(f"{sub}", key=f"{task}_{sub}")
                        subtask_flags.append(is_checked)
                        if is_checked:
                            selected_subs.append(sub)
                    task_subtasks[task] = selected_subs

                    if not all(subtask_flags):
                        reason = st.text_area(
                            f"❗ Reason (Not all sub-tasks completed) – {task}",
                            key=f"{task}_reason", height=80)
                        incomplete[task] = reason

                    if task == "Organizing Materials":
                        st.text_area("🧹 Organizing Details", key="organizing_details", height=120)
                else:
                    reason = st.text_area(f"❗ Reason – {task} not completed", key=f"{task}_reason", height=80)
                    incomplete[task] = reason

            notes = st.text_area("🗒️ Notes (optional)", height=80)
            submit = st.form_submit_button("✅ Submit Report")

            if submit:
                if any(v.strip() == "" for v in incomplete.values()):
                    st.error("All unchecked tasks require a reason.")
                else:
                    incomplete_field = "All completed" if not incomplete else str(incomplete)
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)", (
                            date_sel.strftime("%Y-%m-%d"), day, "Simarjit Kaur",
                            ", ".join(completed), incomplete_field,
                            st.session_state.get("organizing_details", ""),
                            notes,
                            json.dumps(task_subtasks)
                        ))
                    st.success("✅ Report saved!")

with tab2:
    st.header("📅 Weekly Reports")
    df = pd.read_sql_query("SELECT * FROM reports", sqlite3.connect(DB_PATH))

    if df.empty:
        st.info("No records found.")
    else:
        df["Date"] = pd.to_datetime(df["date"])
        df["Week"] = df["Date"].dt.isocalendar().week
        df["Day"] = df["Date"].dt.strftime("%A")
        df["subtasks"] = df["subtasks"].apply(lambda x: json.dumps(json.loads(x), indent=1) if x else "")

        col1, col2 = st.columns(2)
        week_no = col1.number_input("Select Week #", 1, 53, df["Week"].max())
        day_fil = col2.selectbox("Select Day", ["All"] + sorted(df["Day"].unique()))

        df_show = df[df["Week"] == week_no]
        if day_fil != "All":
            df_show = df_show[df_show["Day"] == day_fil]

        st.dataframe(df_show.drop(columns=["Week"]), use_container_width=True)

        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl", mode="w") as writer:
            df_show.drop(columns=["Week"]).to_excel(writer, sheet_name=f"Week{week_no}", index=False)
        excel_buf.seek(0)
        st.download_button("📥 Download Excel", data=excel_buf,
                           file_name=f"Simarjit_Week{week_no}_Report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        pdf_bytes = generate_pdf(df_show.drop(columns=["Week"]), week_no)
        st.download_button("🖨️ Download PDF", data=pdf_bytes,
                           file_name=f"Simarjit_Week{week_no}_Report.pdf",
                           mime="application/pdf")
