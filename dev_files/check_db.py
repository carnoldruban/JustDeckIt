import sqlite3

def check_database():
    """Check existing database structure and data."""
    conn = sqlite3.connect('blackjack_data.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Existing tables:", [t[0] for t in tables])
    
    # Check each table for data
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} records")
        
        # Show sample data if exists
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            samples = cursor.fetchall()
            print(f"    Sample: {samples[0] if samples else 'No data'}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
