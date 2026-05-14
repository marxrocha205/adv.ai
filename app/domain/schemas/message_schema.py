from pydantic import BaseModel
from typing import Optional

class StandardWebhookMessage(BaseModel):
    """
    Formato universal de mensagem do nosso sistema.
    Não importa se veio da Evolution, Meta, ou Twilio, 
    tudo será convertido para esta classe antes de tocar no RAG ou no Banco.
    """
    provider: str               # "evolution" ou "meta"
    wa_id: str                  # Número do WhatsApp (ex: 5511999999999)
    contact_name: Optional[str] # Nome do contato (se disponível)
    text: str                   # Conteúdo da mensagem
    is_from_me: bool            # True se a mensagem foi enviada pelo próprio bot/advogado
    timestamp: int              # Timestamp da mensagem