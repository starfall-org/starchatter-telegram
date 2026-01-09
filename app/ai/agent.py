import asyncio
from datetime import datetime, timedelta
from agents import Agent, Runner, SQLiteSession, function_tool, mcp
from agents.extensions.models.litellm_model import LitellmModel
from ai.base import list_models, set_model
from database.local import local_db
from database.models import AIProvider
from openai import AsyncClient


async def get_default_provider_and_model():
    """Lấy provider và model mặc định cho chat từ local database"""
    default_model = await local_db.get_default_model("chat")
    provider = await local_db.get_default_provider()
    
    model_id = ""
    if default_model and default_model.model:
        model_id = default_model.model
    
    if default_model and default_model.provider_name:
        provider = await local_db.get_provider_by_name(default_model.provider_name)
    
    return provider, model_id


class AIAgent:
    def __init__(self):
        # Lấy provider và model mặc định cho chat
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        provider, model_id = loop.run_until_complete(get_default_provider_and_model())
        
        # Nếu không có model được đặt, lấy model đầu tiên từ provider
        if not model_id and provider:
            models_list = loop.run_until_complete(list_models())
            if models_list:
                model_id = models_list[0]
        
        if provider and model_id:
            self.litellm_model = LitellmModel(
                model="openai/" + model_id,
                base_url=provider.base_url,
                api_key=provider.api_key,
            )
        else:
            raise ValueError("No AI provider configured. Use /add_provider to add one.")

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
            instructions=f"""You are **StarChatter**. You are powered by model `{self.model_id}`. Change model if you can't help the user. To mention a user, use `[user_fullname](tg://user?id=[user_id]).
            - user_fullname: {full_name}
            - user_id: {user_id}
            - message_id: {message.id}
            - previous_message_id: user_message_id - i (i = user_message_id - len(messages_until_target))""",
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
                message_ids (int | list[int], optional): Message ID or list of message IDs to delete. Defaults to None and deletes the message that triggered the command.

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
