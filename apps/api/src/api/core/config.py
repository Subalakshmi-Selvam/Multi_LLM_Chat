from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    # Where the SQLite chat-history database lives. Defaults to a path
    # inside the container's working directory; override via env var to
    # point somewhere persistent (e.g. a mounted volume) in production.
    DATABASE_PATH: str = "chat_history.db"

    model_config = SettingsConfigDict(env_file=".env")


config = Config()
