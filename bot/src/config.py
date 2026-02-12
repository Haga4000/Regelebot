from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM provider settings — must be set in .env
    LLM_PROVIDER: str  # gemini | openai | mistral | anthropic
    LLM_API_KEY: str
    LLM_MODEL: str = ""  # empty = provider default
    LLM_BASE_URL: str | None = None  # for Ollama: http://host:11434/v1

    TMDB_API_KEY: str
    DATABASE_URL: str
    BOT_NAME: str = "Regelebot"
    CONVERSATION_WINDOW_SIZE: int = 20
    WEBHOOK_SECRET: str
    TOKEN_BUDGET: int = 4000
    RATE_LIMIT_PER_MINUTE: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
