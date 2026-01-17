import asyncio
import uuid
import random
from services.db_service import DatabaseService
from datetime import datetime, timedelta

async def create_dummy_data():
    db = DatabaseService()
    print("Database path:", db.db_path)
    
    # User ID defaults to 'senior_engineer' to match frontend ChatView.jsx hardcoded role
    user_id = "senior_engineer"
    
    conversations = [
        {
            "title": "Docker Setup Help",
            "messages": [
                ("user", "How do I list running containers?"),
                ("assistant", "You can use `docker ps` to list running containers."),
                ("user", "What about stopped ones?"),
                ("assistant", "Use `docker ps -a` to see all containers including stopped ones.")
            ]
        },
        {
            "title": "Python Async Debugging",
            "messages": [
                ("user", "My async function is blocking the loop."),
                ("assistant", "Make sure you use `await` and don't call blocking IO functions directly. Use `run_in_executor` for blocking calls."),
                ("user", "Can you show me an example?"),
                ("assistant", "Sure! Here is an example:\n\n```python\nloop = asyncio.get_running_loop()\nawait loop.run_in_executor(None, blocking_function)\n```")
            ]
        },
        {
            "title": "Project Architecture",
            "messages": [
                ("user", "Explain the backend architecture."),
                ("assistant", "The backend is built with FastAPI and uses a microservices approach (modular monolith). Services include LLMService, DBService, and CodeIngestionService.")
            ]
        }
    ]
    
    print("\nCreating dummy conversations...")
    
    for convo in conversations:
        # Create conversation
        c_id = str(uuid.uuid4())
        # Simulate past time
        created_at = (datetime.now() - timedelta(days=random.randint(0, 5))).isoformat()
        
        # Manually insert to override timestamp (db_service methods use now())
        conn = db._get_connection()
        conn.execute(
            "INSERT INTO conversations (id, user_id, role, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (c_id, user_id, "user", convo["title"], created_at, created_at)
        )
        conn.commit()
        
        # Add messages
        for role, content in convo["messages"]:
            await db.add_message(c_id, role, content)
            
        print(f"Created '{convo['title']}' ({c_id})")
        
    print("\n✅ Dummy data created successfully!")

if __name__ == "__main__":
    asyncio.run(create_dummy_data())
