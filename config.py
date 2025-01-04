# Database configurations
DEBUG_MODE = True  # Switch between debug and production

DB_CONFIG = {
    'debug': {
        'name': 'screen_time_debug.db',
        'sample_data': True     # Whether to load sample data
    },
    'production': {
        'name': 'screen_time.db',
        'sample_data': False
    }
}

def get_db_config():
    """Get current database configuration based on mode"""
    return DB_CONFIG['debug'] if DEBUG_MODE else DB_CONFIG['production'] 