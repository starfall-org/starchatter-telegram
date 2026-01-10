"""Owner authentication handler"""
from app.config import OWNER_PASSWORD
from app.database.cloud import cloud_db
from pyrogram import Client, enums, filters, types

db = cloud_db


def verify_password(password: str) -> bool:
    """Verify password (plain text)"""
    if not OWNER_PASSWORD:
        return False
    return password == OWNER_PASSWORD


def is_user_owner(user_id: int) -> bool:
    """Check if user is owner (sync wrapper)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(db.is_owner(user_id))


@Client.on_message(filters.command("owner") & filters.private)  # type: ignore
async def owner_handler(client: Client, message: types.Message):
    """Verify owner privilege with password"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    
    args = message.text.split()
    
    if len(args) < 2:
        await message.reply(
            "**Owner Verification**\n\n"
            "Enter password to verify:\n"
            "/owner <password>",
            quote=True,
        )
        return
    
    password = args[1]
    
    if verify_password(password):
        # Add user to owners list (write via cloud)
        user = message.from_user
        await db.add_owner(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        
        await message.reply(
            "✅ **Verification successful!**\n\n"
            "You have been added to the owners list.",
            quote=True,
        )
    else:
        await message.reply(
            "❌ **Verification failed!**\n\n"
            "Password is incorrect.",
            quote=True,
        )
