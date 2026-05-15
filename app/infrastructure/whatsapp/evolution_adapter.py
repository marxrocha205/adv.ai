from app.domain.schemas.message_schema import StandardWebhookMessage
from app.core.logger import logger

class EvolutionWebhookAdapter:
    
    @staticmethod
    def parse_payload(payload: dict) -> StandardWebhookMessage | None:
        try:
            event = payload.get("event")
            if event != "messages.upsert":
                return None
                
            data = payload.get("data", {})
            message_data = data.get("message", {})
            key = data.get("key", {})
            
            remote_jid = key.get("remoteJid", "")
            wa_id = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
            
            if "status" in remote_jid or "g.us" in remote_jid:
                return None

            # 1. Identificando o Tipo de Mensagem
            msg_type = "text"
            text_content = ""
            mime_type = None
            media_data = None
            message_id = key.get("id")

            # Se for texto normal
            if "conversation" in message_data:
                text_content = message_data["conversation"]
            # Se for resposta a outra mensagem
            elif "extendedTextMessage" in message_data:
                text_content = message_data["extendedTextMessage"].get("text", "")
            # Se for ÁUDIO
            elif "audioMessage" in message_data:
                msg_type = "audio"
                mime_type = message_data["audioMessage"].get("mimetype")
                media_data = message_data["audioMessage"]
                text_content = "[Áudio Recebido]" # Placeholder até a IA processar
            # Se for DOCUMENTO (PDF, Planilha)
            elif "documentMessage" in message_data:
                msg_type = "document"
                mime_type = message_data["documentMessage"].get("mimetype")
                media_data = message_data["documentMessage"]
                text_content = f"[Documento Recebido: {media_data.get('title', 'arquivo')}]"
            # Se for IMAGEM
            elif "imageMessage" in message_data:
                msg_type = "image"
                mime_type = message_data["imageMessage"].get("mimetype")
                media_data = message_data["imageMessage"]
                text_content = "[Imagem Recebida]"

            # Ignora se não conseguimos extrair nada útil
            if not text_content and msg_type == "text":
                return None

            return StandardWebhookMessage(
                provider="evolution",
                wa_id=wa_id,
                contact_name=data.get("pushName", "Desconhecido"),
                text=text_content,
                is_from_me=key.get("fromMe", False),
                timestamp=data.get("messageTimestamp", 0),
                message_type=msg_type,
                mime_type=mime_type,
                media_data=media_data,
                message_id=message_id
            )
            
        except Exception as e:
            logger.error(f"Erro ao parsear payload da Evolution: {str(e)} | Payload: {payload}")
            return None