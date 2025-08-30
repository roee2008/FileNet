import sqlite3
import hashlib

class UserHandler():
    def __init__(self, db_name="UserDB.sqlite"):
        self.conn = sqlite3.connect(db_name)
        self.cur = self.conn.cursor()
        self.create_tables()

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_tables(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL
        )
        """)
        self.conn.commit()

    def new_user(self, username, password):
        hashed_password = self.hash_password(password)
        self.cur.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
        self.conn.commit()

    def get_user(self, username):
        self.cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        return self.cur.fetchone()

    def delete_user(self, username):
        self.cur.execute("DELETE FROM users WHERE username = ?", (username,))
        self.conn.commit()
        
    def update_password(self, username, new_password):
        new_hashed_password = self.hash_password(new_password)
        self.cur.execute("UPDATE users SET hashed_password = ? WHERE username = ?", (new_hashed_password, username))
        self.conn.commit()

    def close(self):
        self.conn.close()   

if __name__ == "__main__":
    user_handler = UserHandler()
    user_handler.update_password("Admin", "1")

