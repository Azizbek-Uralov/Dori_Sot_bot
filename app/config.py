from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://dorsotbot:dorsotbot@localhost:5432/dorsotbot"
    test_database_url: str = "postgresql+asyncpg://dorsotbot:dorsotbot@localhost:5432/dorsotbot_test"

    bot_token: str = "123456:PLACEHOLDER-TOKEN-REPLACE-ME"
    marketing_channel_id: str = "@your_channel_username"
    admin_group_chat_id: str = "-1000000000000"
    support_contact: str = "@your_support_username"

    admin_session_secret: str = "change-me-to-a-long-random-string"
    admin_session_max_age_seconds: int = 28800
    admin_host: str = "0.0.0.0"
    admin_port: int = 8000

    min_order_total: int = 50000


settings = Settings()
