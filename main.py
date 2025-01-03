import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from database import (
    init_db, 
    add_category, 
    add_app, 
    add_screen_time, 
    fetch_screen_time_data,
    fetch_apps,
    insert_sample_data,
    clear_screen_time_data,
    get_db_config,
    get_db_path
)
from visualizer import display_visualization
import sqlite3
from utils import format_date_for_db
from batch_entry import BatchEntryDialog
from settings_dialog import SettingsDialog
from app_config import APP_CONFIG

# Initialize Database
init_db()

# GUI Setup
class ScreenTimeTracker:
    def __init__(self, root):
        self.root = root
        
        # Add debug indicator to title
        title = "Screen Time Tracker"
        if get_db_config()['sample_data']:
            title += " [DEBUG MODE]"
            # Optional: Change background color in debug mode
            self.root.configure(bg='red')  # or any other distinctive color
            
        self.root.title(title)
        
        # Initialize categories and apps
        self.setup_initial_data()
        
        # Insert sample data only in debug mode
        if get_db_config()['sample_data']:
            insert_sample_data()
        
        # Create main frames
        self.create_input_frame()
        
    def setup_initial_data(self):
        self.categories = {}
        
        # Initialize categories and apps from config
        for category_name, apps in APP_CONFIG.items():
            category_id = add_category(category_name)
            if category_id:
                self.categories[category_name] = category_id
                # Add apps for this category
                for app_name in apps:
                    add_app(app_name, category_id)

    def refresh_app_list(self):
        """Refresh the app list in the combobox"""
        apps = fetch_apps()
        self.app_combobox['values'] = apps

    def create_input_frame(self):
        # App selection
        app_frame = ttk.LabelFrame(self.root, text="Add Screen Time", padding="10")
        app_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # Top buttons row
        button_frame = ttk.Frame(app_frame)
        button_frame.grid(row=0, column=0, columnspan=3, pady=5)
        
        ttk.Button(button_frame, text="Batch Entry", 
                  command=self.open_batch_entry).pack(side='left', padx=5)
        ttk.Button(button_frame, text="⚙", width=3,
                  command=self.open_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Visualize", 
                  command=self.visualize_data).pack(side='left', padx=5)

        # Single entry form
        ttk.Label(app_frame, text="App:").grid(row=1, column=0, padx=5, pady=5)
        self.app_combobox = ttk.Combobox(app_frame, values=fetch_apps())
        self.app_combobox.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(app_frame, text="Time (minutes):").grid(row=2, column=0, padx=5, pady=5)
        self.time_entry = ttk.Entry(app_frame)
        self.time_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(app_frame, text="Date (DD/MM/YYYY):").grid(row=3, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(app_frame)
        self.date_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Button(app_frame, text="Submit", 
                  command=self.submit_data).grid(row=4, column=0, columnspan=2, pady=10)

    def open_batch_entry(self):
        BatchEntryDialog(self.root, fetch_apps(), self.submit_single_entry)

    def submit_single_entry(self, app_name, time_spent, date):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM apps WHERE name = ?', (app_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            app_id = result[0]
            add_screen_time(app_id, time_spent, date)

    def visualize_data(self):
        data = fetch_screen_time_data()
        if data:
            display_visualization(data)
        else:
            messagebox.showinfo("Info", "No data to visualize!")

    def open_settings(self):
        SettingsDialog(self.root)
        # Refresh app list after settings dialog is closed
        self.refresh_app_list()

    def submit_data(self):
        app_name = self.app_combobox.get()
        time_spent = self.time_entry.get()
        date = self.date_entry.get()
        
        if not app_name or not time_spent or not date:
            messagebox.showerror("Error", "All fields are required!")
            return
        
        try:
            time_spent = int(time_spent)
            db_date = format_date_for_db(date)
            self.submit_single_entry(app_name, time_spent, db_date)
            messagebox.showinfo("Success", "Data added successfully!")
            
            # Clear inputs
            self.app_combobox.set('')
            self.time_entry.delete(0, tk.END)
            self.date_entry.delete(0, tk.END)
            
        except ValueError:
            messagebox.showerror("Error", "Time spent must be a number!")

def main():
    root = tk.Tk()
    app = ScreenTimeTracker(root)
    
    def on_closing():
        if get_db_config()['sample_data']:  # Only clear data in debug mode
            clear_screen_time_data()
        root.destroy()
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()