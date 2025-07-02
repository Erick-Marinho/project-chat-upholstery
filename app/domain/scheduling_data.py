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
    
    def dados_obrigatorios_completos(self) -> bool:
        """Verifica se todos os dados obrigatórios foram coletados"""
        dados_cliente = self.cliente
        dados_servico = self.servico
        
        # Dados obrigatórios do cliente
        cliente_completo = all([
            dados_cliente.nome_completo,
            dados_cliente.telefone,
            dados_cliente.cpf,
            dados_cliente.email,
            dados_cliente.endereco_completo
        ])
        
        # Dados obrigatórios do serviço
        servico_completo = all([
            dados_servico.item_selecionado,
            self.cidade,
            dados_servico.aceito_orcamento is True
        ])
        
        return cliente_completo and servico_completo
    
    def dados_faltantes(self) -> list[str]:
        """Retorna lista de dados que ainda faltam"""
        faltantes = []
        
        if not self.cliente.nome_completo:
            faltantes.append("Nome completo")
        if not self.cliente.telefone:
            faltantes.append("Telefone")
        if not self.cliente.cpf:
            faltantes.append("CPF")
        if not self.cliente.email:
            faltantes.append("E-mail")
        if not self.cliente.endereco_completo:
            faltantes.append("Endereço completo")
        if not self.cidade:
            faltantes.append("Cidade")
        if not self.servico.item_selecionado:
            faltantes.append("Item para higienização")
        if self.servico.aceito_orcamento is not True:
            faltantes.append("Confirmação do orçamento")
            
        return faltantes
    
    def pode_fazer_transbordo(self) -> bool:
        """Verifica se pode fazer transbordo para humano"""
        return (self.etapa_atual == StatusFluxo.CONFIRMACAO_ORCAMENTO and 
                self.dados_obrigatorios_completos())