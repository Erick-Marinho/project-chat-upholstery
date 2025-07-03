import logging
import asyncio
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from app.infrastructure.config.config import settings
from app.application.agent.node.orchestrator.orchestrator_prompt import (
    orchestrator_prompt_template as ORCHESTRATOR_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class ExtractedInfo(BaseModel):
    """Modelo para informações extraídas da mensagem do usuário"""
    
    # Informações do cliente
    nome_completo: str | None = Field(None, description="Nome completo do cliente")
    telefone: str | None = Field(None, description="Telefone do cliente")
    email: str | None = Field(None, description="Email do cliente")
    cpf: str | None = Field(None, description="CPF do cliente")
    endereco_completo: str | None = Field(None, description="Endereço completo")
    bairro: str | None = Field(None, description="Bairro mencionado")
    ponto_referencia: str | None = Field(None, description="Ponto de referência mencionado")
    
    # Informações do serviço
    item_mencionado: str | None = Field(None, description="Tipo de item (sofá, cadeira, colchão, etc.)")
    quantidade_itens: int | None = Field(None, description="Quantidade de itens")
    tamanho_item: str | None = Field(None, description="Tamanho (2 lugares, queen, etc.)")
    
    # Localização
    cidade: str | None = Field(None, description="Cidade mencionada")
    
    # Contexto da conversa
    foto_enviada: bool = Field(False, description="Se enviou foto")
    aceita_orcamento: bool | None = Field(None, description="Se aceitou orçamento explicitamente")
    quer_agendar: bool = Field(False, description="Se demonstra interesse em agendar")
    
    # Etapa do fluxo
    etapa_detectada: str = Field("inicial", description="Etapa detectada baseada no contexto")


class OpenAIService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY,
        )
        
        # PROMPT DE EXTRAÇÃO DE INFORMAÇÕES
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """
Você é um especialista em extrair informações de conversas de atendimento da Doutor Sofá (limpeza de estofados).

🔧 IMPORTANTE - CIDADE vs PONTO DE REFERÊNCIA:

**CIDADE** (para localizar franquia responsável):
- Aracaju, Fortaleza, Salvador, São Paulo, etc.
- "Moro em Salvador"
- "Sou de Fortaleza" 
- "Estou em Aracaju"

**PONTO DE REFERÊNCIA** (para facilitar localização no endereço):
- "Próximo à Compesa"
- "Ao lado do shopping"
- "Perto da igreja"
- "Em frente ao banco"
- "Próximo ao hospital"
- "Ao lado da escola"

⚠️ **NÃO CONFUNDIR**: "compesa", "shopping", "banco" = ponto_referencia, NÃO cidade

**TELEFONE OBRIGATÓRIO** - Sempre extrair quando mencionado:
- (85)99999-9999 → telefone: "85999999999"
- 85 99999-9999 → telefone: "85999999999"  
- 11999998888 → telefone: "11999998888"
- "esse mesmo" (quando já está no WhatsApp) → telefone: "whatsapp_atual"

**DADOS PESSOAIS** - Seja muito preciso:
- "João Silva, CPF 123" → nome_completo: "João Silva"
- "Maria Santos telefone 11999" → nome_completo: "Maria Santos"
- "Sou Pedro Costa" → nome_completo: "Pedro Costa"
- "Me chamo Ana" → nome_completo: "Ana"

**ENDEREÇO COMPLETO**:
- "Rua das Flores, 123, apto 45" → endereco_completo: "Rua das Flores, 123, apto 45"
- "Rua A, número 80, Bairro B" → endereco_completo: "Rua A, 80, Bairro B"

**ETAPAS DO FLUXO**:
- Cliente pergunta sobre preço/orçamento → "identificacao_item"
- Cliente informa localização → "captacao_localizacao"  
- Cliente aceita orçamento → "confirmacao_orcamento"
- Cliente fornece dados pessoais → "identificacao_cliente"
- Todos dados coletados → "transbordo_humano"

Extraia as informações da mensagem e retorne em JSON estruturado.
"""),
            ("user", "{message}")
        ])

    async def extract_information(self, user_message: str) -> Dict[str, Any]:
        """Extrai informações estruturadas da mensagem do usuário"""
        try:
            structured_llm = self.llm.with_structured_output(ExtractedInfo)
            
            result = await structured_llm.ainvoke(
                self.extraction_prompt.format_messages(message=user_message)
            )
            
            return result.model_dump()
            
        except Exception as e:
            logger.error(f"Erro na extração de informações: {e}")
            return {}

    async def orchestrator_prompt_template(self, user_query: str, chat_history: List[BaseMessage] = None, scheduling_data = None):
        """
        Retorna o prompt do agente orquestrador.
        """
        try:
            if chat_history is None:
                chat_history = []
            
            # Construir contexto baseado no estado atual
            context = self._build_context(scheduling_data) if scheduling_data else ""
            
            response = await self.llm.ainvoke(
                ORCHESTRATOR_PROMPT_TEMPLATE.format_messages(
                    chat_history=chat_history,
                    user_query=user_query,
                    context=context
                )
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Erro no template do orquestrador: {e}")
            return "Desculpe, tive um problema momentâneo. Pode repetir?"

    def _build_context(self, scheduling_data) -> str:
        """Constrói o contexto baseado nos dados de agendamento"""
        if not scheduling_data:
            return ""
        
        contextos = []
        
        try:
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
            
            # Construir contexto
            if etapa_atual:
                contextos.append(f"Etapa atual: {etapa_atual}")
            
            if cliente.get('nome_completo'):
                contextos.append(f"Cliente: {cliente['nome_completo']}")
            
            if servico.get('item_selecionado'):
                item_info = f"Item: {servico['item_selecionado']}"
                if servico.get('tamanho_item'):
                    item_info += f" ({servico['tamanho_item']})"
                contextos.append(item_info)
                
            if cidade:
                contextos.append(f"Localização: {cidade}")
                
            return " | ".join(contextos)
            
        except Exception as e:
            logger.error(f"Erro ao construir contexto no OpenAIService: {e}")
            return ""
