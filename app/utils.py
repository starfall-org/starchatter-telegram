from pyrogram import enums, types
from app.database.cloud import cloud_db


async def is_chat_admin(user: types.User, chat: types.Chat) -> bool:
    member = await chat.get_member(user.id)
    return member.status == enums.ChatMemberStatus.ADMINISTRATOR


async def is_chat_owner(user: types.User, chat: types.Chat) -> bool:
    member = await chat.get_member(user.id)
    return member.status == enums.ChatMemberStatus.OWNER


async def is_owner(user: types.User) -> bool:
    return await cloud_db.is_owner(user.id)
