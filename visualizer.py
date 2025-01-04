import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import matplotlib.pyplot as plt
from utils import format_date_for_display
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import calendar
from database import fetch_categories

# Constants for visualization
INITIAL_ITEMS_SHOWN = 5      # Number of items shown initially in lists
ITEMS_PER_EXPANSION = 5      # Number of items added when clicking "Show More"
WINDOW_WIDTH = 960          # Main window width
WINDOW_HEIGHT = 800          # Main window height
CANVAS_WIDTH = 960           # Scrollable canvas width
CHART_SIZE = (9, 4)         # Size of the figure for charts (width, height)
TITLE_FONT = ("Arial", 16, "bold")
SUBTITLE_FONT = ("Arial", 14)
NORMAL_FONT = ("Arial", 10)
DATE_FORMAT = "dd/mm/yyyy"   # Format for date picker
TIME_SPANS = ["Day", "Week", "Month", "Year"]
PIE_CHART_THRESHOLD = 2.5      # Percentage threshold for grouping small values in pie chart

def format_time(minutes):
    """
    Convert minutes to a readable format with appropriate units
    Examples:
        90 -> '1 h 30 min'
        1500 -> '1 d 1 h'
        11000 -> '1 w 1 d 3 h'
    """
    if minutes == 0:
        return "0 min"

    weeks = minutes // (7 * 24 * 60)
    remaining_minutes = minutes % (7 * 24 * 60)
    
    days = remaining_minutes // (24 * 60)
    remaining_minutes = remaining_minutes % (24 * 60)
    
    hours = remaining_minutes // 60
    remaining_minutes = remaining_minutes % 60

    parts = []
    if weeks > 0:
        parts.append(f"{weeks} weeks")
    if days > 0:
        parts.append(f"{days} days")
    if hours > 0:
        parts.append(f"{hours} h")
    if remaining_minutes > 0 and not (weeks > 0 or days > 0):  # Only show minutes if less than a day
        parts.append(f"{remaining_minutes} min")

    # If no parts (shouldn't happen with positive minutes)
    if not parts:
        return "0 min"

    # Return the formatted string with appropriate units
    return " ".join(parts)

def format_autopct(value, total_minutes):
    """Format the value inside pie chart to show both percentage and time"""
    minutes = int(total_minutes * value / 100)
    return f'{format_time(minutes)}\n({value:.1f}%)'

def get_date_range(date, span):
    """Get start and end dates for the selected time span"""
    if span == "Day":
        return date, date
    elif span == "Week":
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
    elif span == "Month":
        start = date.replace(day=1)
        if date.month == 12:
            end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
    else:  # Year
        start = date.replace(month=1, day=1)
        end = date.replace(month=12, day=31)
    return start, end

def format_date_range(start_date, end_date, span):
    """Format date range for display"""
    if span == "Day":
        return format_date_for_display(start_date)
    elif span == "Week":
        return f"Week {start_date.isocalendar()[1]}, {start_date.year}"
    elif span == "Month":
        return start_date.strftime("%B %Y")
    else:  # Year
        return str(start_date.year)

def create_scrollable_frame(parent):
    # Create a container frame
    container = ttk.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    # Create a canvas
    canvas = tk.Canvas(container, width=960)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

    # Create the scrollable frame inside the canvas
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # Create window inside canvas to hold the frame
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Configure canvas size when window is resized
    def on_frame_configure(event):
        canvas.configure(width=container.winfo_width())
    container.bind('<Configure>', on_frame_configure)

    # Pack scrollbar and canvas
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Add mousewheel scrolling with direction control
    def _on_mousewheel(event):
        # Get current scroll position
        current_pos = canvas.yview()
        
        # Scrolling up (event.delta > 0) only if not at top
        # Scrolling down (event.delta < 0) always allowed
        if event.delta < 0 or current_pos[0] > 0:
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    return scrollable_frame

