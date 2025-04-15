import secrets
from pydantic import EmailStr, HttpUrl, PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file="../.local.env",
    env_ignore_empty=True,
    extra="ignore"
  )
  API_V1_STR: str = "api/v1"
  SECRET_KEY: str = secrets.token_urlsafe(32)
  ENVIRONMENT: Literal["local", "test", "production"] = "local"

  PROJECT_NAME: str
  SENTRY_DSN: HttpUrl | None = None
  POSTGRES_SERVER: str
  POSTGRES_PORT: int = 5432
  POSTGRES_USER: str
  POSTGRES_PASSWORD: str = ""
  POSTGRES_DB: str = ""

  @computed_field
  @property
  def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
      return MultiHostUrl.build(
          scheme="postgresql+psycopg",
          username=self.POSTGRES_USER,
          password=self.POSTGRES_PASSWORD,
          host=self.POSTGRES_SERVER,
          port=self.POSTGRES_PORT,
          path=self.POSTGRES_DB,
      )
  
  EMAIL_TEST_USER: EmailStr = "test@example.com"
  FIRST_SUPERUSER: EmailStr
  FIRST_SUPERUSER_PASSWORD: str

settings = Settings()