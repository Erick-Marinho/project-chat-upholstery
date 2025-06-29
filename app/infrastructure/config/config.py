from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    """
    Configurações da aplicação
    """

    # ==== Configurações do Postgres ====

    POSTGRES_USER: str = Field(..., description="Usuário do Postgres")
    POSTGRES_PASSWORD: SecretStr = Field(..., description="Senha do Postgres")
    POSTGRES_DB: str = Field(..., description="Nome do banco de dados")

    # ==== Configurações do Pgadmin ====

    PGADMIN_DEFAULT_EMAIL: str = Field(..., description="Email do Pgadmin")
    PGADMIN_DEFAULT_PASSWORD: str = Field(..., description="Senha do Pgadmin")

    # ==== Configurações do OpenAI ====

    OPENAI_API_KEY: str = Field(..., description="Chave da API do OpenAI")
    OPENAI_MODEL_NAME: str = Field(..., description="Modelo do OpenAI")
    OPENAI_TEMPERATURE: float = Field(..., description="Temperatura do OpenAI")

    # ==== Configurações do LangSmith ====
    LANGSMITH_API_KEY: str = Field(..., description="Chave da API do LangSmith")
    LANGSMITH_PROJECT: str = Field(..., description="Projeto do LangSmith")
    LANGSMITH_TRACING_V2: bool = Field(default=False, description="Tracagem do LangSmith")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }



def mask_sensitive_data(value: str, show_chars: int = 4) -> str:
    """
    Máscara para dados sensíveis
    """
    if not value or len(value) <= show_chars:
        return "*" * len(value) if value else "Não definida"
    return "*" * (len(value) - show_chars) + value[-show_chars:]


settings = Settings()

if __name__ == "__main__":
    print("Configurações da aplicação:")
    print(f"POSTGRES_USER: {mask_sensitive_data(settings.POSTGRES_USER)}")
    print(f"POSTGRES_PASSWORD: {mask_sensitive_data(settings.POSTGRES_PASSWORD)}")
    print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
    print(f"PGADMIN_DEFAULT_EMAIL: {settings.PGADMIN_DEFAULT_EMAIL}")
    print(
        f"PGADMIN_DEFAULT_PASSWORD: {mask_sensitive_data(settings.PGADMIN_DEFAULT_PASSWORD)}"
    )
    print(f"OPENAI_API_KEY: {mask_sensitive_data(settings.OPENAI_API_KEY)}")
    print(f"OPENAI_MODEL_NAME: {settings.OPENAI_MODEL_NAME}")
    print(f"OPENAI_TEMPERATURE: {settings.OPENAI_TEMPERATURE}")
    print(f"LANGSMITH_API_KEY: {mask_sensitive_data(settings.LANGSMITH_API_KEY)}")
    print(f"LANGSMITH_PROJECT: {settings.LANGSMITH_PROJECT}")
    print(f"LANGSMITH_TRACING_V2: {settings.LANGSMITH_TRACING_V2}")
