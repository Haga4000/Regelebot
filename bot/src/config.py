from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    TMDB_API_KEY: str
    DATABASE_URL: str
    BOT_NAME: str = "Regelebot"
    CONVERSATION_WINDOW_SIZE: int = 20
    WEBHOOK_SECRET: str
    TOKEN_BUDGET: int = 4000
    RATE_LIMIT_PER_MINUTE: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
