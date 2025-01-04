import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from database import (
    init_db, 
    add_category, 
    add_app, 
    add_screen_time, 
    fetch_screen_time_data,
    fetch_app_names,
    insert_sample_data,
    clear_screen_time_data,
    get_db_config,
    get_db_path,
    fetch_apps_with_categories
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
        apps = [app[0] for app in fetch_apps_with_categories()]  # Get just the app names
        if hasattr(self, 'app_combobox'):  # Check if combobox exists
            self.app_combobox['values'] = apps

    def create_input_frame(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="Batch Entry", 
                  command=self.open_batch_entry).pack(side='left', padx=5)
        ttk.Button(button_frame, text="⚙", width=3,
                  command=self.open_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Visualize", 
                  command=self.visualize_data).pack(side='left', padx=5)

    def open_batch_entry(self):
        app_names = fetch_app_names()  # Use new function that returns just names
        BatchEntryDialog(self.root, app_names, self.submit_single_entry)

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
        settings = SettingsDialog(self.root)
        settings.dialog.wait_window()  # Wait for the settings dialog to close
        if hasattr(self, 'app_combobox'):  # Only refresh if combobox exists
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