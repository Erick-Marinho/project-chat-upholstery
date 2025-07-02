import logging
from typing import List
from langchain_core.messages import AIMessage, BaseMessage
from app.application.agent.state.sheduling_agent_state import SchedulingAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.utils.get_last_message import get_last_message
from app.infrastructure.pesistence.postgres_persistence import get_store
from app.application.agent.registry.node_registry import register_node
from app.domain.scheduling_data import TipoItem, StatusFluxo, SchedulingData

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
    Nó orquestrador que extrai informações, atualiza estado e interage com LLM.
    """
    last_message = get_last_message(state)
    phone_number = state.get("phone_number")
    scheduling_data = state.get("scheduling_data")
    current_messages = state.get("messages", [])
    
    # 🔧 SEGURANÇA: Garantir que scheduling_data existe
    if scheduling_data is None:
        logger.warning("scheduling_data era None, criando novo SchedulingData")
        scheduling_data = SchedulingData()
    
    logger.info(f"Executando nó orquestrador para usuário: {phone_number}")
    logger.info(f"Etapa atual: {scheduling_data.etapa_atual}")
    
    llm_service = LLMFactory.create_llm_service("openai")
    
    try:
        # 1. EXTRAÇÃO DE INFORMAÇÕES
        message_content = _extract_message_content(last_message)
        logger.info(f"Conteúdo da mensagem: {message_content}")
        
        extracted_info = await llm_service.extract_information(message_content)
        logger.info(f"Informações extraídas: {extracted_info}")
        
        # 2. ATUALIZAÇÃO DO ESTADO
        await _update_scheduling_data(scheduling_data, extracted_info)
        
        # 3. CONSTRUIR HISTÓRICO DE CONVERSA + CONTEXTO INTELIGENTE
        chat_history = _build_chat_history(current_messages)
        contexto_inteligente = _build_intelligent_context(scheduling_data)
        logger.info(f"Histórico de conversa: {len(chat_history)} mensagens")
        
        # 4. GERAÇÃO DA RESPOSTA COM CONTEXTO
        llm_response = await llm_service.orchestrator_prompt_template(
            user_query=message_content,
            chat_history=chat_history,
            scheduling_data=scheduling_data
        )
        
        # 5. PERSISTÊNCIA
        await _persist_user_data(phone_number, message_content, extracted_info, scheduling_data)
        
        ai_message = AIMessage(content=llm_response.content)
        
        return {
            **state,
            "messages": [ai_message],
            "scheduling_data": scheduling_data
        }
        
    except Exception as e:
        logger.error(f"Erro no nó orquestrador: {e}", exc_info=True)
        ai_message = AIMessage(content="Desculpe, houve um problema. Como posso te ajudar?")
        return {
            **state,
            "messages": [ai_message],
            "scheduling_data": scheduling_data
        }


def _extract_message_content(last_message) -> str:
    """Extrai conteúdo da mensagem de forma segura"""
    if last_message is None:
        return ""
    elif isinstance(last_message, str):
        return last_message
    elif hasattr(last_message, 'content'):
        return last_message.content
    else:
        return str(last_message)


def _build_chat_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Constrói histórico de chat excluindo a última mensagem"""
    if len(messages) <= 1:
        return []
    
    # Retorna todas as mensagens exceto a última (que será processada como 'message')
    return messages[:-1]


def _build_intelligent_context(scheduling_data) -> str:
    """Constrói contexto inteligente baseado no estado e dados faltantes"""
    if not scheduling_data:
        return ""
        
    context_parts = []
    
    # Informações do cliente
    if scheduling_data.cliente.nome_completo:
        context_parts.append(f"Cliente: {scheduling_data.cliente.nome_completo}")
    
    # Informações do serviço
    if scheduling_data.servico.item_selecionado:
        context_parts.append(f"Item: {scheduling_data.servico.item_selecionado}")
        
        # Tamanho se disponível
        if scheduling_data.servico.tamanho_item:
            context_parts.append(f"Tamanho: {scheduling_data.servico.tamanho_item}")
    
    # Localização
    if scheduling_data.cidade:
        context_parts.append(f"Cidade: {scheduling_data.cidade}")
    
    # Etapa atual
    context_parts.append(f"Etapa atual: {scheduling_data.etapa_atual}")
    
    # 🔧 NOVO: Indicar dados faltantes
    if scheduling_data.etapa_atual == StatusFluxo.CONFIRMACAO_ORCAMENTO:
        dados_faltantes = scheduling_data.dados_faltantes()
        if dados_faltantes:
            context_parts.append(f"DADOS FALTANTES: {', '.join(dados_faltantes)}")
        else:
            context_parts.append("TODOS OS DADOS COLETADOS - PRONTO PARA TRANSBORDO")
    
    # Status do orçamento
    if scheduling_data.servico.aceito_orcamento is True:
        context_parts.append("ORÇAMENTO ACEITO")
    elif scheduling_data.servico.aceito_orcamento is False:
        context_parts.append("ORÇAMENTO REJEITADO")
    
    return " | ".join(context_parts) if context_parts else ""


