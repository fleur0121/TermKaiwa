import socket

HOST = "127.0.0.1"
PORT = 5555

expenses = []

"""
Handle ADD command: ADD|payer|amount|description
- Validate input format and values
- Store the expense in the expenses list
- Return a confirmation message

parts[0] = "ADD"
parts[1] = payer
parts[2] = amount
parts[3] = description (can contain '|', so join all remaining parts)
"""


def handle_add(parts):
    if len(parts) != 4:
        return "Format should be ADD|payer|amount|description"
    payer = parts[1].strip()
    amount = float(parts[2].strip())
    description = "|".join(parts[3:]).strip()

    if not payer:
        return "Payer cannot be empty."
    elif description == "":
        return "Description cannot be empty."
    try:
        amount = float(amount)
    except ValueError:
        return "Invalid amount. Please enter a number."
    if amount <= 0:
        return "Amount must be a positive number."

    expense = {"payer": payer, "amount": amount, "description": description}
    expenses.append(expense)
    return f"Expense added: {payer} paid ${amount:.2f} for {description}"


"""
Handle LIST command: LIST
- Return a formatted list of all recorded expenses
- If no expenses, return a message indicating that there are no expenses
"""


def handle_list():
    if len(expenses) == 0:
        return "No expenses recorded."
    lines = []
    for i, expense in enumerate(expenses, start=1):
        lines.append(
            f"{i}. {expense['payer']} paid ${expense['amount']:.2f} for {expense['description']}"
        )
    return "\n".join(lines)


"""
handle TOTAL command: TOTAL
- Calculate the total amount paid by each payer
"""


def handle_total():
    if len(expenses) == 0:
        return "No expenses recorded."
    totals = {}
    for expense in expenses:
        payer = expense["payer"]
        amount = expense["amount"]

        if payer not in totals:
            totals[payer] = 0.0
        totals[payer] += amount
    lines = []
    for payer in sorted(totals.keys()):
        lines.append(f"{payer}: ${totals[payer]:.2f}")
    return "\n".join(lines)


"""
Handle BALANCE command: BALANCE
- Calculate how much each person owes or is owed based on the total expenses
- Determine who owes whom and how much
"""


def handle_balance():
    if len(expenses) == 0:
        return "No expenses recorded."
    totals = {}
    for expense in expenses:
        payer = expense["payer"]
        amount = expense["amount"]

        if payer not in totals:
            totals[payer] = 0.0
        totals[payer] += amount

    people = list(totals.keys())
    if len(people) < 2:
        return "At least two people are needed to calculate balances."
    total_spent = sum(totals.values())
    share = total_spent / len(people)

    balances = {}
    for payer in people:
        balances[payer] = totals[payer] - share

    creditors = []
    debtors = []

    for payer, balance in balances.items():
        if balance > 0:
            creditors.append((payer, balance))
        elif balance < 0:
            debtors.append((payer, -balance))

    results = []
    i = 0
    j = 0

    while i < len(creditors) and j < len(debtors):
        debtor_name, debtor_amount = debtors[i]
        creditor_name, creditor_amount = creditors[j]

        payment = min(debtor_amount, creditor_amount)
        results.append(f"{debtor_name} owes {creditor_name}: ${payment:.2f}")

        debtors[i][1] -= payment
        creditors[j][1] -= payment

        if debtors[i][1] <= 0:
            i += 1
        if creditors[j][1] <= 0:
            j += 1

    if len(results) == 0:
        return "All balances are settled. No one owes anything."

    return "\n".join(results)


"""
Process incoming commands and route them to the appropriate handler functions
- Validate the command format and arguments
- Return error messages for invalid commands or arguments
commands:
- LIST
- TOTAL
- BALANCE
- ADD|payer|amount|description 
"""


def process_command(command):
    command = command.strip()

    if command.upper() == "LIST":
        return handle_list()

    if command.upper() == "TOTAL":
        return handle_total()

    if command.upper() == "BALANCE":
        return handle_balance()

    if command.upper().startswith("ADD|"):
        parts = command.split("|")
        return handle_add(parts)

    if command.upper() == "HELP":
        return (
            "Commands:\n"
            "ADD|payer|amount|description\n"
            "LIST\n"
            "TOTAL\n"
            "BALANCE\n"
            "HELP\n"
            "EXIT"
        )

    return "ERROR: Unknown command. Type HELP for available commands."


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"Server is listening on {HOST}:{PORT}")
    print("Waiting for a connection...")

    client_socket, client_address = server_socket.accept()
    print(f"Connection established with {client_address}")

    while True:
        data = client_socket.recv(1024)

        if not data:
            print("Client disconnected.")
            break

        message = data.decode().strip()
        print(f"Received message: {message}")

        if message.upper() == "EXIT":
            response = "Goodbye!"
            client_socket.sendall(response.encode())
            print("Closing connection.")
            break

        response = process_message(message)
        client_socket.sendall(response.encode())

    client_socket.close()
    server_socket.close()
    print("Server shut down.")


if __name__ == "__main__":
    main()