def display_visualization(data):
    class Visualizer:
        def __init__(self):
            self.show_percentage = False
            self.display_var = tk.BooleanVar(value=False)

        def toggle_display_mode(self):
            self.show_percentage = not self.show_percentage
            update_visualization()

        def format_value(self, value, total_minutes):
            minutes = int(total_minutes * value / 100)
            if self.show_percentage:
                return f'{value:.1f}%'
            else:
                return format_time(minutes)

    viz = Visualizer()
    # Create DataFrame
    df = pd.DataFrame(data, columns=["App Name", "Category Name", "Time Spent", "Date"])
    df["Date"] = pd.to_datetime(df["Date"])
    current_date = [df["Date"].max()]  # Use list to make it mutable
    time_spans = ["Day", "Week", "Month", "Year"]
    current_span = ["Day"]  # Use list to make it mutable

    def create_expandable_list(parent, items, title, total_time):
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        items_frame = ttk.Frame(frame)
        items_frame.pack(fill=tk.X, expand=True)
        
        shown_items = [INITIAL_ITEMS_SHOWN]
        
        def show_items():
            # Clear current items
            for widget in items_frame.winfo_children():
                widget.destroy()
            
            # Show items up to current limit
            for item, time in list(items.items())[:shown_items[0]]:
                percentage = (time / total_time) * 100
                ttk.Label(items_frame, 
                         text=f"{item}: {format_time(time)} ({percentage:.1f}%)", 
                         font=NORMAL_FONT).pack(anchor="w")
            
            # Show "Show More" button if there are more items
            if shown_items[0] < len(items):
                def show_more():
                    shown_items[0] += ITEMS_PER_EXPANSION
                    show_items()
                
                remaining = len(items) - shown_items[0]
                ttk.Button(items_frame, 
                          text=f"Show More ({remaining} remaining)", 
                          command=show_more).pack(pady=5)
        
        show_items()
        return frame

    def update_visualization():
        start_date, end_date = get_date_range(current_date[0], current_span[0])
        filtered_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

        # Clear previous data
        for widget in summary_frame.winfo_children():
            widget.destroy()

        # Calculate summaries
        total_time = filtered_df["Time Spent"].sum()
        apps_summary = filtered_df.groupby("App Name")["Time Spent"].sum().sort_values(ascending=False)
        categories_summary = filtered_df.groupby("Category Name")["Time Spent"].sum().sort_values(ascending=False)

        # Group small app percentages into "Other" (only for pie chart)
        total_apps_time = apps_summary.sum()
        main_apps = apps_summary[apps_summary/total_apps_time * 100 >= PIE_CHART_THRESHOLD]
        other_time = apps_summary[apps_summary/total_apps_time * 100 < PIE_CHART_THRESHOLD].sum()
        
        if other_time > 0:
            main_apps_pie = main_apps.copy()  # Create a copy for the pie chart
            main_apps_pie['Other'] = other_time
        else:
            main_apps_pie = main_apps

        # Create summary frames
        date_label = ttk.Label(summary_frame, 
                             text=f"Period: {format_date_range(start_date, end_date, current_span[0])}", 
                             font=TITLE_FONT)
        date_label.pack(pady=5)
        
        total_label = ttk.Label(summary_frame, 
                               text=f"Total Screen Time: {format_time(total_time)}", 
                               font=SUBTITLE_FONT)
        total_label.pack(pady=5)

        # Create two columns for apps and categories summaries
        columns_frame = ttk.Frame(summary_frame)
        columns_frame.pack(fill=tk.X, expand=True, padx=10, anchor="n")

        # Apps summary (left column) - use full apps_summary
        apps_frame = create_expandable_list(columns_frame, apps_summary, "Top Apps", total_time)
        apps_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, anchor="n")

        # Categories summary (right column)
        categories_frame = create_expandable_list(columns_frame, categories_summary, "Top Categories", total_time)
        categories_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, anchor="n")

        # Update the plots
        for ax in axs:
            ax.clear()

        # Apps pie chart with grouped small percentages
        main_apps_pie.plot(
            kind='pie',
            ax=axs[0],
            autopct=lambda pct: viz.format_value(pct, main_apps_pie.sum()),
            title='Time by App',
            ylabel=''
        )

        # Get category colors
        categories = fetch_categories()
        category_colors = {name: color for name, color in categories}

        # Categories pie chart with colors
        categories_summary.plot(
            kind='pie',
            ax=axs[1],
            autopct=lambda pct: viz.format_value(pct, categories_summary.sum()),
            title='Time by Category',
            ylabel='',
            colors=[category_colors.get(cat, '#808080') for cat in categories_summary.index]
        )

        plt.tight_layout()
        canvas.draw()

    def change_time_span(event):
        current_span[0] = span_combobox.get()
        update_visualization()

    def previous_period():
        if current_span[0] == "Day":
            current_date[0] -= timedelta(days=1)
        elif current_span[0] == "Week":
            current_date[0] -= timedelta(weeks=1)
        elif current_span[0] == "Month":
            if current_date[0].month == 1:
                current_date[0] = current_date[0].replace(year=current_date[0].year - 1, month=12)
            else:
                current_date[0] = current_date[0].replace(month=current_date[0].month - 1)
        else:  # Year
            current_date[0] = current_date[0].replace(year=current_date[0].year - 1)
        update_date_picker()
        update_visualization()

    def next_period():
        if current_date[0] >= df["Date"].max():
            return
        if current_span[0] == "Day":
            current_date[0] += timedelta(days=1)
        elif current_span[0] == "Week":
            current_date[0] += timedelta(weeks=1)
        elif current_span[0] == "Month":
            if current_date[0].month == 12:
                current_date[0] = current_date[0].replace(year=current_date[0].year + 1, month=1)
            else:
                current_date[0] = current_date[0].replace(month=current_date[0].month + 1)
        else:  # Year
            current_date[0] = current_date[0].replace(year=current_date[0].year + 1)
        update_date_picker()
        update_visualization()

    # Create a Tkinter Window
    window = tk.Toplevel()
    window.title("Screen Time Analysis")
    window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    window.resizable(False, True)  # Only allow vertical resizing

    # Create main scrollable container
    main_container = create_scrollable_frame(window)

    # Navigation Frame
    nav_frame = ttk.Frame(main_container, padding=10)
    nav_frame.pack(fill=tk.X)

    # Left side: Time span selection and date picker
    left_nav = ttk.Frame(nav_frame)
    left_nav.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Time span selection
    span_frame = ttk.Frame(left_nav)
    span_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
    ttk.Label(span_frame, text="Time Span:").pack(side=tk.LEFT, padx=5)
    span_combobox = ttk.Combobox(span_frame, values=time_spans, state="readonly", width=10)
    span_combobox.set(current_span[0])
    span_combobox.pack(side=tk.LEFT, padx=5)
    span_combobox.bind('<<ComboboxSelected>>', change_time_span)

    # Date navigation
    date_frame = ttk.Frame(left_nav)
    date_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

    def update_date_picker(*args):
        date_picker.set_date(current_date[0])

    def on_date_change():
        selected_date = date_picker.get_date()
        current_date[0] = datetime(selected_date.year, selected_date.month, selected_date.day)
        update_visualization()

    # Date picker
    date_picker = DateEntry(date_frame, width=12, 
                          year=current_date[0].year,
                          month=current_date[0].month,
                          day=current_date[0].day,
                          date_pattern=DATE_FORMAT,
                          firstweekday='monday')
    date_picker.pack(side=tk.LEFT, padx=5)
    date_picker.bind("<<DateEntrySelected>>", lambda e: on_date_change())

    # Quick navigation buttons
    def jump_to_today():
        current_date[0] = datetime.now()
        update_date_picker()
        update_visualization()

    def jump_to_start():
        current_date[0] = df["Date"].min()
        update_date_picker()
        update_visualization()

    def jump_to_end():
        current_date[0] = df["Date"].max()
        update_date_picker()
        update_visualization()

    quick_nav_frame = ttk.Frame(date_frame)
    quick_nav_frame.pack(side=tk.LEFT, padx=5)

    ttk.Button(quick_nav_frame, text="Today", 
               command=jump_to_today).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_nav_frame, text="Start", 
               command=jump_to_start).pack(side=tk.LEFT, padx=2)
    ttk.Button(quick_nav_frame, text="End", 
               command=jump_to_end).pack(side=tk.LEFT, padx=2)

    # Right side: Previous/Next navigation
    right_nav = ttk.Frame(nav_frame)
    right_nav.pack(side=tk.RIGHT, padx=5)

    ttk.Button(right_nav, text="◀", command=previous_period).pack(side=tk.LEFT, padx=2)
    ttk.Button(right_nav, text="▶", command=next_period).pack(side=tk.LEFT, padx=2)

    # Frame for Summary
    summary_frame = ttk.Frame(main_container, padding=10)
    summary_frame.pack(fill=tk.X)

    # Frame for Plots
    plot_frame = ttk.Frame(main_container, padding=10)
    plot_frame.pack(fill=tk.BOTH, expand=True)

    # Create figure with two pie charts side by side - smaller size
    fig, axs = plt.subplots(1, 2, figsize=CHART_SIZE)
    
    # Embed Plot in Tkinter
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10)  # Added padding

    # Add checkbox to nav_frame
    display_checkbox = ttk.Checkbutton(
        nav_frame, 
        text="Show percentages", 
        variable=viz.display_var,
        command=viz.toggle_display_mode
    )
    display_checkbox.state(['!selected', '!alternate'])
    display_checkbox.pack(side=tk.RIGHT, padx=10)

    # Initialize Visualization
    update_visualization()
