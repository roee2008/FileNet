import socket
import os
import threading
import time
import re
from DBHandler import DBHandler
from UserHandler import UserHandler

HOST = '127.0.0.1'
PORT = 2122
BASE_DIR = "ftp_root"
DEBUG = True
MAX_REQUESTS_PER_MINUTE = 15
request_counts = {}
last_request_times = {}

os.makedirs(BASE_DIR, exist_ok=True)

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def send_response(conn, message):
    debug_print(f"Sent: {message.strip()}")
    conn.sendall(message)

def have_access(username, path, file_db):
    if not os.path.exists(path):
        return False
    path = path.replace(os.sep, "/").split("/")
    files = fileDB.get_user_files(username)
    for names in files:
        if names[1] == path[1]:
            return True
    return False

def list_files(path):
    if not os.path.exists(path):
        return "Directory not found."
    if not os.path.isdir(path):
        return "Not a directory."
    files = os.listdir(path)
    return "\n".join(files) if files else "404 No files found."

def search_by_name(target_file_name):
    found_files = []
    abs_ftp_root = os.path.abspath(BASE_DIR)
    for dirpath, dirnames, filenames in os.walk(BASE_DIR):
        for filename in filenames:
            if target_file_name in filename:
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, abs_ftp_root)
                found_files.append(relative_path.replace(os.sep, "/"))
    return found_files

def is_valid_username(username):
    return re.match("^[a-zA-Z0-9_]{3,20}$", username)

def handle_login(conn, state, context, **kwargs):
    """Handles user login."""
    username = kwargs.get('username')
    password = kwargs.get('password')
    if not is_valid_username(username):
        send_response(conn, b"401 LOGIN FAILED: Invalid username format.\n")
        return
    userDB = context['userDB']
    user_data = userDB.get_user(username)

    if user_data and password == user_data[1]:
        send_response(conn, b"200 LOGIN SUCCESS\n")
        state['name'] = username
    else:
        send_response(conn, b"401 LOGIN FAILED: Invalid username or password.\n")

def handle_register(conn, state, context, **kwargs):
    """Handles user registration."""
    username = kwargs.get('username')
    password = kwargs.get('password')
    if not is_valid_username(username):
        send_response(conn, b"402 REGISTER FAILED: Invalid username format.\n")
        return

    userDB = context['userDB']

    if user_db.get_user(username) is not None:
        send_response(conn, b"402 REGISTER FAILED: User already exists.\n")
    else:
        user_db.new_user(username, password)
        send_response(conn, b"201 REGISTER SUCCESS\n")

def handle_list(conn, state, context, **kwargs):
    """Handles listing files and repositories."""
    file_db = context['fileDB']
    username = state.get('name')
    arg = kwargs.get('arg')

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if not arg:
        try:
            files = file_db.get_user_files(username)
            repo_list = [file[1] for file in files]
            send_response(conn, b"200 OK\n" + "\n".join(repo_list).encode() + b"\n")
        except:
            send_response(conn, b"404 No files found.\n")
    else:
        target_dir = os.path.join(BASE_DIR, arg)
        if not have_access(username, target_dir, file_db):
            send_response(conn, b"403 Access denied.\n")
        else:
            send_response(conn, b"200 OK\n" + list_files(target_dir).encode() + b"\n")

def handle_search(conn, state, context, **kwargs):
    """Handles searching for a file."""
    file_db = context['fileDB']
    username = state.get('name')
    target_file_name = kwargs.get('target_file_name')

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if target_file_name:
        found_files = search_by_name(target_file_name)
        filtered_files = [file for file in found_files if have_access(username, "ftp_root/" + file.split('/')[0], fileDB)]
        if filtered_files:
            response = "200 OK\n" + "\n".join(filtered_files)
        else:
            response = "404 No files found."
        send_response(conn, response.encode())
    else:
        send_response(conn, b"400 Bad Request: Missing filename. Usage: SEARCH <filename>\n")

