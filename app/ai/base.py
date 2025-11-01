import base64
import inspect
import shelve

from config import AI_MODEL, OLLAMA_URL
from ollama import AsyncClient

kv = shelve.open("cache.db", writeback=True)


class BaseFactory:
    _cache_ttl = 6000

    def __init__(self):
        self.client = AsyncClient(
            host=OLLAMA_URL,
        )
        self.instructions = "You are StarChatter, you can chat with users, manage group, handle tasks and provide useful information. You will mute users who sending spam or unsafe content."

    async def _get_chat_session_cached(self, chat_id):
        session = kv.get(f"session_{chat_id}")
        if not session:
            session = kv[f"session_{chat_id}"] = []
        return session

    async def _update_chat_session_cache(self, chat_id, chat_session):
        kv[f"session_{chat_id}"] = chat_session

    async def chat(
        self,
        message: str,
        chat_id: int,
        filtered: bool,
        tools: list | None = None,
        photo: bytes | None = None,
    ):
        chat_session = await self._get_chat_session_cached(chat_id)
        if photo:
            encoded_photo = base64.b64encode(photo).decode("utf-8")
            chat_session.append(
                {
                    "role": "user",
                    "content": message,
                    "image": [encoded_photo],
                }
            )
        else:
            chat_session.append({"role": "user", "content": message})

        messages = [
            {"role": "system", "content": self.instructions},
            *({"role": cm["role"], "content": cm["content"]} for cm in chat_session),
        ]

        response = await self.client.chat(
            model=AI_MODEL, messages=messages, tools=tools
        )

        chat_session.append(response.message)
        if tools:
            if response.message.tool_calls:
                for call in response.message.tool_calls:
                    func = next(
                        (tool for tool in tools if tool.__name__ == call.function.name),
                        None,
                    )
                    args = call.function.arguments
                    if inspect.iscoroutinefunction(func):
                        tool_response = await func.func(**args)
                        chat_session.append(
                            {
                                "role": "tool",
                                "tool_name": call.function.name,
                                "content": str(tool_response),
                            }
                        )
                        response = await self.client.chat(
                            model=AI_MODEL,
                            messages=[
                                {"role": "system", "content": self.instructions},
                                *(
                                    {"role": cm["role"], "content": cm["content"]}
                                    for cm in chat_session
                                ),
                            ],
                        )
                        yield response.message.content or "No response from AI.", True
        else:
            content = response.message.content

            yield content or "Something went wrong! Please try again later.", False

        if filtered:
            await self._update_chat_session_cache(chat_id, chat_session)
