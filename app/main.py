import uvloop

uvloop.install()


async def sync_cloud_to_local(cloud_db, local_db):
    """Sync tất cả dữ liệu từ cloud về local"""
    from database.models import AIProvider, TelegramUser, TelegramGroup, DefaultModel, Base
    from sqlalchemy import select

    models = [AIProvider, TelegramUser, TelegramGroup, DefaultModel]

    for model in models:
        try:
            # Lấy tất cả từ cloud
            result = await cloud_db.execute(select(model))
            cloud_objects = result.scalars().all()

            # Lấy tất cả từ local
            result = await local_db.execute(select(model))
            local_objects = result.scalars().all()

            # Tạo set ID để so sánh
            cloud_ids = {obj.id for obj in cloud_objects}
            local_ids = {obj.id for obj in local_objects}

            # Thêm những object có trong cloud nhưng không có trong local
            for obj in cloud_objects:
                if obj.id not in local_ids:
                    await local_db.add(obj)

            # Xóa những object có trong local nhưng không có trong cloud
            for obj in local_objects:
                if obj.id not in cloud_ids:
                    await local_db.delete(obj)

            print(f"Synced {len(cloud_objects)} {model.__name__} records")
        except Exception as e:
            print(f"Error syncing {model.__name__}: {e}")


async def main():
    from client import client
    from database.cloud import cloud_db
    from database.local import local_db
    from pyrogram import idle

    await client.start()
    print("Bot started.")

    # Khởi tạo cả hai databases
    cloud_db.init_db()
    local_db.init_db()

    # Sync từ cloud về local
    print("Syncing data from cloud to local...")
    await sync_cloud_to_local(cloud_db, local_db)
    print("Sync completed.")

    await idle()
    await client.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
