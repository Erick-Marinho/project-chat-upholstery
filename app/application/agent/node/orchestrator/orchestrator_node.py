import logging
from typing import List
from langchain_core.messages import AIMessage, BaseMessage
from app.application.agent.state.sheduling_agent_state import SchedulingAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.utils.get_last_message import get_last_message
from app.infrastructure.pesistence.postgres_persistence import get_store
from app.application.agent.registry.node_registry import register_node
from app.domain.scheduling_data import TipoItem, StatusFluxo, SchedulingData
from app.domain.exception_handlers import (
    ExceptionDetector, 
    TipoExcecao, 
    ExcecaoDetectada
)

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
    scheduling_data = None
    
    try:
        store = await get_store()
        
        # Recuperar scheduling_data do estado ou criar novo
        if isinstance(state, dict):
            scheduling_data = state.get("scheduling_data")
            user_name = state.get("phone_number", "user_default")
            messages = state.get("messages", [])
        else:
            scheduling_data = state.scheduling_data
            user_name = state.phone_number
            messages = state.messages
            
        if scheduling_data is None:
            logger.warning("scheduling_data era None, criando novo SchedulingData")
            scheduling_data = SchedulingData()
        
        logger.info(f"Executando nó orquestrador para usuário: {user_name}")
        logger.info(f"Etapa atual: {scheduling_data.etapa_atual}")
        
        # Obter a última mensagem do usuário
        user_message = get_last_message(state)
        if not user_message:
            logger.warning("Nenhuma mensagem encontrada no estado")
            return state
        
        logger.info(f"Conteúdo da mensagem: {user_message.content}")
        
        # Extrair informações estruturadas da mensagem
        llm_service = LLMFactory.create_llm_service("openai")
        extracted_info = await llm_service.extract_information(user_message.content)
        logger.info(f"Informações extraídas: {extracted_info}")
        
        exception_detector = ExceptionDetector()
        excecoes = exception_detector.detectar_excecoes(user_message.content, extracted_info)
        if excecoes:
            return await _tratar_excecoes(state, excecoes, scheduling_data)
        
        # Atualizar scheduling_data com informações extraídas
        await _update_scheduling_data(scheduling_data, extracted_info)
        
        # Construir contexto inteligente
        contexto_inteligente = _build_intelligent_context(scheduling_data)
        
        # Gerar resposta do LLM
        llm_response = await llm_service.orchestrator_prompt_template(
            user_query=user_message.content,
            chat_history=messages[:-1],  # Excluir a última mensagem (atual)
            scheduling_data=scheduling_data
        )
        
        ai_message = AIMessage(content=llm_response)
        
        # Persistir no BaseStore
        try:
            user_key = user_name or "user_default"
            await store.aput(("scheduling_data", user_key), "data", scheduling_data.model_dump())
            logger.info("SchedulingData persistido no BaseStore com sucesso")
        except Exception as e:
            logger.error(f"Erro no BaseStore: {e}")
        
        updated_state = state.copy()
        updated_state["messages"] = messages + [ai_message]
        updated_state["scheduling_data"] = scheduling_data
        updated_state["conversation_context"] = contexto_inteligente
        
        return updated_state
        
    except Exception as e:
        logger.error(f"Erro no nó orquestrador: {e}")
        
        # Criar exceção técnica e tratar
        excecao_tecnica = ExcecaoDetectada(
            tipo=TipoExcecao.ERRO_TECNICO,
            confianca=1.0,
            descricao=f"Erro técnico: {str(e)}",
            prioridade=1
        )
        
        # Garantir que scheduling_data existe
        if scheduling_data is None:
            scheduling_data = SchedulingData()
            
        return await _tratar_excecoes(state, [excecao_tecnica], scheduling_data)


def _build_intelligent_context(scheduling_data) -> str:
    """Constrói contexto inteligente baseado no estado e dados faltantes"""
    if not scheduling_data:
        return ""
    
    contextos = []
    
    try:
        # 🔧 CORREÇÃO: Acessar como dict em vez de objeto
        if isinstance(scheduling_data, dict):
            cliente = scheduling_data.get('cliente', {})
            servico = scheduling_data.get('servico', {})
            etapa_atual = scheduling_data.get('etapa_atual')
            cidade = scheduling_data.get('cidade')
        else:
            # Se for objeto SchedulingData
            cliente = scheduling_data.cliente.model_dump() if scheduling_data.cliente else {}
            servico = scheduling_data.servico.model_dump() if scheduling_data.servico else {}
            etapa_atual = scheduling_data.etapa_atual
            cidade = scheduling_data.cidade
            
        # Construir contexto baseado nos dados
        contextos.append(f"Etapa atual: {etapa_atual}")
        
        # Informações do cliente
        if cliente.get('nome_completo'):
            contextos.append(f"Cliente: {cliente['nome_completo']}")
        
        # Informações do serviço
        if servico.get('item_selecionado'):
            item_info = f"Item: {servico['item_selecionado']}"
            if servico.get('tamanho_item'):
                item_info += f" ({servico['tamanho_item']})"
            contextos.append(item_info)
            
        # Localização
        if cidade:
            contextos.append(f"Localização: {cidade}")
            
        return " | ".join(contextos)
        
    except Exception as e:
        logger.error(f"Erro ao construir contexto: {e}")
        return ""


