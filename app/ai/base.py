import os

from agents import function_tool
from config import OAI_COMP_API, OAI_COMP_URL
from openai import OpenAI


def models():
    client = OpenAI(
        base_url=OAI_COMP_URL,
        api_key=OAI_COMP_API,
    )

    models = client.models.list()
    return [m.id for m in models.data]


def get_model() -> str:
    selected_model = os.getenv("AGENT_MODEL")
    if selected_model:
        return selected_model
    else:
        return "lucid-v1-medium/assistant"


@function_tool
def list_models():
    return models()


@function_tool
def set_model(model_id: str):
    os.environ["AGENT_MODEL"] = model_id
