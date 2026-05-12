from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from app.core.logger import logger

# Cria o motor do banco de dados assíncrono.
# pool_size e max_overflow ajudam a gerenciar conexões simultâneas (importante para webhooks)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # Mude para True se quiser ver as queries SQL no terminal durante testes
    pool_size=10,
    max_overflow=20,
)

# Fábrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Classe base para a criação dos nossos modelos (Tabelas do CRM e Memória)
Base = declarative_base()

async def get_db_session():
    """
    Dependency Injection para obter a sessão do banco de dados nos endpoints.
    Garante que a conexão seja fechada automaticamente após o uso.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Erro na sessão do banco de dados: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()