from typing import Annotated, Any, Literal, Self

from pydantic import (
    AnyUrl,
    BeforeValidator,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "App"
    SECRET_KEY: str
    ENVIRONMENT: str = "development"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    OPENAI_API_KEY: str
    OPENAI_VECTOR_STORE_ID: str

    # where the browser is sent back to after connecting Google
    FRONTEND_HOST: str = "http://localhost:5173"

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    TOKEN_ENCRYPTION_KEY: str
    # where DMCA attachment files go: "drive" (the connected Google account), or
    # "memory" for tests
    STORAGE_BACKEND: Literal["drive", "memory"] = "drive"
    # the Drive folder the app puts every file in (created if missing)
    DRIVE_FOLDER_NAME: str = "DMCA takedowns (managed by the app, don't edit)"

    # Outside production, every takedown email goes to this address instead of
    # the real recipient (the subject shows "[TEST → real@address]")
    EMAIL_REDIRECT_TO: str | None = None
    # pause between two takedown emails (3s = 20 a minute), to stay well under
    # Gmail's rate limits and not look like a burst of spam
    SEND_GAP_SECONDS: float = 3.0
    # run the background email queue with the app (off in tests, which have no
    # Postgres)
    QUEUE_ENABLED: bool = True

    @model_validator(mode="after")
    def _require_redirect_outside_production(self) -> Self:
        """Refuse to start outside production without EMAIL_REDIRECT_TO, so a
        dev or staging setup can never email real recipients."""
        if self.ENVIRONMENT != "production" and not self.EMAIL_REDIRECT_TO:
            raise ValueError(
                "Set EMAIL_REDIRECT_TO outside production (e.g. your own address)"
            )
        return self


settings = Settings()  # type: ignore
