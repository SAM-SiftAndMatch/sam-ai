from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Sam AI"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # MongoDB Settings
    MONGO_URI: str | None = None
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str | None = None
    MONGO_PASSWORD: str | None = None
    MONGO_DB_NAME: str = "sam_ai_db"
    MONGO_AUTH_SOURCE: str = "admin"
    MONGO_IS_SRV: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_mongo_uri(self) -> str:
        """Resolve MongoDB connection string from environment settings."""
        if self.MONGO_URI:
            return self.MONGO_URI

        # Construct URI from individual variables
        auth_part = ""
        if self.MONGO_USERNAME and self.MONGO_PASSWORD:
            encoded_user = quote_plus(self.MONGO_USERNAME)
            encoded_pass = quote_plus(self.MONGO_PASSWORD)
            auth_part = f"{encoded_user}:{encoded_pass}@"

        is_srv = self.MONGO_IS_SRV or (
            self.MONGO_HOST and "mongodb.net" in self.MONGO_HOST
        )
        if is_srv:
            return f"mongodb+srv://{auth_part}{self.MONGO_HOST}/{self.MONGO_DB_NAME}?retryWrites=true&w=majority"

        auth_source_param = f"?authSource={self.MONGO_AUTH_SOURCE}" if auth_part else ""
        return f"mongodb://{auth_part}{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB_NAME}{auth_source_param}"


settings = Settings()
