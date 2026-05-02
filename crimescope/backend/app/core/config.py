from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------------------------------------------------------
    # Local Postgres (dev / docker-compose)
    # ---------------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "crimescope"
    postgres_user: str = "crimescope"
    postgres_password: str = "crimescope"
    database_url: str = "postgresql+asyncpg://crimescope:crimescope@localhost:5432/crimescope"
    redis_url: str = "redis://localhost:6379/0"
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # ---------------------------------------------------------------
    # OpenAI (free-form analyst chat fallback)
    # ---------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ---------------------------------------------------------------
    # Databricks Model Serving (single-region scoring)
    # When set, single-region scoring calls hit the UC champion model
    # endpoint instead of the static JSON snapshot. Leave blank for
    # offline-safe demo mode.
    # ---------------------------------------------------------------
    databricks_serving_url: str = ""
    databricks_token: str = ""

    # ---------------------------------------------------------------
    # Databricks Genie — natural-language Q&A over Unity Catalog
    # tables. The frontend AI Analyst panel proxies to /api/genie/query
    # which calls the Genie Conversation API on this space.
    #
    # Required to enable Genie:
    #   DATABRICKS_HOST=https://dbc-XXXX.cloud.databricks.com
    #   DATABRICKS_TOKEN=dapi...
    #   DATABRICKS_GENIE_SPACE_ID=01ef...
    #
    # When unset, /api/genie/* returns 503 and the AI Analyst panel
    # falls back to OpenAI streaming.
    # ---------------------------------------------------------------
    databricks_host: str = ""
    databricks_genie_space_id: str = ""

    # ---------------------------------------------------------------
    # Lakebase — Postgres-on-Databricks read store.
    #
    # When DATA_STORE_BACKEND=lakebase, the backend reads from a
    # Lakebase Postgres instance instead of the local docker-compose
    # Postgres. Same SQL, same governance as the rest of the lakehouse.
    #
    # Required:
    #   DATA_STORE_BACKEND=lakebase
    #   LAKEBASE_URL=postgresql+asyncpg://<user>:<token>@<host>:5432/<db>
    #
    # Falls back to local Postgres or JSON if Lakebase is unreachable.
    # ---------------------------------------------------------------
    data_store_backend: str = "auto"  # auto | lakebase | postgres | json
    lakebase_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
