import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.database import DATABASE_URL
from src.services.dashboard import DashboardService

async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine)
    async with async_session_maker() as session:
        service = DashboardService(session)
        print("Fetching top risk users...")
        try:
            result = await service.get_top_risk_users()
            print(f"Success! Found {result.total_users} users.")
            for user in result.users:
                print(f"- {user.user_email}: {user.risk_score} (Anomalies: {user.top_anomaly_types})")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
            
if __name__ == "__main__":
    asyncio.run(main())
