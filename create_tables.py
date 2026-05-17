import asyncio
from app.infrastructure.database import engine
from app.infrastructure.models import Base

async def init_models():
    print("Conectando ao banco de dados e recriando tabelas...")
    async with engine.begin() as conn:
        # Isso cria todas as tabelas que não existem (messages, rag_memories, clients, etc)
        await conn.run_sync(Base.metadata.create_all)
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(init_models())