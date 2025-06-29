from abc import ABC, abstractmethod


class ILLMService(ABC):
    """
    Interface para serviços de LLM.
    """

    @abstractmethod
    def orchestrator_prompt_template(self):
        """
        Retorna o prompt do agente orquestrador.
        """
        pass
