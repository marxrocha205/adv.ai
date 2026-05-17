from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from app.infrastructure.models import MemoryRAG
from app.core.config import settings
from app.core.logger import logger

class RAGService:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001", 
            google_api_key=settings.GOOGLE_API_KEY
        )
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3 
        )

    async def get_response(
        self, 
        db: AsyncSession, 
        client_id: int, 
        user_message: str, 
        media_data: dict = None,
        is_onboarding: bool = True,
        client_name: str = "Cliente"
    ) -> str:
        """
        Orquestra a triagem inicial ou a busca vetorial (RAG) conforme o estado do cliente.
        """
        try:
            contexto = "Nenhuma informação prévia."
            
            # 1. Lógica de Contexto: Só faz busca vetorial se NÃO estiver no onboarding
            if not is_onboarding:
                question_embedding = await self.embeddings.aembed_query(user_message)
                query = (
                    select(MemoryRAG)
                    .where(MemoryRAG.client_id == client_id)
                    .order_by(MemoryRAG.embedding.cosine_distance(question_embedding))
                    .limit(3)
                )
                result = await db.execute(query)
                memories = result.scalars().all()
                if memories:
                    contexto = "\n".join([mem.text_content for mem in memories])

            # 2. Definição do System Prompt Dinâmico
            if is_onboarding:
                system_prompt = f"""Você é Junior, um assistente jurídico sênior altamente empático.
                CLIENTE ATUAL: {client_name}
                
                ESTADO ATUAL: TRIAGEM INICIAL (Aguardando identificação)
    
    SUA MISSÃO:
    1. Obter o NOME COMPLETO e o CPF do cliente. Esses dados são obrigatórios para qualquer consulta.
    
    DIRETRIZES DE COMPORTAMENTO:
    - CASO SEJA O PRIMEIRO "OI" OU CONTATO INICIAL: Dê as boas-vindas calorosas ao escritório e solicite o Nome Completo e CPF explicando que é para localização de processos ou abertura de protocolo.
    - CASO O CLIENTE JÁ TENHA SIDO SAUDADO E ENVIE OUTRA MENSAGEM (como um novo 'oi', 'tudo bem?' ou perguntas gerais) SEM ENVIAR O CPF OU NOME: Não repita a saudação de boas-vindas. Seja direto e diga firmemente, mas com gentileza, que você ainda está aguardando o Nome Completo e o CPF para poder iniciar o atendimento técnico.
    
    REGRAS CRÍTICAS:
    - NÃO responda nenhuma dúvida jurídica ou técnica enquanto o cliente não fornecer o CPF.
    - Insista sempre na coleta desses dois dados."""
            else:
                system_prompt = f"""Você é Junior, um assistente jurídico sênior.
                CLIENTE ATUAL: {client_name} (Identificado)
                
                INFORMAÇÕES DO CRM/VETORIAL:
                {contexto}
                
                DIRETRIZES DE ATENDIMENTO:
                1. Comece saudando o cliente e perguntando como pode ajudá-lo hoje (ex: "Como posso ajudar você hoje?" ou "Teria alguma dúvida específica?").
                2. Utilize o contexto acima para responder de forma precisa.
                3. Se a informação não estiver no contexto, diga que consultará os advogados responsáveis.
                4. Evite juridiquês. Seja claro."""

            # 3. Montagem da Mensagem Multimodal
            content_parts = [{"type": "text", "text": f"MENSAGEM DO CLIENTE: {user_message}"}]
            
            if media_data and "base64" in media_data:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_data['mimetype']};base64,{media_data['base64']}"}
                })

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=content_parts)
            ]

            # 4. Execução
            logger.info(f"Processando resposta para Cliente ID: {client_id} (Onboarding: {is_onboarding})")
            response = await self.llm.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Erro no RAG Service: {e}")
            return "Peço desculpas, tive um problema técnico ao processar sua solicitação. Poderia repetir?"