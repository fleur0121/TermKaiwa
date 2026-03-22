import socket

HOST = "127.0.0.1"
PORT = 5555


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    print(f"Connected to server at {HOST} : {PORT}")
    print(
        "Available commands: LIST, TOTAL, BALANCE, ADD|payer|amount|description, HELP, EXIT"
    )

    while True:
        message = input("\nEnter command: ").strip()

        if message == "":
            print("Empty message. Please enter a valid command.")
            continue

        client_socket.sendall(message.encode())
        response = client_socket.recv(1024).decode()

        print("\n--- Server Response ---")
        print(response)
        print("-----------------------")

        if message.upper() == "EXIT":
            print("Exiting client.")
            break

    client_socket.close()
    print("Client shut down.")


if __name__ == "__main__":
    main()
