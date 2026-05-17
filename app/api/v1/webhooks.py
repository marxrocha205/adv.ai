from fastapi import APIRouter, Request, BackgroundTasks, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.whatsapp.evolution_adapter import EvolutionWebhookAdapter
from app.services.chat_manager import ChatManager
from app.infrastructure.database import get_db_session
from app.core.logger import logger

router = APIRouter()
chat_manager = ChatManager()

async def background_processor(msg, db: AsyncSession):
    await chat_manager.process_message(db, msg)
    await db.close()

# Mudança 1: Adicionamos o {event_type} na rota
@router.post("/evolution/{event_type}", tags=["Webhooks"])
@router.post("/evolution", tags=["Webhooks"]) # Mantém a rota antiga por segurança
async def evolution_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    event_type: str = "unknown", # Captura o tipo de evento
    db: AsyncSession = Depends(get_db_session) 
):
    try:
        # 1. Lidando com eventos de status de conexão do WhatsApp
        if event_type == "connection-update":
            logger.info("Evolution: Status de conexão atualizado (QR Code gerado ou aparelho conectado).")
            return JSONResponse(content={"status": "success"}, status_code=status.HTTP_200_OK)

        # 2. Ignora eventos que não nos interessam no momento (ex: status de envio)
        if event_type not in ["messages-upsert", "unknown"]:
            return JSONResponse(content={"status": "ignored"}, status_code=status.HTTP_200_OK)

        # 3. Fluxo normal para mensagens recebidas
        payload = await request.json()
        standard_msg = EvolutionWebhookAdapter.parse_payload(payload)
        
        if standard_msg and not standard_msg.is_from_me:
            logger.debug(f"Webhook validado. Enviando para o ChatManager: {standard_msg.wa_id}")
            background_tasks.add_task(background_processor, standard_msg, db)
            
        return JSONResponse(content={"status": "success"}, status_code=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Falha estrutural ao receber webhook: {e}")
        return JSONResponse(content={"status": "error"}, status_code=status.HTTP_200_OK)