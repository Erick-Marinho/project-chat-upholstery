from app.infrastructure.services.llm.openai_service import OpenAIService
from app.infrastructure.interfaces.illm_service import ILLMService


class LLMFactory:
    @staticmethod
    def create_llm_service(provider: str) -> ILLMService:
        if provider == "openai":
            return OpenAIService()
        else:
            raise ValueError(f"Provider {provider} not supported")
