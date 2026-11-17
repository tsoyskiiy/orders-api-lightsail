import os


class Settings:
    """Вся конфигурация приходит из переменных окружения (см. .env / docker-compose.yml)."""

    def __init__(self) -> None:
        self.database_url: str = os.environ["DATABASE_URL"]
        self.secret_key: str = os.environ["SECRET_KEY"]
        self.algorithm: str = "HS256"
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )


settings = Settings()
