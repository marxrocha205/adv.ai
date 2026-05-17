from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.schemas.message_schema import StandardWebhookMessage
from app.infrastructure.models import Client, Message
from app.infrastructure.whatsapp.evolution_client import EvolutionClient
from app.services.rag_service import RAGService
from app.core.logger import logger
from sqlalchemy.dialects.postgresql import insert
import re

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
        """
        Busca o cliente ou cria um novo usando a estratégia de Upsert 
        para evitar Race Conditions em chamadas simultâneas.
        """
        # 1. Prepara a instrução de INSERT
        stmt = (
            insert(Client)
            .values(
                wa_id=msg.wa_id,
                name=msg.contact_name,
                status="onboarding" # Garante que comece no onboarding
            )
            .on_conflict_do_update(
                index_elements=["wa_id"], # Coluna com o UNIQUE INDEX
                set_={"name": msg.contact_name} # Se já existir, apenas atualiza o nome se mudou
            )
            .returning(Client)
        )

        # 2. Executa e faz o commit
        result = await db.execute(stmt)
        await db.commit()
        client = result.scalar_one()
        
        return client

    async def _save_message(self, db: AsyncSession, client_id: int, content: str, direction: str):
        """Salva a mensagem no histórico do banco de dados."""
        new_msg = Message(client_id=client_id, direction=direction, content=content)
        db.add(new_msg)
        await db.commit()
    def _extract_cpf(self, text: str) -> str | None:
        """Extrai e limpa um padrão de CPF (11 dígitos) do texto."""
        if not text:
            return None
        # Procura por 11 números seguidos ou no formato 000.000.000-00
        cpf_pattern = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
        match = cpf_pattern.search(text)
        if match:
            # Remove pontos e traços, deixando apenas os dígitos
            return re.sub(r'\D', '', match.group(0))
        return None
    
    async def _update_onboarding_data(self, db: AsyncSession, client: Client, user_message: str):
        """Verifica se o usuário enviou os dados de triagem e atualiza o banco."""
        cpf_encontrado = self._extract_cpf(user_message)
        
        if cpf_encontrado:
            logger.info(f"CPF extraído com sucesso para o wa_id {client.wa_id}: {cpf_encontrado}")
            client.cpf = cpf_encontrado
            
            # Tenta extrair o nome real. Se o texto for longo, removemos o CPF para tentar isolar o nome.
            # Uma abordagem sênior simples: se o usuário digitou "Fulano de tal - 123...", 
            # limpamos o CPF e salvamos o resto se parecer um nome.
            texto_limpo = re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '', user_message).strip()
            
            if len(texto_limpo) > 3 and client.full_name is None:
                # Se sobrou um texto considerável, assumimos que é o nome completo informado
                client.full_name = texto_limpo
            else:
                # Caso contrário, usamos o pushName do WhatsApp como fallback estruturado
                client.full_name = client.name

            # Muta o status para active! A partir daqui o RAG vira a chave.
            client.status = "active"
            
            db.add(client)
            await db.commit()
            await db.refresh(client)
    async def process_message(self, db: AsyncSession, msg: StandardWebhookMessage):
        try:
            # 1. Busca ou Cria o Cliente
            client = await self._get_or_create_client(db, msg)
            
            # 2. Define se está em Onboarding (Se não tiver CPF, status é onboarding)
            # Note que adicionamos a verificação do campo 'cpf' que você criou no Model
            if client.status == "onboarding" or not client.cpf:
                await self._update_onboarding_data(db, client, msg.text)
            
            # 3. Recalcula a flag após a tentativa de atualização
            is_onboarding = client.status == "onboarding" or not client.cpf

            # 3. Lógica de Mídia
            media_content = None
            if msg.message_type in ["audio", "document", "image"] and msg.message_id:
                logger.info(f"Mídia detectada ({msg.message_type}). Baixando...")
                await self.evo_client.send_presence(msg.instance, msg.wa_id, "composing")
                
                downloaded_data = await self.evo_client.download_media(msg.instance, msg.message_id)
                if downloaded_data:
                    media_content = {
                        "base64": downloaded_data.get("base64"),
                        "mimetype": msg.mime_type
                    }
                else:
                    msg.text = "[Erro ao processar o arquivo enviado pelo cliente.]"

            # 4. Salva a mensagem de entrada (Inbound)
            await self._save_message(db, client.id, msg.text, "inbound")

            # 5. Presença (Gravando áudio ou Digitando)
            presence_type = "recording" if msg.message_type == "audio" else "composing"
            await self.evo_client.send_presence(msg.instance, msg.wa_id, presence_type)

            # 6. Chama o RAG Service UMA ÚNICA VEZ com todos os parâmetros
            ai_response = await self.rag_service.get_response(
                db=db,
                client_id=client.id,
                user_message=msg.text,
                media_data=media_content,
                is_onboarding=is_onboarding,
                client_name=client.name or "Cliente"
            )

            # 7. Salva a resposta da IA (Outbound) e envia via Evolution
            await self._save_message(db, client.id, ai_response, "outbound")
            await self.evo_client.send_text_message(msg.instance, msg.wa_id, ai_response)

            logger.info(f"Atendimento {'Onboarding' if is_onboarding else 'RAG'} concluído para {msg.wa_id}")

        except Exception as e:
            logger.error(f"Falha crítica no fluxo para {msg.wa_id}: {e}")
            await db.rollback() # Limpa a transação para não travar o banco
            try:
                await self.evo_client.send_text_message(
                    msg.instance,
                    msg.wa_id, 
                    "Nosso sistema está passando por uma atualização. O advogado já foi notificado."
                )
            except:
                pass