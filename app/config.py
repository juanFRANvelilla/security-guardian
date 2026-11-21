from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    CHECK_INTERVAL_HOURS: int = 4
    HN_MIN_SCORE: int = 40
    APP_ENV: str = "development"

    # Host RHEL 10 inspection settings
    ENABLE_HOST_INSPECTION: bool = True
    HOST_SSH_HOST: str = "192.168.0.176"
    HOST_SSH_USER: str = "juanfran"
    HOST_SSH_PASSWORD: str = ""

    # Alert persistence
    ALERT_STORE_PATH: str = "data/seen_alerts.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
