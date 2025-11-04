import os
from agents import function_tool, set_default_openai_api, set_default_openai_client
from config import OPENAI_API_KEY, OPENAI_BASE_URL
from openai import AsyncOpenAI, OpenAI


openai = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)


def setup_agent():
    set_default_openai_client(openai)
    set_default_openai_api("chat_completions")


def models():
    client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
    return client.models.list()


def get_model():
    selected_model = os.getenv("AGENT_MODEL")
    all_models = models()
    first_model = None
    for model in all_models:
        if model.id:
            if not first_model:
                first_model = model
            if model.id == selected_model:
                return model
    if first_model:
        return first_model


@function_tool
def list_models():
    return models().model_dump_json()


@function_tool
def set_model(model_id: str):
    os.environ["AGENT_MODEL"] = model_id
