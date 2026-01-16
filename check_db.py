import sqlite3
import time
import sys

# Wait for potential background write
print("Checking DB in 15 seconds...")
time.sleep(15)

try:
    conn = sqlite3.connect('backend/copilot.db')
    c = conn.cursor()
    c.execute("SELECT content FROM messages WHERE role='assistant' ORDER BY timestamp DESC LIMIT 1")
    row = c.fetchone()
    if row:
        print(f"LATEST_MESSAGE: {row[0][:100]}...")
        if len(row[0]) > 10:
             print("SUCCESS: Message saved.")
        else:
             print("FAILURE: Message too short.")
    else:
        print("NO_MESSAGE_FOUND")
    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
