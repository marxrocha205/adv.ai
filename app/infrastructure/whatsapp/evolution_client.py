import httpx
from app.core.config import settings
from app.core.logger import logger

class EvolutionClient:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def send_presence(self, instance: str, number: str, presence: str = "composing") -> bool:
        url = f"{self.base_url}/chat/sendPresence/{instance}"
        payload = {
            "number": number, 
            "presence": presence, 
            "delay": 2000
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Usa timeout curto para presença, não precisa travar o bot
                await client.post(url, json=payload, headers=self.headers, timeout=5.0)
                return True
            except Exception as e:
                logger.warning(f"Falha ao enviar presença ({presence}) para {number} na instância {instance}: {e}")
                return False

    async def send_text_message(self, instance: str, number: str, text: str) -> bool:
        # Primeiro manda o "digitando..."
        await self.send_presence(instance=instance, number=number, presence="composing")
        
        url = f"{self.base_url}/message/sendText/{instance}"
        payload = {
            "number": number, 
            "text": text
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=15.0)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar texto para {number} na instância {instance}: {e}")
                return False

    async def send_media(self, instance: str, number: str, media_url_or_base64: str, media_type: str = "audio", caption: str = "") -> bool:
        """
        Envia áudios, PDFs, ou imagens.
        media_type pode ser: "audio", "document", "image", "video".
        """
        if media_type == "audio":
            await self.send_presence(number, "recording")
            
        url = f"{self.base_url}/message/sendWhatsAppMedia/{instance}"
        payload = {
            "number": number,
            "options": {"delay": 1000},
            "mediaMessage": {
                "mediatype": media_type, 
                "caption": caption,
                "media": media_url_or_base64
            }
        }
        
    async def download_media(self,instance:str, message_id: str) -> dict | None:
        """
        Baixa a mídia (Áudio, Documento, Imagem) da Evolution API em formato Base64.
        """
        url = f"{self.base_url}/chat/getBase64FromMediaMessage/{instance}"
        payload = {
            "message": {
                "key": {
                    "id": message_id
                }
            }
        }  
        
        async with httpx.AsyncClient() as client:
            try:
                # O timeout precisa ser maior aqui, pois converter PDFs/Áudios grandes para base64 pode demorar
                response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                # A Evolution retorna a string base64 dentro de data["base64"]
                if data and "base64" in data:
                    logger.info(f"Mídia {message_id} baixada com sucesso.")
                    return data
                
                logger.warning(f"Resposta inesperada ao baixar mídia {message_id}: {data}")
                return None
                
            except Exception as e:
                logger.error(f"Erro ao baixar mídia {message_id}: {e}")
                return None