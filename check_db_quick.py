import sqlite3
import sys

try:
    conn = sqlite3.connect('backend/db.sqlite')
    c = conn.cursor()
    # Check for the specific query response
    c.execute("SELECT content FROM messages WHERE role='assistant' ORDER BY created_at DESC LIMIT 1")
    row = c.fetchone()
    if row:
        print(f"LATEST_MESSAGE: {row[0]}")
        if "def fibonacci" in row[0] or "fib" in row[0].lower():
             print("SUCCESS: Fibonacci function found.")
        else:
             print("NOTE: Latest message might not be the fibonacci one.")
    else:
        print("NO_MESSAGE_FOUND")
    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
