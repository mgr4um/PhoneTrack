import tkinter as tk
from tkinter import ttk
from datetime import datetime
from utils import format_date_for_display

def set_date_to_today(date_entry):
    today = format_date_for_display(datetime.today().strftime('%Y-%m-%d'))
    date_entry.delete(0, tk.END)
    date_entry.insert(0, today)

def filter_combobox(event, combobox, apps):
    value = event.widget.get()
    if value == '':
        combobox['values'] = [app['name'] for app in apps]
    else:
        data = []
        for app in apps:
            if value.lower() in app['name'].lower():
                data.append(app['name'])
        combobox['values'] = data

def create_input_frame(root, submit_data, visualize_data, apps):
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    ttk.Label(main_frame, text="App Name:").grid(row=0, column=0, pady=5, sticky=tk.W)
    app_name_var = tk.StringVar()
    app_name_combobox = ttk.Combobox(main_frame, textvariable=app_name_var, values=[app['name'] for app in apps], state="normal", width=30)
    app_name_combobox.grid(row=0, column=1, pady=5)
    app_name_combobox.bind('<KeyRelease>', lambda event: filter_combobox(event, app_name_combobox, apps))

    ttk.Label(main_frame, text="Time Spent (minutes):").grid(row=1, column=0, pady=5, sticky=tk.W)
    time_spent_entry = ttk.Entry(main_frame, width=30)
    time_spent_entry.grid(row=1, column=1, pady=5)

    ttk.Label(main_frame, text="Date (DD/MM/YYYY):").grid(row=2, column=0, pady=5, sticky=tk.W)
    date_entry = ttk.Entry(main_frame, width=30)
    date_entry.grid(row=2, column=1, pady=5)

    ttk.Button(main_frame, text="Set Date to Today", command=lambda: set_date_to_today(date_entry)).grid(row=2, column=2, padx=5)

    ttk.Button(main_frame, text="Submit", command=submit_data).grid(row=3, column=0, pady=10, sticky=tk.W)
    ttk.Button(main_frame, text="Visualize Data", command=visualize_data).grid(row=3, column=1, pady=10, sticky=tk.E)

    return app_name_combobox, time_spent_entry, date_entry