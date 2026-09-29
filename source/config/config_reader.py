from datetime import time

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis


class NestedSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")


class AppSettings(NestedSettings):
    env: str = "production"
    domain: str = "localhost"


class TelegramSettings(NestedSettings):
    bot_token: SecretStr
    admin_ids: list[int] = []
    webhook_use: bool = False
    webhook_path: str = "/telegram"
    bot_username: str = ""
    miniapp_short_name: str = "chamcong"


class WebhookSettings(NestedSettings):
    url: str = "https://localhost"
    host: str = "0.0.0.0"
    port: int = 8000
    secret: SecretStr = SecretStr("change-me")


class DatabaseSettings(NestedSettings):
    host: str = "db"
    port: int = 5432
    user: str = "default"
    password: SecretStr = SecretStr("password")
    name: str = "crv_workforce"

    def postgres_connection(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg", username=self.user,
            password=self.password.get_secret_value(), host=self.host,
            port=self.port, path=self.name,
        ))


class RedisSettings(NestedSettings):
    host: str = "redis"
    port: int = 6379
    user: str = "default"
    password: SecretStr = SecretStr("password")
    db: int = 0

    def redis_connection(self) -> Redis:
        return Redis(host=self.host, port=self.port, username=self.user,
                     password=self.password.get_secret_value(), db=self.db,
                     decode_responses=True)


class ApiSettings(NestedSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class WebAppSettings(NestedSettings):
    url: str = "http://localhost:3000"


class AuthSettings(NestedSettings):
    initdata_max_age_seconds: int = 3600
    session_secret: SecretStr = SecretStr("development-secret-change-me-32chars")
    dev_bypass: bool = False


class WorkshopSettings(NestedSettings):
    lat: float = 10.0
    lng: float = 106.0
    radius_m: int = 100


class RuleSettings(NestedSettings):
    gps_max_accuracy_m: int = 100
    checkin_cutoff: time = time(18, 0)
    reminder_at: time = time(18, 0)
    escalate_at: time = time(18, 30)
    sweep_at: time = time(0, 5)
    output_edit_minutes: int = 10
    pay_round_unit: int = 1000
    invite_expire_days: int = 7
    min_hourly_rate: int = 1_000
    max_hourly_rate: int = 1_000_000


class LarkSettings(NestedSettings):
    sync_webhook_url: str = ""
    sync_secret: SecretStr = SecretStr("")


class AlertSettings(NestedSettings):
    admin_chat_id: int = 0


class SeedSettings(NestedSettings):
    manager_name: str = "Quan ly"
    director_name: str = "Giam doc"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, env_file=".env", env_file_encoding="utf-8",
        env_nested_delimiter="__", extra="ignore",
    )
    app: AppSettings = AppSettings()
    tg: TelegramSettings
    webhook: WebhookSettings = WebhookSettings()
    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    api: ApiSettings = ApiSettings()
    webapp: WebAppSettings = WebAppSettings()
    auth: AuthSettings = AuthSettings()
    workshop: WorkshopSettings
    rules: RuleSettings = RuleSettings()
    lark: LarkSettings = LarkSettings()
    alert: AlertSettings = AlertSettings()
    seed: SeedSettings = SeedSettings()

    @property
    def environment(self) -> str:
        return self.app.env

    @model_validator(mode="after")
    def production_settings_are_safe(self):
        errors: list[str] = []
        session_secret = self.auth.session_secret.get_secret_value()

        if len(session_secret) < 32:
            errors.append("AUTH__SESSION_SECRET must contain at least 32 characters")

        if self.app.env == "production":
            db_password = self.db.password.get_secret_value()
            redis_password = self.redis.password.get_secret_value()
            webhook_secret = self.webhook.secret.get_secret_value()
            lark_secret = self.lark.sync_secret.get_secret_value()

            if self.auth.dev_bypass:
                errors.append("AUTH__DEV_BYPASS is forbidden in production")
            if db_password == "password":
                errors.append('DB__PASSWORD must not be "password" in production')
            if redis_password == "password":
                errors.append('REDIS__PASSWORD must not be "password" in production')
            if "change-me" in session_secret:
                errors.append('AUTH__SESSION_SECRET must not contain "change-me" in production')
            if lark_secret.startswith("development-"):
                errors.append("LARK__SYNC_SECRET must not use a development-* sample value in production")
            if webhook_secret.startswith("development-"):
                errors.append("WEBHOOK__SECRET must not use a development-* sample value in production")
            if not self.webapp.url.startswith("https://"):
                errors.append("WEBAPP__URL must start with https:// in production")

        if errors:
            raise ValueError("; ".join(errors))
        return self


settings = Settings()
