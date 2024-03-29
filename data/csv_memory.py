import uuid
import csv
import os
from datetime import datetime
import random

#DATA
def initialize(db):
    try:
        if not os.path.exists(db):
            with open(db, 'w') as csvfile:
                fieldnames = ['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            return os.path.isfile(db)
    except (IOError, OSError) as e:
        print(f"Error writing to database: {e}")


def create_case(db, report):
    fieldnames = [
        'id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'
    ]
    try:
        with open(db, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(report)
    except (IOError, OSError) as e:
        print(f"Error writing to database: {e}")


def update_case(db,id,updated_case):
    data = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(db, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['id'] == id:
                    updated_case['updated_at'] = current_time
                    row.update(updated_case)
                data.append(row)
    except (IOError, OSError) as e:
        print(f"Error writing to database: {e}")

    try:
        with open(db, 'w') as csvfile:
            fieldnames = [
                'id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
            return True
    except (IOError, OSError) as e:
        print(f"Error writing to database: {e}")


def scan_case(db, location):
    all_cases = get_all_cases(db)
    found = []
    for row in all_cases:
        if row['location'] == location:
            found.append(row)
        return found


def get_all_cases(db):
    try:
        with open(db, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)
    except (IOError, OSError) as e:
        print(f"Error writing to database: {e}")
def resolve_case(db, id):
  all_cases = get_all_cases(db)
  for row in all_cases:
      if row['id'] == id:
        row['status'] = 'RESOLVED'
        if update_case(db, id, row):
          return row
        
    
#SEED
def seed():
  locations = ['Nasirov', 'Rajabli', 'Mayakovski']
  current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  for i in range(1, 10):
    create_case(
      'cats.csv', {
        'id': f'{str(uuid.uuid4())}',
        'photo': 'https://picsum.photos/200/300',
        'location': random.choice(locations),
        'need': 'Medicine',
        'status': 'OPEN',
        'created_at': current_time,
        'updated_at': current_time
      }
    )

