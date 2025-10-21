from gradio_client import Client
from PIL import Image


async def gen_img(
    prompt,
    negative_prompt="nsfw, (low quality, worst quality:1.2), very displeasing, 3d, watermark, signature, ugly, poorly drawn",
):
    client = Client("aiqtech/NSFW-Real")
    result = client.predict(
        prompt="Hello!!",
        negative_prompt="",
        seed=0,
        randomize_seed=True,
        width=1024,
        height=1024,
        guidance_scale=7,
        num_inference_steps=28,
        api_name="/infer",
    )

    # result có thể là đường dẫn hoặc list các đường dẫn

    img = Image.open(result).convert("RGB")
    img.save(result.split(".")[0] + ".jpg")  # hoặc .jpg

    return result.split(".")[0] + ".jpg"
