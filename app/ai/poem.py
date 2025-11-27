from aiohttp import ClientSession
from langdetect import detect


async def get_poem(hint: str, locale: str | None = None):
    if not locale:
        locale = detect(hint)
        if len(locale) > 2:
            locale = "en"

    async with ClientSession() as s:
        async with s.get(
            "https://typegpt.io/api/openAI", json={"input": hint, "locale": locale}
        ) as r:
            resp = await r.json()
            poem: str = resp["result"]
            poem = poem.split("\n", 2)[-1]

            if hint in poem:
                poem = poem.replace(hint, f"**{hint}**")

            return poem


"""
curl 'https://typegpt.io/api/openAI' \
  -H 'Content-Type: application/json' \
  --data '{"input":"tốt"}'
"""
