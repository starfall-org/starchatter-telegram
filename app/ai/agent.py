import asyncio
from datetime import datetime, timedelta
import os
from agents import Agent, Runner, SQLiteSession, function_tool, mcp
from agents.extensions.models.litellm_model import LitellmModel
from ai.base import get_model, list_models, set_model
from config import AI_API_KEY, AI_BASE_URL
from database.client import Database
from database.models import MutedCase
from pyrogram import Client, types
from sqlalchemy import select

db = Database()


def _get_user_muted_case(
    message: types.Message,
    group_title: str | None = None,
    group_username: str | None = None,
    group_id: int | None = None,
) -> str | None:
    session = db._get_session()
    if session:
        if group_id:
            query = select(MutedCase).where(
                MutedCase.group_id == group_id,
                MutedCase.user_id == message.from_user.id,
            )
            result = session.execute(query)
        if group_username and not group_id:
            query = select(MutedCase).where(
                MutedCase.group_username == group_username,
                MutedCase.user_id == message.from_user.id,
            )
            result = session.execute(query)
        if group_title and not group_username and not group_id:
            query = select(MutedCase)
            results = session.execute(query)
            for item in results:
                if (
                    group_title.lower() in item.group_title.lower()
                    and item.user_id == message.from_user.id
                ):
                    result = session.execute(
                        select(MutedCase).where(MutedCase.id == item.id)
                    )
                    break
        else:
            return "Please provide at least one identifier: group_title, group_username, or group_id."
        muted_case = result.scalars().first()
        if muted_case and isinstance(muted_case, MutedCase):
            return str(muted_case)
        return "This case not found in database."


@function_tool
def get_violation_rules():
    preset = os.environ.get(
        "PRESET_VIOLATION_RULES",
        "No violation rules found. Use default rules: 'spam, unsafe advertisement'.",
    )
    return preset


@function_tool
def set_violation_rules(rules: str):
    os.environ["PRESET_VIOLATION_RULES"] = rules
    return "Violation rules set."


class AIAgent:
    def __init__(self):
        self.model_id = get_model()
        self.litellm_model = LitellmModel(
            model="openai/" + self.model_id,
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY,
        )

    def star_chatter(
        self,
        mcp_server: list,
        message: types.Message,
        functions: list = [],
    ):
        return Agent(
            "StarChatter",
            instructions=f"You are **StarChatter**. You are powered by model `{self.model_id}`. You can do everything. Remember to use tools if required. \nuser_message_id: {message.id}\nassistant_message_id: list of [user_message_id + (1 per 4000 characters)]",
            tools=functions,
            model=self.litellm_model,
            mcp_servers=mcp_server,
        )

    async def run_chat(
        self, client: Client, message: types.Message, detected: str | None = None
    ):
        chat_id = message.chat.id
        session = SQLiteSession(f"chat_{chat_id}", "conversations.sqlite")

        @function_tool
        def clear_your_memory():
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(session.clear_session(), loop)
            return "History cleared."

        @function_tool
        def get_user_muted_case(
            group_title: str | None = None,
            group_username: str | None = None,
            group_id: int | None = None,
        ):
            """
            Check if the user is currently muted in the chat. If muted, return json object of the muted case.

            Args:
                group_title (str | None, optional): Group title. Defaults to None.
                group_username (str | None, optional): Group username. Defaults to None.
                group_id (int | None, optional): Group ID. Defaults to None.

            Returns:
                str: Python object of the muted case or a message indicating no mute found.

            """
            return _get_user_muted_case(message, group_title, group_username, group_id)

        @function_tool
        def mute_user(
            user_id: int,
            reason: str,
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
            text = message.text or message.caption or ""
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
            punished_case = MutedCase(
                user_id=message.from_user.id,
                group_id=message.chat.id,
                group_title=message.chat.title,
                group_username=message.chat.username,
                reason=reason,
                content=text,
            )
            asyncio.run_coroutine_threadsafe(db.add(punished_case), loop)
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
        def delete_message(message_id: int | None = None):
            """Delete message with id if provided, otherwise delete the message that triggered the command.

            Args:
                message_id (int | None, optional): Message ID to delete. Defaults to None and deletes the message that triggered the command.

            Returns:
                str: Success message

            """
            loop = asyncio.get_event_loop()
            if message_id:
                asyncio.run_coroutine_threadsafe(
                    client.delete_messages(message.chat.id, [message_id]), loop
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
                detected
                or (message.text or message.caption or "") + f"\n[{message.id}]"
            )
            res = await Runner.run(
                self.star_chatter(
                    mcp_server=[mcp_server],
                    message=message,
                    functions=[
                        get_user_muted_case,
                        mute_user,
                        unmute_user,
                        delete_message,
                        clear_your_memory,
                        list_models,
                        set_model,
                        get_violation_rules,
                        set_violation_rules,
                    ],
                ),
                text,
                session=session,
            )
            return res.final_output
