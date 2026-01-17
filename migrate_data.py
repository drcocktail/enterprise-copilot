import sqlite3
import os

db_path = "backend/db.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Migration Started...")

# 1. Update Repositories
cursor.execute("SELECT count(*) FROM repositories WHERE user_id = 'CHIEF_STRATEGY_OFFICER'")
count_repo = cursor.fetchone()[0]
if count_repo > 0:
    cursor.execute("UPDATE repositories SET user_id = 'PRINCIPAL_ARCHITECT' WHERE user_id = 'CHIEF_STRATEGY_OFFICER'")
    print(f"Updated {count_repo} repositories to PRINCIPAL_ARCHITECT")

# 2. Update Conversations
cursor.execute("SELECT count(*) FROM conversations WHERE user_id = 'CHIEF_STRATEGY_OFFICER'")
count_conv = cursor.fetchone()[0]
if count_conv > 0:
    cursor.execute("UPDATE conversations SET user_id = 'PRINCIPAL_ARCHITECT' WHERE user_id = 'CHIEF_STRATEGY_OFFICER'")
    print(f"Updated {count_conv} conversations to PRINCIPAL_ARCHITECT")

conn.commit()
conn.close()
print("Migration Complete.")
