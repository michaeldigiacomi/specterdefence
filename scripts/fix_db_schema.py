import asyncio
import os
import sys

# Override ENV to force sync with k8s
os.environ["DATABASE_URL"] = "postgresql+asyncpg://specterdefence_user:specterdefence123@100.110.214.40/specterdefence"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def migrate():
    print("Fixing database timestamps for asyncpg...")
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    
    async with engine.begin() as conn:
        # Get all timestamp columns
        result = await conn.execute(text("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND data_type = 'timestamp without time zone'
        """))
        columns = result.fetchall()
        
        if not columns:
            print("No naive timestamp columns found.")
            return

        for row in columns:
            table = row[0]
            column = row[1]
            print(f"Altering {table}.{column} to TIMESTAMPTZ...")
            try:
                await conn.execute(text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE TIMESTAMPTZ'))
            except Exception as e:
                print(f"  Failed for {table}.{column}: {e}")
            
        print("Database schema migration complete.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
