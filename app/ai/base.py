from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_URL


class BaseFactory:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_URL)

        

    async def chat(self, messages):
        return await self.client.chat.completions.create(
            model="gpt-3.5-turbo", messages=messages
        )
