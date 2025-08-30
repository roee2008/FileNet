import sqlite3

class DBHandler:
    def __init__(self, db_name="ReposDB.sqlite"):
        self.conn = sqlite3.connect(db_name)
        self.cur = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fileName TEXT NOT NULL UNIQUE,
            ownerHash TEXT NOT NULL
        )
        """)
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS file_access (
            fileId INTEGER,
            accessUser TEXT,
            FOREIGN KEY (fileId) REFERENCES files(id)
        )
        """)
        self.conn.commit()

    def insert_file(self, file_name, owner_hash, access_users):
        self.cur.execute("INSERT INTO files (fileName, ownerHash) VALUES (?, ?)", (file_name, owner_hash))
        file_id = self.cur.lastrowid
        if access_users:
            self.cur.executemany("INSERT INTO file_access (fileId, accessUser) VALUES (?, ?)",
                                 [(file_id, user) for user in access_users])
        self.conn.commit()

    def get_all_files(self):
        self.cur.execute("""
        SELECT f.id, f.fileName, f.ownerHash, GROUP_CONCAT(a.accessUser)
        FROM files f
        LEFT JOIN file_access a ON f.id = a.fileId
        GROUP BY f.id
        """ )
        return self.cur.fetchall()

    def get_user_files(self, username, include_shared=True):
        if include_shared:
            self.cur.execute("""
            SELECT DISTINCT f.id, f.fileName, f.ownerHash
            FROM files AS f
            LEFT JOIN file_access AS a ON a.fileId = f.id
            WHERE f.ownerHash = ? OR a.accessUser = ?
            """, (username, username))
        else:
            self.cur.execute("""
            SELECT id, fileName, ownerHash
            FROM files
            WHERE ownerHash = ?
            """, (username,))
        files = self.cur.fetchall()
        return files

    def share_file_with_user(self, file_id, username):
        """Adds a user to the access list for a given file."""
        self.cur.execute("INSERT INTO file_access (fileId, accessUser) VALUES (?, ?)", (file_id, username))
        self.conn.commit()

    def has_access(self, username, file_name):
        """Checks if a user has access to a file."""
        self.cur.execute("""
        SELECT f.id
        FROM files f
        LEFT JOIN file_access a ON f.id = a.fileId
        WHERE (f.ownerHash = ? OR a.accessUser = ?) AND f.fileName = ?
        """, (username, username, file_name))
        return self.cur.fetchone() is not None

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    db_handler = DBHandler()
    
    # Example usage:
    # Clear tables for a clean run

    # Insert some files
    db_handler.insert_file("hi", "Admin", [])
    db_handler.insert_file("g", "Admin", ["Roee"])
    db_handler.conn.commit()




    db_handler.close()