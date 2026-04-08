# ✿ TermKaiwa – GUI Chat Application 💕

## Course Information

Course: CMPT 371 – Data Communications & Networking

Instructor: Mirza Zaeem Baig

Semester: Spring 2026

## Overview 🌸

TermKaiwa is a chat application built on Python’s Socket API (TCP).

It includes a colorful tkinter GUI client, so multiple users can connect and chat in real time.

The system follows a client-server architecture and supports:

- Group chat 💬
- Direct messaging 💌
- Secret room with a shared password 🔒
- Username change ✨
- Mute specific users locally 🤫

## Features ✨

- Multiple clients can connect simultaneously 👥
- Real-time group chat 💬
- Private messaging 💌
- Username system (prevents duplicates) 🏷️
- Username change 🔄
- Join/leave notifications 🔔
- Online user list 👀
- Secret room with password 🔐
- Client-side mute 🤐
- Graphical User Interface using tkinter 🖥️

## Commands (Optional) 📋

The GUI client provides buttons for these actions, so you usually do not need to type commands.

You can still enter the following server commands in the chat input if you want.

### Server commands

| Command                    | Description                        |
| -------------------------- | ---------------------------------- |
| `/users`                   | Show all online users 👥           |
| `/rename <username>`       | Change your username 🔄            |
| `/dm <username> <message>` | Send a private message 💌          |
| `/dm <username>`           | Show last 15 DMs with that user 💬 |
| `/secret <password>`       | Enter the secret room 🔒           |
| `/secret_leave`            | Leave the secret room 🚪           |
| `/help`                    | Show available commands ❓         |
| `/quit`                    | Leave the chat 👋                  |

## Technologies Used 🛠️

- Python 3 🐍
- Socket API (TCP) 🔌
- Threading (for handling multiple clients concurrently) 🧵
- tkinter (GUI client) 🖼️

## Prerequisites 📋

- Python 3.10 or higher 🐍
- pip installed 📦

## Installation 🚀

### Clone the repository

```bash
git clone https://github.com/fleur0121/TermKaiwa.git
cd TermKaiwa
```

## Step-by-Step Run Guide 📖

### 0) Verify Python on a fresh machine

```bash
python3 --version
```

If the command is not found, install Python 3.10+ first.

### 1) (Optional) Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No external dependencies are required for this project.

### 2) Start the server

```bash
python3 app/server.py
```

You will be prompted to set the secret room password.

### 3) Start a client

Open another terminal and run:

```bash
python3 app/chat_app.py
```

You can open multiple GUI clients to simulate multiple users.

### 4) Connect and chat

In the GUI:

- Click `Connect`
- Enter a username
- Send messages or use the toolbar (Users, DM, Rename, Secret)

## Example Usage 🌟

1. Start the server
2. Open two GUI clients
3. Click `Connect` and enter usernames
4. Send messages and try DM/Secret from the toolbar

Example:

- Client A: Click `Connect` -> name: `Fuka`
- Client B: Click `Connect` -> name: `Noa`
- Client A: Type `hello everyone` and click `Send`
- Client A: Click `DM` -> choose `Noa` -> send a private message
- Client A: Click `Secret` -> enter password -> send a secret message
- Client A: Click `Secret` again to leave

## System Limitations & Design Considerations ⚠️

### Handling Multiple Clients

The server uses Python threading to handle multiple client connections.

Each client runs in a separate thread.

Limitation:
Thread-based design may not scale efficiently for a very large number of users.

### Client Disconnections

Disconnected clients are removed from the active list and other users are notified.

Limitation:
There is no automatic reconnection feature.

### Message Handling

The system uses TCP to ensure reliable message delivery.

Limitation:
Messages are stored only in memory for the current server session.

When the server restarts, history is lost.

History behavior:

- Public chat: new clients see the last 15 public messages on connect
- Secret room: clients see the last 15 secret messages upon entering
- Direct messages: clients see the last 15 DMs with that user

### Security

Messages are transmitted without encryption.

Limitation:
This application is not secure for sensitive communication.

### GUI Environment

The GUI is built with tkinter.

Limitation:
Some environments may not have tkinter available, configured or may not support GUI applications.

## Video Demo 🎥

https://discord.com/channels/@me/1419908037145133088/1491325410896773240

## Repository Structure 📁

```text
TERMKAIWA/
├── app/
│   ├── chat_app.py
│   ├── chat_ui.py
│   ├── chat_client.py
│   └── server.py
└── README.md
```

### Files

- chat_app.py: Main GUI client logic (event handling, message routing, state)
- chat_ui.py: Tkinter UI layout and styling components
- chat_client.py: Socket connection and background receive loop
- server.py: Multi-client chat server with rooms, history, and commands

## Group Members

| Name           | Student ID | Email        |
| -------------- | ---------- | ------------ |
| Fuka Nagata    | 301608021  | fna16@sfu.ca |
| Narihiro Okada | 301462533  | noa15@sfu.ca |

## Academic Integrity & References 📚

### GenAI Usage 🤖

ChatGPT and GitHub Copilot were used to assist with:

- Debugging socket communication issues and understanding error messages

- Assisting with the design, implementation, and refinement of the GUI using tkinter

- Suggesting improvements for code structure and organization

- Assisting in writing and polishing parts of the README for clarity and structure

- Brainstorming feature ideas such as secret rooms, rename, and mute commands

- Reviewing edge cases around username validation and disconnect handling

- Drafting example usage steps and command summaries

### References 📖

- Python Socket Programming Documentation

- Python threading module documentation

- Python networking tutorials (https://www.youtube.com/watch?v=oEOiBt6mD6Y, https://www.youtube.com/playlist?list=PLhTjy8cBISErYuLZUvVOYsR1giva2payF)

- TA tutorials (https://www.youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx)

- tkinter module documentation (https://docs.python.org/3/library/tkinter.html)

- tkinter.ttk module documentation (https://docs.python.org/3/library/tkinter.ttk.html)

- Notes from CMPT 371
