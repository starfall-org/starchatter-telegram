from datetime import datetime, timedelta

from ai.base import BaseFactory
from database.client import Database
from database.models import MutedCase, TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types
from sqlalchemy import select

base = BaseFactory()
db = Database()


@Client.on_message(filters.incoming)  # type: ignore
async def chatbot_handler(client: Client, message: types.Message):
    text = message.text or message.caption or ""
    filtered = (
        client.me.username in text  # type: ignore
        or "StarChatter" in text
        or (
            (
                message.reply_to_message.from_user.id == client.me.id  # type: ignore
                if message.reply_to_message.from_user
                else False
            )
            if message.reply_to_message
            else False
        )
        or message.chat.type == enums.ChatType.PRIVATE
    ) and not text.startswith("/")

    if filtered:
        await message.reply_chat_action(enums.ChatAction.TYPING)

    async def mute_user(reason: str, duration: int = 0):
        f"""
        Mute the user for a specified duration (in seconds).
        If duration less than 30, mute permanently.
        After muting, send a notification message to the user about the mute reason in the language have language code '{message.from_user.language_code}'. And tell them contact admin to unmute or contact you to appeal, you will recheck user's case.

        Args:
            reason (str): Reason for muting the user in the language have language code '{message.from_user.language_code}'.
            duration (int): Duration in seconds to mute the user. Default is 0 (permanent mute).

        Returns:
            str: Success message or error message if muting fails.

        """
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
            return "User has been muted successfully."
        except Exception as e:
            print(f"Error muting user: {e}")
            return str(e)

    async def unmute_user(user_id: int, chat_id: int):
        """
        Unmute the user.

        Returns:
            str: Success message or error message if unmuting fails.
        """
        try:
            await message.chat.restrict_member(
                user_id=message.from_user.id,
                permissions=types.ChatPermissions(
                    all_perms=True,
                ),
            )
            return "User has been unmuted successfully."
        except Exception as e:
            print(f"Error unmuting user: {e}")
            return str(e)

    async def delete_message():
        """
        Delete the offending message.

        Returns:
            str: Success message or error message if deletion fails.
        """
        try:
            await message.delete()
            return "Message has been deleted successfully."
        except Exception as e:
            print(f"Error deleting message: {e}")
            return str(e)

    async def get_user_muted_case(
        group_title: str | None = None,
        group_username: str | None = None,
        group_id: int | None = None,
    ) -> str:
        """
        Check if the user is currently muted in the chat. If muted, return json object of the muted case.

        Args:
            group_title (str | None, optional): Group title. Defaults to None.
            group_username (str | None, optional): Group username. Defaults to None.
            group_id (int | None, optional): Group ID. Defaults to None.

        Returns:
            str: Python object of the muted case or a message indicating no mute found.

        """
        if group_id:
            query = select(MutedCase).where(
                MutedCase.group_id == group_id,
                MutedCase.user_id == message.from_user.id,
            )
            result = await db.execute(query)
        if group_username and not group_id:
            query = select(MutedCase).where(
                MutedCase.group_username == group_username,
                MutedCase.user_id == message.from_user.id,
            )
            result = await db.execute(query)
        if group_title and not group_username and not group_id:
            query = select(MutedCase)
            results = await db.execute(query)
            for item in results:
                if (
                    group_title.lower() in item.group_title.lower()
                    and item.user_id == message.from_user.id
                ):
                    result = await db.execute(
                        select(MutedCase).where(MutedCase.id == item.id)
                    )
                    break
        else:
            return "Please provide at least one identifier: group_title, group_username, or group_id."
        muted_case = result.scalars().first()
        if muted_case and isinstance(muted_case, MutedCase):
            return str(muted_case)
        return "This case not found in database."

    tools = [
        unmute_user,
        get_user_muted_case,
        delete_message,
    ]
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        tools.append(mute_user)

    photo_bytes = None
    if message.photo:
        photo = await message.download(in_memory=True)
        photo_bytes = photo.getvalue()  # type: ignore

    async for content, tool_called in base.chat(
        text, message.chat.id, filtered, tools, photo=photo_bytes
    ):
        if tool_called and filtered:
            await message.reply(content, reply_to_message_id=message.id)
    if filtered and not message.sender_chat:
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
