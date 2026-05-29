from langchain_anthropic import ChatAnthropic
from app.core.config import get_settings


settings = get_settings()
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514", streaming=True, api_key=settings.anthropic_api_key
)