from agents import function_tool
from database.cloud import cloud_db
from database.local import local_db
from database.models import AIProvider
from openai import AsyncClient


async def get_client() -> AsyncClient:
    """Lấy OpenAI client từ provider mặc định trong database (đọc từ local)"""
    provider = await local_db.get_default_provider()
    if provider:
        return AsyncClient(
            base_url=provider.base_url,
            api_key=provider.api_key,
        )
    raise ValueError("No AI provider configured. Use /add_provider to add one.")


async def models():
    """Lấy danh sách models - ưu tiên gọi API provider, nếu thất bại thì dùng models trong AIProvider"""
    try:
        client = await get_client()
        models_list = await client.models.list()
        return [m.id for m in models_list.data]
    except Exception as e:
        print(f"Error calling provider API: {e}, falling back to AIProvider models")
        # Fallback: lấy từ AIProvider
        provider = await local_db.get_default_provider()
        if provider and provider.models:
            return provider.models
        # Nếu không có models nào, trả về list rỗng
        return []


async def get_model() -> str:
    """Lấy model ID từ DefaultModel (đọc từ local)"""
    default_model = await local_db.get_default_model("chat")
    if default_model and default_model.model:
        return default_model.model
    # Nếu không có model nào được đặt, trả về empty string
    return ""


@function_tool
def list_models():
    """Tool để liệt kê models - chạy async trong sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(models())


@function_tool
def set_model(model_id: str):
    """Tool để đặt model mặc định cho chat - chạy async trong sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Lấy provider hiện tại
    provider = loop.run_until_complete(local_db.get_default_provider())
    if provider:
        # Lưu model vào DefaultModel (ghi qua cloud, sẽ mirror sang local)
        loop.run_until_complete(cloud_db.set_default_model("chat", provider.name, model_idú
        return f"Model `{model_id}` đã được đặt làm mặc định cho chat!"
    return "Không có provider nào được cấu hình. Use /add_provider để thêm provider."
