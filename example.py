import random
import csv
import os
from datetime import datetime


#DATA
def initialize(db):
  if not os.path.exists(db):
    with open(db, 'w') as csvfile:
        fieldnames = ['id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
  return os.path.isfile(db)

def create_case(db, report):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report['created_at'] = current_time
    report['updated_at'] = current_time
    
    fieldnames = [
        'id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'
    ]
    with open(db, 'a') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(report)

def update_case(db,id,updated_case):
  data = []
  with open(db, 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
      if row['id'] == id:
        row.update(updated_case)
      data.append(row)
  with open(db, 'w') as csvfile:
    fieldnames = [
      'id', 'photo', 'location', 'need', 'status', 'created_at', 'updated_at'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
      writer.writerow(row)
  return True
  


def scan_case(db, location):
  all_cases = get_all_cases(db)
  found = []
  for row in all_cases:
    if row['location'] == location:
      found.append(row)
  return found


def get_all_cases(db):
  with open(db, 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    return list(reader)

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
  for i in range(1, 10):
    create_case(
      'cats.csv', {
        'id': f'{random.random()}',
        'photo': 'https://picsum.photos/200/300',
        'location': random.choice(locations),
        'need': 'Medicine',
        'status': 'OPEN'
      }
    )




# VIEW
def present(cases):
  for case in cases:
    print(f"ID: {case['id']} | Photo: {case['photo']} | Location: {case['location']}")  

#Inputs
def report_inputs():
  photo  = input("A photo about case\t")
  area   = input("An area name to tag\t")
  need = input("What should be done?\t")
  return {'photo': photo, 'area': area, 'need': need}

def scan_inputs():
    area   = input("An area name to tag\t")
    return area

def resolve_inputs():
    case_id = input("Case id to resolve\t")
    return case_id


#Entity
def build_report(r):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        'id': f'{random.random()}',
        'photo': r['photo'],
        'location': r['area'],
        'need': r['need'],
        'status': 'OPEN',
        'created_at': current_time
    }    


#BOOT
db_created = initialize('cats.csv')
x = input('Do you want to seed the database? (y/n)')
if x == 'y':
  seed()

#PROGRAM
while True:
  print("1. Report case\n2. Scan area for cats\n3. Resolve case")
  command = input("What would you like to do?")
  if command == "1":
    print('You chose reporting case')
    
    r = report_inputs()
    report = build_report(r)
    create_case('cats.csv', report)
  elif command == "2":
    print('You chose scanning area for cats')
    area = scan_inputs()
    found = scan_case('cats.csv', area)
    present(found)
  elif command == "3":
    case_id = resolve_inputs()
    result = resolve_case('cats.csv', case_id)
    present([result])
  else:
    print("Invalid command")
  command = input("Do you want to proceed or quit? (p/q)")
  if command == 'p':
    continue
  else:
    print('Bye')
    break