from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.domain.scheduling_data import SchedulingData


class SchedulingAgentState(TypedDict):
    """
    Representa o estado do agente de agendamento.
    """

    # Mensagens da conversa
    messages: Annotated[list[BaseMessage], add_messages]

    # Dados do usuário
    phone_number: str
    message_id: str

    # Dados do agendamento
    scheduling_data: SchedulingData

    # Controle de fluxo
    next_step: Optional[str] = None

    # Contexto da conversa
    conversation_context: Optional[str]
