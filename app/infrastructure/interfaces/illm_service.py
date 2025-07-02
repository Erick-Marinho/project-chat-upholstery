from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage


class ILLMService(ABC):
    """
    Interface para serviços de LLM.
    """

    @abstractmethod
    async def orchestrator_prompt_template(self, user_query: str, chat_history: List[BaseMessage] = None, scheduling_data = None):
        """
        Retorna o prompt do agente orquestrador.
        """
        pass
    
    @abstractmethod
    async def extract_information(self, user_message: str) -> Dict[str, Any]:
        """
        Extrai informações estruturadas da mensagem do usuário.
        """
        pass
