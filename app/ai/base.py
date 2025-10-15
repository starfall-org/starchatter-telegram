import asyncio
import shelve
import time

from config import AI_MODEL, OPENAI_API_KEY, OPENAI_URL
from database.client import Database
from database.models import LLMConfig
from openai import AsyncOpenAI

kv = shelve.open("cache.db", writeback=True)


class BaseFactory:
    _cache_ttl = 6000

    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_URL)
        self.db = Database()

    async def _get_llm_config_cached(self):
        now = time.time()
        cached = kv.get("llm_config")
        if cached and now - kv["llm_config_time"] < self._cache_ttl:
            return cached

        old = cached
        asyncio.create_task(self._refresh_llm_config())
        return old

    async def _refresh_llm_config(self):
        llmc = await self.db.get(LLMConfig)
        if conf := llmc.scalar_one_or_none():
            kv["llm_config"] = conf
            kv["llm_config_time"] = time.time()

    async def _get_chat_session_cached(self, chat_id):
        session = kv.get(f"session_{chat_id}")
        if not session:
            session = kv[f"session_{chat_id}"] = []
        return session

    async def _update_chat_session_cache(self, chat_id, chat_session):
        kv[f"session_{chat_id}"] = chat_session

    async def chat(self, message, chat_id):
        llm_config = await self._get_llm_config_cached()
        chat_session = await self._get_chat_session_cached(chat_id)

        if llm_config:
            instructions = llm_config.instructions or ""
            if llm_config.provider_id:
                provider = llm_config.provider
                self.client = AsyncOpenAI(
                    api_key=provider.api_key,
                    base_url=provider.base_url,
                )

            model = llm_config.model_id or AI_MODEL
        else:
            model = AI_MODEL
            instructions = ""

        chat_session.append({"role": "user", "content": message})
        messages = [
            {"role": "system", "content": f"You are StarChatter. {instructions}"},
            *({"role": cm["role"], "content": cm["content"]} for cm in chat_session),
        ]

        response = await self.client.chat.completions.create(
            model=model, messages=messages
        )
        content = response.choices[0].message.content
        chat_session.append({"role": "assistant", "content": content})
        await self._update_chat_session_cache(chat_id, chat_session)
        return content
