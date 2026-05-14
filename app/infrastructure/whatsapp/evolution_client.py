import httpx
from app.core.config import settings
from app.core.logger import logger

class EvolutionClient:
    """
    Cliente HTTP assíncrono para interagir com a Evolution API.
    Responsável por disparar mensagens ativas ou de resposta.
    """
    def __init__(self):
        # Removemos barras extras no final da URL para evitar erros de rota
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def send_text_message(self, number: str, text: str) -> bool:
        """
        Envia uma mensagem de texto simples.
        Inclui um 'delay' e o status de 'composing' (digitando) para humanizar o bot.
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": number,
            "options": {
                "delay": 1500, # 1.5 segundos simulando digitação
                "presence": "composing"
            },
            "textMessage": {
                "text": text
            }
        }
        
        # AsyncClient garante que a aplicação não trave enquanto espera o disparo
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Mensagem enviada com sucesso para {number}")
                return True
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP da Evolution API: {e.response.text}")
                return False
            except Exception as e:
                logger.error(f"Falha de conexão ao enviar mensagem para {number}: {e}")
                return False