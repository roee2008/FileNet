from BaseDBHandler import BaseDBHandler

class DBHandler(BaseDBHandler):
    def __init__(self, db_name="ReposDB.sqlite"):
        super().__init__(db_name)
        self.create_tables()

    def create_tables(self):
        self._execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fileName TEXT NOT NULL UNIQUE,
            ownerHash TEXT NOT NULL
        )
        """)
        self._execute("""
        CREATE TABLE IF NOT EXISTS file_access (
            fileId INTEGER,
            accessUser TEXT,
            FOREIGN KEY (fileId) REFERENCES files(id)
        )
        """)

    def insert_file(self, file_name, owner_hash, access_users):
        cursor = self._execute("INSERT INTO files (fileName, ownerHash) VALUES (?, ?)", (file_name, owner_hash))
        file_id = cursor.lastrowid
        if access_users:
            self._execute("INSERT INTO file_access (fileId, accessUser) VALUES (?, ?)",
                                 [(file_id, user) for user in access_users])

    def get_all_files(self):
        return self._execute("""
        SELECT f.id, f.fileName, f.ownerHash, GROUP_CONCAT(a.accessUser)
        FROM files f
        LEFT JOIN file_access a ON f.id = a.fileId
        GROUP BY f.id
        """).fetchall()

    def get_user_files(self, username, include_shared=True):
        if include_shared:
            query = """
            SELECT DISTINCT f.id, f.fileName, f.ownerHash
            FROM files AS f
            LEFT JOIN file_access AS a ON a.fileId = f.id
            WHERE f.ownerHash = ? OR a.accessUser = ?
            """
            params = (username, username)
        else:
            query = """
            SELECT id, fileName, ownerHash
            FROM files
            WHERE ownerHash = ?
            """
            params = (username,)
        return self._execute(query, params).fetchall()

    def share_file_with_user(self, file_id, username):
        """Adds a user to the access list for a given file."""
        self._execute("INSERT INTO file_access (fileId, accessUser) VALUES (?, ?)", (file_id, username))

    def has_access(self, username, file_name):
        """Checks if a user has access to a file."""
        return self._execute("""
        SELECT f.id
        FROM files f
        LEFT JOIN file_access a ON f.id = a.fileId
        WHERE (f.ownerHash = ? OR a.accessUser = ?) AND f.fileName = ?
        """, (username, username, file_name)).fetchone() is not None

if __name__ == '__main__':
    db_handler = DBHandler()
    
    # Example usage:
    # Clear tables for a clean run

    # Insert some files
    db_handler.insert_file("hi", "Admin", [])
    db_handler.insert_file("g", "Admin", ["Roee"])

    db_handler.close()
