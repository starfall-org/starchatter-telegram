import asyncio
import time
from config import AI_MODEL, OPENAI_API_KEY, OPENAI_URL
from database.client import Database
from database.models import ChatMessage, ChatSession
from openai import AsyncOpenAI


class BaseFactory:
    _cache = {
        "llm_config": None,
        "llm_config_time": 0,
        "sessions": {},  # {chat_id: {"session": ChatSession, "timestamp": float}}
    }
    _cache_ttl = 300  # 5 phút

    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_URL)
        self.base = Database()

    async def _get_llm_config_cached(self):
        """Trả về llm_config từ cache, đồng thời cập nhật nền nếu cache hết hạn"""
        now = time.time()
        cached = self._cache.get("llm_config")
        if cached and now - self._cache["llm_config_time"] < self._cache_ttl:
            return cached

        # Trả về cache cũ ngay lập tức, khởi chạy cập nhật nền
        old = cached
        asyncio.create_task(self._refresh_llm_config())
        return old

    async def _refresh_llm_config(self):
        """Cập nhật llm_config trong nền"""
        llm_config = await self.base.get_llm_config()
        self._cache["llm_config"] = llm_config
        self._cache["llm_config_time"] = time.time()

    async def _get_chat_session_cached(self, chat_id):
        """Trả về session từ cache, cập nhật nền nếu hết TTL"""
        now = time.time()
        cache_entry = self._cache["sessions"].get(chat_id)
        if cache_entry and now - cache_entry["timestamp"] < self._cache_ttl:
            return cache_entry["session"]

        # Trả về session cũ nếu có, khởi chạy cập nhật nền
        old_session = cache_entry["session"] if cache_entry else None
        asyncio.create_task(self._refresh_chat_session(chat_id))
        return old_session

    async def _refresh_chat_session(self, chat_id):
        """Cập nhật session trong nền"""
        chat_session = await self.base.get_chat_session(chat_id)
        if chat_session:
            self._cache["sessions"][chat_id] = {
                "session": chat_session,
                "timestamp": time.time(),
            }

    async def _update_chat_session_cache(self, chat_id, chat_session):
        """Cập nhật cache và lưu DB nền"""
        self._cache["sessions"][chat_id] = {
            "session": chat_session,
            "timestamp": time.time(),
        }
        asyncio.create_task(self.base.update_chat_session(chat_session))

    async def chat(self, message, chat_id, user_id):
        llm_config = await self._get_llm_config_cached()
        chat_session = await self._get_chat_session_cached(chat_id)

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
            instructions = ""

        if chat_session:
            chat_messages = chat_session.messages
            chat_messages.append(ChatMessage(role="user", content=message))
        else:
            chat_messages = [ChatMessage(role="user", content=message)]
            chat_session = ChatSession(chat_id=chat_id, messages=chat_messages)
            # Thêm session nền, không chờ
            asyncio.create_task(self.base.add_chat_session(chat_session))
            self._cache["sessions"][chat_id] = {
                "session": chat_session,
                "timestamp": time.time(),
            }

        messages = [
            {"role": "system", "content": f"You are StarChatter. {instructions}"},
            *({"role": cm.role, "content": cm.content}
              for cm in chat_messages),
        ]

        response = await self.client.chat.completions.create(
            model=model, messages=messages
        )
        content = response.choices[0].message.content
        chat_messages.append(ChatMessage(role="assistant", content=content))

        await self._update_chat_session_cache(chat_id, chat_session)
        return content
