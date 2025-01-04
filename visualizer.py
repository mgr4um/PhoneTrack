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
HISTORY_CHART_SIZE = (9, 1)     # Size of the bar chart figure
HISTORY_PERIODS = 17         # Number of periods to show in history
EMPTY_PERIODS = 5           # Number of empty periods at the end of history chart
TITLE_FONT = ("Arial", 16, "bold")
SUBTITLE_FONT = ("Arial", 14)
NORMAL_FONT = ("Arial", 10)
DATE_FORMAT = "dd/mm/yyyy"   # Format for date picker
TIME_SPANS = ["Day", "Week", "Month", "Year"]
PIE_CHART_THRESHOLD = 2.5    # Percentage threshold for grouping small values in pie chart

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
            self.selected_category = None

        def toggle_display_mode(self):
            self.show_percentage = not self.show_percentage
            update_visualization()

        def format_value(self, value, total_minutes):
            # Round the percentage first to avoid floating point errors
            value = round(value, 1)
            # Calculate minutes and round to nearest integer
            minutes = round((total_minutes * value) / 100)
            
            if self.show_percentage:
                return f'{value:.1f}%'
            else:
                return format_time(minutes)

    viz = Visualizer()
    categories_summary = None  # Initialize at module level

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
                percentage = (time / total_time) * 100 if total_time > 0 else 0
                ttk.Label(items_frame, 
                         text=f"{item}: {format_time(time)} ({percentage:.1f}%)", 
                         font=NORMAL_FONT).pack(anchor="w")
            
            # Show buttons based on current state
            buttons_frame = ttk.Frame(items_frame)
            buttons_frame.pack(pady=5)
            
            if shown_items[0] < len(items):
                def show_more():
                    shown_items[0] += ITEMS_PER_EXPANSION
                    show_items()
                
                remaining = len(items) - shown_items[0]
                ttk.Button(buttons_frame, 
                          text=f"Show More ({remaining} remaining)", 
                          command=show_more).pack(side='left', padx=2)
            
            if shown_items[0] > INITIAL_ITEMS_SHOWN:
                def show_less():
                    shown_items[0] = INITIAL_ITEMS_SHOWN
                    show_items()
                
                ttk.Button(buttons_frame, text="Show Less", 
                          command=show_less).pack(side='left', padx=2)
        
        show_items()
        return frame

    def on_category_click(event):
        nonlocal categories_summary
        if event.inaxes == axs[1]:
            # Get the clicked wedge
            for wedge in axs[1].patches:
                contains, _ = wedge.contains(event)
                if contains:
                    # Get category from wedge label
                    clicked_category = wedge.get_label()
                    if viz.selected_category == clicked_category:
                        viz.selected_category = None
                    else:
                        viz.selected_category = clicked_category
                    update_visualization()
                    break

    def update_visualization():
        nonlocal categories_summary
        start_date, end_date = get_date_range(current_date[0], current_span[0])
        filtered_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
        filtered_df = filtered_df.copy()  # Create a copy to avoid SettingWithCopyWarning
        filtered_df["Time Spent"] = filtered_df["Time Spent"].astype(int)  # Force integer values

        # Clear previous data
        for widget in summary_frame.winfo_children():
            widget.destroy()

        # Calculate full categories summary first
        categories_summary = filtered_df.groupby("Category Name")["Time Spent"].sum().astype(int)
        categories_summary = categories_summary.sort_values(ascending=False)
        
        # Filter apps by selected category if one is selected
        if viz.selected_category:
            filtered_df = filtered_df[filtered_df["Category Name"] == viz.selected_category]
            apps_summary = filtered_df.groupby("App Name")["Time Spent"].sum().astype(int)
            apps_summary = apps_summary.sort_values(ascending=False)
            total_time = filtered_df["Time Spent"].sum()
        else:
            apps_summary = filtered_df.groupby("App Name")["Time Spent"].sum().astype(int)
            apps_summary = apps_summary.sort_values(ascending=False)
            total_time = filtered_df["Time Spent"].sum()

        # Group small app percentages into "Other" (only for pie chart)
        total_apps_time = apps_summary.sum()
        main_apps = apps_summary[apps_summary/total_apps_time * 100 >= PIE_CHART_THRESHOLD]
        other_time = apps_summary[apps_summary/total_apps_time * 100 < PIE_CHART_THRESHOLD].sum()
        
        if other_time > 0:
            main_apps_pie = main_apps.copy()
            main_apps_pie['Other'] = other_time
        else:
            main_apps_pie = main_apps

        # Create summary frames
        date_text = f"Period: {format_date_range(start_date, end_date, current_span[0])}"
        if viz.selected_category:
            date_text += f" (Filtered by: {viz.selected_category})"
        date_label = ttk.Label(summary_frame, text=date_text, font=TITLE_FONT)
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

        # Create explode array for pie chart - make selected category stand out
        explode = [0.1 if cat == viz.selected_category else 0 for cat in categories_summary.index]

        # Categories pie chart with colors and explode effect
        if len(categories_summary) > 0:  # Only plot if we have data
            colors = [category_colors.get(cat, '#808080') for cat in categories_summary.index]
            if colors:  # Only plot if we have colors
                categories_summary.plot(
                    kind='pie',
                    ax=axs[1],
                    autopct=lambda pct: viz.format_value(pct, categories_summary.sum()),
                    title='Time by Category',
                    ylabel='',
                    colors=colors,
                    explode=explode,
                    shadow=bool(viz.selected_category)
                )

        # Create bar chart - pass the full df instead of filtered_df
        create_history_chart(df, current_date[0], current_span[0], axs[2])

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

    def create_history_chart(df, start_date, span, ax):
        """Create a minimal bar chart showing total screen time for the last HISTORY_PERIODS"""
        dates = []
        current = start_date
        
        # Add the current date and future dates
        for i in range(EMPTY_PERIODS + 1):  # +1 to include current date
            dates.append(current)
            if span == "Day":
                current = current + timedelta(days=1)
            elif span == "Week":
                current = current + timedelta(weeks=1)
            elif span == "Month":
                year = current.year
                month = current.month + 1
                if month > 12:
                    year += 1
                    month = 1
                _, last_day = calendar.monthrange(year, month)
                day = min(current.day, last_day)
                current = current.replace(year=year, month=month, day=day)
            else:  # Year
                current = current.replace(year=current.year + 1)
        
        # Then go back from start_date to add past periods
        current = start_date
        for _ in range(HISTORY_PERIODS - EMPTY_PERIODS - 1):
            if span == "Day":
                current = current - timedelta(days=1)
            elif span == "Week":
                current = current - timedelta(weeks=1)
            elif span == "Month":
                year = current.year
                month = current.month - 1
                if month == 0:
                    year -= 1
                    month = 12
                _, last_day = calendar.monthrange(year, month)
                day = min(current.day, last_day)
                current = current.replace(year=year, month=month, day=day)
            else:  # Year
                current = current.replace(year=current.year - 1)
            dates.insert(0, current)
        
        # Create a copy of df and convert to int at the start
        df_copy = df.copy()
        df_copy["Time Spent"] = df_copy["Time Spent"].astype(int)
        
        # Get total screen time for each period
        totals = []
        for date in dates:
            period_start, period_end = get_date_range(date, span)
            period_data = df_copy[(df_copy["Date"] >= period_start) & (df_copy["Date"] <= period_end)]
            
            if viz.selected_category:
                period_data = period_data[period_data["Category Name"] == viz.selected_category]
            
            total_minutes = period_data["Time Spent"].sum()
            totals.append(total_minutes)

        # Avoid division by zero
        if not any(totals):  # If all totals are 0
            totals = [0] * len(dates)  # Keep the zeros but avoid the warning
        
        # Create minimal bar chart with thinner bars and highlight selected date
        bars = ax.bar(range(len(totals)), totals, width=0.5)
        
        # Set colors - darker for selected date
        for i, bar in enumerate(bars):
            if dates[i] == start_date:
                bar.set_color('#0d47a1')  # Much darker blue for selected date
            else:
                bar.set_color('#63a7e3')  # Lighter blue for other dates
        
        # Remove all decorations
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        # Add tooltips and click handling
        def hover(event):
            # Clear previous tooltip
            for txt in ax.texts:
                txt.remove()
            
            if event.inaxes == ax:
                for i, bar in enumerate(bars):
                    contains, _ = bar.contains(event)
                    if contains:
                        # Format date based on span
                        if span == "Day":
                            date_str = dates[i].strftime("%d/%m/%Y")
                        elif span == "Week":
                            date_str = f"Week {dates[i].isocalendar()[1]}, {dates[i].year}"
                        elif span == "Month":
                            date_str = dates[i].strftime("%B %Y")
                        else:  # Year
                            date_str = str(dates[i].year)
                        
                        # Use the exact same value without any additional processing
                        tooltip_text = f"{date_str}\n{format_time(totals[i])}"
                        ax.text(i, totals[i], tooltip_text,
                               ha='center', va='bottom',
                               fontsize=8,
                               bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
            event.canvas.draw_idle()

        def on_click(event):
            if event.inaxes == ax:
                for i, bar in enumerate(bars):
                    contains, _ = bar.contains(event)
                    if contains:
                        # Update current date to the clicked bar's date
                        current_date[0] = dates[i]
                        update_date_picker()
                        update_visualization()
                        break

        fig.canvas.mpl_connect('motion_notify_event', hover)
        fig.canvas.mpl_connect('button_press_event', on_click)

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

    # Create figure with two pie charts side by side and bar chart below
    fig = plt.figure(figsize=CHART_SIZE)
    
    # Create grid for subplots with smaller bar chart
    gs = fig.add_gridspec(2, 2, height_ratios=[4, 1])  # Changed ratio to make bar chart smaller
    
    # Create axes for pie charts (top row)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    
    # Create axis for bar chart (bottom row, spans both columns)
    ax3 = fig.add_subplot(gs[1, :])
    
    # Store axes in list for easy access
    axs = [ax1, ax2, ax3]
    
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

    # Connect the click handler once, outside of update_visualization
    fig.canvas.mpl_connect('button_press_event', on_category_click)

    # Initialize Visualization
    update_visualization()
