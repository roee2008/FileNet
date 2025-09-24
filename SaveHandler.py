import hashlib
import os
import difflib
from BaseDBHandler import BaseDBHandler


class DiffCheck:
    def check_diff(self, old_file, new_file):
        with open(old_file, 'r', encoding='utf-8') as f:
            old_file_content = f.readlines()
        with open(new_file, 'r', encoding='utf-8') as f:
            new_file_content = f.readlines()

        diff = difflib.unified_diff(
            old_file_content,
            new_file_content,
            fromfile='old_file',
            tofile='new_file',
            lineterm='',
        )

        for line in diff:
            print(line)

    def apply_patch(self, patch_content, old_content):
        """
        Applies a unified diff patch to a string content.
        Returns the new string content.
        Raises ValueError if the patch does not apply cleanly.
        """
        patch_lines = patch_content.splitlines()
        old_lines = old_content.splitlines()
        new_lines = []
        old_line_idx = 0
        
        patch_iter = iter(patch_lines)
        # Skip header lines until '@@'
        for line in patch_iter:
            if line.startswith('@@'):
                break
        
        # Process hunk lines
        for line in patch_iter:
            if not line: continue
            
            if line.startswith(' '):
                # Context line
                context_line = line[1:]
                if old_line_idx < len(old_lines) and old_lines[old_line_idx] == context_line:
                    new_lines.append(old_lines[old_line_idx])
                    old_line_idx += 1
                else:
                    raise ValueError("Patch does not apply: context mismatch")
            elif line.startswith('-'):
                # Deletion line
                deleted_line = line[1:]
                if old_line_idx < len(old_lines) and old_lines[old_line_idx] == deleted_line:
                    old_line_idx += 1
                else:
                    raise ValueError("Patch does not apply: deletion mismatch")
            elif line.startswith('+'):
                # Addition line
                added_line = line[1:]
                new_lines.append(added_line)
                
        # Append any remaining lines from the old file
        if old_line_idx < len(old_lines):
            new_lines.extend(old_lines[old_line_idx:])
                
        return '\n'.join(new_lines)
    
    
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
        raw = f"{file_loc}"
        id_hash = hashlib.sha256(raw.encode()).hexdigest()

        # insert new row
        self._execute("UPDATE Saves SET version = ? WHERE id = ?", (next_version, id_hash))
        # cur.execute(
        #     "INSERT INTO Saves (id, fileLoc, version) VALUES (?, ?, ?)",
        #     (id_hash, file_loc, next_version)
        # )
        os.makedirs("Abyss", exist_ok=True)
        file_path = os.path.join("Abyss", id_hash)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{file_change}\nV{next_version}\n")
        self.conn.commit()
        return id_hash, next_version

if __name__ == '__main__':
    db_handler = SaveHandler()
    
    # Example usage:
    # Clear tables for a clean run
    # db_handler._execute("DELETE FROM Saves")
    # db_handler.commit()

    # Insert some files
    print(db_handler.save_file("C:/foo.txt","ddddds"))

    db_handler.close()