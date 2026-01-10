from app.database.local import local_db
from pyrogram import Client, enums, filters, types


@Client.on_chat_join_request(filters.chat)  # type: ignore
async def on_chat_join_request(client: Client, message: types.Message):
    chat = message.chat

    if chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await local_db.add_group(
            group_id=chat.id,
            title=chat.title or "",
            username=chat.username,
        )
    elif chat.type == enums.ChatType.CHANNEL:
        await local_db.add_channel(
            channel_id=chat.id,
            title=chat.title or "",
            username=chat.username,
        )


@Client.on_message(filters.new_chat_members)  # type: ignore
async def on_new_chat_members(client: Client, message: types.Message):
    chat = message.chat
    new_members = message.new_chat_members

    for member in new_members:
        if member.is_self:
            if chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                await local_db.add_group(
                    group_id=chat.id,
                    title=chat.title or "",
                    username=chat.username,
                )
                inviter = message.from_user
                if inviter:
                    try:
                        chat_member = await chat.get_member(inviter.id)
                        is_admin = chat_member.status in [
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER,
                        ]
                        is_owner = chat_member.status == enums.ChatMemberStatus.OWNER
                    except Exception:
                        is_admin = False
                        is_owner = False

                    user = await local_db.get_user(inviter.id)
                    if user:
                        await local_db.add_or_update_user(
                            user_id=inviter.id,
                            username=inviter.username,
                            first_name=inviter.first_name,
                            last_name=inviter.last_name,
                        )
                        await local_db.add_group_member(
                            user_id=inviter.id,
                            group_id=chat.id,
                            is_admin=is_admin,
                            is_owner=is_owner,
                        )

            elif chat.type == enums.ChatType.CHANNEL:
                await local_db.add_channel(
                    channel_id=chat.id,
                    title=chat.title or "",
                    username=chat.username,
                )
                inviter = message.from_user
                if inviter:
                    try:
                        chat_member = await chat.get_member(inviter.id)
                        is_admin = chat_member.status in [
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER,
                        ]
                        is_owner = chat_member.status == enums.ChatMemberStatus.OWNER
                    except Exception:
                        is_admin = False
                        is_owner = False

                    user = await local_db.get_user(inviter.id)
                    if user:
                        await local_db.add_or_update_user(
                            user_id=inviter.id,
                            username=inviter.username,
                            first_name=inviter.first_name,
                            last_name=inviter.last_name,
                        )
                        await local_db.add_channel_member(
                            user_id=inviter.id,
                            channel_id=chat.id,
                            is_admin=is_admin,
                            is_owner=is_owner,
                        )

        else:
            if chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                inviter = message.from_user
                is_admin = False
                is_owner = False
                if inviter:
                    try:
                        chat_member = await chat.get_member(inviter.id)
                        is_admin = chat_member.status in [
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER,
                        ]
                        is_owner = chat_member.status == enums.ChatMemberStatus.OWNER
                    except Exception:
                        pass

                await local_db.add_group_member(
                    user_id=member.id,
                    group_id=chat.id,
                    is_admin=is_admin,
                    is_owner=is_owner,
                )
