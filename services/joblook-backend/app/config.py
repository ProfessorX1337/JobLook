from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://joblook:joblook@localhost:5432/joblook"
    session_secret: str = "dev-only-change-me"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    profile_encryption_master_key: str = ""  # 32 bytes, base64-encoded

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/oauth/google/callback"

    extension_jwt_secret: str = "dev-only-change-me"
    extension_jwt_ttl_days: int = 7

    base_url: str = "http://localhost:8000"
    cookie_secure: bool = False  # set True in prod

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
