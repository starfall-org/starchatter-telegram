import os

from agents import function_tool, set_default_openai_api
from config import OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI


def setup_agent():
    set_default_openai_api("chat_completions")


def models():
    client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
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
