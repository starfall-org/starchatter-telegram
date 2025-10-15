from pyrogram import enums, types
from config import OWNER_ID


async def is_chat_admin(user: types.User, chat: types.Chat) -> bool:
    member = await chat.get_member(user.id)
    return member.status == enums.ChatMemberStatus.ADMINISTRATOR


async def is_chat_owner(user: types.User, chat: types.Chat) -> bool:
    member = await chat.get_member(user.id)
    return member.status == enums.ChatMemberStatus.OWNER


async def is_owner(user: types.User) -> bool:
    return user.id == OWNER_ID
