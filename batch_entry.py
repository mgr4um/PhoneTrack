import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from utils import format_date_for_display, format_date_for_db, format_time_display
from tkcalendar import DateEntry
from database import toggle_app_favorite, fetch_apps

class BatchEntryDialog:
    def __init__(self, parent, apps, submit_callback):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Time Entry")
        self.dialog.geometry("600x600")
        
        self.submit_callback = submit_callback
        self.entries = []

        # Date frame with total
        date_frame = ttk.LabelFrame(self.dialog, text="Date", padding=10)
        date_frame.pack(fill='x', padx=5, pady=5)

        # Left side - date controls
        date_controls = ttk.Frame(date_frame)
        date_controls.pack(side='left', fill='x', expand=True)

        # Date navigation buttons
        nav_frame = ttk.Frame(date_controls)
        nav_frame.pack(side='left', padx=5)
        
        # First row of date buttons
        nav_row1 = ttk.Frame(nav_frame)
        nav_row1.pack(fill='x', pady=2)
        ttk.Button(nav_row1, text="Yesterday", 
                  command=lambda: self.set_relative_date(-1)).pack(side='left', padx=2)
        ttk.Button(nav_row1, text="2 Days Ago", 
                  command=lambda: self.set_relative_date(-2)).pack(side='left', padx=2)
        ttk.Button(nav_row1, text="3 Days Ago", 
                  command=lambda: self.set_relative_date(-3)).pack(side='left', padx=2)

        # Second row of date buttons
        nav_row2 = ttk.Frame(nav_frame)
        nav_row2.pack(fill='x', pady=2)
        ttk.Button(nav_row2, text="4 Days Ago", 
                  command=lambda: self.set_relative_date(-4)).pack(side='left', padx=2)
        ttk.Button(nav_row2, text="5 Days Ago", 
                  command=lambda: self.set_relative_date(-5)).pack(side='left', padx=2)
        ttk.Button(nav_row2, text="6 Days Ago", 
                  command=lambda: self.set_relative_date(-6)).pack(side='left', padx=2)

        # Replace Entry with DateEntry
        self.date_entry = DateEntry(date_frame, width=12,
                                  date_pattern='dd/mm/yyyy',
                                  firstweekday='monday')
        self.date_entry.pack(side='left', padx=5)

        # Right side - total display
        total_frame = ttk.Frame(date_frame)
        total_frame.pack(side='right', padx=10)
        
        ttk.Label(total_frame, text="Total Time:").pack(side='left')
        self.total_label = ttk.Label(total_frame, text="0")
        self.total_label.pack(side='left', padx=5)

        # Entries frame with scrollbar
        entries_frame = ttk.LabelFrame(self.dialog, text="Time Entries", padding=10)
        entries_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create scrollable frame
        canvas = tk.Canvas(entries_frame)
        scrollbar = ttk.Scrollbar(entries_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # Bind mousewheel to canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Unbind when dialog is closed
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: (
            canvas.unbind_all("<MouseWheel>"), 
            self.dialog.destroy()
        ))

        # Headers
        ttk.Label(self.scrollable_frame, text="⭐", width=3).grid(row=0, column=0, padx=2)
        ttk.Label(self.scrollable_frame, text="App", width=20).grid(row=0, column=1, padx=5)
        ttk.Label(self.scrollable_frame, text="Time (minutes)", width=15).grid(row=0, column=2, padx=5)

        # Create entry rows for each app
        self.create_entries()

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons frame
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(buttons_frame, text="Submit All", 
                  command=self.submit_all).pack(side='right', padx=5)
        ttk.Button(buttons_frame, text="Clear All", 
                  command=self.clear_all).pack(side='right', padx=5)

        # Set initial date to yesterday
        self.set_relative_date(-1)
        
        # Focus first time entry
        if self.entries:
            self.entries[0][1].focus()

    def set_relative_date(self, days_offset):
        """Set date relative to today"""
        target_date = datetime.today() + timedelta(days=days_offset)
        self.date_entry.set_date(target_date)  # DateEntry uses set_date instead of insert

    def focus_next(self, current_idx):
        if current_idx < len(self.entries):
            self.entries[current_idx][1].focus()

    def clear_all(self):
        for _, entry, _ in self.entries:  # Unpack 3 values
            entry.delete(0, tk.END)
        self.entries[0][1].focus()
        self.total_label.config(text="0 min")  # Reset total display

    def submit_all(self):
        date = self.date_entry.get_date()  # Get datetime object directly
        if not date:
            messagebox.showerror("Error", "Please enter a date")
            return

        entries_to_submit = []
        for app, entry, _ in self.entries:  # Unpack 3 values, ignore fav_btn
            time_value = entry.get().strip()
            if time_value:  # Only process entries with values
                try:
                    time_spent = int(time_value)
                    entries_to_submit.append((app, time_spent))
                except ValueError:
                    messagebox.showerror("Error", f"Invalid time value for {app}")
                    return

        if entries_to_submit:
            db_date = date.strftime('%Y-%m-%d')  # Format date for database
            for app, time_spent in entries_to_submit:
                self.submit_callback(app, time_spent, db_date)
            
            messagebox.showinfo("Success", "All entries submitted successfully!")
            self.clear_all()
        else:
            messagebox.showwarning("Warning", "No entries to submit") 

    def toggle_favorite(self, app_name, current_state):
        """Toggle favorite status and update button"""
        toggle_app_favorite(app_name)
        btn = next(btn for app, _, btn in self.entries if app == app_name)
        btn.configure(text="☆" if current_state == "⭐" else "⭐")
        # Refresh the app list to reorder
        self.refresh_app_list()

    def refresh_app_list(self):
        """Refresh and reorder the app list"""
        # Store current values
        current_values = {app: entry.get() for app, entry, _ in self.entries}
        
        # Clear frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Recreate headers and entries
        self.create_entries()
        
        # Restore values
        for app, entry, _ in self.entries:
            if app in current_values:
                entry.insert(0, current_values[app]) 

    def create_entries(self):
        """Create entry rows for apps"""
        apps = fetch_apps()
        self.entries = []

        def validate_number(P):
            """Validate entry to only allow numbers"""
            if P == "": return True
            return P.isdigit()

        vcmd = self.dialog.register(validate_number)

        def update_total(*args):
            """Update total minutes display"""
            total = 0
            for _, entry, _ in self.entries:
                value = entry.get().strip()
                if value.isdigit():
                    total += int(value)
            self.total_label.config(text=format_time_display(total))

        for i, (app, is_favorite) in enumerate(apps, 1):
            # Favorite toggle button
            fav_text = "⭐" if is_favorite else "☆"
            fav_btn = ttk.Button(self.scrollable_frame, text=fav_text, width=3,
                                command=lambda a=app, b=fav_text: self.toggle_favorite(a, b))
            fav_btn.grid(row=i, column=0, padx=2, pady=2)
            
            # App name and time entry
            app_label = ttk.Label(self.scrollable_frame, text=app, width=20)
            time_entry = ttk.Entry(self.scrollable_frame, width=15, 
                                 validate='key', 
                                 validatecommand=(vcmd, '%P'))
            
            app_label.grid(row=i, column=1, padx=5, pady=2)
            time_entry.grid(row=i, column=2, padx=5, pady=2)
            
            time_entry.bind('<Return>', lambda e, idx=i: self.focus_next(idx))
            self.entries.append((app, time_entry, fav_btn)) 

            # Bind to update total when value changes
            time_entry.bind('<KeyRelease>', update_total)
            time_entry.bind('<FocusOut>', update_total)
            
        self.total_label.config(text=format_time_display(
            sum(int(entry.get().strip()) for _, entry, _ in self.entries 
                if entry.get().strip().isdigit())
        )) 