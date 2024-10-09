import sqlite3
from datetime import datetime
import uuid
import random

DATABASE_NAME = 'cats.db'


# DATA
def initialize(db):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS cases
                          (id TEXT PRIMARY KEY, photo TEXT, location TEXT, need TEXT, 
                           status TEXT, created_at TEXT, updated_at TEXT)''')
        conn.commit()


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
    status = status.upper()  # Convert status to uppercase for consistency
    print(status)
    if status not in ["OPEN", "RESOLVED"]:
        raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE status=?', (status,))
        cases = cursor.fetchall()
        return [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], row)) for row in cases]

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
        
def search_and_filter_cases(db, search=None, location=None, status=None, need=None, created_at=None):
    query = 'SELECT * FROM cases WHERE 1=1'  # Base query
    params = []

    if search:
        query += ' AND (location LIKE ? OR need LIKE ?)'
        search_param = f"%{search}%"
        params.extend([search_param, search_param])

    if location:
        query += ' AND location LIKE ?'
        params.append(f"%{location}%")

    if status:
        query += ' AND status = ?'
        params.append(status)

    if need:
        query += ' AND need LIKE ?'
        params.append(f"%{need}%")

    if created_at:
        query += ' AND created_at >= ?'
        params.append(created_at)

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        cases = cursor.fetchall()
        case_dicts = [dict(zip(['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'], case)) for case in cases]
        return case_dicts
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
