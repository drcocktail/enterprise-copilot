import asyncio
import aiofiles
import os
import sys
from collections import deque

LOG_DIR = "logs"
LOG_FILES = {
    "GATEWAY": "gateway.log",
    "INGESTION": "ingestion.log",
    "CHAT": "chat.log",
    "CORE": "core.log",
    "FRONTEND": "frontend.log"
}

COLORS = {
    "GATEWAY": "\033[94m", # Blue
    "INGESTION": "\033[96m", # Cyan
    "CHAT": "\033[92m", # Green
    "CORE": "\033[93m", # Yellow
    "FRONTEND": "\033[95m", # Magenta
    "ERROR": "\033[91m", # Red
    "RESET": "\033[0m"
}

async def follow(name, filename):
    filepath = os.path.join(LOG_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Waiting for {filepath}...")
        while not os.path.exists(filepath):
            await asyncio.sleep(1)

    async with aiofiles.open(filepath, mode='r') as f:
        # Seek to end
        await f.seek(0, 2)
        
        while True:
            line = await f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            
            line = line.strip()
            if not line:
                continue

            color = COLORS.get(name, COLORS["RESET"])
            prefix = f"{color}[{name}]{COLORS['RESET']}"
            
            # Highlight errors
            if "ERROR" in line or "Exception" in line or "Traceback" in line or "failed" in line.lower():
                print(f"{prefix} {COLORS['ERROR']}{line}{COLORS['RESET']}")
            else:
                print(f"{prefix} {line}")

async def main():
    print(f"🚀 Starting Unified Log Monitor...")
    print(f"Monitoring: {', '.join(LOG_FILES.keys())}")
    print("-" * 50)
    
    tasks = []
    for name, filename in LOG_FILES.items():
        tasks.append(follow(name, filename))
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nStopping monitor...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
