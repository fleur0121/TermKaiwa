import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

HOST = "127.0.0.1"
PORT = 5555
BUFFER_SIZE = 1024

# Locally muted usernames
muted_users = set()
muted_lock = threading.Lock()

def is_muted(username):
    with muted_lock:
        return username in muted_users

def mute_user(username):
    with muted_lock:
        if username in muted_users:
            return False
        muted_users.add(username)
        return True

def unmute_user(username):
    with muted_lock:
        if username not in muted_users:
            return False
        muted_users.discard(username)
        return True

def get_sender_chat(message):
    if ": " in message and not message.startswith("["):
        return message.split(": ", 1)[0]
    return None

def get_sender_dm(message):
    if message.startswith("[DM from "):
        try:
            return message[len("[DM from "):].split("]", 1)[0]
        except IndexError:
            return None
    return None

def handle_local_mute(parts, insert_message):
    if len(parts) < 2 or parts[1].strip() == "":
        insert_message("[LOCAL] Usage: /mute <username>", "error")
        return True
    target = parts[1].strip()
    if mute_user(target):
        insert_message(f"[LOCAL] {target} has been muted.", "local")
    else:
        insert_message(f"[LOCAL] {target} is already muted.", "local")
    return True

def handle_local_unmute(parts, insert_message):
    if len(parts) < 2 or parts[1].strip() == "":
        insert_message("[LOCAL] Usage: /unmute <username>", "error")
        return True
    target = parts[1].strip()
    if unmute_user(target):
        insert_message(f"[LOCAL] {target} has been unmuted.", "local")
    else:
        insert_message(f"[LOCAL] {target} is not muted.", "local")
    return True

def is_local_command(message, insert_message):
    parts = message.split()
    if not parts:
        return False
    command = parts[0]
    if command == "/mute":
        return handle_local_mute(parts, insert_message)
    if command == "/unmute":
        return handle_local_unmute(parts, insert_message)
    return False

def main():
    root = tk.Tk()
    root.title("Chat Client")
    root.geometry("400x500")
    root.configure(bg="lightgray")

    # Chat display area
    frame = tk.Frame(root)
    chat_text = tk.Text(frame, wrap=tk.WORD, state=tk.DISABLED, bg="white", font=("Arial", 10), padx=10, pady=10)
    scrollbar = tk.Scrollbar(frame, command=chat_text.yview)
    chat_text.config(yscrollcommand=scrollbar.set)
    chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    frame.pack(fill=tk.BOTH, expand=True)

    # Configure tags for styling
    chat_text.tag_configure("server", foreground="blue", font=("Arial", 10, "bold"))
    chat_text.tag_configure("you", foreground="green", font=("Arial", 10, "bold"))
    chat_text.tag_configure("dm_in", foreground="purple", font=("Arial", 10, "italic"))
    chat_text.tag_configure("dm_out", foreground="purple", font=("Arial", 10, "italic"))
    chat_text.tag_configure("join_leave", foreground="orange", font=("Arial", 10, "bold"))
    chat_text.tag_configure("error", foreground="red", font=("Arial", 10, "bold"))
    chat_text.tag_configure("chat", foreground="black")
    chat_text.tag_configure("local", foreground="cyan", font=("Arial", 10, "bold"))

    # Bottom input area
    bottom_frame = tk.Frame(root, bg="lightgray")
    entry = tk.Entry(bottom_frame, font=("Arial", 10))
    send_button = tk.Button(bottom_frame, text="Send", command=lambda: send_message(), bg="lightblue", font=("Arial", 10))
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
    send_button.pack(side=tk.RIGHT, padx=5, pady=5)
    bottom_frame.pack(fill=tk.X)

    # Bind Enter to send
    entry.bind("<Return>", lambda e: send_message())

    client_socket = None
    username = None

    def insert_message(text, tag):
        chat_text.config(state=tk.NORMAL)
        chat_text.insert(tk.END, text + "\n", tag)
        chat_text.see(tk.END)
        chat_text.config(state=tk.DISABLED)

    def print_message(message):
        dm_sender = get_sender_dm(message)
        if dm_sender is not None:
            if is_muted(dm_sender):
                return
            insert_message(message, "dm_in")
            return
        if message.startswith("[DM to "):
            insert_message(message, "dm_out")
            return
        if message.startswith("[You]"):
            insert_message(message, "you")
            return
        if message.startswith("***") and message.endswith("***"):
            insert_message(message, "join_leave")
            return
        if message.startswith("[SERVER]"):
            if "\n" in message:
                for line in message.split("\n"):
                    if any(kw in line for kw in ("not found", "Wrong", "cannot", "already", "Usage", "Error")):
                        insert_message(line, "error")
                    else:
                        insert_message(line, "server")
            elif any(kw in message for kw in ("not found", "Wrong", "cannot", "already", "Usage", "Error")):
                insert_message(message, "error")
            else:
                insert_message(message, "server")
            return
        chat_sender = get_sender_chat(message)
        if chat_sender is not None:
            if is_muted(chat_sender):
                return
            insert_message(message, "chat")
            return
        insert_message(message, "chat")

    def connect(uname):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            sock.sendall(uname.encode())
            response = sock.recv(BUFFER_SIZE).decode()
            root.after(0, lambda: print_message(response))
            if "Welcome" in response:
                return sock
            else:
                sock.close()
                return None
        except:
            return None

    def send_message():
        message = entry.get().strip()
        entry.delete(0, tk.END)
        if not message:
            return
        if is_local_command(message, insert_message):
            return
        try:
            client_socket.sendall(message.encode())
            if message == "/quit":
                root.quit()
        except:
            insert_message("[ERROR] Failed to send message.", "error")

    def receive_messages(sock):
        while True:
            try:
                message = sock.recv(BUFFER_SIZE).decode()
                if not message:
                    break
                root.after(0, lambda: print_message(message))
            except:
                break
        root.after(0, lambda: insert_message("[SERVER] Connection closed.", "error"))

    def on_close():
        if client_socket:
            try:
                client_socket.sendall("/quit".encode())
                client_socket.close()
            except:
                pass
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Connect loop
    while not client_socket:
        uname = simpledialog.askstring("Username", "Enter your username:", parent=root)
        if not uname:
            root.quit()
            return
        client_socket = connect(uname.strip())
        if not client_socket:
            messagebox.showerror("Error", "Invalid username or connection failed. Try again.")

    username = uname.strip()

    # Start receive thread
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.daemon = True
    receive_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()