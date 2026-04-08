import socket
import threading

HOST = "127.0.0.1"
PORT = 5555
BUFFER_SIZE = 1024
SOCKET_TIMEOUT_SEC = 1.0
HISTORY_LIMIT = 15

# Shared data
clients = []
socket_to_username = {}
username_to_socket = {}
socket_to_room = {}
room_history = {
    "public": [],
    "secret": [],
}
dm_history = {}

# Lock for thread-safe access
clients_lock = threading.Lock()


def frame_message(message):
    """
    Add a trailing newline so clients can safely separate TCP messages.
    """
    if message.endswith("\n"):
        return message
    return message + "\n"


def send_to_client(client_socket, message):
    """
    # Description
    Send one message to one client.s

    # Arguments
    client_socket: the socket to send to
    message: the string message to send

    # Returns
    True if the message was sent successfully, False if there was an error
    (e.g. the client disconnected)
    """
    try:
        client_socket.sendall(frame_message(message).encode())
        return True
    except:
        return False


def broadcast(message, exclude_client=None):
    """
    # Description
    Send a message to all connected clients.
    If exclude_client is provided, that client will not receive the message.

    # Arguments
    message: the string message to send
    exclude_client: a socket to exclude from receiving the message (optional)
    """
    with clients_lock:
        disconnected_clients = []

        for client_socket in clients:
            if client_socket == exclude_client:
                continue

            try:
                client_socket.sendall(frame_message(message).encode())
            except:
                disconnected_clients.append(client_socket)

    for dead_client in disconnected_clients:
        remove_client(dead_client)


def remove_client(client_socket):
    """
    # Description
    Remove a client from all shared structures and close its socket.

    # Arguments
    client_socket: the socket to remove
    """
    with clients_lock:
        username = socket_to_username.get(client_socket)

        if client_socket in clients:
            clients.remove(client_socket)

        if client_socket in socket_to_username:
            del socket_to_username[client_socket]

        if username in username_to_socket:
            del username_to_socket[username]

        if client_socket in socket_to_room:
            del socket_to_room[client_socket]

    try:
        client_socket.close()
    except:
        pass


def get_user_list_string():
    """
    # Description
    Return a comma-separated string of online usernames.

    # Returns
    A string of the form "user1, user2, user3" or "No users connected." if there are no users.
    """
    with clients_lock:
        if not username_to_socket:
            return "No users connected."
        return ", ".join(username_to_socket.keys())


def send_help(client_socket):
    """
    # Description
    Send command help text to one client.

    # Arguments
    client_socket: the socket to send the help text to
    """
    help_text = (
        "[SERVER] Commands:\n"
        "/users                  -> show online users\n"
        "/secret <password>      -> enter secret room\n"
        "/secret_leave           -> leave secret room\n"
        "/rename <username>      -> change your username\n"
        "/dm <username> <msg>    -> send a private message\n"
        "/dm <username>          -> show last 15 DMs\n"
        "/help                   -> show commands\n"
        "/quit                   -> leave the chat\n"
    )
    send_to_client(client_socket, help_text)


def get_room_clients(room_name):
    """
    # Description
    Get a list of client sockets that are currently in the specified room.

    # Arguments
    room_name: the name of the room ("public" or "secret")

    # Returns
    A list of client sockets that are in the specified room.
    """
    with clients_lock:
        return [
            client_socket
            for client_socket in clients
            if socket_to_room.get(client_socket) == room_name
        ]


def broadcast_room(message, room_name, exclude_client=None):
    """
    # Description
    Send a message to all clients in a specific room.

    # Arguments
    message: the string message to send
    room_name: the name of the room ("public" or "secret")
    exclude_client: a socket to exclude from receiving the message (optional)
    """
    room_clients = get_room_clients(room_name)
    disconnected_clients = []

    for client_socket in room_clients:
        if client_socket == exclude_client:
            continue

        try:
            client_socket.sendall(frame_message(message).encode())
        except:
            disconnected_clients.append(client_socket)

    for dead_client in disconnected_clients:
        remove_client(dead_client)


def append_room_history(room_name, message):
    """
    # Description
    Append a message to the history of a room.

    # Arguments
    room_name: the name of the room ("public" or "secret")
    message: the message string to append to the history
    """
    history = room_history.get(room_name)
    if history is None:
        history = []
        room_history[room_name] = history

    history.append(message)
    if len(history) > HISTORY_LIMIT:
        del history[: len(history) - HISTORY_LIMIT]


def get_room_history(room_name):
    """
    # Description
    Get the message history for a room as a list of message strings.

    # Arguments
    room_name: the name of the room ("public" or "secret")

    # Returns
    A list of message strings for the specified room, or an empty list if there is no history.
    """
    return room_history.get(room_name, [])


