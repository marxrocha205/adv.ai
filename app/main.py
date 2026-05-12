from fastapi import FastAPI
from app.core.logger import setup_logging, logger

# Inicializa o sistema de logs antes de qualquer outro componente
setup_logging()

def create_app() -> FastAPI:
    """
    Factory function para criar e configurar a instância do FastAPI.
    
    Isso facilita testes unitários e a injeção de dependências no futuro.
    """
    app = FastAPI(
        title="Adv.AI - CRM e Atendimento Jurídico",
        description="API para orquestração de webhooks do WhatsApp, RAG e CRM jurídico.",
        version="0.1.0"
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        """Executado quando a aplicação inicia."""
        logger.info("Iniciando serviços da Adv.AI...")
        # Aqui inicializaremos conexões com banco e modelos de IA no futuro

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """
        Endpoint de checagem de saúde.
        Utilizado pela Railway para saber se a aplicação subiu corretamente.
        """
        logger.debug("Health check acionado.")
        return {"status": "ok", "message": "Adv.AI is running"}

    # TODO: app.include_router(webhooks.router, prefix="/api/v1/whatsapp")

    return app

app = create_app()