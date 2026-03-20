import asyncio
import sys
import os

# Add the current directory to sys.path to import src
sys.path.insert(0, os.getcwd())

from sqlalchemy import select, func
from src.database import async_session_maker
from src.models.audit_log import AuditLogModel, LogType
from src.models.sharepoint import SharePointSharingModel

async def check_db():
    async with async_session_maker() as session:
        # Count total SharePoint audit logs
        result = await session.execute(
            select(func.count(AuditLogModel.id)).where(AuditLogModel.log_type == LogType.SHAREPOINT)
        )
        total_sp_logs = result.scalar()
        print(f"Total SharePoint audit logs: {total_sp_logs}")

        # Count unprocessed SharePoint audit logs
        result = await session.execute(
            select(func.count(AuditLogModel.id)).where(
                AuditLogModel.log_type == LogType.SHAREPOINT,
                AuditLogModel.processed == False
            )
        )
        unprocessed_sp_logs = result.scalar()
        print(f"Unprocessed SharePoint audit logs: {unprocessed_sp_logs}")

        # Count SharePoint sharing analytics records
        result = await session.execute(select(func.count(SharePointSharingModel.id)))
        sharing_records = result.scalar()
        print(f"Total SharePoint sharing records: {sharing_records}")

        # Sample operations from SharePoint logs
        result = await session.execute(
            select(func.distinct(AuditLogModel.raw_data['Operation']))
            .where(AuditLogModel.log_type == LogType.SHAREPOINT)
            .limit(10)
        )
        ops = result.scalars().all()
        print(f"Sample operations found: {ops}")

if __name__ == "__main__":
    asyncio.run(check_db())
