import sys
from loguru import logger

def setup_logging() -> None:
    """
    Configura o sistema de logs da aplicação.
    
    Remove o handler padrão e adiciona um formatador customizado
    que facilita a leitura em plataformas cloud como a Railway,
    além de suportar rotação de logs em arquivo se necessário no futuro.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.info("Sistema de logs inicializado com sucesso.")