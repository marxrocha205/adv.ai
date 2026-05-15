from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from app.infrastructure.models import MemoryRAG
from app.core.config import settings
from app.core.logger import logger

class RAGService:
    def __init__(self):
        # Modelo de Embeddings (Transforma texto em números vetoriais)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=settings.GOOGLE_API_KEY
        )
        
        # Modelo de Linguagem (Gera a resposta)
        # Usamos o gemini-1.5-flash por ser extremamente rápido para WhatsApp
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3 # Mais baixo para ser factual e jurídico
        )
        
        # O Prompt de Sistema
        self.prompt_template = PromptTemplate(
            input_variables=["contexto", "pergunta"],
            template="""Você é um assistente jurídico sênior altamente educado, trabalhando para um escritório de advocacia.
Seu objetivo é atender os clientes no WhatsApp de forma clara e empática.

INFORMAÇÕES DO CLIENTE (MEMÓRIA RAG):
{contexto}

PERGUNTA DO CLIENTE:
{pergunta}

DIRETRIZES:
1. Responda apenas com base no contexto fornecido. Se a informação não estiver lá, diga cordialmente que irá verificar com os advogados.
2. Evite "juridiquês" complexo. Explique as coisas de forma que qualquer pessoa entenda.
3. Seja breve e direto, é uma conversa de WhatsApp.

SUA RESPOSTA:"""
        )

    async def get_response(self, db: AsyncSession, client_id: int, user_message: str) -> str:
        """Orquestra a busca vetorial e a geração da resposta."""
        try:
            # 1. Gera o vetor da pergunta atual
            question_embedding = await self.embeddings.aembed_query(user_message)
            
            # 2. Busca no pgvector as 3 memórias mais relevantes do cliente
            # Usamos a distância de cosseno (<=>) nativa do pgvector via SQLAlchemy
            query = (
                select(MemoryRAG)
                .where(MemoryRAG.client_id == client_id)
                .order_by(MemoryRAG.embedding.cosine_distance(question_embedding))
                .limit(3)
            )
            
            result = await db.execute(query)
            memories = result.scalars().all()
            
            # 3. Monta o contexto juntando os textos das memórias
            contexto = "\n".join([mem.text_content for mem in memories]) if memories else "Nenhuma informação prévia."
            
            # 4. Formata o prompt e chama o Gemini
            final_prompt = self.prompt_template.format(contexto=contexto, pergunta=user_message)
            
            logger.info(f"Gerando resposta via Gemini para o cliente {client_id}")
            response = await self.llm.ainvoke(final_prompt)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Erro no RAG Service: {e}")
            return "Peço desculpas, estou enfrentando uma instabilidade técnica no momento. Logo retornarei."