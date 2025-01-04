import sqlite3
from config import get_db_config

def get_db_path():
    """Get the current database path"""
    return get_db_config()['name']

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # Categories table with color column
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#808080'  -- Default gray color
        )
    ''')
    
    # Apps table with foreign key to categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category_id INTEGER NOT NULL,
            is_favorite BOOLEAN DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Screen time records table with foreign key to apps
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS screen_time_records (
            id INTEGER PRIMARY KEY,
            app_id INTEGER NOT NULL,
            time_spent INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (app_id) REFERENCES apps (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_category(name, color='#808080'):
    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO categories (name, color) VALUES (?, ?)', (name, color))
            category_id = cursor.lastrowid
            conn.commit()
            return category_id
    except sqlite3.IntegrityError:
        # If category already exists, fetch its id
        return get_category_id(name)

def update_category_color(name, color):
    """Update category color"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE categories SET color = ? WHERE name = ?', (color, name))
        conn.commit()

def add_app(name, category_id):
    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO apps (name, category_id, is_favorite) 
                VALUES (?, ?, 0)
            ''', (name, category_id))
            app_id = cursor.lastrowid
            conn.commit()
            return app_id
    except sqlite3.IntegrityError:
        # If app already exists, fetch its id
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM apps WHERE name = ?', (name,))
            result = cursor.fetchone()
            return result[0] if result else None

def add_screen_time(app_id, time_spent, date):
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO screen_time_records (app_id, time_spent, date)
            VALUES (?, ?, ?)
        ''', (app_id, time_spent, date))
        conn.commit()

def fetch_screen_time_data():
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                a.name as app_name,
                c.name as category_name,
                sr.time_spent,
                sr.date
            FROM screen_time_records sr
            JOIN apps a ON sr.app_id = a.id
            JOIN categories c ON a.category_id = c.id
        ''')
        return cursor.fetchall()

def fetch_apps():
    """Fetch apps ordered by favorite status and then name"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, is_favorite 
            FROM apps 
            ORDER BY is_favorite DESC, name
        ''')
        return cursor.fetchall()

def fetch_app_names():
    """Fetch just app names"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM apps ORDER BY name')
        return [row[0] for row in cursor.fetchall()]

def get_category_id(name):
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
        result = cursor.fetchone()
        return result[0] if result else None

def clear_screen_time_data():
    """Remove all screen time records"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM screen_time_records')
        conn.commit()

def insert_sample_data():
    """Insert sample screen time data for the entire year 2024"""
    from datetime import datetime, timedelta
    import random

    # Generate dates for all of 2024
    start_date = datetime(2024, 1, 1)
    dates = [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(366)]  # 2024 is leap year

    # Define apps and their typical usage patterns (minutes)
    app_patterns = {
        "Instagram": {
            "weekday": (30, 60),    # (min, max) minutes on weekdays
            "weekend": (45, 90)     # (min, max) minutes on weekends
        },
        "X": {
            "weekday": (15, 30),
            "weekend": (20, 45)
        },
        "Clash of Clans": {
            "weekday": (45, 90),
            "weekend": (90, 180)
        },
        "Clash Royale": {
            "weekday": (30, 60),
            "weekend": (60, 120)
        },
        "Brawl Stars": {
            "weekday": (30, 75),
            "weekend": (60, 150)
        }
    }

    # Generate sample data
    sample_data = {}
    for app_name, patterns in app_patterns.items():
        sample_data[app_name] = []
        for date_str in dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            is_weekend = date_obj.weekday() >= 5
            
            # Select appropriate pattern
            pattern = patterns["weekend"] if is_weekend else patterns["weekday"]
            
            # Generate random time within pattern range
            time_spent = random.randint(pattern[0], pattern[1])
            
            # Add some randomness to make data more realistic
            if random.random() < 0.1:  # 10% chance of unusually high usage
                time_spent = int(time_spent * 1.5)
            elif random.random() < 0.1:  # 10% chance of unusually low usage
                time_spent = int(time_spent * 0.5)
                
            sample_data[app_name].append((time_spent, date_str))
    
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        
        for app_name, time_records in sample_data.items():
            # Get app_id
            cursor.execute('SELECT id FROM apps WHERE name = ?', (app_name,))
            result = cursor.fetchone()
            if result:
                app_id = result[0]
                # Insert time records for this app
                for time_spent, date in time_records:
                    cursor.execute('''
                        INSERT INTO screen_time_records (app_id, time_spent, date)
                        VALUES (?, ?, ?)
                    ''', (app_id, time_spent, date))
        
        conn.commit()

def fetch_categories():
    """Fetch all categories with their colors"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, color 
            FROM categories 
            GROUP BY name 
            ORDER BY name
        ''')
        return cursor.fetchall()

def toggle_app_favorite(app_name):
    """Toggle favorite status for an app"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE apps 
            SET is_favorite = NOT is_favorite 
            WHERE name = ?
        ''', (app_name,))
        conn.commit()

def fetch_apps_with_categories():
    """Fetch apps with categories, ordered by favorite status and then name"""
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.name, a.is_favorite, c.name as category_name
            FROM apps a
            JOIN categories c ON a.category_id = c.id
            ORDER BY a.is_favorite DESC, a.name
        ''')
        return cursor.fetchall()
