import httpx
from app.core.config import settings
from app.core.logger import logger

class EvolutionClient:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def send_presence(self, number: str, presence: str = "composing") -> bool:
        """
        Envia o status de digitação ou gravação.
        presence pode ser: "composing" (digitando) ou "recording" (gravando áudio).
        """
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {"number": number, "presence": presence, "delay": 2000}
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, headers=self.headers)
                return True
            except Exception as e:
                logger.warning(f"Falha ao enviar presença para {number}: {e}")
                return False

    async def send_text_message(self, number: str, text: str) -> bool:
        # Primeiro, simulamos que estamos digitando
        await self.send_presence(number, "composing")
        
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {"number": number, "textMessage": {"text": text}}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar texto para {number}: {e}")
                return False

    async def send_media(self, number: str, media_url_or_base64: str, media_type: str = "audio", caption: str = "") -> bool:
        """
        Envia áudios, PDFs, ou imagens.
        media_type pode ser: "audio", "document", "image", "video".
        """
        if media_type == "audio":
            await self.send_presence(number, "recording")
            
        url = f"{self.base_url}/message/sendWhatsAppMedia/{self.instance}"
        payload = {
            "number": number,
            "options": {"delay": 1000},
            "mediaMessage": {
                "mediatype": media_type,
                "caption": caption,
                "media": media_url_or_base64
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar mídia ({media_type}) para {number}: {e}")
                return False