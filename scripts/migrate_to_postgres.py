#!/usr/bin/env python3
"""Migrate data from SQLite to PostgreSQL.

Usage:
    # Set environment variables
    export SQLITE_URL="sqlite:///./specterdefence.db"
    export POSTGRES_URL="postgresql+asyncpg://user:pass@localhost:5432/specterdb"
    
    # Run migration
    python scripts/migrate_to_postgres.py
"""

import asyncio
import sys
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def parse_datetime(value):
    """Parse SQLite datetime string to datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle various SQLite datetime formats
    if isinstance(value, str):
        # Try ISO format first
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
        # Try common formats
        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


async def migrate():
    """Migrate data from SQLite to PostgreSQL."""
    sqlite_url = "sqlite+aiosqlite:///./specterdefence.db"
    postgres_url = input("Enter PostgreSQL URL (postgresql+asyncpg://...): ").strip()

    if not postgres_url.startswith("postgresql+asyncpg://"):
        print("Error: URL must start with postgresql+asyncpg://")
        sys.exit(1)

    print("\nMigrating from SQLite to PostgreSQL...")
    print(f"Source: {sqlite_url}")
    print(f"Target: {postgres_url}")

    # Create engines
    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    postgres_engine = create_async_engine(postgres_url, echo=False)

    try:
        # Test connections
        async with sqlite_engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"\n✓ SQLite connection successful ({user_count} users found)")

        async with postgres_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("✓ PostgreSQL connection successful")

        # Confirm migration
        confirm = input("\nThis will delete existing PostgreSQL data and migrate from SQLite. Continue? (yes/no): ")
        if confirm.lower() != "yes":
            print("Migration cancelled.")
            return

        # Create tables in PostgreSQL
        print("\nCreating tables in PostgreSQL...")
        async with postgres_engine.begin() as conn:
            # Drop existing tables
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

            # Create users table
            await conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
                    last_login TIMESTAMP WITHOUT TIME ZONE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("✓ Tables created")

        # Migrate users
        print("\nMigrating users...")
        async with sqlite_engine.connect() as sqlite_conn:
            result = await sqlite_conn.execute(text("SELECT * FROM users"))
            users = result.fetchall()

            async with postgres_engine.begin() as pg_conn:
                for user in users:
                    # Convert SQLite integers to booleans for PostgreSQL
                    is_active = bool(user.is_active) if user.is_active is not None else True
                    is_admin = bool(user.is_admin) if user.is_admin is not None else False

                    # Convert SQLite datetime strings to datetime objects
                    last_login = parse_datetime(user.last_login)
                    created_at = parse_datetime(user.created_at) if user.created_at else datetime.now()
                    updated_at = parse_datetime(user.updated_at) if user.updated_at else datetime.now()

                    await pg_conn.execute(
                        text("""
                            INSERT INTO users (id, username, password_hash, is_active, is_admin, last_login, created_at, updated_at)
                            VALUES (:id, :username, :password_hash, :is_active, :is_admin, :last_login, :created_at, :updated_at)
                        """),
                        {
                            "id": user.id,
                            "username": user.username,
                            "password_hash": user.password_hash,
                            "is_active": is_active,
                            "is_admin": is_admin,
                            "last_login": last_login,
                            "created_at": created_at,
                            "updated_at": updated_at
                        }
                    )

                # Reset sequence
                if users:
                    max_id = max(u.id for u in users)
                    await pg_conn.execute(text(f"ALTER SEQUENCE users_id_seq RESTART WITH {max_id + 1}"))

            print(f"✓ Migrated {len(users)} users")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print(f"1. Update DATABASE_URL in your Kubernetes secret to: {postgres_url}")
        print("2. Restart the specterdefence deployment")
        print("3. Verify both pods can connect to PostgreSQL")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await sqlite_engine.dispose()
        await postgres_engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
