import json
import base64
from ollama import AsyncClient
from config import OLLAMA_URL, DETECTOR_MODEL


async def detector(content: str, images: bytes | None = None) -> dict:
    if images:
        image = base64.b64encode(images).decode("utf-8")
    messages = [
        {
            "role": "system",
            "content": """You are spam detection AI. Your task is to analyze messages and determine if they are spam or not.
Respond in this format with two fields: {"is_spam": true/false, "content": "the message", "reason": "explanation"}.
Here are the rules to identify spam:
1. Messages that contain unsolicited advertisements or promotions.
2. Messages that include links to malicious or suspicious websites.
3. Messages that are repetitive or sent in bulk.
4. Messages that contain phishing attempts or requests for sensitive information.
5. Messages that use excessive capitalization or special characters to grab attention.
6. Messages that are irrelevant to the context of the conversation.
7. Messages that contain offensive or inappropriate content.""",
        },
        {"role": "user", "content": content} if not images else {
            "role": "user", "content": content, "images": [image]
        },
    ]
    response = await AsyncClient(
        host=OLLAMA_URL,
    ).chat(model=DETECTOR_MODEL, messages=messages, format="json")

    result = response.message.content
    if result:
        try:
            result_json = json.loads(result)
        except json.JSONDecodeError:
            result = result.split("\n")[1:-1]
            result = "\n".join(result).strip()
            result_json = json.loads(result)
    else:
        result_json = {
            "is_spam": False,
            "content": content,
            "reason": "No reason provided",
        }
    return result_json


async def test():
    test_messages = [
        "Congratulations! You've won a free iPhone! Click here to claim your prize: http://spamlink.com",
        "Hey, check out this amazing deal on shoes at http://shoesale.com!",
        "Buy now and get 50% off on all products! Limited time offer!",
        "Hello everyone, I hope you're having a great day!",
        "Don't forget our meeting tomorrow at 10 AM.",
        "This is a spam message. This is a spam message. This is a spam message.",
        "Please verify your account by providing your password and credit card information.",
        "WIN A MILLION DOLLARS NOW!!! CLICK HERE!!!",
        "Join our group for exclusive content and updates.",
        "This is an inappropriate message with offensive language.",
    ]

    for msg in test_messages:
        result = await detector(msg)
        try:
            print(result)
        except Exception as e:
            print(f"Error printing result: {e}")