def handle_get(conn, state, context, **kwargs):
    """Handles retrieving a file."""
    file_db = context['fileDB']
    username = state.get('name')
    arg = kwargs.get('arg')
    target_dir = os.path.join(BASE_DIR, arg)

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if not have_access(username, target_dir, file_db):
        send_response(conn, b"403 Access denied.\n")
    else:
        path = os.path.join(BASE_DIR, arg)
        if os.path.exists(path) and os.path.isfile(path):
            send_response(conn, b"200 OK\n")
            with open(path, "rb") as f:
                send_response(conn, f.read())
        else:
            send_response(conn, b"404 File not found.\n")

def handle_getdir(conn, state, context, **kwargs):
    """Handles retrieving a directory."""
    file_db = context['fileDB']
    username = state.get('name')
    arg = kwargs.get('arg')
    target_dir = os.path.join(BASE_DIR, arg)

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if not have_access(username, target_dir, file_db):
        send_response(conn, b"403 Access denied.\n")
    else:
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            send_response(conn, b"404 Directory not found.\n")
            return

        send_response(conn, b"200 OK\n")
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR).replace(os.sep, "/")
                size = os.path.getsize(full_path)
                send_response(conn, f"FILE {rel_path} {size}\n".encode())
                with open(full_path, "rb") as f:
                    send_response(conn, f.read())
        send_response(conn, b"DONE\n")

def handle_put(conn, state, context, **kwargs):
    """Handles uploading a file."""
    file_db = context['fileDB']
    username = state.get('name')
    arg = kwargs.get('arg')
    target_dir = os.path.dirname(os.path.join(BASE_DIR, arg))

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if not have_access(username, target_dir, file_db):
        send_response(conn, b"403 Access denied.\n")
    else:
        path = os.path.join(BASE_DIR, arg)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        send_response(conn, b"200 OK: Send file data, end with EOF marker '<EOF>'\n")
        file_data = b""
        while True:
            chunk = conn.recv(1024)
            if b"<EOF>" in chunk:
                file_data += chunk.replace(b"<EOF>", b"")
                break
            file_data += chunk
        with open(path, "wb") as f:
            f.write(file_data)
        send_response(conn, b"200 File uploaded successfully.\n")

def handle_mkdir(conn, state, context, **kwargs):
    """Handles creating a directory."""
    file_db = context['fileDB']
    username = state.get('name')
    arg = kwargs.get('arg')
    target_dir = os.path.join(BASE_DIR, arg)

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    if not have_access(username, target_dir, file_db):
        send_response(conn, b"403 Access denied.\n")
    else:
        new_dir = os.path.join(BASE_DIR, arg)
        try:
            os.makedirs(new_dir, exist_ok=False)
            send_response(conn, b"201 Directory created successfully.\n")
        except FileExistsError:
            send_response(conn, b"409 Directory already exists.\n")

def handle_getrepos(conn, state, context, **kwargs):
    """Handles getting user's repositories."""
    file_db = context['fileDB']
    username = state.get('name')

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    repos = file_db.get_user_files(username, include_shared=False)
    repo_names = [repo[1] for repo in repos]
    send_response(conn, b"200 OK\n" + ",".join(repo_names).encode() + b"\n")

def handle_adduser(conn, state, context, **kwargs):
    """Handles adding a user to a repo."""
    file_db = context['fileDB']
    username = state.get('name')
    repo_name = kwargs.get('repo_name')
    user_to_add = kwargs.get('user_to_add')

    if not username:
        send_response(conn, b"403 You must be logged in to perform this action.\n")
        return

    files = file_db.get_all_files()
    file_id = -1
    for file in files:
        if file[1] == repo_name:
            file_id = file[0]
            break
    if file_id != -1:
        file_db.share_file_with_user(file_id, user_to_add)
        send_response(conn, b"200 User added successfully.\n")
    else:
        send_response(conn, b"404 Repository not found.\n")

def handle_quit(conn, state, context, **kwargs):
    """Handles disconnection."""
    send_response(conn, b"221 Goodbye!\n")
    return "QUIT"

