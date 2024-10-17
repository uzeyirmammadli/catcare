import sqlite3
from datetime import datetime
import uuid
import random
import logging
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DATABASE_NAME = 'cats.db'


# DATA
def initialize(db):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           username TEXT NOT NULL UNIQUE,
                           password_hash TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS cases
                          (id TEXT PRIMARY KEY, photo TEXT, location TEXT, need TEXT, 
                           status TEXT, created_at TEXT, updated_at TEXT)''')
        conn.commit()
        print("Database tables created.")

def create_test_user(db):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        
        # Check if the test user already exists
        cursor.execute("SELECT * FROM user WHERE username = ?", ('testuser',))
        existing_user = cursor.fetchone()
        
        if existing_user is None:
            hashed_password = generate_password_hash('testpassword')
            cursor.execute('''INSERT INTO user (username, password_hash)
                              VALUES (?, ?)''', ('testuser', hashed_password))
            conn.commit()
            print("Test user created.")
        else:
            
            print("Test user already exists.")
def create_case(db, report):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO cases (id, photo, location, need, status, created_at, updated_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (report['id'], report['photo'], report['location'], report['need'],
                        report['status'], report['created_at'], report['updated_at']))
        conn.commit()


def update_case(db, case_id, updated_case):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_case['updated_at'] = current_time

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('''UPDATE cases SET photo=?, location=?, need=?, status=?, updated_at=?
                          WHERE id=?''',
                       (updated_case['photo'], updated_case['location'], updated_case['need'],
                        updated_case['status'], updated_case['updated_at'], case_id))
        conn.commit()


def delete_cat(db, case_id):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cases WHERE id=?', (case_id,))
        conn.commit()

def select_cats_by_status(db, status):
    logger.debug(f"Selecting cats with status: {status} from database: {db}")
    status = status.upper()
    if status not in ["OPEN", "RESOLVED"]:
        raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")

    try:
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cases WHERE status=?', (status,))
            cases = cursor.fetchall()
            return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in cases]
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
# def select_cats_by_status(db, status):
#     logger.debug(f"Selecting cats with status: {status} from database: {db}")
#     print(f"Connecting to database: {db}") 
#     status = status.upper()  # Convert status to uppercase for consistency
#     print(status)
#     if status not in ["OPEN", "RESOLVED"]:
#         raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")

#     with sqlite3.connect(db) as conn:
#         cursor = conn.cursor()
#         cursor.execute('SELECT * FROM cases WHERE status=?', (status,))
#         cases = cursor.fetchall()
#         return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in cases]

def scan_case(db, location):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE location=?', (location,))
        found = cursor.fetchall()
        return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in found]


def get_all_cases(db):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases')
        all_cases = cursor.fetchall()
        return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in all_cases]

def get_case_by_id(db,case_id):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE id=?', (case_id,))
        case = cursor.fetchone()
        if case:
            case_dict = dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], case))
            return case_dict
        else:
            return None

def resolve_case(db, case_id):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE id=?', (case_id,))
        case = cursor.fetchone()
        if case:
            case_dict = dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], case))
            case_dict['status'] = 'RESOLVED'
            update_case(db, case_id, case_dict)
            return case_dict
        else:
            return None
        
# SEED
def seed(db):
    locations = ['Nasirov', 'Rajabli', 'Mayakovski']
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i in range(1, 10):
        create_case(db, {
            'id': str(uuid.uuid4()),
            'photo': 'https://picsum.photos/200/300',
            'location': random.choice(locations),
            'need': 'Medicine',
            'status': 'OPEN',
            'created_at': current_time,
            'updated_at': current_time
        })
