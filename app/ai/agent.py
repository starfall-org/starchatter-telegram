import asyncio
from datetime import datetime, timedelta
from agents import Agent, Runner, SQLiteSession, function_tool, mcp
from agents.extensions.models.litellm_model import LitellmModel
from ai.base import get_model, list_models, set_model, update_models
from config import UPSTAGE_API, UPSTAGE_URL, A21_API, A21_URL
from database.client import Database
from pyrogram import Client, types

db = Database()


class AIAgent:
    def __init__(self):
        self.model_id = get_model()
        upstage_model = LitellmModel(
            model="openai/" + self.model_id,
            base_url=UPSTAGE_URL,
            api_key=UPSTAGE_API,
        )
        a21_model = LitellmModel(
            model="openai/" + self.model_id,
            base_url=A21_URL,
            api_key=A21_API,
        )
        if self.model_id in update_models():
            self.litellm_model = upstage_model
        else:
            self.litellm_model = a21_model

    def star_chatter(
        self,
        mcp_server: list,
        message: types.Message,
        functions: list = [],
    ):
        full_name = (
            (
                f"{message.sender_chat.title} (Group/Anonymous Admin)"
                if message.sender_chat.title == message.chat.title
                else f"{message.sender_chat.title} (Channel/Anonymous User)"
            )
            if message.sender_chat
            else message.from_user.full_name
        )
        user_id = (
            message.sender_chat.id if message.sender_chat else message.from_user.id
        )
        return Agent(
            "StarChatter",
            instructions=f"""You are **StarChatter**. You are powered by model `{self.model_id}`. You can do everything. To mention a user, use `[user_fullname](tg://user?id=[user_id]). 
            - user_fullname: {full_name}
            - user_id: {user_id}
            - message_id: {message.id}
            - previos_message_id: user_message_id - i (i = user_message_id - len(messages_until_target))""",
            tools=functions,
            model=self.litellm_model,
            mcp_servers=mcp_server,
        )

    async def run_chat(
        self, client: Client, message: types.Message, prompt: str | None = None
    ):
        chat_id = message.chat.id
        session = SQLiteSession(f"chat_{chat_id}", "conversations.sqlite")

        @function_tool
        def clear_your_memory():
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(session.clear_session(), loop)
            return "History cleared."

        @function_tool
        def mute_user(
            user_id: int,
            duration_seconds: int = 0,
        ):
            """
            Mute the user for a specified duration (in seconds).
            If duration less than 30s, mute permanently.

            Args:
                reason (str): Reason for muting the user.
                duration_seconds (int): Duration in seconds to mute the user. Default is 0 (permanent mute).

            Returns:
                str: Success message or error message if muting fails.
            """
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                message.chat.restrict_member(
                    user_id,
                    permissions=types.ChatPermissions(
                        all_perms=False,
                    ),
                    until_date=(datetime.now() + timedelta(seconds=duration_seconds)),
                ),
                loop,
            )
            return "Action completed."

        @function_tool
        def unmute_user(
            group_id: int,
            user_id: int,
        ):
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                client.restrict_chat_member(
                    group_id, user_id, permissions=types.ChatPermissions(all_perms=True)
                ),
                loop,
            )

            return "Action completed."

        @function_tool
        def delete_message(message_ids: int | list[int] | None = None):
            """Delete message with id if provided, otherwise delete the message that triggered the command.

            Args:
                message_ids (int | list[int] | None, optional): Message ID or list of message IDs to delete. Defaults to None and deletes the message that triggered the command.

            Returns:
                str: Success message

            """
            loop = asyncio.get_event_loop()
            if message_ids:
                asyncio.run_coroutine_threadsafe(
                    client.delete_messages(message.chat.id, message_ids), loop
                )
            else:
                asyncio.run_coroutine_threadsafe(message.delete(), loop)
            return "Action completed."

        async with mcp.MCPServerSse(
            name="Tools",
            params={"url": "https://nymbo-tools.hf.space/gradio_api/mcp/sse"},
            cache_tools_list=True,
        ) as mcp_server:
            text = (
                prompt or (message.text or message.caption or "") + f"\n[{message.id}]"
            )
            res = await Runner.run(
                self.star_chatter(
                    mcp_server=[mcp_server],
                    message=message,
                    functions=[
                        mute_user,
                        unmute_user,
                        delete_message,
                        clear_your_memory,
                        list_models,
                        set_model,
                    ],
                ),
                text,
                session=session,
            )
            return res.final_output
