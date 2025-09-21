import hashlib
import os
from BaseDBHandler import BaseDBHandler

class SaveHandler(BaseDBHandler):
    def __init__(self, db_name="SaveDB.sqlite"):
        super().__init__(db_name)
        self.create_tables()

    def create_tables(self):
        self._execute("""
        CREATE TABLE IF NOT EXISTS Saves (
            id TEXT PRIMARY KEY,
            fileLoc TEXT NOT NULL,
            version INTEGER NOT NULL
        )
        """)

    def save_file(self, file_loc,file_change):
        cur = self.cursor
        
        # find the current max version for this fileLoc
        cur.execute("SELECT MAX(version) FROM Saves WHERE fileLoc = ?", (file_loc,))
        row = cur.fetchone()
        next_version = (row[0] or 0) + 1

        # build the id as a SHA256 hash of "fileLoc:version"
        raw = f"{file_loc}:{next_version}"
        id_hash = hashlib.sha256(raw.encode()).hexdigest()

        # insert new row
        cur.execute(
            "INSERT INTO Saves (id, fileLoc, version) VALUES (?, ?, ?)",
            (id_hash, file_loc, next_version)
        )
        os.makedirs("Abyss", exist_ok=True)
        file_path = os.path.join("Abyss", id_hash)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_change)
        self.conn.commit()
        return id_hash, next_version

if __name__ == '__main__':
    db_handler = SaveHandler()
    
    # Example usage:
    # Clear tables for a clean run
    # db_handler._execute("DELETE FROM Saves")
    # db_handler.commit()

    # Insert some files
    print(db_handler.save_file("C:/foo.txt","dsds"))

    db_handler.close()