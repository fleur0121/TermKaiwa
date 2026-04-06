import socket
import threading
import time

from rich.console import Console
from rich.theme import Theme

HOST = "127.0.0.1"
PORT = 5555
BUFFER_SIZE = 1024

# Custom theme for terminal UI
custom_theme = Theme(
    {
        "server": "bold bright_cyan",
        "dm_in": "bold bright_magenta",
        "dm_out": "italic bright_magenta",
        "you": "bold bright_green",
        "join_leave": "bold bright_yellow",
        "error": "bold bright_red",
        "info": "dim bright_white",
        "chat": "bright_white",
        "secret": "bold bright_blue",
    }
)

console = Console(theme=custom_theme)

# Locally muted usernames
# create set for muted users
muted_users = set()
muted_lock = threading.Lock()

# Display Helper Functions

def print_server(message):
    console.print(message, style="server")

def print_dm_in(message):
    console.print(message, style="dm_in")

def print_dm_out(message):
    console.print(message, style="dm_out")

def print_you(message):
    console.print(message, style="you")

def print_join_leave(message):
    console.print(message, style="join_leave")
    
def print_error(message):
    console.print(message, style="error")

def print_secret(message):
    console.print(message, style="secret")
    
def print_chat(message):
    console.print(message, style="chat")


# check if user is muted
def is_muted(username):
    with muted_lock:
        # check if user exist in muted users set
        return username in muted_users

# mute user, adds to set
def mute_user(username):
    with muted_lock:
        if username in muted_users:
            return False
        # add user to set
        muted_users.add(username)
        return True
    
# unmute user, removes from set
def unmute_user(username):
    with muted_lock:
        if username not in muted_users:
            return False
        # remove user from set
        muted_users.discard(username)
        return True

# extract sender for group chat message
def get_sender_chat(message):
    # username: message
    if ": " in message and not message.startswith("["):
        # retrieve username
        return message.split(": ", 1)[0]
    return None

# extract sender for direct chat message
def get_sender_dm(message):
    # [DM from username]
    if message.startswith("[DM from "):
        try:
            # retrieve username
            return message[len("[DM from "):].split("]", 1)[0]
        except IndexError:
            return None
    return None

#
def print_message(message):
    # 1. check if message is incoming direct message
    dm_sender = get_sender_dm(message)
    if dm_sender is not None:
        # do not print if user is muted
        if is_muted(dm_sender):
            return
        print_dm_in(message)
        return

    # 2. check if message is outgoing direct message
    if message.startswith("[DM to "):
        print_dm_out(message)
        return

    # 3. check if message is your echo
    if message.startswith("[You]"):
        print_you(message)
        return

    # 4. check if message is system message
    if message.startswith("***") and message.endswith("***"):
        console.print()
        print_join_leave(message)
        console.print()
        return

    # 5. check if message is server message
    if message.startswith("[SERVER]"):
        # check if message is a multi-line 
        if "\n" in message:
            for line in message.split("\n"):
                # check if line is an error
                if any(kw in line for kw in ("not found", "Wrong", "cannot", "already", "Usage", "Error")):
                    print_error(line)
                # check if line is a success
                else:
                    print_server(line)
        # check if message is a single line error
        elif any(kw in message for kw in ("not found", "Wrong", "cannot", "already", "Usage", "Error")):
            print_error(message)
        # check if message is a single line success
        else:
            print_server(message)
        return

    # 6. check if message is a group chat message
    chat_sender = get_sender_chat(message)
    if chat_sender is not None:
        # do not print if user is muted
        if is_muted(chat_sender):
            return
        print_chat(message)
        return

    # 7. print message without formatting   
    console.print(message)

# handle the /mute command
# parts = ["/mute", "username"]
def handle_local_mute(parts):
    # check if command is valid
    if len(parts) < 2 or parts[1].strip() == "":
        print_error("[LOCAL] Usage: /mute <username>")
        return True

    # target = username
    target = parts[1].strip()
    # mute target user
    if mute_user(target):
        print_server(f"[LOCAL] {target} has been muted.")
    else:
        print_server(f"[LOCAL] {target} is already muted.")
    return True

# handle the /unmute command
# parts = ["/unmute", "username"]
def handle_local_unmute(parts):
    # check if command is valid
    if len(parts) < 2 or parts[1].strip() == "":
        print_error("[LOCAL] Usage: /unmute <username>")
        return True

    # target = username
    target = parts[1].strip()
    # mute target user
    if unmute_user(target):
        print_server(f"[LOCAL] {target} has been unmuted.")
    else:
        print_server(f"[LOCAL] {target} is not muted.")
    return True

# check if message is a local command
def is_local_command(message):
    parts = message.split()
    if not parts:
        return False
    
    command = parts[0]

    # check if command is a local mute command
    if command == "/mute":
        return handle_local_mute(parts)

    # check if command is a local unmute command
    if command == "/unmute":
        return handle_local_unmute(parts)

    return False

# receive messages from the server
def receive_messages(client_socket):
    # loop forever waiting for messages
    while True:
        try:
            message = client_socket.recv(BUFFER_SIZE).decode()
            # empty, server disconnected
            if not message:
                print_error("[SERVER] Connection closed.")
                break
            print_message(message)
        # unexpected connection lost
        except:
            print_error("[SERVER] Connection lost.")
            break

# handles the initial connection and username registration before the chat starts.
def connect_and_register(host, port):
    while True:
        # 1. Create a TCP socket and connect
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 2. Connect
        client_socket.connect((host, port))

        # 3. Register username
        username = console.input("[bold cyan]Enter your username:[/bold cyan] ").strip()
        client_socket.sendall(username.encode())

        # 4. Wait for response
        response = client_socket.recv(BUFFER_SIZE).decode()
        print_message(response)

        # 5. Check if username is valid
        if "already taken" in response or "cannot be empty" in response:
            client_socket.close()
            continue

        if "Welcome" in response:
            return client_socket, username

def main():
    username = "Unknown" 
    client_socket = None 
    try:
        # 1. Create a TCP socket and connect 
        client_socket, username = connect_and_register(HOST, PORT)

        # 2. Start background receiver thread
        receiver_thread = threading.Thread(
            target=receive_messages, args=(client_socket,)
        )
        receiver_thread.daemon = True
        receiver_thread.start()

        # Small delay for server printing the help text
        time.sleep(0.2)

        # 3. Main loop: read input and send to server
        while True:
            message = input()
            if message.strip() == "":
                continue
            if is_local_command(message):
                continue
            client_socket.sendall(message.encode())
            if message.strip() == "/quit":
                break
            
      
    # 4. Handle errors 
    except KeyboardInterrupt:
        print_error(f"\n[DISCONNECTED] {username} disconnected.")
    except ConnectionResetError:
        print_error(f"[DISCONNECTED] {username} connection was reset.")
    except Exception as error:
        print_error(f"[ERROR] Problem with {username}: {error}")
    finally:
        console.print(f"[LEFT] {username} left the chat.")
        if client_socket:
            client_socket.close()

if __name__ == "__main__":
    main()
