from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class StatusCliente(str, Enum):
    """Status do cliente no sistema ERP"""
    NOVO = "novo"
    EXISTENTE = "existente" 
    BUSCANDO = "buscando"

class StatusFluxo(str, Enum):
    """Etapas do fluxo de atendimento - Yasmin Doutor Sofá"""
    INICIAL = "inicial"
    IDENTIFICACAO_CLIENTE = "identificacao_cliente"
    IDENTIFICACAO_ITEM = "identificacao_item"
    CAPTACAO_LOCALIZACAO = "captacao_localizacao"
    ORCAMENTO = "orcamento"
    CONFIRMACAO_ORCAMENTO = "confirmacao_orcamento"
    TRANSBORDO_HUMANO = "transbordo_humano"

class TipoItem(str, Enum):
    """Tipos de itens para higienização"""
    SOFA = "sofá"
    POLTRONA = "poltrona" 
    CADEIRA = "cadeira"
    COLCHAO = "colchão"
    CABECEIRA = "cabeceira"
    BANCO_CARRO = "banco_carro"

class ClienteInfo(BaseModel):
    """Informações do cliente"""
    nome_completo: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    endereco_completo: Optional[str] = None
    status_erp: StatusCliente = StatusCliente.NOVO
    cliente_id_erp: Optional[str] = None

class ServicoInfo(BaseModel):
    """Informações do serviço solicitado"""
    item_selecionado: Optional[TipoItem] = None
    quantidade_itens: Optional[int] = 1
    tamanho_item: Optional[str] = None
    foto_enviada: bool = False
    valor_orcamento: Optional[float] = None
    aceito_orcamento: Optional[bool] = None

class SchedulingData(BaseModel):
    """
    Dados de atendimento para limpeza de estofados - Doutor Sofá
    """
    
    # Manter compatibilidade com versão anterior
    user_name: Optional[str] = None
    
    # Informações do cliente
    cliente: ClienteInfo = Field(default_factory=ClienteInfo)
    
    # Informações do serviço
    servico: ServicoInfo = Field(default_factory=ServicoInfo)
    
    # Localização
    cidade: Optional[str] = None
    franquia: str = "Aracaju"  # Padrão para nossa implementação
    
    # Controle de fluxo
    etapa_atual: StatusFluxo = StatusFluxo.INICIAL
    
    # Timestamps para auditoria
    criado_em: Optional[datetime] = Field(default_factory=datetime.now)
    atualizado_em: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    def avancar_etapa(self, nova_etapa: StatusFluxo):
        """Avança para a próxima etapa do fluxo"""
        self.etapa_atual = nova_etapa
        self.atualizado_em = datetime.now()
    
    def atualizar_cliente(self, **kwargs):
        """Atualiza informações do cliente"""
        for key, value in kwargs.items():
            if hasattr(self.cliente, key):
                setattr(self.cliente, key, value)
        self.atualizado_em = datetime.now()
    
    def atualizar_servico(self, **kwargs):
        """Atualiza informações do serviço"""
        for key, value in kwargs.items():
            if hasattr(self.servico, key):
                setattr(self.servico, key, value)
        self.atualizado_em = datetime.now()
    
    def atualizar_localizacao(self, cidade: str = None):
        """Atualiza informações de localização"""
        if cidade:
            self.cidade = cidade
        self.atualizado_em = datetime.now()
