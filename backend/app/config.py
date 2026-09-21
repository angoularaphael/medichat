from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://eir:eir_demo@localhost:5432/eir"
    mqtt_broker: str = "mqtt://mqtt:1883"
    mqtt_client_id: str = "eir-api"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2:3b"
    cors_origins: str = "http://localhost:5173"
    crew_size: int = 20
    crisis_sick_ratio: float = 0.15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
