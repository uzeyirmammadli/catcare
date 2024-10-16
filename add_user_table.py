import sqlite3

def add_user_table():
    conn = sqlite3.connect('cats.db')
    cursor = conn.cursor()
    
    # Check if user table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
    if cursor.fetchone() is None:
        # Create user table
        cursor.execute("""
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """)
        print("User table created successfully.")
    else:
        print("User table already exists.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_user_table()