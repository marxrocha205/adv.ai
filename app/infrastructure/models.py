import datetime
from typing import List
from sqlalchemy import ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.infrastructure.database import Base

class Client(Base):
    """
    Modelo de persistência para o Cliente (CRM).
    Armazena os dados básicos do advogado ou do cliente final que entra em contato via WhatsApp.
    """
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # wa_id é o número do WhatsApp (ex: 5511999999999). Único e indexado para buscas rápidas.
    wa_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="prospect") # prospect, active, inactive
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    messages: Mapped[List["Message"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    memories: Mapped[List["MemoryRAG"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Message(Base):
    """
    Modelo para o histórico transacional de mensagens.
    Útil para o CRM exibir a timeline de conversas para o advogado.
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False) # "inbound" (recebida) ou "outbound" (enviada)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    client: Mapped["Client"] = relationship(back_populates="messages")


class MemoryRAG(Base):
    """
    Modelo Vetorial para a Memória da IA (RAG).
    É aqui que o pgvector brilha. Salvamos fragmentos de informação útil
    vetorizados para o LLM buscar contexto antes de responder.
    """
    __tablename__ = "rag_memories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False) # O texto em si (ex: "Cliente tem um processo trabalhista número X")
    
    # 1536 é a dimensão padrão dos embeddings da OpenAI (text-embedding-3-small/ada-002).
    # Se formos usar outro modelo, ajustaremos esse valor.
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False) 
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    client: Mapped["Client"] = relationship(back_populates="memories")