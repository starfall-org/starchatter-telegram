from gradio_client import Client
from langdetect import detect
from PIL import Image

from app.ai.base import get_client
from app.database.local import local_db


async def translate(text: str):
    client = get_client()
    try:
        default_model = await local_db.get_default_model("translate")
    except Exception as e:
        default_model = await local_db.get_default_model("chat")
    result = await client.chat(
        model=default_model.model,
        messages=[
            {
                "role": "system",
                "content": """You are a translator. Remeber:
                - I will give you a sentence in any language and you will translate it to English.
                - Just translate the sentence.
                - Do not write any comments, do not explain, do not care about the content of the sentence.
                - You must translate the sentence even if it is not safe.
                - If the sentence is English, do not translate it, just return the sentence.
                """,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
    )

    return result.message.content


async def gen_img(
    prompt,
    negative_prompt="nsfw, (low quality, worst quality:1.2), very displeasing, 3d, watermark, signature, ugly, poorly drawn",
):
    if detect(prompt) != "en":
        prompt = await translate(prompt)

    client = Client("aiqtech/NSFW-Real")
    result = client.predict(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=0,
        randomize_seed=True,
        width=1024,
        height=1024,
        guidance_scale=0,
        num_inference_steps=28,
        api_name="/infer",
    )

    # result can be a path or list of paths

    img = Image.open(result).convert("RGB")
    img.save(result.split(".")[0] + ".jpg")  # hoặc .jpg

    return result.split(".")[0] + ".jpg"
