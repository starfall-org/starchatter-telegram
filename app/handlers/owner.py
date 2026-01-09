"""Owner authentication handler"""
from config import OWNER_PASSWORD
from database.cloud import cloud_db
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
    """Xác thực quyền owner bằng password"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    
    args = message.text.split()
    
    if len(args) < 2:
        await message.reply(
            "**Xác thực Owner**\n\n"
            "Nhập password để xác thực:\n"
            "`/owner <password>`",
            quote=True,
        )
        return
    
    password = args[1]
    
    if verify_password(password):
        # Thêm user vào danh sách owners (ghi qua cloud)
        user = message.from_user
        await db.add_owner(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        
        await message.reply(
            "✅ **Xác thực thành công!**\n\n"
            "Bạn đã được thêm vào danh sách owners.",
            quote=True,
        )
    else:
        await message.reply(
            "❌ **Xác thực thất bại!**\n\n"
            "Password không đúng.",
            quote=True,
        )
