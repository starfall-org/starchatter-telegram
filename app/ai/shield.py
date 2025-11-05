import base64
import inspect

from config import AI_MODEL, OLLAMA_URL
from ollama import AsyncClient
from pyrogram.types import Message

client = AsyncClient(
    host=OLLAMA_URL,
)


async def detector(
    message: Message,
    tools: list | None = None,
    photo: bytes | None = None,
):
    text = message.text or message.caption or ""
    sender_chat = None
    if message.sender_chat:
        sender_chat = message.sender_chat.title
        user = sender_chat
        user_id = message.sender_chat.id
    elif message.from_user:
        user = message.from_user.full_name
        user_id = message.from_user.id
    instructions = f"""I will give you a message and you will analyze. If the message is spam, advertising, or illegal, you will:
- Delete the message
- Mute the user
- Send a report message in format:
'''
❌Violation detected in __**[{user}](tg://user?id={user_id})**__'s message.

<your comment in English. Explain why the message was deleted and the user was muted. Remember to mention the user>

----

<the user language version>

'''
+   **{"Chat Sender" if sender_chat else "User"} name:** "**{sender_chat or user}**"
+   **{"Chat Sender" if sender_chat else "User"} ID: `{user_id}`
"""
    if photo:
        encoded_photo = base64.b64encode(photo).decode("utf-8")
        images = [encoded_photo]
        messages = [
            {
                "role": "system",
                "content": instructions,
            },
            {
                "role": "user",
                "content": text,
                "image": images,
            },
        ]

    else:
        messages = [
            {
                "role": "system",
                "content": instructions,
            },
            {
                "role": "user",
                "content": text,
            },
        ]

    response = await client.chat(model=AI_MODEL, messages=messages, tools=tools)

    if tools:
        if response.message.tool_calls:
            for call in response.message.tool_calls:
                func = next(
                    (tool for tool in tools if tool.__name__ == call.function.name),
                    None,
                )
                args = call.function.arguments
                if inspect.iscoroutinefunction(func):
                    tool_response = await func(**args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": call.function.name,
                            "content": str(tool_response),
                        }
                    )
                    response = await client.chat(
                        model=AI_MODEL,
                        messages=messages,
                    )

                    return response.message.content or "No response from AI."
