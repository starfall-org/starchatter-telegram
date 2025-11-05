from datetime import datetime, timedelta

from ai.agent import AIAgent
from ai.shield import detector
from database.client import Database
from database.models import MutedCase, TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types

db = Database()


@Client.on_message(
    filters.incoming & filters.group,  # type: ignore
    group=1,
)
async def spam_detector(client: Client, message: types.Message):
    text = message.text or message.caption or ""

    async def mute_user_and_delete_message(reason: str, duration: int = 0):
        """
        Mute the user for a specified duration (in seconds).
        If duration less than 30, mute permanently.

        Args:
            reason (str): Reason for muting the user.
            duration (int): Duration in seconds to mute the user. Default is 0 (permanent mute).

        Returns:
            str: Success message or error message if muting fails.
        """
        bot_member = await client.get_chat_member(message.chat.id, client.me.id)  # type: ignore

        if bot_member.status != enums.ChatMemberStatus.ADMINISTRATOR:
            return "You must be an admin to mute users."
        bot_privileges = bot_member.privileges

        if not bot_privileges.can_restrict_members:
            return "I don't have enough privileges to mute users."

        user_member = await client.get_chat_member(
            message.chat.id, message.from_user.id
        )
        if user_member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]:
            return "Cannot mute an admin or owner."
        try:
            await message.chat.restrict_member(
                user_id=message.from_user.id,
                permissions=types.ChatPermissions(
                    all_perms=False,
                ),
                until_date=(datetime.now() + timedelta(seconds=duration)),
            )
            punished_case = MutedCase(
                user_id=message.from_user.id,
                group_id=message.chat.id,
                group_title=message.chat.title,
                group_username=message.chat.username,
                reason=reason,
                content=text,
            )
            await db.add(punished_case)
            await db.commit()
            if bot_privileges.can_delete_messages:
                return "User has been muted successfully."
            else:
                return "User has been muted successfully. You can't delete messages because you don't have enough privileges."
        except Exception as e:
            print(f"Error muting user: {e}")
            return str(e)

    detected = await detector(message, tools=[mute_user_and_delete_message])
    if detected:
        await message.reply_chat_action(enums.ChatAction.TYPING)
        await message.reply(detected)


@Client.on_message(
    (filters.mentioned | filters.private)
    & filters.incoming
    & ~filters.create(lambda _, __, m: m.text.startswith("/"))  # type: ignore
)
async def chatbot_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    agent = AIAgent()

    resp = await agent.run_chat(client, message)
    if resp:
        await message.reply(
            resp,
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN,
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
