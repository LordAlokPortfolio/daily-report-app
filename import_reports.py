# import_reports.py

import pandas as pd
import sqlite3

def load_vertical_sheet(df_sheet):
    """
    Convert a vertical Field/Value sheet into a list of record dicts.
    Starts a new record whenever Field == "date".
    """
    records = []
    current = {}
    # iterate over rows
    for _, row in df_sheet.iterrows():
        field = str(row["Field"]).strip()
        value = row["Value"]
        # normalize missing
        if pd.isna(value):
            value = ""
        else:
            value = str(value)

        # When we hit a new date, push the last record (if any)
        if field.lower() == "date":
            if current:
                records.append(current)
            current = {}

        # assign the field
        current[field] = value

    # append the final record
    if current:
        records.append(current)
    return records

def main():
    # 1. Read all sheets
    xls = pd.read_excel(
        "Simarjit_All_Reports.xlsx",
        sheet_name=None,
        engine="openpyxl",
    )
    print("Found sheets:", list(xls.keys()))

    all_records = []
    for name, df in xls.items():
        # ensure columns are exactly ['Field','Value']
        df_sheet = df[["Field", "Value"]]
        recs = load_vertical_sheet(df_sheet)
        all_records.extend(recs)

    print(f"Parsed {len(all_records)} records from {len(xls)} sheets.")

    # 2. Build DataFrame
    df = pd.DataFrame(all_records)

    # 3. Ensure all DB columns exist
    cols = [
        "date", "day", "name", "completed_tasks",
        "incomplete_tasks", "organizing_details",
        "notes", "subtasks"
    ]
    # fill missing columns with empty strings
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    df = df[cols]  # reorder

    # 4. Normalize date
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # 5. Write to SQLite
    conn = sqlite3.connect("daily_reports.db")
    df.to_sql("reports", conn, if_exists="replace", index=False)
    conn.close()

    print(f"Imported {len(df)} rows into daily_reports.db")

if __name__ == "__main__":
    main()
