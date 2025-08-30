import socket
import os
import threading
import os
from DBHandler import DBHandler
from UserHandler import UserHandler



HOST = '127.0.0.1'
PORT = 2122
BASE_DIR = "ftp_root"
fileDB = DBHandler()
userDB = UserHandler()

os.makedirs(BASE_DIR, exist_ok=True)
def have_access(username, path,fileDB):
    #print("debug path", path)
    if not os.path.exists(path):
        return False
    path = path.replace("\\", "/").split("/")
    files = fileDB.get_user_files(username)
    for names in files:
        #print("debug",names[1], path[1])
        if names[1] == path[1]:
            return True
    return False

    
def list_files(path):
    if not os.path.exists(path):
        return "Directory not found."
    if not os.path.isdir(path):
        return "Not a directory."
    files = os.listdir(path)
    return "\n".join(files) if files else "No files."
FTP_ROOT = 'ftp_root'

def search_by_name(root_dir, target_file_name):
    found_files = []
    abs_ftp_root = os.path.abspath(FTP_ROOT)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if  target_file_name in filename:
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, abs_ftp_root)
                found_files.append(relative_path.replace("\\", "/"))
    return found_files

def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")
    conn.sendall(b"Welcome Server Online\n")
    try:
        fileDB = DBHandler()
        userDB = UserHandler()
        name = ""
        password = ""
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break

            parts = data.split(" ", 1)
            cmd = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "LIST":
                if arg=="":
                    try:
                        files = fileDB.get_user_files(name)
                        repoList = [file[1] for file in files]
                        conn.sendall("\n".join(repoList).encode() + b"\n")
                    except:
                        conn.sendall(b"No files.\n")
                else:
                    target_dir = os.path.join(BASE_DIR, arg)
                    if not have_access(name, target_dir,fileDB):
                        conn.sendall(b"Access denied")
                    else:
                        conn.sendall(list_files(target_dir).encode() + b"\n")
            elif cmd == "SEARCH":
                parts = arg.split(" ", 1) # arg already contains the rest of the command after "SEARCH"
                if len(parts) > 0 and parts[0]: # Check if there's a filename provided
                    target_file_name = parts[0]
                    found_files = search_by_name(FTP_ROOT, target_file_name)
                    filtered_files = [file for file in found_files if have_access(name, "ftp_root\\"+file.split('/')[0], fileDB)]
                    response = filtered_files[0] if filtered_files else "No files found."
                    conn.send(response.encode())
                else:
                    conn.send("Usage: SEARCH <filename>".encode())
            elif cmd == "GET":
                if not have_access(name, target_dir,fileDB):
                        conn.sendall(b"Access denied")
                else:
                    path = os.path.join(BASE_DIR, arg)
                    if os.path.exists(path) and os.path.isfile(path):
                        with open(path, "rb") as f:
                            conn.sendall(f.read())
                    else:
                        conn.sendall(b"File not found.\n")
            elif cmd == "GETDIR":
                if not have_access(name, target_dir,fileDB):
                        conn.sendall(b"Access denied")
                else:
                    target_dir = os.path.join(BASE_DIR, arg)
                    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
                        conn.sendall(b"Directory not found.\n")
                        continue

                    for root, dirs, files in os.walk(target_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, BASE_DIR).replace("\\", "/")
                            size = os.path.getsize(full_path)
                            conn.sendall(f"FILE {rel_path} {size}\n".encode())
                            with open(full_path, "rb") as f:
                                conn.sendall(f.read())
                    conn.sendall(b"DONE\n")
            elif cmd == "PUT":
                if not have_access(name, target_dir,fileDB):
                        conn.sendall(b"Access denied")
                else:
                    path = os.path.join(BASE_DIR, arg)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    conn.sendall(b"Send file data, end with EOF marker '<EOF>'\n")
                    file_data = b""
                    while True:
                        chunk = conn.recv(1024)
                        if b"<EOF>" in chunk:
                            file_data += chunk.replace(b"<EOF>", b"")
                            break
                        file_data += chunk
                    with open(path, "wb") as f:
                        f.write(file_data)
                    conn.sendall(b"File uploaded successfully.\n")
            elif cmd == "LOGIN":
                name, password = arg.split("_")
                user_data = userDB.get_user(name)
                if user_data and password == user_data[1]:
                    conn.sendall(b"LOGIN SUCCESS\n")
                else:
                    conn.sendall(b"LOGIN FAILED\n")
            elif cmd == "REGISTER":
                if userDB.get_user(name)!=None:
                    conn.sendall(b"REGISTER FAILED\n")
                else:
                    name, password = arg.split("_")
                    userDB.new_user(name, password)
                    conn.sendall(b"REGISTER SUCCESS\n")
            elif cmd == "MKDIR":
                if not have_access(name, target_dir,fileDB):
                        conn.sendall(b"Access denied")
                else:
                    new_dir = os.path.join(BASE_DIR, arg)
                    try:
                        os.makedirs(new_dir, exist_ok=False)
                        conn.sendall(b"Directory created successfully.\n")
                    except FileExistsError:
                        conn.sendall(b"Directory already exists.\n")
            elif cmd == "GETREPOS":
                repos = fileDB.get_user_files(name,include_shared=False)
                repo_names = [repo[1] for repo in repos]
                conn.sendall(",".join(repo_names).encode() + b"\n")
            elif cmd == "ADDUSER":
                repo_name, user_to_add = arg.split("_")
                files = fileDB.get_all_files()
                file_id = -1
                for file in files:
                    if file[1] == repo_name:
                        file_id = file[0]
                        break
                if file_id != -1:
                    fileDB.share_file_with_user(file_id, user_to_add)
                    conn.sendall(b"User added successfully.\n")
                else:
                    conn.sendall(b"Repository not found.\n")
            elif cmd == "QUIT":
                conn.sendall(b"Goodbye!\n")
                break
            else:
                conn.sendall(b"Unknown command.\n")
    finally:
        conn.close()
        fileDB.close()
        userDB.close()
        print(f"[-] {addr} disconnected abruptly")
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        s.bind((HOST, PORT))
        s.listen()
        print(f"[+] FTP-like server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            # Create a new thread to handle the client
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVECONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    main()
    