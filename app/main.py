import uvloop

uvloop.install()


async def main():
    from ai.base import setup_agent
    from client import client
    from database.client import Database
    from pyrogram import idle

    await client.start()
    setup_agent()
    print("Bot started.")
    db = Database()
    db.init_db()
    await idle()
    await client.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
