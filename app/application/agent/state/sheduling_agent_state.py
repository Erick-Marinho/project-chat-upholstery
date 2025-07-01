from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.domain.scheduling_data import SchedulingData


class SchedulingAgentState(TypedDict):
    """
    Representa o estado do agente de atendimento.
    """

    # Mensagens da conversa
    messages: Annotated[list[BaseMessage], add_messages]

    # Dados do usuário
    phone_number: str
    message_id: str

    # Dados do atendimento
    scheduling_data: SchedulingData

    # Controle de ferramentas
    tool_calls: Optional[list] = None
    tool_results: Optional[list] = None

    # **REFLEXÃO AVANÇADA**
    draft_response: Optional[str] = None  # Resposta inicial para análise
    self_critique: Optional[str] = None   # Auto-crítica da resposta
    refinement_count: int = 0             # Contador de refinamentos

    # Controle de fluxo 
    next_step: Optional[str] = None

    # Contexto da conversa
    conversation_context: Optional[str] = None
