from data.sqlite_memory import initialize, create_case, scan_case, resolve_case, seed
from domain.view import build_report, present
from port.inputs import report_inputs, scan_inputs, resolve_inputs
import sys

#BOOT
# db_created = initialize('cats.csv')
db_path = 'cats.db'
db_created = initialize('cats.db')
x = input('Do you want to seed the database? (y/n)')
if x == 'y':
  seed(db_path)

#PROGRAM
try:
    while True:
        print("1. Report case\n2. Scan area for cats\n3. Resolve case")
        command = input("What would you like to do?")
        if command == "1":
            print('You chose reporting case')
            r = report_inputs()
            report = build_report(r)
            create_case('cats.db', report)
        elif command == "2":
            print('You chose scanning area for cats')
            area = scan_inputs()
            found = scan_case('cats.db', area)
            present(found)
        elif command == "3":
            case_id = resolve_inputs()
            result = resolve_case('cats.db', case_id)
            present([result])
        else:
            print("Invalid command")
        command = input("Do you want to proceed or quit? (p/q)")
        if command == 'p':
            continue
        else:
            print('Bye')
            break
except Exception as e:
    print(f"An unexpected error occurred: {e}")