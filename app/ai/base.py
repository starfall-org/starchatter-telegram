from config import AI_MODEL, OPENAI_API_KEY, OPENAI_URL
from database.client import Database
from database.models import ChatMessage, ChatSession
from openai import AsyncOpenAI


class BaseFactory:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_URL)
        self.base = Database()

    async def chat(self, message, chat_id, user_id):
        llm_config = await self.base.get_llm_config()
        chat_session = await self.base.get_chat_session(chat_id)
        if llm_config:
            model = llm_config.model or AI_MODEL
            instructions = llm_config.instructions or ""
            if llm_config.provider_id:
                provider = llm_config.provider
                self.client = AsyncOpenAI(
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                )
        else:
            model = AI_MODEL
        if chat_session:
            await self.base.update_chat_session(chat_session)
            chat_messages = chat_session.messages
            chat_messages.append(ChatMessage(role="user", content=message))
        else:
            chat_messages = [ChatMessage(role="user", content=message)]
            chat_session = ChatSession(
                chat_id=chat_id,
                user_id=user_id,
                messages=chat_messages,
            )
            await self.base.add_chat_session(chat_session)
        messages = [
            {"role": "system", "content": instructions},
            *({"role": cm.role, "content": cm.content} for cm in chat_messages),
        ]
        response = await self.client.chat.completions.create(
            model=model, messages=messages
        )
        content = response.choices[0].message.content
        chat_messages.append(ChatMessage(role="assistant", content=content))
        await self.base.update_chat_session(chat_session)
        return content
