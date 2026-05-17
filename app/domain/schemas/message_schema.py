from pydantic import BaseModel
from typing import Optional

class StandardWebhookMessage(BaseModel):
    provider: str
    instance: str
    wa_id: str
    contact_name: Optional[str]
    text: str
    is_from_me: bool
    timestamp: int
    
    # --- NOVOS CAMPOS MULTIMODAIS ---
    message_type: str = "text" # Pode ser: text, audio, document, image
    mime_type: Optional[str] = None # Ex: application/pdf, audio/ogg
    media_data: Optional[dict] = None # Guardaremos os dados brutos da mídia aqui para baixar depois
    message_id: Optional[str] = None # ID da mensagem na Evolution (necessário para baixar a mídia)