def _determinar_nova_etapa(etapa_atual: StatusFluxo, etapa_detectada: str, extracted_info: dict, scheduling_data) -> StatusFluxo:
    """Determina a nova etapa baseada na atual, detectada e contexto"""
    
    etapa_map = {
        "inicial": StatusFluxo.INICIAL,
        "identificacao_cliente": StatusFluxo.IDENTIFICACAO_CLIENTE,
        "identificacao_item": StatusFluxo.IDENTIFICACAO_ITEM,
        "captacao_localizacao": StatusFluxo.CAPTACAO_LOCALIZACAO,
        "orcamento": StatusFluxo.ORCAMENTO,
        "confirmacao_orcamento": StatusFluxo.CONFIRMACAO_ORCAMENTO,
        "transbordo_humano": StatusFluxo.TRANSBORDO_HUMANO
    }
    
    # 1. 🔧 VALIDAÇÃO RIGOROSA: Só vai para transbordo se TODOS os dados estiverem completos
    if (etapa_atual == StatusFluxo.CONFIRMACAO_ORCAMENTO and 
        scheduling_data.pode_fazer_transbordo()):
        logger.info("TRANSBORDO AUTORIZADO: Cliente pronto para atendimento humano")
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 2. Se cliente aceitou orçamento mas ainda faltam dados
    if extracted_info.get("aceita_orcamento") is True:
        if scheduling_data.dados_faltantes():
            logger.info(f"ORÇAMENTO ACEITO mas ainda faltam dados: {scheduling_data.dados_faltantes()}")
            return StatusFluxo.CONFIRMACAO_ORCAMENTO
        else:
            return StatusFluxo.TRANSBORDO_HUMANO
    
    # 3. Se detectou dados pessoais, pode ir para identificacao_cliente
    if (extracted_info.get("nome_completo") or 
        extracted_info.get("telefone") or 
        extracted_info.get("cpf") or
        extracted_info.get("endereco_completo")):
        return StatusFluxo.IDENTIFICACAO_CLIENTE
    
    # 4. Se cliente quer agendar explicitamente
    if extracted_info.get("quer_agendar") is True:
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 5. Se detectou transbordo diretamente
    if etapa_detectada == "transbordo_humano":
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 6. Progressão normal
    etapa_nova = etapa_map.get(etapa_detectada, StatusFluxo.INICIAL)
    
    # Ordem de prioridade das etapas
    ordem_etapas = {
        StatusFluxo.INICIAL: 1,
        StatusFluxo.IDENTIFICACAO_ITEM: 2,
        StatusFluxo.CAPTACAO_LOCALIZACAO: 3,
        StatusFluxo.IDENTIFICACAO_CLIENTE: 4,
        StatusFluxo.ORCAMENTO: 5,
        StatusFluxo.CONFIRMACAO_ORCAMENTO: 6,
        StatusFluxo.TRANSBORDO_HUMANO: 7
    }
    
    # Só avança se a nova etapa tem prioridade maior
    if ordem_etapas.get(etapa_nova, 0) > ordem_etapas.get(etapa_atual, 0):
        return etapa_nova
    
    # Mantém a etapa atual
    return etapa_atual


