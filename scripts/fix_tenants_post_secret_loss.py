import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings
from src.services.enhanced_encryption import encryption_service

async def fix_tenants():
    print("Fixing tenants due to lost encryption key...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Create a new encrypted secret that is just a placeholder
    # Because we have the NEW encryption key in env, this will successfully encrypt/decrypt
    placeholder = "LOST_SECRET_PLEASE_RECONNECT_TENANT"
    encrypted_placeholder = encryption_service.encrypt(placeholder)
    
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, name FROM tenants"))
        tenants = result.fetchall()
        
        for t in tenants:
            print(f"Resetting secret for tenant {t.name} ({t.id})")
            await conn.execute(
                text("UPDATE tenants SET client_secret = :secret, connection_status = 'error', connection_error = 'Encryption key was lost. Please edit this tenant and re-enter your client secret.' WHERE id = :id"),
                {"secret": encrypted_placeholder, "id": t.id}
            )
            
        print(f"Fixed {len(tenants)} tenants.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_tenants())
