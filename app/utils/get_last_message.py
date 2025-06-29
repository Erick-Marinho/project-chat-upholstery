from typing import Optional
from langchain_core.messages import BaseMessage
from app.application.agent.state.sheduling_agent_state import SchedulingAgentState


def get_last_message(state: SchedulingAgentState) -> Optional[BaseMessage]:
    """
    Retorna a última mensagem da lista de mensagens no estado do agente.

    Esta função encapsula a lógica de acessar a lista de mensagens
    de forma segura, evitando erros caso a lista esteja vazia.

    Args:
        state (SchedulingAgentState): O estado atual do agente.

    Returns:
        Optional[BaseMessage]: O último objeto de mensagem (como HumanMessage ou AIMessage), 
                               ou None se a lista de mensagens estiver vazia.
    """
    messages = state.get("messages")
    if not messages:
        return None
    return messages[-1].content.lower().strip()