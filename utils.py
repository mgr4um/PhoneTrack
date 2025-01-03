from datetime import datetime

def format_date_for_display(date_str):
    """Convert YYYY-MM-DD to DD/MM/YYYY"""
    if isinstance(date_str, str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        date_obj = date_str
    return date_obj.strftime('%d/%m/%Y')

def format_date_for_db(date_str):
    """Convert DD/MM/YYYY to YYYY-MM-DD"""
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        # If the input is already in YYYY-MM-DD format
        return date_str 

def format_time_display(minutes):
    """Format minutes into hours and minutes display"""
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    remaining_mins = minutes % 60
    if remaining_mins == 0:
        return f"{hours} h"
    return f"{hours} h {remaining_mins} min" 