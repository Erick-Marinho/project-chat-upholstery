import logging
from typing import Callable, Tuple
from langchain_core.messages import AIMessage
from app.application.agent.state.sheduling_agent_state import SchedulingAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.utils.get_last_message import get_last_message
from app.infrastructure.pesistence.postgres_persistence import get_store
from app.application.agent.registry.node_registry import register_node

logger = logging.getLogger(__name__)

@register_node(
        name="ORCHESTRATOR",
        enabled=True,
        timeout=0,
        priority=1,
        description="Nó principal de orquestração que interage como LLM"
)


async def orchestrator_node(state: SchedulingAgentState) -> SchedulingAgentState:
    """
    Nó orquestrador que interage como LLM e utiliza o BaseStore para persistir dados.
    """
    last_message = get_last_message(state)
    phone_number = state.get("phone_number")
    
    print("Executando nó orquestrador para o usuário: ", phone_number)
    
    # Teste básico do BaseStore
    try:
        store = await get_store()
        
        # Teste: salvar dados do usuário
        await store.put(
            namespace=["users"], 
            key=phone_number, 
            value={
                "last_message": last_message,
                "interaction_count": 1,
                "timestamp": "2025-01-18"
            }
        )
        
        # Teste: recuperar dados
        user_data = await store.get(namespace=["users"], key=phone_number)
        if user_data:
            print(f"BaseStore funcionando! Dados do usuário: {user_data.value}")
        else:
            print("Nenhum dado encontrado para o usuário")
            
    except Exception as e:
        print(f"Erro no BaseStore: {e}")
    
    llm_service = LLMFactory.create_llm_service("openai")
    llm_response = llm_service.orchestrator_prompt_template(last_message)
    
    ai_message = AIMessage(content=llm_response.content)
    
    return {
        **state,
        "messages": [ai_message]
    }
