from fastapi import APIRouter, Request, BackgroundTasks, status
from fastapi.responses import JSONResponse
from app.infrastructure.whatsapp.evolution_adapter import EvolutionWebhookAdapter
from app.core.logger import logger

router = APIRouter()

# Utilizando BackgroundTasks para não travar a resposta HTTP
async def process_incoming_message(standard_msg):
    """
    Função assíncrona que vai lidar com o peso do negócio.
    É aqui que, no futuro, chamaremos o RAG, salvaremos no banco e enviaremos a resposta.
    """
    logger.info(f"Processando nova mensagem de {standard_msg.wa_id}: {standard_msg.text}")
    # TODO: Passar a mensagem para a Camada de Serviço (CRM e IA)

@router.post("/evolution", tags=["Webhooks"])
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint dedicado a receber webhooks da Evolution API.
    A Evolution faz um POST para cá toda vez que algo acontece no WhatsApp.
    """
    try:
        # Pega o JSON cru enviado pela Evolution
        payload = await request.json()
        logger.debug(f"Webhook Evolution recebido")
        
        # Usa nosso Adapter para traduzir o payload
        standard_msg = EvolutionWebhookAdapter.parse_payload(payload)
        
        if standard_msg and not standard_msg.is_from_me:
            # Envia para processamento em background (assim respondemos 200 OK rápido para a Evolution)
            background_tasks.add_task(process_incoming_message, standard_msg)
            
        return JSONResponse(content={"status": "success"}, status_code=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Falha ao processar webhook: {e}")
        # Mesmo com erro interno, retornamos 200 para a Evolution não bloquear a fila de mensagens dela
        return JSONResponse(content={"status": "error"}, status_code=status.HTTP_200_OK)