async def _update_scheduling_data(scheduling_data, extracted_info: dict):
    """Atualiza o SchedulingData com as informações extraídas"""
    
    # Atualizar informações do cliente
    cliente_updates = {}
    if extracted_info.get("nome_completo"):
        cliente_updates["nome_completo"] = extracted_info["nome_completo"]
    if extracted_info.get("telefone"):
        cliente_updates["telefone"] = extracted_info["telefone"]
    if extracted_info.get("email"):
        cliente_updates["email"] = extracted_info["email"]
    if extracted_info.get("cpf"):
        cliente_updates["cpf"] = extracted_info["cpf"]
    if extracted_info.get("endereco_completo"):
        cliente_updates["endereco_completo"] = extracted_info["endereco_completo"]
    
    if cliente_updates:
        scheduling_data.atualizar_cliente(**cliente_updates)
        logger.info(f"Cliente atualizado: {cliente_updates}")
    
    # Atualizar informações do serviço
    servico_updates = {}
    if extracted_info.get("item_mencionado"):
        # Mapear string para enum
        item_map = {
            "sofá": TipoItem.SOFA,
            "sofa": TipoItem.SOFA,
            "cadeira": TipoItem.CADEIRA,
            "poltrona": TipoItem.POLTRONA,
            "colchão": TipoItem.COLCHAO,
            "colchao": TipoItem.COLCHAO,
            "cabeceira": TipoItem.CABECEIRA,
            "banco_carro": TipoItem.BANCO_CARRO
        }
        item_str = extracted_info["item_mencionado"].lower()
        if item_str in item_map:
            servico_updates["item_selecionado"] = item_map[item_str]
    
    if extracted_info.get("quantidade_itens"):
        servico_updates["quantidade_itens"] = extracted_info["quantidade_itens"]
    if extracted_info.get("tamanho_item"):
        servico_updates["tamanho_item"] = extracted_info["tamanho_item"]
    if extracted_info.get("foto_enviada"):
        servico_updates["foto_enviada"] = extracted_info["foto_enviada"]
    
    # 🎯 MELHORAR: Detectar aceitação de orçamento
    if extracted_info.get("aceita_orcamento") is not None:
        servico_updates["aceito_orcamento"] = extracted_info["aceita_orcamento"]
    
    if servico_updates:
        scheduling_data.atualizar_servico(**servico_updates)
        logger.info(f"Serviço atualizado: {servico_updates}")
    
    # Atualizar localização
    if extracted_info.get("cidade"):
        scheduling_data.atualizar_localizacao(cidade=extracted_info["cidade"])
        logger.info(f"Localização atualizada: {extracted_info.get('cidade')}")
    
    # Atualizar etapa do fluxo com validação rigorosa
    etapa_detectada = extracted_info.get("etapa_detectada", "inicial")
    etapa_atual = scheduling_data.etapa_atual
    
    # Usar nova função que considera os dados obrigatórios
    nova_etapa = _determinar_nova_etapa(etapa_atual, etapa_detectada, extracted_info, scheduling_data)
    
    if nova_etapa != etapa_atual:
        scheduling_data.avancar_etapa(nova_etapa)
        logger.info(f"Etapa avançada de {etapa_atual} para {nova_etapa}")
        
        # Log adicional para transbordo
        if nova_etapa == StatusFluxo.TRANSBORDO_HUMANO:
            logger.info("🎯 TRANSBORDO ATIVADO: Cliente pronto para atendimento humano")


async def _persist_user_data(phone_number: str, message_content: str, extracted_info: dict, scheduling_data):
    """Persiste dados no BaseStore"""
    try:
        store = await get_store()
        
        # 🔧 Serialização segura do scheduling_data
        scheduling_data_dict = {
            "etapa_atual": str(scheduling_data.etapa_atual),
            "cidade": scheduling_data.cidade,
        }
        
        # Tentar serializar cliente e servico de forma segura
        try:
            if hasattr(scheduling_data.cliente, 'model_dump'):
                scheduling_data_dict["cliente"] = scheduling_data.cliente.model_dump()
            elif hasattr(scheduling_data.cliente, 'dict'):
                scheduling_data_dict["cliente"] = scheduling_data.cliente.dict()
        except:
            scheduling_data_dict["cliente"] = str(scheduling_data.cliente)
            
        try:
            if hasattr(scheduling_data.servico, 'model_dump'):
                scheduling_data_dict["servico"] = scheduling_data.servico.model_dump()
            elif hasattr(scheduling_data.servico, 'dict'):
                scheduling_data_dict["servico"] = scheduling_data.servico.dict()
        except:
            scheduling_data_dict["servico"] = str(scheduling_data.servico)
        
        await store.aput(
            namespace=["users"], 
            key=phone_number, 
            value={
                "last_message": message_content,
                "extracted_info": extracted_info,
                "scheduling_data": scheduling_data_dict,
                "timestamp": "2025-01-18"
            }
        )
        logger.info("Dados persistidos no BaseStore com sucesso")
    except Exception as e:
        logger.error(f"Erro no BaseStore: {e}")
