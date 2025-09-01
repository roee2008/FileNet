import sqlite3

class BaseDBHandler:
    def __init__(self, db_name):
        """Initializes the database connection."""
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Connects to the SQLite database."""
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    def _execute(self, query, params=()):
        """Executes a SQL query."""
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor
