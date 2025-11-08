import base64
import inspect

from agents import SQLiteSession, TResponseInputItem

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
    instructions = """I will give you a message and you will analyze. If the message is spam, advertising, or illegal, you will call violent_detection function and send me your report about it."""
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
                if func:
                    tool_response = await func(**args)
                else:
                    tool_response = None
                if tool_response:
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

                    return (
                        f"❌Violation detected in __**[{user}](tg://user?id={user_id})**__'s message.\n\n"
                        + f"USER FULL NAME: {user}\n"
                        + f"USER ID: {user_id}\n\n"
                        + f"SYSTEM REPORT: {response.message.content}\n\n"
                        + f"MESSAGE: {text}\n\n"
                        + "REQUEST: You will verify the system report to confirm if it is a violation. If it is a violation, you will delete the message and mute the user, otherwise you will do nothing and reply user's message normally and do not include the system report. In case of a violation, if user's message is not English, you will send 2 versions of the message in English and that language as well."
                    )
