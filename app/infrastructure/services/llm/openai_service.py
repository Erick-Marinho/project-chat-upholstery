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
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.OPENAI_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )
        
        # LLM estruturado para extração
        self.structured_llm = self.llm.with_structured_output(ExtractedInfo)
        
        # Prompt de extração MELHORADO
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """
Você é um especialista em extrair informações de conversas de atendimento da Doutor Sofá (limpeza de estofados).

Analise a mensagem e extraia:

DADOS PESSOAIS: nome, telefone, email, CPF, endereço completo, bairro
SERVIÇO: item (sofá, cadeira, colchão, cabeceira, poltrona, banco_carro), quantidade, tamanho  
LOCALIZAÇÃO: cidade, bairro
CONTEXTO: foto_enviada, aceita_orcamento, quer_agendar

DETECÇÃO DE ETAPAS - SEJA PRECISO:

1. **inicial**: 
   - Saudações: "boa tarde", "olá", "bom dia"
   - Primeira interação: "gostaria de orçamento", "preciso de limpeza"

2. **identificacao_item**: 
   - Menciona item: "sofá", "cadeira", "colchão", "cabeceira", "poltrona"
   - Descreve móvel: "sofá de 3 lugares", "colchão queen"

3. **captacao_localizacao**: 
   - Menciona cidade: "Chapecó", "Aracaju", "moro em..."
   - Informa endereço: "Rua das Flores, 123"

4. **identificacao_cliente**:
   - Fornece dados pessoais: nome, CPF, telefone, email
   - Se apresenta: "Meu nome é João"

5. **orcamento**: 
   - Discute preços: "quanto custa", "qual o valor"
   - Apresentação de orçamento já foi feita

6. **confirmacao_orcamento**: 
   - ACEITA: "sim", "ok", "pode ser", "vou querer", "gostei", "fechado"
   - REJEITA: "não", "muito caro", "vou pensar"

7. **transbordo_humano**: 
   - Quer agendar: "quero agendar", "quando vocês têm disponível", "qual horário"
   - Aceita e quer prosseguir: depois de aceitar orçamento
   - Pergunta fora do escopo: "vocês limpam carro?"

REGRAS IMPORTANTES:
- Se mencionou item E cidade = captacao_localizacao
- Se aceitou orçamento (sim/ok) = confirmacao_orcamento 
- Se aceitou E quer prosseguir = transbordo_humano
- Extraia apenas informações explicitamente mencionadas
- Seja conservador nas detecções
            """),
            ("human", "{message}")
        ])

    async def orchestrator_prompt_template(self, user_query: str, chat_history: List[BaseMessage] = None, scheduling_data = None):
        """
        Prepara o prompt do agente orquestrador com histórico e contexto.
        """
        if chat_history is None:
            chat_history = []
        
        # Construir contexto baseado no estado atual
        context = self._build_context(scheduling_data) if scheduling_data else ""
        
        chain = ORCHESTRATOR_PROMPT_TEMPLATE | self.llm
        try:
            llm_response = await asyncio.to_thread(
                chain.invoke, 
                {
                    "message": user_query, 
                    "chat_history": chat_history,
                    "agent_scratchpad": [],
                    "context": context
                }
            )
            return llm_response
        except Exception as e:
            logger.error(f"Erro ao gerar resposta do agente orquestrador: {e}")
            raise e

    async def extract_information(self, user_message: str) -> Dict[str, Any]:
        """
        Extrai informações estruturadas da mensagem do usuário.
        """
        chain = self.extraction_prompt | self.structured_llm
        try:
            extracted_info = await asyncio.to_thread(
                chain.invoke, 
                {"message": user_message}
            )
            return extracted_info.dict()
        except Exception as e:
            logger.error(f"Erro ao extrair informações: {e}")
            return {}
    
    def _build_context(self, scheduling_data) -> str:
        """Constrói contexto baseado no estado atual"""
        if not scheduling_data:
            return ""
            
        context_parts = []
        
        # Informações do cliente
        if scheduling_data.cliente.nome_completo:
            context_parts.append(f"Cliente: {scheduling_data.cliente.nome_completo}")
        
        # Informações do serviço
        if scheduling_data.servico.item_selecionado:
            context_parts.append(f"Item: {scheduling_data.servico.item_selecionado}")
        
        # Etapa atual
        context_parts.append(f"Etapa atual: {scheduling_data.etapa_atual}")
        
        # Localização
        if scheduling_data.cidade:
            context_parts.append(f"Cidade: {scheduling_data.cidade}")
        
        return " | ".join(context_parts) if context_parts else ""