def get_dm_key(user_a, user_b):
    """
    # Description
    Get a consistent key for the DM history between two users, regardless of their order.

    # Arguments
    user_a: one username
    user_b: the other username

    # Returns
    A tuple of the two usernames in sorted order, which can be used as a key for DM history storage.
    """
    return tuple(sorted([user_a, user_b]))


def append_dm_history(user_a, user_b, message):
    """
    # Description
    Append a message to the DM history between two users.

    # Arguments
    user_a: one username
    user_b: the other username
    message: the message string to append to the history
    """
    key = get_dm_key(user_a, user_b)
    history = dm_history.get(key)
    if history is None:
        history = []
        dm_history[key] = history

    history.append(message)
    if len(history) > HISTORY_LIMIT:
        del history[: len(history) - HISTORY_LIMIT]


def get_dm_history(user_a, user_b):
    """
    # Description
    Get the DM history between two users as a list of message strings.

    # Arguments
    user_a: one username
    user_b: the other username

    # Returns
    A list of message strings for the DM history between the two users, or an empty list if there is no history.
    """
    return dm_history.get(get_dm_key(user_a, user_b), [])


def handle_dm(sender_socket, sender_username, message):
    """
    # Description
    Handle a private message command of the form:
    /dm username message

    # Arguments
    sender_socket: the socket of the sender
    sender_username: the username of the sender
    message: the full command message string
    """
    parts = message.split(" ", 2)

    if len(parts) < 2:
        send_to_client(
            sender_socket, "[SERVER] Usage: /dm <username> <message>"
        )
        return

    target_username = parts[1].strip()
    dm_text = ""
    if len(parts) >= 3:
        dm_text = parts[2].strip()

    if target_username == "":
        send_to_client(
            sender_socket, "[SERVER] Usage: /dm <username> <message>"
        )
        return

    with clients_lock:
        target_socket = username_to_socket.get(target_username)

    if target_socket is None:
        send_to_client(
            sender_socket, f"[SERVER] User '{target_username}' not found."
        )
        return

    if target_socket == sender_socket:
        send_to_client(sender_socket, "[SERVER] You cannot DM yourself.")
        return

    if dm_text == "":
        history = get_dm_history(sender_username, target_username)
        if not history:
            send_to_client(sender_socket, "[SERVER] No DM history.")
            return
        send_to_client(
            sender_socket,
            "[SERVER] Last 15 DMs:\n" + "\n".join(history),
        )
        return

    delivered_to_target = send_to_client(
        target_socket, f"[DM from {sender_username}] {dm_text}"
    )

    if not delivered_to_target:
        send_to_client(
            sender_socket,
            f"[SERVER] Could not deliver DM to '{target_username}'.",
        )
        return

    send_to_client(sender_socket, f"[DM to {target_username}] {dm_text}")
    append_dm_history(
        sender_username,
        target_username,
        f"{sender_username} -> {target_username}: {dm_text}",
    )


def handle_rename(client_socket, current_username, message):
    """
    # Description
    Handle a rename command of the form:
    /rename new_username

    # Arguments
    client_socket: the socket of the sender
    current_username: the current username
    message: the full command message string

    # Returns
    The new username if the rename was successful, or None if it failed (e.g. invalid format, username taken, etc.).
    If successful, also updates all relevant data structures and broadcasts the username change to all clients.
    """
    parts = message.split(" ", 1)

    if len(parts) < 2:
        send_to_client(client_socket, "[SERVER] Usage: /rename <new_username>")
        return None

    new_username = parts[1].strip()

    if new_username == "":
        send_to_client(client_socket, "[SERVER] Username cannot be empty.")
        return None

    if new_username == current_username:
        send_to_client(
            client_socket, "[SERVER] You are already using that username."
        )
        return None

    with clients_lock:
        if new_username in username_to_socket:
            send_to_client(client_socket, "[SERVER] Username already taken.")
            return None

        if current_username in username_to_socket:
            del username_to_socket[current_username]

        username_to_socket[new_username] = client_socket
        socket_to_username[client_socket] = new_username

    send_to_client(
        client_socket, f"[SERVER] Username changed to {new_username}."
    )
    return new_username


