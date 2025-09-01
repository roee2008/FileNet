# Welcome to the final, heavily commented dispatch example!
# This file demonstrates a robust, metadata-driven command dispatch pattern
# that cleanly separates command definition, parsing, and execution.

import socket
import os

# --- Mock Objects for Demonstration ---
# These fake classes simulate the behavior of your real objects.
class MockDBHandler:
    def get_user_files(self, username, include_shared=False): return [ (1, "repo1", "user1") ]
    def get_all_files(self): return [(1, "repo1", "user1")]
    def share_file_with_user(self, file_id, user_to_add): pass
    def close(self): pass

class MockUserHandler:
    def get_user(self, username):
        if username == "testuser": return ("testuser", "password123")
        return None
    def new_user(self, username, password): pass
    def close(self): pass

class MockConn:
    def sendall(self, data):
        print(f"CONN: Sending: {data.strip()}")
    def close(self): print("\nCONN: Closed")


# --- Step 1: The Handler Functions ---
# These functions contain the actual logic for each command.
#
# THE MOST IMPORTANT CONCEPT: THE FUNCTION SIGNATURE
# (conn, state, context, **kwargs)
#
# - conn: The client's connection object.
#
# - state: The Client's "Private Notepad". A dictionary holding state for THIS client
#          (e.g., their login name). Each client gets their own.
#
# - context: The Server's "Toolbox". A dictionary holding server-wide resources
#            (like database handlers) that all clients share.
#
# - **kwargs: A dictionary of the arguments parsed from the client's command string.

def handle_login(conn, state, context, **kwargs):
    """Handles user login."""
    username = kwargs.get('username')
    password = kwargs.get('password')
    print(f"HANDLER: handle_login received user='{username}', pass='******'")

    # Get the userDB from the Server's Toolbox (context).
    userDB = context['userDB']
    user_data = userDB.get_user(username)

    if user_data and password == user_data[1]:
        conn.sendall(b"LOGIN SUCCESS\n")
        # Login successful! Write the user's name on their Private Notepad (state).
        state['name'] = username
    else:
        conn.sendall(b"LOGIN FAILED\n")

def handle_adduser(conn, state, context, **kwargs):
    """Handles adding a user to a repo."""
    repo_name = kwargs.get('repo_name')
    user_to_add = kwargs.get('user_to_add')
    print(f"HANDLER: handle_adduser received repo='{repo_name}', add_user='{user_to_add}'")

    # Check the client's Private Notepad to see if they are logged in.
    if not state.get('name'):
        conn.sendall(b"You must be logged in to do that.")
        return

    conn.sendall(f"User {user_to_add} added to {repo_name}.".encode())

def handle_list(conn, state, context, **kwargs):
    """Handles listing repositories."""
    # Check the client's Private Notepad to get their username.
    current_user = state.get('name')
    print(f"HANDLER: handle_list called for user '{current_user}'")
    if not current_user:
        conn.sendall(b"You must be logged in.")
        return

    # Get the fileDB from the Server's Toolbox to fetch the files.
    fileDB = context['fileDB']
    # files = fileDB.get_user_files(current_user)
    conn.sendall(b"repo1\nrepo2") # Mock response

def handle_quit(conn, state, context, **kwargs):
    """Handles disconnection."""
    conn.sendall(b"Goodbye!")
    return "QUIT"


# --- Step 2: The Metadata-Driven Dispatch Table ---
# This dictionary is the "brain" of our server. It declaratively defines every command.
command_handlers = {
    "LOGIN": {
        "handler": handle_login,
        "args": ["username", "password"],
        "separator": "_",
        "description": "Logs in. Usage: LOGIN <username>_<password>"
    },
    "ADDUSER": {
        "handler": handle_adduser,
        "args": ["repo_name", "user_to_add"],
        "separator": "_",
        "description": "Shares a repo. Usage: ADDUSER <repo_name>_<user_to_add>"
    },
    "LIST": {
        "handler": handle_list,
        "args": [],
        "separator": None,
        "description": "Lists your repositories."
    },
    "QUIT": {
        "handler": handle_quit,
        "args": [],
        "separator": None,
        "description": "Disconnects from the server."
    }
}


# --- Step 3: The Generic Command Runner ---
# This is the engine. It uses the metadata from `command_handlers` to do all the work.
def run_command(conn, state, context, command_string):
    """Parses and executes a command using the metadata table."""
    cmd, _, arg_string = command_string.strip().partition(" ")
    cmd = cmd.upper()

    if cmd not in command_handlers:
        conn.sendall(b"Unknown command.")
        return
    config = command_handlers[cmd]

    parsed_args = {}
    expected_args = config["args"]
    if expected_args:
        if not arg_string:
            conn.sendall(f"Command '{cmd}' requires arguments. {config['description']}".encode())
            return
        separator = config["separator"]
        if separator:
            values = arg_string.split(separator, len(expected_args) - 1)
        else:
            values = [arg_string]
        if len(values) != len(expected_args):
            conn.sendall(f"Invalid arguments for '{cmd}'. {config['description']}".encode())
            return
        parsed_args = dict(zip(expected_args, values))

    print(f"DISPATCHER: Calling {config['handler'].__name__} with parsed args: {parsed_args}")
    return config['handler'](conn, state, context, **parsed_args)


# --- Main execution block ---
def main():
    """Simulates a client session using the new metadata-driven approach."""
    # --- Server Setup ---
    # The Server's Toolbox (context): A dictionary holding shared, server-wide
    # resources that never change, like database handlers. Every client uses this same toolbox.
    server_context = {
        "fileDB": MockDBHandler(),
        "userDB": MockUserHandler()
    }
    print(f"SERVER: Toolbox created with {list(server_context.keys())}")

    # --- Client Connection Setup ---
    conn = MockConn()
    addr = ("127.0.0.1", 12345)
    # The Client's Private Notepad (state): A dictionary holding information for this
    # specific client's session. Each connecting client gets their own fresh notepad.
    client_state = {"name": None}
    print(f"SERVER: New client connected. Initial state (notepad): {client_state}\n")

    # --- SIMULATING A CLIENT SESSION ---
    print("---" + " 1. Login (correct) ---")
    run_command(conn, client_state, server_context, "LOGIN testuser_password123")
    print(f"Notepad after command: {client_state}\n")

    print("---" + " 2. LIST (now logged in) ---")
    run_command(conn, client_state, server_context, "LIST")
    print(f"Notepad after command: {client_state}\n")

    print("---" + " 3. ADDUSER (correct) ---")
    run_command(conn, client_state, server_context, "ADDUSER myrepo_teammate")
    print(f"Notepad after command: {client_state}\n")

    print("---" + " 4. QUIT ---")
    run_command(conn, client_state, server_context, "QUIT")

    # --- Cleanup ---
    server_context['fileDB'].close()
    server_context['userDB'].close()
    conn.close()
    print("SERVER: Shutdown complete.")

if __name__ == "__main__":
    main()