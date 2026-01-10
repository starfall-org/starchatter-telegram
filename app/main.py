from sqlalchemy import select
from pyrogram import idle
from app.client import client
from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider, DefaultModel, TelegramGroup, TelegramUser


async def sync_cloud_to_local(cloud_db, local_db):
    """Sync all data from cloud to local"""

    models = [AIProvider, TelegramUser, TelegramGroup, DefaultModel]

    for model in models:
        try:
            # Lấy tất cả từ cloud
            result = await cloud_db.execute(select(model))
            cloud_objects = result.scalars().all()

            # Lấy tất cả từ local
            result = await local_db.execute(select(model))
            local_objects = result.scalars().all()

            # Create ID set for comparison
            cloud_ids = {obj.id for obj in cloud_objects}
            local_ids = {obj.id for obj in local_objects}

            # Add objects present in cloud but not in local
            for obj in cloud_objects:
                if obj.id not in local_ids:
                    # Create a new object instance to avoid session conflicts
                    obj_copy = type(obj)(
                        ** {col.name: getattr(obj, col.name)
                           for col in obj.__table__.columns
                           if hasattr(obj, col.name)}
                    )
                    await local_db.add(obj_copy)

            # Remove objects present in local but not in cloud
            for obj in local_objects:
                if obj.id not in cloud_ids:
                    # Create a new object instance to avoid session conflicts
                    obj_copy = type(obj)(
                        ** {col.name: getattr(obj, col.name)
                           for col in obj.__table__.columns
                           if hasattr(obj, col.name)}
                    )
                    await local_db.delete(obj_copy)

            print(f"Synced {len(cloud_objects)} {model.__name__} records")
        except Exception as e:
            print(f"Error syncing {model.__name__}: {e}")


async def main():
    await client.start()
    cloud_db.init_db()
    local_db.init_db()

    # Sync từ cloud về local
    print("Syncing data from cloud to local...")
    # try:
    await sync_cloud_to_local(cloud_db, local_db)
    # except Exception as e:
    #     print(f"Sync error: {e}")
    print("Sync completed.")
    await idle()
    await client.stop()
