import sqlite3
import os

db_path = "backend/db.sqlite"

if not os.path.exists(db_path):
    print(f"❌ Database file not found at {db_path}")
else:
    print(f"✅ Database found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check Tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    # Check Conversations
    if 'conversations' in tables:
        cursor.execute("SELECT count(*) as count FROM conversations")
        count = cursor.fetchone()['count']
        print(f"Conversations: {count}")
        
        cursor.execute("SELECT * FROM conversations LIMIT 5")
        for row in cursor.fetchall():
            print(dict(row))
            
    # Check Repositories
    if 'repositories' in tables:
        cursor.execute("SELECT count(*) as count FROM repositories")
        count = cursor.fetchone()['count']
        print(f"Repositories: {count}")
        
        cursor.execute("SELECT * FROM repositories LIMIT 5")
        for row in cursor.fetchall():
            print(dict(row))

    conn.close()
