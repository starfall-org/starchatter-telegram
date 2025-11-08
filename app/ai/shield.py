import base64
import os

from config import AI_MODEL, OLLAMA_URL
from ollama import AsyncClient
from pyrogram.types import Message

client = AsyncClient(
    host=OLLAMA_URL,
)


def get_violation_rules():
    """
    Get violation rules variable.

    Returns:
        str: Violation rules
    """
    preset = os.environ.get(
        "PRESET_VIOLATION_RULES",
        "spam, unsafe advertisement.",
    )
    return preset


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
    instructions = """I will give you a message and you will analyze. If the message matches the violation rules, you will call violent_detection function and send your report about it."""
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
    if tools:
        tools.append(get_violation_rules)

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
                        "__(\nSYSTEM WARNING: ❌Violation detected\n"
                        + f"**User Fullname:** {user}\n"
                        + f"**User ID:** {user_id}\n\n"
                        + f"**System Response:** {response.message.content}\n"
                        + "**Notice:** Please verify the user's message. If you think this is a violation, you will delete the message and mute the user and send a report. If the user's message is not English, you will send 2 versions of the report, one in English and one in that language. \nIf you think this is a mistake, just ignore this warning.\n)__\n\n"
                        + text
                    )
