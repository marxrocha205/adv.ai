from app.domain.schemas.message_schema import StandardWebhookMessage
from app.core.logger import logger

class EvolutionWebhookAdapter:
    """
    Adapter responsável por interpretar o Webhook da Evolution API
    e converter para o nosso formato padrão.
    """
    
    @staticmethod
    def parse_payload(payload: dict) -> StandardWebhookMessage | None:
        try:
            # A Evolution manda vários eventos. Só nos interessam as mensagens recebidas/enviadas.
            # O evento principal geralmente é "messages.upsert"
            event = payload.get("event")
            if event != "messages.upsert":
                return None
                
            data = payload.get("data", {})
            message_data = data.get("message", {})
            key = data.get("key", {})
            
            # Pega o número de quem enviou (removendo o sufixo @s.whatsapp.net)
            remote_jid = key.get("remoteJid", "")
            wa_id = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
            
            # Se for status, grupo ou não tiver texto claro, ignoramos por enquanto
            if "status" in remote_jid or "g.us" in remote_jid:
                return None
                
            # Extrai o texto (a Evolution pode mandar o texto em diferentes chaves dependendo do tipo da mensagem)
            # Aqui estamos focando em texto puro ou respostas (extended text)
            text = (
                message_data.get("conversation") or 
                message_data.get("extendedTextMessage", {}).get("text") or 
                ""
            )
            
            if not text:
                return None

            return StandardWebhookMessage(
                provider="evolution",
                wa_id=wa_id,
                contact_name=data.get("pushName", "Desconhecido"),
                text=text,
                is_from_me=key.get("fromMe", False),
                timestamp=data.get("messageTimestamp", 0)
            )
            
        except Exception as e:
            logger.error(f"Erro ao parsear payload da Evolution: {str(e)} | Payload: {payload}")
            return None