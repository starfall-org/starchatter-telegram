import os

from agents import function_tool
from config import AI_API_KEY, AI_BASE_URL
from openai import OpenAI


def models():
    client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)
    return client.models.list()


def get_model() -> str:
    selected_model = os.getenv("AGENT_MODEL")
    if selected_model:
        return selected_model
    else:
        all_models = models()
        for model in all_models:
            os.environ["AGENT_MODEL"] = model.id
            return model.id
        return "gpt-3.5-turbo"


@function_tool
def list_models():
    return models().model_dump_json()


@function_tool
def set_model(model_id: str):
    os.environ["AGENT_MODEL"] = model_id
