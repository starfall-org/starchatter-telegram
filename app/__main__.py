import asyncio
# import uvloop

# Install uvloop and ensure an event loop exists before importing pyrogram
# uvloop.install()


from app.client import client
from app.main import main


if __name__ == "__main__":
    client.run(main())
