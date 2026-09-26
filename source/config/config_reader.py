from pydantic import PostgresDsn
from pydantic import SecretStr
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from redis.asyncio import Redis


class TelegramSettings(BaseSettings):
    bot_token: SecretStr
    admin_ids: list[int]
    webhook_use: bool
    webhook_path: str

    @field_validator("admin_ids")
    @classmethod
    def validate_admin_ids(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("Admin IDs list cannot be empty")
        if len(value) != len(set(value)):
            raise ValueError("Admin IDs list contains duplicates")
        if any(admin_id <= 0 for admin_id in value):
            raise ValueError("Admin IDs must be positive integers")
        return value


class WebhookSettings(BaseSettings):
    url: str
    host: str
    port: int
    secret: SecretStr


class DatabaseSettings(BaseSettings):
    host: str
    port: int
    user: str
    password: SecretStr
    name: str

    def postgres_connection(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.user,
                password=self.password.get_secret_value(),
                host=self.host,
                port=self.port,
                path=self.name,
            ),
        )


class RedisSettings(BaseSettings):
    host: str
    port: int
    user: str
    password: SecretStr
    db: int

    def redis_connection(self) -> Redis:
        return Redis(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password.get_secret_value(),
            db=self.db,
            decode_responses=True,
        )


class ApiSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class WebAppSettings(BaseSettings):
    url: str = "http://localhost:3000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    environment: str = "production"
    db: DatabaseSettings
    webhook: WebhookSettings
    tg: TelegramSettings
    redis: RedisSettings
    api: ApiSettings = ApiSettings()
    webapp: WebAppSettings = WebAppSettings()


settings = Settings()
