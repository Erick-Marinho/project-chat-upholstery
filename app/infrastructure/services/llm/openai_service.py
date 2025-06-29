import logging
from langchain_openai import ChatOpenAI
from app.infrastructure.config.config import settings
from app.application.agent.node.orchestrator.orchestrator_prompt import (
    orchestrator_prompt_template as ORCHESTRATOR_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.OPENAI_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )

    def orchestrator_prompt_template(self, user_query: str):
        """
        Prepara o prompt do agente orquestrador.
        """
        chain = ORCHESTRATOR_PROMPT_TEMPLATE | self.llm
        try:
            llm_response = chain.invoke({"message": user_query, "chat_history": [], "agent_scratchpad": []})
            return llm_response
        except Exception as e:
            logger.error(f"Erro ao gerar resposta do agente orquestrador: {e}")
            raise e
