import random
import csv


print("1. Report case\n2. Scan area for cats\n3. Resolve case")
command = input("What would you like to do?")

if command == "1":
    print('You chose reporting case')
    photo = input("Photo ->")
    area = input("Area ->")
    need = input("Need ->")
    report = {
        'id': f'{random.random()}',
        'photo': photo,
        'area': area,
        'need': need,
        'status': 'OPEN'
    }
    with open('cats.csv', 'a', newline='') as csvfile:
        fieldnames = ['id', 'photo', 'area', 'need', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(report)
elif command == "2":
    print('You chose scanning area for cats')
    area = input("Area ->")
    with open('cats.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        found = False
        for row in reader:
            address = row['area']
            street = address.split(' ')[0]
            if street == area:
                print(f"ID: {row['id']}, Photo: {row['photo']}, Need: {row['need']}, Status: {row['status']}, Area: {row['area']}")
                found = True
        if not found:
            print("No cases found in the specified area.")
elif command == "3":
    temp_list = []
    case_id = input("ID -> ")
    with open('cats.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        found = False
        for row in reader:
            if row['id'] == case_id:
                row['status'] = 'RESOLVED'
                print(f"ID: {row['id']}, Photo: {row['photo']}, Need: {row['need']}, Status: {row['status']}, Area: {row['area']}")
                found = True
                temp_list.append(row)
        if not found:
            print("No cases found with this id.")
    with open('cats.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'photo', 'area', 'need', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        for row in temp_list:
            writer.writerow(row)
    result = f'You chose resolving case'
else:
    result = f'Your command is unknown'


