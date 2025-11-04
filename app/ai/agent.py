import asyncio

from agents import Agent, Runner, SQLiteSession, function_tool, mcp
from agents.extensions.models.litellm_model import LitellmModel
from ai.base import get_model, list_models, set_model
from database.client import Database
from database.models import MutedCase
from pyrogram import Client, types
from sqlalchemy import select
from config import AI_API_KEY, AI_BASE_URL

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


class AIAgent:
    def __init__(self):
        self.model_id = get_model()
        self.litellm_model = LitellmModel(
            model="openai/" + self.model_id,
            base_url=AI_BASE_URL,
            api_key=AI_API_KEY,
        )

    def star_chatter(self, mcp_server: list, functions: list = []):
        functions.append(list_models)
        functions.append(set_model)
        return Agent(
            "StarChatter",
            instructions=f"You are **StarChatter**. You are powered by model `{self.model_id}`. You can do everything. Remember to use tools if required.",
            tools=functions,
            model=self.litellm_model,
            mcp_servers=mcp_server,
        )

    async def run_chat(self, client: Client, message: types.Message):
        chat_id = message.chat.id
        session = SQLiteSession(f"chat_{chat_id}", "conversations.sqlite")

        @function_tool
        def clear_history():
            loop = asyncio.get_event_loop()
            result = asyncio.run_coroutine_threadsafe(session.clear_session(), loop)
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
        def unmute_user(
            group_id: int,
            user_id: int,
        ):
            loop = asyncio.get_event_loop()
            result = asyncio.run_coroutine_threadsafe(
                client.restrict_chat_member(
                    group_id, user_id, permissions=types.ChatPermissions(all_perms=True)
                ),
                loop,
            )
            
            return "Action completed."

        async with mcp.MCPServerSse(
            name="Tools",
            params={"url": "https://nymbo-tools.hf.space/gradio_api/mcp/sse"},
            cache_tools_list=True,
        ) as mcp_server:
            res = await Runner.run(
                self.star_chatter(
                    mcp_server=[mcp_server],
                    functions=[get_user_muted_case, unmute_user, clear_history],
                ),
                message.text,
                session=session,
            )
            return res.final_output
