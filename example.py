print("1. Report case\n2. Scan area for cats\n3. Resolve case")
command = input("What would you like to do?")

if command == "1":
    result = f'You chose reporting case'
elif command == "2":
    result = f'You chose scanning area for cats'
elif command == "3":
    result = f'You chose resolving case'
else:
    result = f'Your command is unknown'
print(result)


