import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import queue

HOST = "127.0.0.1"
PORT = 5555
BUFFER_SIZE = 1024
SOCKET_TIMEOUT_SEC = 1.0
HISTORY_LIMIT = 15

class ChatServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌸 TermKaiwa Server 🌸")
        self.root.geometry("1200x800")
        self.root.configure(bg="#F8F9FA")

        # Server state
        self.server_socket = None
        self.is_running = False
        self.secret_password = ""
        self.log_queue = queue.Queue()

        # Shared data
        self.clients = []
        self.socket_to_username = {}
        self.username_to_socket = {}
        self.socket_to_room = {}
        self.room_history = {
            "public": [],
            "secret": [],
        }
        self.dm_history = {}

        # Lock for thread-safe access
        self.clients_lock = threading.Lock()

        # Style configuration
        self.style = ttk.Style()
        self.style.configure("Pastel.TFrame", background="#F8F9FA")
        self.style.configure("Pastel.TLabel", background="#F8F9FA", foreground="#2D3748")
        self.style.configure("Pastel.TButton", background="#E2E8F0", foreground="#2D3748")
        self.style.configure("Start.TButton", background="#48BB78", foreground="white")
        self.style.configure("Stop.TButton", background="#F56565", foreground="white")

        # Create GUI
        self.create_gui()

        # Start log processing
        self.process_logs()

    def create_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root, style="Pastel.TFrame")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Top control panel
        control_frame = ttk.Frame(main_frame, style="Pastel.TFrame")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Title
        title_label = ttk.Label(control_frame, text="🌸 TermKaiwa Chat Server 🌸",
                               font=("Arial", 20, "bold"), style="Pastel.TLabel")
        title_label.pack(side=tk.LEFT, padx=(0, 20))

        # Server status
        self.status_label = ttk.Label(control_frame, text="🛑 Server Stopped",
                                     font=("Arial", 12, "bold"), foreground="#F56565",
                                     background="#F8F9FA")
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))

        # Start/Stop buttons
        self.start_btn = ttk.Button(control_frame, text="▶️ Start Server",
                                   command=self.start_server, style="Start.TButton")
        self.start_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.stop_btn = ttk.Button(control_frame, text="⏹️ Stop Server",
                                  command=self.stop_server, state=tk.DISABLED, style="Stop.TButton")
        self.stop_btn.pack(side=tk.RIGHT)

        # Content area
        content_frame = ttk.Frame(main_frame, style="Pastel.TFrame")
        content_frame.pack(expand=True, fill=tk.BOTH)

        # Left sidebar
        sidebar = ttk.Frame(content_frame, width=300, style="Pastel.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Users section
        users_frame = ttk.LabelFrame(sidebar, text="👥 Connected Users", style="Pastel.TFrame")
        users_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.users_listbox = tk.Listbox(users_frame, bg="#FFFFFF", fg="#2D3748",
                                       font=("Arial", 11), selectbackground="#CBD5E0",
                                       relief=tk.FLAT, borderwidth=0)
        users_scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_listbox.yview)
        self.users_listbox.configure(yscrollcommand=users_scrollbar.set)

        self.users_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        users_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Rooms section
        rooms_frame = ttk.LabelFrame(sidebar, text="🏠 Active Rooms", style="Pastel.TFrame")
        rooms_frame.pack(fill=tk.BOTH, expand=True)

        self.rooms_text = tk.Text(rooms_frame, bg="#FFFFFF", fg="#2D3748",
                                 font=("Arial", 10), relief=tk.FLAT, borderwidth=0,
                                 wrap=tk.WORD, state=tk.DISABLED)
        rooms_scrollbar = ttk.Scrollbar(rooms_frame, orient=tk.VERTICAL, command=self.rooms_text.yview)
        self.rooms_text.configure(yscrollcommand=rooms_scrollbar.set)

        self.rooms_text.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Right log area
        log_frame = ttk.LabelFrame(content_frame, text="📋 Server Logs", style="Pastel.TFrame")
        log_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.log_text = scrolledtext.ScrolledText(log_frame, bg="#FFFFFF", fg="#2D3748",
                                                 font=("Consolas", 10), relief=tk.FLAT, borderwidth=0,
                                                 wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Bottom info panel
        info_frame = ttk.Frame(main_frame, style="Pastel.TFrame")
        info_frame.pack(fill=tk.X, pady=(10, 0))

        info_text = f"🎯 Server Address: {HOST}:{PORT} | 💬 Features: Group Chat, DMs, Secret Rooms"
        info_label = ttk.Label(info_frame, text=info_text, font=("Arial", 10),
                              style="Pastel.TLabel")
        info_label.pack()

    def log_message(self, message):
        self.log_queue.put(message)

    def process_logs(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass

        self.root.after(100, self.process_logs)

    def update_users_list(self):
        self.users_listbox.delete(0, tk.END)
        with self.clients_lock:
            for username in self.username_to_socket.keys():
                room = "public"
                for sock, r in self.socket_to_room.items():
                    if self.socket_to_username.get(sock) == username:
                        room = r
                        break
                emoji = "🔒" if room == "secret" else "🌍"
                self.users_listbox.insert(tk.END, f"{emoji} {username}")

    def update_rooms_info(self):
        self.rooms_text.config(state=tk.NORMAL)
        self.rooms_text.delete(1.0, tk.END)

        with self.clients_lock:
            public_count = sum(1 for sock, room in self.socket_to_room.items() if room == "public")
            secret_count = sum(1 for sock, room in self.socket_to_room.items() if room == "secret")

        info = f"🌍 Public Room: {public_count} users\n🔒 Secret Room: {secret_count} users\n\n💬 Recent Activity:\n"

        # Add recent messages from both rooms
        for room_name, emoji in [("public", "🌍"), ("secret", "🔒")]:
            history = self.room_history.get(room_name, [])
            if history:
                info += f"\n{emoji} {room_name.title()}:\n"
                for msg in history[-3:]:  # Show last 3 messages
                    info += f"  • {msg}\n"

        self.rooms_text.insert(1.0, info)
        self.rooms_text.config(state=tk.DISABLED)

    def start_server(self):
        if self.is_running:
            return

        # Get secret password
        if not self.secret_password:
            self.secret_password = simpledialog.askstring("Secret Room Password",
                                                         "Enter password for secret room:",
                                                         parent=self.root)
            if not self.secret_password:
                messagebox.showerror("Error", "Password is required! 💔")
                return

        try:
            # Set up the server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(SOCKET_TIMEOUT_SEC)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen()

            self.is_running = True
            self.status_label.config(text="🟢 Server Running", foreground="#48BB78")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            self.log_message("=" * 55)
            self.log_message(" 🌸 TermKaiwa Server Started 🌸 ")
            self.log_message("=" * 55)
            self.log_message(f"Listening on {HOST}:{PORT}")
            self.log_message("Features: group chat, direct messages, secret rooms")
            self.log_message("=" * 55)

            # Start accepting clients
            self.accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            self.accept_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.log_message(f"❌ Failed to start server: {e}")

    def stop_server(self):
        if not self.is_running:
            return

        self.is_running = False
        self.status_label.config(text="🛑 Server Stopped", foreground="#F56565")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        # Close all client connections
        with self.clients_lock:
            current_clients = self.clients[:]

        for client_socket in current_clients:
            try:
                client_socket.close()
            except:
                pass

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.log_message("🛑 Server stopped")
        self.log_message("=" * 55)

    def accept_clients(self):
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.log_message(f"📨 [NEW CONNECTION] {client_address}")

                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                )
                client_thread.start()

            except socket.timeout:
                continue
            except:
                if self.is_running:
                    self.log_message("❌ Error accepting client connection")
                break

    # All the server logic methods (send_to_client, broadcast, remove_client, etc.)
    def send_to_client(self, client_socket, message):
        try:
            client_socket.sendall(message.encode())
            return True
        except:
            return False

    def broadcast(self, message, exclude_client=None):
        with self.clients_lock:
            disconnected_clients = []

            for client_socket in self.clients:
                if client_socket == exclude_client:
                    continue

                try:
                    client_socket.sendall(message.encode())
                except:
                    disconnected_clients.append(client_socket)

        for dead_client in disconnected_clients:
            self.remove_client(dead_client)

    def remove_client(self, client_socket):
        with self.clients_lock:
            username = self.socket_to_username.get(client_socket)

            if client_socket in self.clients:
                self.clients.remove(client_socket)

            if client_socket in self.socket_to_username:
                del self.socket_to_username[client_socket]

            if username in self.username_to_socket:
                del self.username_to_socket[username]

            if client_socket in self.socket_to_room:
                del self.socket_to_room[client_socket]

        try:
            client_socket.close()
        except:
            pass

        # Update GUI
        self.root.after(0, self.update_users_list)
        self.root.after(0, self.update_rooms_info)

    def get_user_list_string(self):
        with self.clients_lock:
            if not self.username_to_socket:
                return "No users connected."
            return ", ".join(self.username_to_socket.keys())

    def send_help(self, client_socket):
        help_text = (
            "[SERVER] Commands:\n"
            "/users                  -> show online users\n"
            "/secret <password>      -> enter secret room\n"
            "/secret_leave           -> leave secret room\n"
            "/rename <username>      -> change your username\n"
            "/dm <username> <msg>    -> send a private message\n"
            "/dm <username>          -> show last 15 DMs\n"
            "/help                   -> show commands\n"
            "/quit                   -> leave the chat"
        )
        self.send_to_client(client_socket, help_text)

    def get_room_clients(self, room_name):
        with self.clients_lock:
            return [
                client_socket
                for client_socket in self.clients
                if self.socket_to_room.get(client_socket) == room_name
            ]

    def broadcast_room(self, message, room_name, exclude_client=None):
        room_clients = self.get_room_clients(room_name)
        disconnected_clients = []

        for client_socket in room_clients:
            if client_socket == exclude_client:
                continue

            try:
                client_socket.sendall(message.encode())
            except:
                disconnected_clients.append(client_socket)

        for dead_client in disconnected_clients:
            self.remove_client(dead_client)

    def append_room_history(self, room_name, message):
        history = self.room_history.get(room_name)
        if history is None:
            history = []
            self.room_history[room_name] = history

        history.append(message)
        if len(history) > HISTORY_LIMIT:
            del history[: len(history) - HISTORY_LIMIT]

        # Update rooms info
        self.root.after(0, self.update_rooms_info)

    def get_room_history(self, room_name):
        return self.room_history.get(room_name, [])

    def get_dm_key(self, user_a, user_b):
        return tuple(sorted([user_a, user_b]))

    def append_dm_history(self, user_a, user_b, message):
        key = self.get_dm_key(user_a, user_b)
        history = self.dm_history.get(key)
        if history is None:
            history = []
            self.dm_history[key] = history

        history.append(message)
        if len(history) > HISTORY_LIMIT:
            del history[: len(history) - HISTORY_LIMIT]

    def get_dm_history(self, user_a, user_b):
        return self.dm_history.get(self.get_dm_key(user_a, user_b), [])

    def handle_dm(self, sender_socket, sender_username, message):
        parts = message.split(" ", 2)

        if len(parts) < 2:
            self.send_to_client(
                sender_socket, "[SERVER] Usage: /dm <username> <message>"
            )
            return

        target_username = parts[1].strip()
        dm_text = ""
        if len(parts) >= 3:
            dm_text = parts[2].strip()

        if target_username == "":
            self.send_to_client(
                sender_socket, "[SERVER] Usage: /dm <username> <message>"
            )
            return

        with self.clients_lock:
            target_socket = self.username_to_socket.get(target_username)

        if target_socket is None:
            self.send_to_client(
                sender_socket, f"[SERVER] User '{target_username}' not found."
            )
            return

        if target_socket == sender_socket:
            self.send_to_client(sender_socket, "[SERVER] You cannot DM yourself.")
            return

        if dm_text == "":
            history = self.get_dm_history(sender_username, target_username)
            if not history:
                self.send_to_client(sender_socket, "[SERVER] No DM history.")
                return
            self.send_to_client(
                sender_socket,
                "[SERVER] Last 15 DMs:\n" + "\n".join(history),
            )
            return

        delivered_to_target = self.send_to_client(
            target_socket, f"[DM from {sender_username}] {dm_text}"
        )

        if not delivered_to_target:
            self.send_to_client(
                sender_socket,
                f"[SERVER] Could not deliver DM to '{target_username}'.",
            )
            return

        self.send_to_client(sender_socket, f"[DM to {target_username}] {dm_text}")
        self.append_dm_history(
            sender_username,
            target_username,
            f"{sender_username} -> {target_username}: {dm_text}",
        )

    def handle_rename(self, client_socket, current_username, message):
        parts = message.split(" ", 1)

        if len(parts) < 2:
            self.send_to_client(client_socket, "[SERVER] Usage: /rename <new_username>")
            return None

        new_username = parts[1].strip()

        if new_username == "":
            self.send_to_client(client_socket, "[SERVER] Username cannot be empty.")
            return None

        if new_username == current_username:
            self.send_to_client(
                client_socket, "[SERVER] You are already using that username."
            )
            return None

        with self.clients_lock:
            if new_username in self.username_to_socket:
                self.send_to_client(client_socket, "[SERVER] Username already taken.")
                return None

            if current_username in self.username_to_socket:
                del self.username_to_socket[current_username]

            self.username_to_socket[new_username] = client_socket
            self.socket_to_username[client_socket] = new_username

        self.send_to_client(
            client_socket, f"[SERVER] Username changed to {new_username}."
        )

        # Update GUI
        self.root.after(0, self.update_users_list)

        return new_username

    def handle_client(self, client_socket, client_address):
        username = "Unknown"

        try:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                self.remove_client(client_socket)
                return

            proposed_username = data.decode().strip()

            if proposed_username == "":
                self.send_to_client(client_socket, "[SERVER] Username cannot be empty.")
                self.remove_client(client_socket)
                return

            with self.clients_lock:
                if proposed_username in self.username_to_socket:
                    self.send_to_client(
                        client_socket, "[SERVER] Username already taken."
                    )
                    self.remove_client(client_socket)
                    return

                username = proposed_username
                self.clients.append(client_socket)
                self.socket_to_username[client_socket] = username
                self.username_to_socket[username] = client_socket
                self.socket_to_room[client_socket] = "public"

            self.log_message(f"🎉 [CONNECTED] {username} joined from {client_address}")
            self.send_to_client(client_socket, f"[SERVER] Welcome, {username}!")
            self.send_help(client_socket)
            self.broadcast(f"*** {username} joined the chat ***", exclude_client=None)

            public_history = self.get_room_history("public")
            if public_history:
                self.send_to_client(
                    client_socket,
                    "[SERVER] Last 15 public messages:\n"
                    + "\n".join(public_history),
                )

            # Update GUI
            self.root.after(0, self.update_users_list)
            self.root.after(0, self.update_rooms_info)

            while True:
                data = client_socket.recv(BUFFER_SIZE)

                if not data:
                    break

                message = data.decode().strip()

                if message == "":
                    continue

                # Command: /users
                if message == "/users":
                    user_list = self.get_user_list_string()
                    self.send_to_client(
                        client_socket, f"[SERVER] Online users: {user_list}"
                    )
                    continue

                # Command: /help
                if message == "/help":
                    self.send_help(client_socket)
                    continue

                # Command: /secret password
                if message.startswith("/secret "):
                    provided = message.split(" ", 1)[1].strip()
                    if provided == "":
                        self.send_to_client(
                            client_socket, "[SERVER] Usage: /secret <password>"
                        )
                        continue

                    if provided != self.secret_password:
                        self.send_to_client(client_socket, "[SERVER] Wrong password.")
                        continue

                    if self.socket_to_room.get(client_socket) == "secret":
                        self.send_to_client(
                            client_socket,
                            "[SERVER] You are already in the secret room.",
                        )
                        continue

                    self.socket_to_room[client_socket] = "secret"
                    self.send_to_client(
                        client_socket,
                        "[SERVER] Entered the secret room.",
                    )
                    secret_history = self.get_room_history("secret")
                    if secret_history:
                        self.send_to_client(
                            client_socket,
                            "[SERVER] Last 15 secret messages:\n"
                            + "\n".join(secret_history),
                        )
                    self.broadcast_room(
                        f"*** {username} joined the secret room ***",
                        "secret",
                        exclude_client=client_socket,
                    )
                    # Update GUI
                    self.root.after(0, self.update_users_list)
                    continue

                # Command: /secret_leave
                if message == "/secret_leave":
                    if self.socket_to_room.get(client_socket) != "secret":
                        self.send_to_client(
                            client_socket,
                            "[SERVER] You are not in the secret room.",
                        )
                        continue

                    self.socket_to_room[client_socket] = "public"
                    self.send_to_client(
                        client_socket,
                        "[SERVER] Left the secret room.",
                    )
                    self.broadcast_room(
                        f"*** {username} left the secret room ***",
                        "secret",
                        exclude_client=client_socket,
                    )
                    # Update GUI
                    self.root.after(0, self.update_users_list)
                    continue

                # Command: /rename new_username
                if message.startswith("/rename "):
                    updated_username = self.handle_rename(
                        client_socket, username, message
                    )
                    if updated_username:
                        self.broadcast(
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
                    self.handle_dm(client_socket, username, message)
                    continue

                # Otherwise: group chat message
                full_message = f"{username}: {message}"
                self.log_message(f"💬 [GROUP] {full_message}")

                if self.socket_to_room.get(client_socket) == "secret":
                    self.append_room_history("secret", full_message)
                    self.broadcast_room(
                        full_message,
                        "secret",
                        exclude_client=client_socket,
                    )
                    self.send_to_client(client_socket, f"[You] {message}")
                else:
                    self.append_room_history("public", full_message)
                    self.broadcast(full_message, exclude_client=client_socket)
                    self.send_to_client(client_socket, f"[You] {message}")

        # Handle client disconnection and cleanup
        except ConnectionResetError:
            self.log_message(f"🔌 [DISCONNECTED] {username} connection was reset.")
        except Exception as error:
            self.log_message(f"❌ [ERROR] Problem with {username}: {error}")
        finally:
            self.log_message(f"👋 [LEFT] {username} left the chat.")
            self.remove_client(client_socket)
            self.broadcast(f"*** {username} left the chat ***", exclude_client=None)

def main():
    root = tk.Tk()
    app = ChatServerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()