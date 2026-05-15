from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.schemas.message_schema import StandardWebhookMessage
from app.infrastructure.models import Client, Message
from app.infrastructure.whatsapp.evolution_client import EvolutionClient
from app.services.rag_service import RAGService
from app.core.logger import logger

class ChatManager:
    """
    Orquestrador central do fluxo de atendimento.
    Aplica as regras de negócio: garante que o cliente exista no CRM,
    salva as mensagens e pede para a IA formular a resposta.
    """
    def __init__(self):
        self.evo_client = EvolutionClient()
        self.rag_service = RAGService()

    async def _get_or_create_client(self, db: AsyncSession, msg: StandardWebhookMessage) -> Client:
        """Busca o cliente no CRM pelo número do WhatsApp, ou cria um novo."""
        query = select(Client).where(Client.wa_id == msg.wa_id)
        result = await db.execute(query)
        client = result.scalars().first()

        if not client:
            logger.info(f"Novo cliente identificado: {msg.contact_name} ({msg.wa_id})")
            client = Client(wa_id=msg.wa_id, name=msg.contact_name, status="prospect")
            db.add(client)
            await db.commit()
            await db.refresh(client)
        
        return client

    async def _save_message(self, db: AsyncSession, client_id: int, content: str, direction: str):
        """Salva a mensagem no histórico do banco de dados."""
        new_msg = Message(client_id=client_id, direction=direction, content=content)
        db.add(new_msg)
        await db.commit()

    async def process_message(self, db: AsyncSession, msg: StandardWebhookMessage):
        """
        Fluxo principal de atendimento.
        1. Identifica o cliente.
        2. Salva a mensagem recebida.
        3. Consulta a IA (RAG).
        4. Salva a resposta gerada.
        5. Envia para o WhatsApp (simulando digitação).
        """
        try:
            # 1. CRM: Busca ou cria o cliente
            client = await self._get_or_create_client(db, msg)

            # 2. CRM: Salva a mensagem recebida (inbound)
            await self._save_message(db, client.id, msg.text, "inbound")

            # 3. IA: Manda o bot demonstrar que está "pensando" / "digitando"
            await self.evo_client.send_presence(msg.wa_id, "composing")

            # 4. IA: Busca contexto no RAG e gera a resposta
            ai_response = await self.rag_service.get_response(db, client.id, msg.text)

            # 5. CRM: Salva a resposta gerada no histórico (outbound)
            await self._save_message(db, client.id, ai_response, "outbound")

            # 6. WhatsApp: Envia de fato a resposta pro cliente
            await self.evo_client.send_text_message(msg.wa_id, ai_response)

            logger.info(f"Atendimento concluído para {msg.wa_id}")

        except Exception as e:
            logger.error(f"Falha crítica no fluxo de atendimento para {msg.wa_id}: {e}")
            await self.evo_client.send_text_message(
                msg.wa_id, 
                "Nosso sistema está passando por uma rápida atualização. O advogado responsável já foi notificado e responderá em breve."
            )