# FileNet

A simple FTP-like server for file storage and sharing.
## Instraction

* dont ever change between "\\" with "\"

## Features

*   **User authentication:** Login and register new users.
*   **File and directory management:** List, search, download, upload, and create directories.
*   **Repository management:** List user-specific repositories.
*   **Access control:** Share repositories with other users.

## Core Components

*   `Server.py`: The main server application that handles client connections and commands.
*   `DBHandler.py`: Manages the database for file and repository metadata.
*   `UserHandler.py`: Manages user data and authentication.
*   `BaseDBHandler.py`: A base class for database handlers, providing common database operations.

## Security

*   **SQL Injection:** The application uses parameterized queries to prevent SQL injection attacks.
*   **Spam and Brute-Force Protection:** Rate limiting is implemented to block clients that send too many requests in a short period.
*   **Input Validation:** Usernames and passwords are validated to ensure they meet the required format and complexity.
