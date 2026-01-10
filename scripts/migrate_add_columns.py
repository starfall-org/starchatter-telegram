"""
Migration script to add missing columns to database
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.cloud import cloud_db


async def migrate():
    """Add missing columns to telegram_users table"""
    from sqlalchemy import text

    print("Starting migration...")
    cloud_db.init_db()

    # Get session synchronously and run all operations in a thread
    def run_migration():
        session = cloud_db._get_session()
        if session is None:
            raise RuntimeError("Failed to get database session")

        try:
            # Check if is_owner column already exists
            result = session.execute(
                text(
                    "SELECT name FROM pragma_table_info('telegram_users') WHERE name = 'is_owner'"
                )
            )
            column_exists = result.fetchone() is not None

            if not column_exists:
                print("Adding 'is_owner' column to telegram_users...")
                session.execute(
                    text(
                        "ALTER TABLE telegram_users ADD COLUMN is_owner BOOLEAN DEFAULT 0"
                    )
                )
                session.commit()
                print("Added 'is_owner' column")
            else:
                print("'is_owner' column already exists")

            # Check and add other columns if needed
            result = session.execute(
                text(
                    "SELECT name FROM pragma_table_info('telegram_users') WHERE name = 'last_name'"
                )
            )
            if result.fetchone() is None:
                session.execute(
                    text("ALTER TABLE telegram_users ADD COLUMN last_name VARCHAR(100)")
                )
                session.commit()
                print("Added 'last_name' column")
        finally:
            session.close()

    await asyncio.to_thread(run_migration)
    print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
