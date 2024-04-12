import sqlite3
import os
from datetime import datetime
import uuid
import random

DATABASE_NAME = 'cats.db'

# DATA
def initialize(db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS cases
                      (id TEXT PRIMARY KEY, photo TEXT, location TEXT, need TEXT, 
                       status TEXT, created_at TEXT, updated_at TEXT)''')
    conn.commit()
    conn.close()


def create_case(db, report):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO cases (id, photo, location, need, status, created_at, updated_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                      (report['id'], report['photo'], report['location'], report['need'], 
                       report['status'], report['created_at'], report['updated_at']))
    conn.commit()
    conn.close()


def update_case(db, case_id, updated_case):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_case['updated_at'] = current_time

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''UPDATE cases SET photo=?, location=?, need=?, status=?, updated_at=?
                      WHERE id=?''', 
                      (updated_case['photo'], updated_case['location'], updated_case['need'], 
                       updated_case['status'], updated_case['updated_at'], case_id))
    conn.commit()
    conn.close()
    return True

# def update_case(db, case_dict):
#     conn = sqlite3.connect(db)
#     cursor = conn.cursor()

#     # Construct the update SQL statement with placeholders for values
#     sql = """
#         UPDATE cases 
#         SET photo = ?, location = ?, need = ?, status = ?, updated_at = ?
#         WHERE id = ?
#     """
#     values = (case_dict['photo'], case_dict['location'], case_dict['need'],
#               case_dict['status'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#               case_dict['id'])

#     # Execute the update statement with the values
#     cursor.execute(sql, values)

#     # Assuming successful update returns True, otherwise False
#     return cursor.rowcount > 0  # Check if at least one row was updated

#     conn.close()

def delete_cat(db, case_id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cases WHERE id=?', (case_id,))
    conn.commit()
    conn.close()


def select_cats_by_status(db, status):
    status = status.upper()  # Convert status to uppercase for consistency

    if status not in ["OPEN", "RESOLVED"]:
        raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")  # Raise an exception for invalid status

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cases WHERE status=?', (status,))
    cases = cursor.fetchall()
    conn.close()
    return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in cases]



def scan_case(db, location):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cases WHERE location=?', (location,))
    found = cursor.fetchall()
    conn.close()
    return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in found]


def get_all_cases(db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cases')
    all_cases = cursor.fetchall()
    conn.close()
    return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in all_cases]


def resolve_case(db, case_id):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cases WHERE id=?', (case_id,))
    case = cursor.fetchone()
    if case:
        case_dict = dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], case))
        case_dict['status'] = 'RESOLVED'
        if update_case(db, case_id, case_dict):
            return case_dict
    conn.close()
    
# def resolve_case(db, case_id):
#     conn = sqlite3.connect(db)
#     cursor = conn.cursor()

#     # Fetch the case by ID
#     cursor.execute('SELECT * FROM cases WHERE id=?', (case_id,))
#     case = cursor.fetchone()

#     if case:
#         case_dict = dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], case))
#         case_dict['status'] = 'RESOLVED'

#         # Implement update_case function to update the database with the modified dictionary
#         if update_case(db, case_dict):
#             conn.commit()  # Commit the changes if update is successful
#             return case_dict
#         else:
#             # Handle update failure (consider logging the error)
#             return False  # Or provide a specific error message
#     else:
#         # Handle case not found (consider logging or returning a specific error message)
#         return None

#     conn.close()

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
