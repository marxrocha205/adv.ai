from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Classe central de configurações da aplicação.
    Utiliza Pydantic para validar e tipar as variáveis de ambiente.
    """
    PROJECT_NAME: str = "Adv.AI"
    VERSION: str = "0.1.0"
    
    # URL de conexão com o banco de dados
    DATABASE_URL: str

    # Configuração para ler do arquivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instância global das configurações
settings = Settings()