command_handlers = {
    "LOGIN": {
        "handler": handle_login,
        "args": ["username", "password"],
        "separator": "_",
        "description": "Logs in. Usage: LOGIN <username>_<password>"
    },
    "REGISTER": {
        "handler": handle_register,
        "args": ["username", "password"],
        "separator": "_",
        "description": "Registers a new user. Usage: REGISTER <username>_<password>"
    },
    "LIST": {
        "handler": handle_list,
        "args": ["arg"],
        "separator": None,
        "description": "Lists files in the current repository or all repositories. Usage: LIST [path]"
    },
    "SEARCH": {
        "handler": handle_search,
        "args": ["target_file_name"],
        "separator": " ",
        "description": "Searches for a file. Usage: SEARCH <filename>"
    },
    "GET": {
        "handler": handle_get,
        "args": ["arg"],
        "separator": None,
        "description": "Downloads a file. Usage: GET <file_path>"
    },
    "GETDIR": {
        "handler": handle_getdir,
        "args": ["arg"],
        "separator": None,
        "description": "Downloads a directory. Usage: GETDIR <dir_path>"
    },
    "PUT": {
        "handler": handle_put,
        "args": ["arg"],
        "separator": None,
        "description": "Uploads a file. Usage: PUT <file_path>"
    },
    "MKDIR": {
        "handler": handle_mkdir,
        "args": ["arg"],
        "separator": None,
        "description": "Creates a directory. Usage: MKDIR <dir_path>"
    },
    "GETREPOS": {
        "handler": handle_getrepos,
        "args": [],
        "separator": None,
        "description": "Lists your repositories."
    },
    "ADDUSER": {
        "handler": handle_adduser,
        "args": ["repo_name", "user_to_add"],
        "separator": "_",
        "description": "Shares a repo. Usage: ADDUSER <repo_name>_<user_to_add>"
    },
    "QUIT": {
        "handler": handle_quit,
        "args": [],
        "separator": None,
        "description": "Disconnects from the server."
    }
}

def run_command(conn, state, context, command_string):
    """Parses and executes a command using the metadata table."""
    debug_print(f"Received: {command_string}")
    cmd, _, arg_string = command_string.strip().partition(" ")
    cmd = cmd.upper()

    if cmd not in command_handlers:
        send_response(conn, b"500 Unknown command.\n")
        return
    config = command_handlers[cmd]

    parsed_args = {}
    expected_args = config["args"]
    if expected_args:
        if not arg_string and len(expected_args) > 0 and expected_args != ['arg']:
            send_response(conn, f"400 Command '{cmd}' requires arguments. {config['description']}".encode())
            return
        separator = config["separator"]
        if separator:
            values = arg_string.split(separator, len(expected_args) - 1)
        else:
            values = [arg_string]
        if len(values) != len(expected_args) and expected_args != ['arg']:
            send_response(conn, f"400 Invalid arguments for '{cmd}'. {config['description']}".encode())
            return
        parsed_args = dict(zip(expected_args, values))

    debug_print(f"Calling handler for {cmd} with args: {parsed_args}")
    return config['handler'](conn, state, context, **parsed_args)

def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")
    ip = addr[0]
    current_time = time.time()
    if ip in last_request_times and current_time - last_request_times[ip] < 60:
        request_counts[ip] = request_counts.get(ip, 0) + 1
    else:
        request_counts[ip] = 1
    last_request_times[ip] = current_time

    if request_counts.get(ip, 0) > MAX_REQUESTS_PER_MINUTE:
        send_response(conn, b"429 Too Many Requests\n")
        conn.close()
        return
    send_response(conn, b"220 Welcome Server Online\n")
    client_state = {"name": None}
    server_context = {
        "fileDB": DBHandler(),
        "userDB": UserHandler()
    }

    try:
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break

            if run_command(conn, client_state, server_context, data) == "QUIT":
                break
    finally:
        conn.close()
        server_context['fileDB'].close()
        server_context['userDB'].close()
        print(f"[-] {addr} disconnected")

def cleanup_request_logs():
    while True:
        time.sleep(60)
        current_time = time.time()
        for ip, last_time in list(last_request_times.items()):
            if current_time - last_time > 60:
                del last_request_times[ip]
                if ip in request_counts:
                    del request_counts[ip]

def main():
    cleanup_thread = threading.Thread(target=cleanup_request_logs, daemon=True)
    cleanup_thread.start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[+] FTP-like server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVECONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    main()