async def _update_scheduling_data(scheduling_data, extracted_info: dict):
    """Atualiza o SchedulingData com as informações extraídas"""
    
    # Atualizar informações do cliente
    cliente_updates = {}
    if extracted_info.get("nome_completo"):
        cliente_updates["nome_completo"] = extracted_info["nome_completo"]
    if extracted_info.get("telefone"):
        # Limpar formatação do telefone
        telefone = extracted_info["telefone"].replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        cliente_updates["telefone"] = telefone
    if extracted_info.get("email"):
        cliente_updates["email"] = extracted_info["email"]
    if extracted_info.get("cpf"):
        # Limpar formatação do CPF
        cpf = extracted_info["cpf"].replace(".", "").replace("-", "").replace(" ", "")
        cliente_updates["cpf"] = cpf
    if extracted_info.get("endereco_completo"):
        cliente_updates["endereco_completo"] = extracted_info["endereco_completo"]
    if extracted_info.get("ponto_referencia"):
        cliente_updates["ponto_referencia"] = extracted_info["ponto_referencia"]
    
    if cliente_updates:
        scheduling_data.atualizar_cliente(**cliente_updates)
        logger.info(f"Cliente atualizado: {cliente_updates}")
    
    # Atualizar informações do serviço
    servico_updates = {}
    if extracted_info.get("item_mencionado"):
        item_map = {
            "sofá": TipoItem.SOFA,
            "cadeira": TipoItem.CADEIRA,
            "colchão": TipoItem.COLCHAO,
            "cabeceira": TipoItem.CABECEIRA,
            "poltrona": TipoItem.POLTRONA
        }
        servico_updates["item_selecionado"] = item_map.get(extracted_info["item_mencionado"], TipoItem.OUTRO)
    
    if extracted_info.get("quantidade_itens"):
        servico_updates["quantidade_itens"] = extracted_info["quantidade_itens"]
    
    if extracted_info.get("tamanho_item"):
        servico_updates["tamanho_item"] = extracted_info["tamanho_item"]
    
    if extracted_info.get("foto_enviada"):
        servico_updates["foto_enviada"] = extracted_info["foto_enviada"]
    
    # Detectar aceitação de orçamento
    if extracted_info.get("aceita_orcamento") is not None:
        servico_updates["aceito_orcamento"] = extracted_info["aceita_orcamento"]
    
    if servico_updates:
        scheduling_data.atualizar_servico(**servico_updates)
        logger.info(f"Serviço atualizado: {servico_updates}")
    
    # Atualizar localização (apenas cidade, não ponto de referência)
    if extracted_info.get("cidade"):
        scheduling_data.atualizar_localizacao(cidade=extracted_info["cidade"])
        logger.info(f"Localização atualizada: {extracted_info.get('cidade')}")
    
    # 🔧 MELHORAR: Lógica de avanço de etapas mais inteligente
    etapa_detectada = extracted_info.get("etapa_detectada", "inicial")
    etapa_atual = scheduling_data.etapa_atual
    
    # Determinar nova etapa baseada na atual e na detectada
    nova_etapa = _determinar_nova_etapa(etapa_atual, etapa_detectada, extracted_info, scheduling_data)
    
    if nova_etapa != etapa_atual:
        scheduling_data.avancar_etapa(nova_etapa)
        logger.info(f"Etapa avançada de {etapa_atual} para {nova_etapa}")


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
    
    # 🔧 PRIORIDADE 1: Se todos dados obrigatórios coletados → TRANSBORDO
    if scheduling_data.dados_obrigatorios_completos():
        logger.info("✅ TODOS OS DADOS COLETADOS - Enviando para transbordo humano")
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 2. Se detectou dados pessoais, verificar se ainda faltam
    if any([extracted_info.get(campo) for campo in ["nome_completo", "telefone", "cpf", "email", "endereco_completo"]]):
        if etapa_atual in [StatusFluxo.CONFIRMACAO_ORCAMENTO, StatusFluxo.IDENTIFICACAO_CLIENTE]:
            # Ainda coletando dados pessoais
            return StatusFluxo.IDENTIFICACAO_CLIENTE
    
    # 3. Se cliente aceitou orçamento explicitamente
    if extracted_info.get("aceita_orcamento") is True:
        if scheduling_data.dados_faltantes():
            logger.info(f"ORÇAMENTO ACEITO mas ainda faltam dados: {scheduling_data.dados_faltantes()}")
            return StatusFluxo.CONFIRMACAO_ORCAMENTO
        else:
            return StatusFluxo.TRANSBORDO_HUMANO
    
    # 4. Fluxo de localização e orçamento
    if extracted_info.get("cidade") and etapa_atual in [StatusFluxo.IDENTIFICACAO_ITEM, StatusFluxo.CAPTACAO_LOCALIZACAO]:
        # Se informou cidade mas ainda não temos orçamento apresentado
        if scheduling_data.servico.aceito_orcamento is None:
            return StatusFluxo.ORCAMENTO  # Apresentar orçamento e aguardar confirmação
        else:
            return StatusFluxo.CAPTACAO_LOCALIZACAO
    
    # 5. Se cliente quer agendar explicitamente
    if extracted_info.get("quer_agendar") is True:
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 6. Se detectou transbordo diretamente
    if etapa_detectada == "transbordo_humano":
        return StatusFluxo.TRANSBORDO_HUMANO
    
    # 7. Progressão normal
    etapa_nova = etapa_map.get(etapa_detectada, StatusFluxo.INICIAL)
    
    # Ordem de prioridade das etapas
    ordem_etapas = {
        StatusFluxo.INICIAL: 1,
        StatusFluxo.IDENTIFICACAO_ITEM: 2,
        StatusFluxo.CAPTACAO_LOCALIZACAO: 3,
        StatusFluxo.ORCAMENTO: 4,
        StatusFluxo.CONFIRMACAO_ORCAMENTO: 5,
        StatusFluxo.IDENTIFICACAO_CLIENTE: 6,
        StatusFluxo.TRANSBORDO_HUMANO: 7
    }
    
    # Só avança se a nova etapa tem prioridade maior
    if ordem_etapas.get(etapa_nova, 0) > ordem_etapas.get(etapa_atual, 0):
        return etapa_nova
    
    # Mantém a etapa atual
    return etapa_atual


