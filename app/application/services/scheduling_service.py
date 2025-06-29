import logging
from langchain_core.messages import HumanMessage
from fastapi import Depends
from app.application.agent.scheduling_agent_builder import get_scheduling_agent
from app.domain.scheduling_data import SchedulingData

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    Serviço da camada de aplicação responsável por orquestrar
    o caso de uso de agendamento.
    """

    def __init__(self, scheduling_agent):
        """
        Inicializa o serviço de agendamento.
        """
        self.scheduling_agent = scheduling_agent

    async def handle_incoming_message(
        self, phone_number: str, message_text: str, message_id: str
    ) -> dict:
        """
        Serviço de agendamento processando mensagem.
        """
        logger.info(f"Serviço de agendamento processando mensagem de {phone_number}.")
        logger.info(f"Conteúdo para análise: '{message_text}'")
        logger.info(f"ID da mensagem: '{message_id}'")

        try:
            thread_id = phone_number
            config = {"configurable": {"thread_id": thread_id}}

            initial_state = {
                "phone_number": phone_number,
                "message_id": message_id,
                "messages": [HumanMessage(content=message_text)],
                "scheduling_data": SchedulingData(),
            }

            final_state = await self.scheduling_agent.ainvoke(
                initial_state, config=config
            )

            logger.info(
                f"Processamento do agente concluído. Estado final: {final_state}"
            )

            messages = final_state.get("messages", [])

            last_message = messages[-1]

            return {
                "status": "success",
                "message": last_message.content,
            }

        except Exception as e:
            logger.error(f"Erro ao processar mensagem com agente: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Erro ao processar mensagem com agente: {e}",
            }


def get_scheduling_service(agent=Depends(get_scheduling_agent)) -> SchedulingService:
    """
    Provedor de dependência para o SchedulingService.
    O FastAPI chamará esta função para injetar o serviço onde for necessário.
    """
    return SchedulingService(scheduling_agent=agent)
