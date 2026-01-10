import asyncio
from datetime import datetime, timedelta
from agents import Agent, Runner, SQLiteSession, function_tool, mcp
from agents.extensions.models.litellm_model import LitellmModel
from app.ai.base import list_models, models, set_model
from app.database.local import local_db
from app.database.models import AIProvider
from openai import AsyncClient
from pyrogram import types, Client
import logging

logger = logging.getLogger(__name__)


async def get_default_provider_and_model():
    """Get default provider and model for chat from local database"""
    default_model = await local_db.get_default_model("chat")
    provider = await local_db.get_default_provider()
    
    model_id = ""
    if default_model and default_model.model:
        model_id = default_model.model

    # Only override provider if default_model has provider_name and provider exists
    if default_model and default_model.provider_name:
        new_provider = await local_db.get_provider_by_name(default_model.provider_name)
        if new_provider:
            provider = new_provider
    
    return provider, model_id


class AIAgent:
    def __init__(self):
        # Prevent direct instantiation; use AIAgent.create() instead
        raise RuntimeError("Use AIAgent.create() instead of AIAgent()")
    
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(AIAgent, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    async def create(cls):
        """Factory method to create AIAgent asynchronously"""
        if hasattr(cls, '_instance') and cls._instance._initialized:
            return cls._instance
            
        provider, model_id = await get_default_provider_and_model()
        
        # If no model is set, get first model from provider
        if not model_id and provider:
            models_list = await models()
            if models_list:
                model_id = models_list[0]
        
        if provider and model_id:
            self = cls.__new__(cls)
            self.model_id = model_id
            self.litellm_model = LitellmModel(
                model="openai/" + model_id,
                base_url=provider.base_url,
                api_key=provider.api_key,
            )
            self._initialized = True
            # Initialize queue and lock for request processing
            self._request_queue = asyncio.Queue()
            self._processing_lock = asyncio.Lock()
            self._is_processing = False
            self._queue_task = None
            return self
        else:
            raise ValueError("No AI provider configured. Use /add_provider to add one.")

    def star_chatter(
        self,
        mcp_server: list,
        message: types.Message,
        functions: list | None = None,
    ):
        if functions is None:
            functions = []
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

    async def _process_request_core(self, client, message, prompt):
        """Process request core - common processing part for both run_chat and queue"""
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

    async def _process_request_from_queue(self, request_data):
        """Process a request from queue when request fails"""
        client, message, prompt = request_data
        chat_id = message.chat.id
        try:
            return await self._process_request_core(client, message, prompt)
        except Exception as e:
            logger.error(f"Error processing request from queue for chat {chat_id}: {e}")
            return f"Error: {str(e)}"

    async def _queue_processor(self):
        """Loop to process requests in queue when request fails"""
        while True:
            try:
                # Lấy request từ queue (khối blocking)
                request_data = await self._request_queue.get()
                
                # Mark as processing
                self._is_processing = True

                # Process request
                result = await self._process_request_from_queue(request_data)

                # Mark as processed
                self._is_processing = False
                self._request_queue.task_done()

                # Return result (may need adjustment depending on usage)
                logger.info(f"Request from queue processed successfully")
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                self._is_processing = False
                if hasattr(self, '_request_queue'):
                    self._request_queue.task_done()

    async def run_chat(
        self, client: Client, message: types.Message, prompt: str | None = None
    ):
        """Process request directly, if failed then move to queue"""
        # Check if this is the first time starting queue processor
        if not hasattr(self, '_queue_task') or self._queue_task is None or self._queue_task.done():
            self._queue_task = asyncio.create_task(self._queue_processor())
        
        try:
            return await self._process_request_core(client, message, prompt)
        except Exception as e:
            chat_id = message.chat.id
            logger.error(f"Request failed for chat {chat_id}, adding to queue: {e}")
            # Add request to queue for reprocessing
            request_data = (client, message, prompt)
            await self._request_queue.put(request_data)
            return f"Request failed, added to retry queue: {str(e)}"
