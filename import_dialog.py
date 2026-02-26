import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import os
from datetime import date, timedelta
from tkcalendar import DateEntry
from database import fetch_app_names, add_screen_time, get_db_path

# Path to persist the applicationId → app name mapping
MAPPING_FILE = os.path.join(os.path.dirname(__file__), 'app_id_mapping.json')

EPOCH = date(1970, 1, 1)


def load_mapping() -> dict:
    """Load saved applicationId → app name mapping from disk."""
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_mapping(mapping: dict):
    """Persist the applicationId → app name mapping to disk."""
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)


def day_int_to_date(day_int: int) -> date:
    """Convert integer day offset from 1970-01-01 to a date object."""
    return EPOCH + timedelta(days=day_int)


def ms_to_minutes(ms: int) -> int:
    """Convert milliseconds to minutes, returning 0 if under 30 seconds."""
    seconds = ms / 1000
    if seconds < 30:
        return 0
    return round(seconds / 60)


class ImportDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Import from SQLite")
        self.dialog.geometry("620x520")
        self.dialog.resizable(False, True)
        self.dialog.grab_set()

        # State
        self.source_path = tk.StringVar()
        self.saved_mapping = load_mapping()       # Persisted mapping from disk
        self.combo_vars = {}                      # applicationId → StringVar for dropdowns
        self.unmatched_ids = []                   # applicationIds not in saved mapping or DB
        self.preview_data = []                    # Rows ready to import after mapping step

        self._build_step1()

    # ------------------------------------------------------------------ #
    #  STEP 1 — File + Date Range                                         #
    # ------------------------------------------------------------------ #

    def _build_step1(self):
        self._clear_dialog()
        self.dialog.title("Import from SQLite — Step 1 of 3")

        ttk.Label(self.dialog, text="Import Screen Time Data",
                  font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ttk.Label(self.dialog, text="Select a source SQLite file and the date range to import.",
                  font=("Arial", 10)).pack(pady=(0, 15))

        # File picker
        file_frame = ttk.LabelFrame(self.dialog, text="Source File", padding=10)
        file_frame.pack(fill='x', padx=15, pady=5)

        entry_row = ttk.Frame(file_frame)
        entry_row.pack(fill='x')
        ttk.Entry(entry_row, textvariable=self.source_path, width=50).pack(side='left', padx=(0, 5))
        ttk.Button(entry_row, text="Browse…", command=self._browse_file).pack(side='left')

        # Date range
        range_frame = ttk.LabelFrame(self.dialog, text="Date Range", padding=10)
        range_frame.pack(fill='x', padx=15, pady=10)

        row = ttk.Frame(range_frame)
        row.pack()

        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)

        ttk.Label(row, text="From:").grid(row=0, column=0, padx=5, pady=4, sticky='e')
        self.from_date = DateEntry(row, width=12, date_pattern='dd/mm/yyyy',
                                   firstweekday='monday')
        self.from_date.set_date(yesterday)
        self.from_date.grid(row=0, column=1, padx=5, pady=4)

        ttk.Label(row, text="To:").grid(row=0, column=2, padx=5, pady=4, sticky='e')
        self.to_date = DateEntry(row, width=12, date_pattern='dd/mm/yyyy',
                                 firstweekday='monday')
        self.to_date.set_date(yesterday)
        self.to_date.grid(row=0, column=3, padx=5, pady=4)

        # Hint: last imported date
        self._hint_label = ttk.Label(range_frame, text="", font=("Arial", 9, "italic"),
                                     foreground="#555555")
        self._hint_label.pack(pady=(6, 0))

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(side='bottom', fill='x', padx=15, pady=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side='left')
        ttk.Button(btn_frame, text="Next →", command=self._step1_next).pack(side='right')

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select SQLite database",
            filetypes=[("SQLite files", "*.sqlite3 *.sqlite *.db"), ("All files", "*.*")]
        )
        if path:
            self.source_path.set(path)
            self._apply_last_date_hint()
            
    def _apply_last_date_hint(self):
        """Query the target DB for the last imported date and pre-fill from_date."""
        try:
            with sqlite3.connect(get_db_path()) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(date) FROM screen_time_records')
                result = cursor.fetchone()
            if result and result[0]:
                last_imported = date.fromisoformat(result[0])
                default_from = last_imported + timedelta(days=1)
                self._hint_label.config(
                    text=f"Last imported date in database: {last_imported.strftime('%d/%m/%Y')}"
                )
            else:
                default_from = date.today() - timedelta(days=1)
                self._hint_label.config(text="No data in database yet.")
            self.from_date.set_date(default_from)
        except Exception:
            pass  # Silently leave dates as-is if anything fails

    def _step1_next(self):
        path = self.source_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Error", "Please select a valid SQLite file.", parent=self.dialog)
            return

        from_d = self.from_date.get_date()
        to_d = self.to_date.get_date()
        if from_d > to_d:
            messagebox.showerror("Error", "'From' date must be before 'To' date.", parent=self.dialog)
            return

        self._from_date = from_d
        self._to_date = to_d
        self._source_path = path

        # Read source DB and compute unmatched IDs
        try:
            rows = self._read_source(path, from_d, to_d)
        except Exception as e:
            messagebox.showerror("Read Error", str(e), parent=self.dialog)
            return

        if not rows:
            messagebox.showinfo("No Data",
                                "No records found in the selected date range.",
                                parent=self.dialog)
            return

        self._raw_rows = rows  # [(app_id_str, date_obj, minutes), ...]

        # Determine which applicationIds need interactive mapping
        known_app_names = set(fetch_app_names())
        all_app_ids = {r[0] for r in rows}

        self.unmatched_ids = [
            aid for aid in sorted(all_app_ids)
            if aid not in self.saved_mapping or
               self.saved_mapping[aid] not in known_app_names
        ]

        if self.unmatched_ids:
            self._build_step2()
        else:
            # All IDs already mapped — jump straight to preview
            self._prepare_preview()
            if self.preview_data:
                self._build_step3()

    def _read_source(self, path: str, from_d: date, to_d: date) -> list:
        """
        Read usageStats from source DB, filtered to the date range.
        Returns list of (applicationId, date_obj, minutes).
        Rows with 0 minutes (< 30s) are dropped.
        """
        from_day = (from_d - EPOCH).days
        to_day = (to_d - EPOCH).days

        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT applicationId, day, timeUsed
                FROM usageStats
                WHERE day >= ? AND day <= ?
            ''', (from_day, to_day))
            raw = cursor.fetchall()

        result = []
        for app_id, day_int, time_ms in raw:
            minutes = ms_to_minutes(time_ms)
            if minutes == 0:
                continue
            result.append((app_id, day_int_to_date(day_int), minutes))
        return result

    # ------------------------------------------------------------------ #
    #  STEP 2 — Interactive Mapping                                        #
    # ------------------------------------------------------------------ #

    def _build_step2(self):
        self._clear_dialog()
        self.dialog.title("Import from SQLite — Step 2 of 3")

        ttk.Label(self.dialog, text="Map Unrecognised Apps",
                  font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ttk.Label(self.dialog,
                  text="These application IDs were not found in your database.\n"
                       "Map each one to an existing app, or choose Skip.",
                  font=("Arial", 10), justify='center').pack(pady=(0, 10))

        # Scrollable table
        container = ttk.Frame(self.dialog)
        container.pack(fill='both', expand=True, padx=15)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        canvas.bind('<MouseWheel>',
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        # Header
        ttk.Label(inner, text="Application ID", font=("Arial", 10, "bold"),
                  width=40).grid(row=0, column=0, padx=5, pady=4, sticky='w')
        ttk.Label(inner, text="Map to App", font=("Arial", 10, "bold"),
                  width=25).grid(row=0, column=1, padx=5, pady=4, sticky='w')

        known_app_names = sorted(fetch_app_names())
        options = ["— Skip —"] + known_app_names
        self.combo_vars = {}

        for i, aid in enumerate(self.unmatched_ids, 1):
            ttk.Label(inner, text=aid, width=40, anchor='w').grid(
                row=i, column=0, padx=5, pady=3, sticky='w')

            var = tk.StringVar()
            # Pre-fill from saved mapping if the mapped name still exists
            saved = self.saved_mapping.get(aid, '')
            var.set(saved if saved in known_app_names else "— Skip —")
            self.combo_vars[aid] = var

            cb = ttk.Combobox(inner, textvariable=var, values=options,
                              state='readonly', width=25)
            cb.grid(row=i, column=1, padx=5, pady=3)

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(side='bottom', fill='x', padx=15, pady=10)
        ttk.Button(btn_frame, text="← Back", command=self._build_step1).pack(side='left')
        ttk.Button(btn_frame, text="Next →", command=self._step2_next).pack(side='right')

    def _step2_next(self):
        # Merge new choices into saved_mapping and persist
        for aid, var in self.combo_vars.items():
            choice = var.get()
            if choice != "— Skip —":
                self.saved_mapping[aid] = choice
            elif aid in self.saved_mapping:
                # User explicitly chose Skip — remove from saved mapping
                del self.saved_mapping[aid]
        save_mapping(self.saved_mapping)

        self._prepare_preview()
        if self.preview_data:
            self._build_step3()

    # ------------------------------------------------------------------ #
    #  Preview / confirmation helpers                                     #
    # ------------------------------------------------------------------ #

    def _prepare_preview(self):
        """
        Resolve raw rows to (app_name, date_obj, minutes) using saved_mapping.
        Skips rows whose applicationId maps to "Skip" or is unmapped.
        Also detects duplicates against the current DB.
        """
        known_app_names = set(fetch_app_names())
        resolved = []
        skipped_ids = set()

        for app_id, date_obj, minutes in self._raw_rows:
            app_name = self.saved_mapping.get(app_id)
            if not app_name or app_name not in known_app_names:
                skipped_ids.add(app_id)
                continue
            resolved.append((app_name, date_obj, minutes))

        self._skipped_ids = skipped_ids

        # Check for duplicates in target DB
        duplicates = self._find_duplicates(resolved)
        if duplicates:
            lines = "\n".join(
                f"  • {app} on {d.strftime('%d/%m/%Y')}"
                for app, d in sorted(duplicates)[:10]
            )
            if len(duplicates) > 10:
                lines += f"\n  … and {len(duplicates) - 10} more"
            messagebox.showerror(
                "Duplicate Entries Found",
                f"Import cancelled — the following entries already exist in your database:\n\n{lines}\n\n"
                "Please choose a different date range or remove the existing records first.",
                parent=self.dialog
            )
            self.preview_data = []
            return

        self.preview_data = resolved

    def _find_duplicates(self, resolved: list) -> list:
        """Return list of (app_name, date) tuples that already exist in the DB."""
        if not resolved:
            return []

        # Build a set of (app_id, date_str) already in the DB
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.name, sr.date
                FROM screen_time_records sr
                JOIN apps a ON sr.app_id = a.id
            ''')
            existing = {(row[0], row[1]) for row in cursor.fetchall()}

        duplicates = []
        for app_name, date_obj, _ in resolved:
            date_str = date_obj.strftime('%Y-%m-%d')
            if (app_name, date_str) in existing:
                duplicates.append((app_name, date_obj))
        return duplicates

    # ------------------------------------------------------------------ #
    #  STEP 3 — Confirmation / Summary                                    #
    # ------------------------------------------------------------------ #

    def _build_step3(self):
        if not self.preview_data:
            # Duplicate check cancelled the import — stay on step 2 or step 1
            return

        self._clear_dialog()
        self.dialog.title("Import from SQLite — Step 3 of 3")

        ttk.Label(self.dialog, text="Confirm Import",
                  font=("Arial", 14, "bold")).pack(pady=(15, 5))

        # Summary stats
        app_names = sorted({r[0] for r in self.preview_data})
        total_entries = len(self.preview_data)
        total_minutes = sum(r[2] for r in self.preview_data)
        hours = total_minutes // 60
        mins = total_minutes % 60

        summary_frame = ttk.LabelFrame(self.dialog, text="Summary", padding=12)
        summary_frame.pack(fill='x', padx=15, pady=10)

        def row(label, value, r):
            ttk.Label(summary_frame, text=label, font=("Arial", 10, "bold")).grid(
                row=r, column=0, sticky='w', padx=5, pady=2)
            ttk.Label(summary_frame, text=value).grid(
                row=r, column=1, sticky='w', padx=10, pady=2)

        row("Date range:", f"{self._from_date.strftime('%d/%m/%Y')}  →  {self._to_date.strftime('%d/%m/%Y')}", 0)
        row("Entries to import:", str(total_entries), 1)
        row("Total time:", f"{hours} h {mins} min" if hours else f"{mins} min", 2)
        row("Apps included:", str(len(app_names)), 3)
        if self._skipped_ids:
            row("Skipped IDs:", f"{len(self._skipped_ids)} (unmapped)", 4)

        # App list
        apps_frame = ttk.LabelFrame(self.dialog, text="Apps Being Imported", padding=10)
        apps_frame.pack(fill='both', expand=True, padx=15, pady=5)

        canvas = tk.Canvas(apps_frame, height=120)
        sb = ttk.Scrollbar(apps_frame, orient='vertical', command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        for i, name in enumerate(app_names):
            app_rows = [r for r in self.preview_data if r[0] == name]
            count = len(app_rows)
            total_mins = sum(r[2] for r in app_rows)
            hours = total_mins // 60
            mins = total_mins % 60
            time_str = f"{hours} h {mins} min" if hours else f"{mins} min"
            ttk.Label(inner, text=f"  {name}  ({count} {'entry' if count == 1 else 'entries'}, {time_str})").grid(
                row=i, column=0, sticky='w', padx=5, pady=1)

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(side='bottom', fill='x', padx=15, pady=10)
        back_target = self._build_step2 if self.unmatched_ids else self._build_step1
        ttk.Button(btn_frame, text="← Back", command=back_target).pack(side='left')
        ttk.Button(btn_frame, text="✔ Import", command=self._do_import).pack(side='right')

    # ------------------------------------------------------------------ #
    #  Final Import                                                       #
    # ------------------------------------------------------------------ #

    def _do_import(self):
        if not self.preview_data:
            return

        try:
            with sqlite3.connect(get_db_path()) as conn:
                cursor = conn.cursor()
                for app_name, date_obj, minutes in self.preview_data:
                    cursor.execute('SELECT id FROM apps WHERE name = ?', (app_name,))
                    result = cursor.fetchone()
                    if result:
                        cursor.execute('''
                            INSERT INTO screen_time_records (app_id, time_spent, date)
                            VALUES (?, ?, ?)
                        ''', (result[0], minutes, date_obj.strftime('%Y-%m-%d')))
                conn.commit()

            messagebox.showinfo(
                "Import Complete",
                f"Successfully imported {len(self.preview_data)} entries across "
                f"{len({r[0] for r in self.preview_data})} apps.",
                parent=self.dialog
            )
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self.dialog)

    # ------------------------------------------------------------------ #
    #  Utility                                                            #
    # ------------------------------------------------------------------ #

    def _clear_dialog(self):
        for widget in self.dialog.winfo_children():
            widget.destroy()