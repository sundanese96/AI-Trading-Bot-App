import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import read_database, load_ai_config

async def main():
    db = read_database()
    config = await load_ai_config()
    print("Database Keys in 'aiConfig':")
    for k, v in config.items():
        if "Key" in k or "key" in k:
            print(f"  {k}: {repr(v)}")
        else:
            print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
