from ai.anti_spam import detector
from ai.base import BaseFactory
from database.client import Database
from database.models import TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types

base = BaseFactory()
db = Database()


@Client.on_message(
    filters.text
    & filters.incoming
    & (filters.private | filters.mentioned)
    # pyright: ignore[reportArgumentType]
    & ~filters.create(lambda _, __, m: m.text.startswith("/"))
)
async def chatbot_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)

    content = await base.chat(message.text, message.chat.id)

    await message.reply(
        content or "Something went wrong!", reply_to_message_id=message.id
    )

    if not message.sender_chat:
        user = await db.get(TelegramUser, id=message.from_user.id)
        user = user.scalars().first()
        if not user:
            await db.add(
                TelegramUser(
                    id=message.from_user.id,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    username=message.from_user.username,
                )
            )
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group = await db.get(TelegramGroup, id=message.chat.id)
        group = group.scalars().first()
        if not group:
            await db.add(
                TelegramGroup(
                    id=message.chat.id,
                    title=message.chat.title,
                    username=message.chat.username,
                )
            )


@Client.on_message(filters.group & filters.incoming, group=1)  # type: ignore
async def detect_spam_handler(client: Client, message: types.Message):
    text = message.text or message.caption or ""
    if text:
        result = await detector(text)
        if result.get("is_spam"):
            group = await db.get(TelegramGroup, id=message.chat.id)
            group = group.scalars().first()
            if group and (not group.disable_anti_spam):
                bot_member = await client.get_chat_member(
                    message.chat.id,
                    client.me.id,  # type: ignore
                )
                if (
                    bot_member.status == enums.ChatMemberStatus.ADMINISTRATOR
                    and bot_member.privileges.can_delete_messages
                ):
                    actions = []
                    try:
                        await message.delete()
                        actions.append("deleted the message")
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                    try:
                        user_member = await client.get_chat_member(
                            message.chat.id, message.from_user.id
                        )
                        if user_member.status in [
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER,
                        ]:
                            actions.append(
                                "no action against the user (they are an admin/owner)"
                            )
                        else:
                            if user_member.status == enums.ChatMemberStatus.RESTRICTED:
                                actions.append("user is already restricted")
                            await message.chat.restrict_member(
                                user_id=message.from_user.id,
                                permissions=types.ChatPermissions(
                                    all_perms=False,
                                ),
                            )
                            actions.append("restricted the user")
                    except Exception as e:
                        print(f"Error sending reply: {e}")

                    if actions:
                        action_text = " and ".join(actions)
                        reason = result.get("reason", "No reason provided")
                        reply_text = f"⚠️ __User **{message.from_user.first_name}** was detected as spam and I have {action_text}.__\n\n**Reason:** ```\n{reason}\n```"
                        try:
                            await message.reply(reply_text)
                        except Exception as e:
                            print(f"Error sending reply: {e}")

                else:
                    print("Bot does not have permission to delete messages.")
