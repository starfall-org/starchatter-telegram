import os

from agents import function_tool
from config import UPSTAGE_API, UPSTAGE_URL, A21_API, A21_URL
from openai import OpenAI


def upstage_models():
    c = OpenAI(base_url=UPSTAGE_URL, api_key=UPSTAGE_API)
    models = c.models.list()
    return [*models]


def a21_models():
    a21 = OpenAI(base_url=A21_URL, api_key=A21_API)
    models = a21.models.list()
    return [*models]

def anondrop_models():
    anondrop = OpenAI(base_url="https://anondrop.net/v1", api_key="*")
    models = anondrop.models.list()
    return [*models]


def models():
    u_models = upstage_models()
    a_models = a21_models()
    ad_models = anondrop_models()
    return [*u_models, *a_models, *ad_models]


def get_model() -> str:
    selected_model = os.getenv("AGENT_MODEL")
    if selected_model:
        return selected_model
    else:
        return "gpt-fast"


@function_tool
def list_models():
    return models()


@function_tool
def set_model(model_id: str):
    os.environ["AGENT_MODEL"] = model_id
