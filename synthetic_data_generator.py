import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta

# --- CONFIGURATION ---
DB_PATH = 'screen_time.db'    # <--- Make sure this matches your file
WINDOW_DAYS = 7              # Look 1 week back and 1 week forward
NOISE_SCALE = 0.1             # 10% variance (+/- 10% of the average)
MIN_USAGE_THRESHOLD = 10       # Apps with avg usage < 5 mins are ignored

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_data():
    """Loads existing data to know what to skip."""
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM screen_time_records", conn)
        df['date'] = pd.to_datetime(df['date'])
        return df
    finally:
        conn.close()

def load_app_mapping():
    """Fetches app names for better readability."""
    conn = get_connection()
    try:
        # Tries to load names. If table/columns differ, it fails gracefully.
        df_apps = pd.read_sql("SELECT id, name FROM apps", conn)
        return dict(zip(df_apps['id'], df_apps['name']))
    except Exception:
        return {}
    finally:
        conn.close()

def get_neighbor_dates(target_date, weeks=2):
    """Calculates specific dates to look at (e.g., previous 2 Tuesdays)."""
    neighbors = []
    for i in range(1, weeks + 1):
        neighbors.append(target_date - timedelta(weeks=i))
        neighbors.append(target_date + timedelta(weeks=i))
    return neighbors

def generate_value_for_app(df, app_id, target_date):
    """
    Calculates synthetic value using a continuous rolling window 
    (e.g., all days from -14 to +14 days).
    """
    # Define the date range
    start_window = target_date - timedelta(days=WINDOW_DAYS)
    end_window = target_date + timedelta(days=WINDOW_DAYS)
    
    # Filter: Match App ID AND fall within the date range
    mask = (
        (df['app_id'] == app_id) & 
        (df['date'] >= start_window) & 
        (df['date'] <= end_window)
    )
    neighbor_data = df.loc[mask, 'time_spent']

    # If no data in this window, return None
    if neighbor_data.empty: return None
    
    avg_val = neighbor_data.mean()

    # If the app is barely used in this period, skip it
    if avg_val < MIN_USAGE_THRESHOLD: return None

    # Add Noise
    noise_magnitude = max(1, avg_val * NOISE_SCALE) 
    noise = np.random.normal(0, noise_magnitude)
    final_val = int(round(avg_val + noise))
    
    return max(0, min(final_val, 1440))

def main():
    print(f"--- Processing {DB_PATH} ---")
    df = load_data()
    app_map = load_app_mapping()
    
    # Define the full year range to check
    start_date = pd.Timestamp("2025-01-01")
    end_date = pd.Timestamp("2025-12-31")
    all_days = pd.date_range(start_date, end_date)
    
    unique_apps = df['app_id'].unique()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("\n--- Scanning Calendar ---\n")
        
        for current_day in all_days:
            day_str = current_day.strftime('%Y-%m-%d')
            
            # --- CRITICAL CHECK ---
            # If ANY record exists for this date, strictly skip the whole day.
            if not df[df['date'] == current_day].empty:
                # Optional: Print that we are skipping it (can comment out to reduce noise)
                # print(f"[EXISTS] {day_str} has data. Skipping.")
                continue 

            # If we reach here, the day is completely empty. Let's generate data.
            proposed_entries = []
            display_lines = []

            for app_id in unique_apps:
                val = generate_value_for_app(df, app_id, current_day)
                
                if val is not None and val > 0:
                    proposed_entries.append((int(app_id), val, day_str))
                    app_name = app_map.get(app_id, f"App {app_id}")
                    display_lines.append(f"   - {app_name}: {val} m")

            # Only ask user if we actually have data to propose
            if proposed_entries:
                print(f"\n[EMPTY DATE FOUND] {day_str} ({current_day.day_name()})")
                print(f"-> Proposed Data ({len(proposed_entries)} apps):")
                
                # Show first 5 apps
                for line in display_lines:
                    print(line)
                # if len(display_lines) > 5:
                #     print(f"   ... and {len(display_lines) - 5} more.")
                
                user_input = input(f"   >>> Insert? (y/n/q): ").strip().lower()
                
                if user_input == 'y':
                    cursor.executemany(
                        "INSERT INTO screen_time_records (app_id, time_spent, date) VALUES (?, ?, ?)",
                        proposed_entries
                    )
                    conn.commit()
                    print("   [SAVED]")
                    
                    # Update memory so next days can use this new data
                    new_rows = pd.DataFrame(proposed_entries, columns=['app_id', 'time_spent', 'date'])
                    new_rows['date'] = pd.to_datetime(new_rows['date'])
                    df = pd.concat([df, new_rows], ignore_index=True)
                    
                elif user_input == 'q':
                    break
                else:
                    print("   [SKIPPED]")
    
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()