async def _tratar_excecoes(state: SchedulingAgentState, 
                          excecoes: List[ExcecaoDetectada], 
                          scheduling_data) -> SchedulingAgentState:
    """Trata exceções detectadas"""
    
    # Pegar a exceção mais prioritária
    excecao_principal = max(excecoes, key=lambda x: x.prioridade)
    
    # Gerar resposta baseada no tipo de exceção
    respostas_excecao = {
        TipoExcecao.SERVICO_FORA_ESCOPO: "Para esse tipo de serviço, preciso conectar você com nossa equipe especializada que poderá te orientar melhor. Um momento, por favor!",
        TipoExcecao.RECLAMACAO: "Entendo sua preocupação e quero resolver isso da melhor forma. Vou conectar você imediatamente com nossa equipe de atendimento especializada.",
        TipoExcecao.CANCELAMENTO: "Entendo que deseja cancelar. Vou conectar você com nossa equipe para verificarmos os detalhes e processos necessários.",
        TipoExcecao.HORARIO_NAO_COMERCIAL: "Nosso atendimento é das 8h às 18h. Assim que iniciarmos o expediente, nossa equipe retornará seu contato.",
        TipoExcecao.DADOS_INVALIDOS: "Verifiquei que algumas informações precisam ser corrigidas. Vou conectar você com nossa equipe para ajustar os dados.",
        TipoExcecao.RESISTENCIA_CLIENTE: "Entendo suas preocupações. Vou conectar você com nossa equipe comercial que poderá esclarecer melhor todos os detalhes do nosso serviço.",
        TipoExcecao.ERRO_TECNICO: "Desculpe, tivemos um problema técnico momentâneo. Vou conectar você com nossa equipe para continuarmos o atendimento."
    }
    
    resposta = respostas_excecao.get(excecao_principal.tipo, "Vou conectar você com nossa equipe para melhor atendimento.")
    
    # Atualizar scheduling_data para transbordo humano
    scheduling_data.avancar_etapa(StatusFluxo.TRANSBORDO_HUMANO)
    
    ai_message = AIMessage(content=resposta)
    
    # 🔧 FIX: Tratar state como dict (TypedDict)
    updated_state = state.copy()
    
    # Obter mensagens atuais
    if isinstance(state, dict):
        current_messages = state.get("messages", [])
    else:
        current_messages = state.messages
    
    updated_state["messages"] = current_messages + [ai_message]
    updated_state["scheduling_data"] = scheduling_data
    updated_state["conversation_context"] = f"EXCEÇÃO: {excecao_principal.tipo}"
    
    return updated_state