def handle_client(client_socket, client_address, secret_password):
    """
    # Description
    Handle all communication for one client.

    # Arguments
    client_socket: the socket for this client
    client_address: the (ip, port) tuple of the client's address
    secret_password: the password required to enter the secret room
    """
    username = "Unknown"

    try:
        data = client_socket.recv(BUFFER_SIZE)
        if not data:
            remove_client(client_socket)
            return

        proposed_username = data.decode().strip()

        if proposed_username == "":
            send_to_client(client_socket, "[SERVER] Username cannot be empty.")
            remove_client(client_socket)
            return

        with clients_lock:
            if proposed_username in username_to_socket:
                send_to_client(
                    client_socket, "[SERVER] Username already taken."
                )
                remove_client(client_socket)
                return

            username = proposed_username
            clients.append(client_socket)
            socket_to_username[client_socket] = username
            username_to_socket[username] = client_socket
            socket_to_room[client_socket] = "public"

        print(f"[CONNECTED] {username} joined from {client_address}")
        send_to_client(client_socket, f"[SERVER] Welcome, {username}!")
        broadcast(f"*** {username} joined the chat ***", exclude_client=None)

        public_history = get_room_history("public")
        if public_history:
            send_to_client(client_socket, "\n".join(public_history))

        while True:
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                break

            message = data.decode().strip()

            if message == "":
                continue

            # Command: /users
            if message == "/users":
                user_list = get_user_list_string()
                send_to_client(
                    client_socket, f"[SERVER] Online users: {user_list}"
                )
                continue

            # Command: /help
            if message == "/help":
                send_help(client_socket)
                continue

            # Command: /secret password
            if message.startswith("/secret "):
                provided = message.split(" ", 1)[1].strip()
                if provided == "":
                    send_to_client(
                        client_socket, "[SERVER] Usage: /secret <password>"
                    )
                    continue

                if provided != secret_password:
                    send_to_client(client_socket, "[SERVER] Wrong password.")
                    continue

                if socket_to_room.get(client_socket) == "secret":
                    send_to_client(
                        client_socket,
                        "[SERVER] You are already in the secret room.",
                    )
                    continue

                socket_to_room[client_socket] = "secret"
                send_to_client(
                    client_socket,
                    "[SERVER] Entered the secret room.",
                )
                secret_history = get_room_history("secret")
                if secret_history:
                    send_to_client(client_socket, "\n".join(secret_history))
                broadcast_room(
                    f"*** {username} joined the secret room ***",
                    "secret",
                    exclude_client=client_socket,
                )
                continue

            # Command: /secret_leave
            if message == "/secret_leave":
                if socket_to_room.get(client_socket) != "secret":
                    send_to_client(
                        client_socket,
                        "[SERVER] You are not in the secret room.",
                    )
                    continue

                socket_to_room[client_socket] = "public"
                send_to_client(
                    client_socket,
                    "[SERVER] Left the secret room.",
                )
                broadcast_room(
                    f"*** {username} left the secret room ***",
                    "secret",
                    exclude_client=client_socket,
                )
                continue

            # Command: /rename new_username
            if message.startswith("/rename "):
                updated_username = handle_rename(
                    client_socket, username, message
                )
                if updated_username:
                    broadcast(
                        f"*** {username} is now known as {updated_username} ***",
                        exclude_client=None,
                    )
                    username = updated_username
                continue

            # Command: /quit
            if message == "/quit":
                break

            # Command: /dm username message
            if message.startswith("/dm "):
                handle_dm(client_socket, username, message)
                continue

            # Otherwise: group chat message
            full_message = f"{username}: {message}"
            print(f"[GROUP] {full_message}")

            if socket_to_room.get(client_socket) == "secret":
                append_room_history("secret", full_message)
                broadcast_room(
                    full_message,
                    "secret",
                    exclude_client=client_socket,
                )
                send_to_client(client_socket, f"[You] {message}")
            else:
                append_room_history("public", full_message)
                broadcast(full_message, exclude_client=client_socket)
                send_to_client(client_socket, f"[You] {message}")

    # Handle client disconnection and cleanup
    except ConnectionResetError:
        print(f"[DISCONNECTED] {username} connection was reset.")
    except Exception as error:
        print(f"[ERROR] Problem with {username}: {error}")
    finally:
        print(f"[LEFT] {username} left the chat.")
        remove_client(client_socket)
        broadcast(f"*** {username} left the chat ***", exclude_client=None)


def main():
    """
    Start the chat server and accept clients forever.
    """
    # Get the secret room password from the server operator
    secret_password = input("Set secret room password: ").strip()
    while secret_password == "":
        print("Password cannot be empty.")
        secret_password = input("Set secret room password: ").strip()

    # Set up the server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(SOCKET_TIMEOUT_SEC)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    # Server info display
    print("=" * 55)
    print(" Terminal Chat Server ")
    print("=" * 55)
    print(f"Listening on {HOST}:{PORT}")
    print("Features: group chat, direct messages, /users, /help, /quit")
    print("Press Ctrl+C to stop the server.")
    print("=" * 55)

    # Accept clients
    try:
        while True:
            try:
                client_socket, client_address = server_socket.accept()
            except socket.timeout:
                continue

            print(f"[NEW CONNECTION] {client_address}")

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address, secret_password),
                daemon=True,
            )
            client_thread.start()

    # Handle server shutdown and cleanup
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server is shutting down.")
    finally:
        with clients_lock:
            current_clients = clients[:]

        for client_socket in current_clients:
            try:
                client_socket.close()
            except:
                pass

        server_socket.close()


if __name__ == "__main__":
    main()
