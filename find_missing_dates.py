import sqlite3
import pandas as pd

# --- CONFIGURATION ---
DB_PATH = 'screen_time.db'  # <--- Update this to your filename
TARGET_YEAR = 2025            # The year you want to check
TABLE_NAME = 'screen_time_records'

def get_missing_dates():
    # 1. Connect and Fetch Existing Dates
    conn = sqlite3.connect(DB_PATH)
    try:
        # We only need the distinct dates, not the whole table
        query = f"SELECT DISTINCT date FROM {TABLE_NAME} WHERE date LIKE '{TARGET_YEAR}%'"
        existing_dates_df = pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error reading database: {e}")
        return
    finally:
        conn.close()

    # 2. Process Dates
    # Convert string dates (YYYY-MM-DD) to datetime objects for comparison
    existing_dates_df['date'] = pd.to_datetime(existing_dates_df['date'])
    existing_dates_set = set(existing_dates_df['date'])

    # 3. Generate the "Perfect" Year
    full_year_range = pd.date_range(
        start=f'{TARGET_YEAR}-01-01', 
        end=f'{TARGET_YEAR}-12-31', 
        freq='D'
    )

    # 4. Find the Difference
    # (All Days in Year) - (Days Present in DB)
    missing_dates = [d for d in full_year_range if d not in existing_dates_set]

    # 5. Print Results
    print(f"--- Analysis for {TARGET_YEAR} ---")
    print(f"Total days in year: {len(full_year_range)}")
    print(f"Days with data:     {len(existing_dates_set)}")
    print(f"MISSING DAYS:       {len(missing_dates)}")
    print("-" * 30)

    if not missing_dates:
        print("Great! No missing dates found.")
    else:
        print("Dates with NO records:")
        for d in missing_dates:
            print(f" - {d.strftime('%Y-%m-%d')} ({d.day_name()})")

if __name__ == "__main__":
    get_missing_dates()