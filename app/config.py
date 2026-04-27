from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    aviationstack_api_key: str = ""
    anthropic_api_key: str = ""
    langsmith_api_key: str = ""

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "flight_docs"


settings = Settings()
