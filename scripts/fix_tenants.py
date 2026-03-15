import asyncio
import os

# Override ENV to force sync with k8s
os.environ["DATABASE_URL"] = "postgresql+asyncpg://specterdefence_user:specterdefence123@100.110.214.40/specterdefence"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings
from src.services.encryption import encryption_service

async def fix_tenants():
    print("Fixing tenants due to lost encryption key...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    placeholder = "LOST_SECRET_PLEASE_RECONNECT_TENANT"
    encrypted_placeholder = encryption_service.encrypt(placeholder)

    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, name FROM tenants"))
        tenants = result.fetchall()

        for t in tenants:
            print(f"Resetting secret for tenant {t.name} ({t.id})")
            await conn.execute(
                text("UPDATE tenants SET client_secret = :secret, connection_status = 'error', connection_error = 'Encryption key was lost. Please reconnect this tenant in the dashboard.' WHERE id = :id"),
                {"secret": encrypted_placeholder, "id": t.id}
            )

        print(f"Fixed {len(tenants)} tenants.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_tenants())
