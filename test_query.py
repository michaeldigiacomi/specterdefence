import asyncio
from sqlalchemy import select, String, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.models.analytics import LoginAnalyticsModel

async def test():
    engine = create_async_engine("sqlite+aiosqlite:///specterdefence.db")
    async with AsyncSession(engine) as session:
        try:
            q = select(LoginAnalyticsModel).where(LoginAnalyticsModel.anomaly_flags != "[]").limit(1)
            result = await session.execute(q)
            print("!= '[]' works")
        except Exception as e:
            print(f"!= '[]' failed: {e}")

        try:
            q = select(LoginAnalyticsModel).where(func.json_array_length(LoginAnalyticsModel.anomaly_flags) > 0).limit(1)
            result = await session.execute(q)
            print("json_array_length works")
        except Exception as e:
            print(f"json_array_length failed: {e}")

        try:
            q = select(LoginAnalyticsModel).where(LoginAnalyticsModel.anomaly_flags.cast(String) != "[]").limit(1)
            result = await session.execute(q)
            print("cast != '[]' works")
        except Exception as e:
            print(f"cast != '[]' failed: {e}")

asyncio.run(test())
