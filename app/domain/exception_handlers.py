from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import re

class TipoExcecao(str, Enum):
    """Tipos de exceção que requerem intervenção humana"""
    SERVICO_FORA_ESCOPO = "servico_fora_escopo"
    RECLAMACAO = "reclamacao"
    CANCELAMENTO = "cancelamento"
    HORARIO_NAO_COMERCIAL = "horario_nao_comercial"
    DADOS_INVALIDOS = "dados_invalidos"
    PERGUNTA_COMPLEXA = "pergunta_complexa"
    RESISTENCIA_CLIENTE = "resistencia_cliente"
    ERRO_TECNICO = "erro_tecnico"

class ExcecaoDetectada(BaseModel):
    """Modelo para exceções detectadas"""
    tipo: TipoExcecao = Field(..., description="Tipo da exceção")
    confianca: float = Field(..., description="Nível de confiança (0-1)")
    descricao: str = Field(..., description="Descrição da exceção")
    prioridade: int = Field(1, description="Prioridade da exceção (1=alta, 3=baixa)")
    sugestao_resposta: Optional[str] = Field(None, description="Sugestão de resposta")
    requer_transbordo: bool = Field(True, description="Se requer transbordo imediato")

class ExceptionDetector:
    """Detector inteligente de exceções e casos especiais"""
    
    def __init__(self):
        # Padrões que indicam serviços fora do escopo
        self.servicos_fora_escopo = [
            r"banco.*carro", r"carro.*banco", r"assento.*carro",
            r"tapete.*carro", r"volante", r"painel.*carro",
            r"carpete.*residencial", r"piso", r"tapete.*comum",
            r"roupa", r"tecido.*roupa", r"cortina.*lavagem",
            r"móvel.*madeira", r"mesa.*madeira", r"guarda.*roupa"
        ]
        
        # Padrões de reclamação
        self.padroes_reclamacao = [
            r"não.*ficou.*bom", r"ficou.*pior", r"danificou", r"estragou",
            r"mancha.*não.*saiu", r"cheiro.*ruim", r"problema.*serviço",
            r"insatisfeito", r"não.*gostei", r"quero.*reclamar",
            r"técnico.*mal.*educado", r"atraso", r"não.*veio"
        ]
        
        # Padrões de cancelamento
        self.padroes_cancelamento = [
            r"cancelar.*agendamento", r"desmarcar", r"não.*quero.*mais",
            r"mudei.*ideia", r"cancelar.*serviço", r"não.*vai.*dar"
        ]
        
        # Padrões de resistência do cliente
        self.padroes_resistencia = [
            r"não.*quero.*dar.*dados", r"muita.*pergunta", r"já.*disse",
            r"esse.*mesmo.*número", r"não.*precisa.*saber",
            r"por.*que.*precisa", r"muito.*burocrático"
        ]
        
        # Perguntas complexas que requerem especialista
        self.perguntas_complexas = [
            r"que.*produto.*usa", r"é.*tóxico", r"faz.*mal.*pet",
            r"alergia.*produto", r"garantia.*quanto.*tempo",
            r"seguro.*dano", r"responsabilidade.*civil",
            r"como.*funciona.*equipamento", r"técnica.*limpeza"
        ]
    
    def detectar_excecoes(self, mensagem: str, contexto: dict = None) -> List[ExcecaoDetectada]:
        """Detecta exceções na mensagem do usuário"""
        excecoes = []
        mensagem_lower = mensagem.lower()
        
        # 1. Detectar serviços fora do escopo
        for padrao in self.servicos_fora_escopo:
            if re.search(padrao, mensagem_lower):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.SERVICO_FORA_ESCOPO,
                    confianca=0.9,
                    descricao=f"Serviço fora do escopo detectado: {padrao}",
                    prioridade=1,
                    sugestao_resposta="Para esse tipo de serviço, vou conectar você com nossa equipe especializada.",
                    requer_transbordo=True
                ))
        
        # 2. Detectar reclamações
        for padrao in self.padroes_reclamacao:
            if re.search(padrao, mensagem_lower):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.RECLAMACAO,
                    confianca=0.85,
                    descricao=f"Reclamação detectada: {padrao}",
                    prioridade=1,
                    sugestao_resposta="Entendo sua preocupação. Vou conectar você imediatamente com nossa equipe para resolver essa situação.",
                    requer_transbordo=True
                ))
        
        # 3. Detectar cancelamentos
        for padrao in self.padroes_cancelamento:
            if re.search(padrao, mensagem_lower):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.CANCELAMENTO,
                    confianca=0.8,
                    descricao=f"Solicitação de cancelamento: {padrao}",
                    prioridade=1,
                    sugestao_resposta="Vou conectar você com nossa equipe para processar o cancelamento.",
                    requer_transbordo=True
                ))
        
        # 4. Detectar resistência do cliente
        for padrao in self.padroes_resistencia:
            if re.search(padrao, mensagem_lower):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.RESISTENCIA_CLIENTE,
                    confianca=0.7,
                    descricao=f"Resistência detectada: {padrao}",
                    prioridade=2,
                    sugestao_resposta="Entendo. Esses dados são necessários apenas para o agendamento e são protegidos pela LGPD.",
                    requer_transbordo=False
                ))
        
        # 5. Detectar perguntas complexas
        for padrao in self.perguntas_complexas:
            if re.search(padrao, mensagem_lower):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.PERGUNTA_COMPLEXA,
                    confianca=0.8,
                    descricao=f"Pergunta complexa: {padrao}",
                    prioridade=1,
                    sugestao_resposta="Essa é uma excelente pergunta técnica. Vou conectar você com nosso especialista.",
                    requer_transbordo=True
                ))
        
        # 6. Detectar horário não comercial (baseado no contexto se disponível)
        if contexto and contexto.get("horario_nao_comercial"):
            excecoes.append(ExcecaoDetectada(
                tipo=TipoExcecao.HORARIO_NAO_COMERCIAL,
                confianca=1.0,
                descricao="Atendimento fora do horário comercial",
                prioridade=1,
                sugestao_resposta="Nosso horário de atendimento é Segunda à Sexta das 08:00 às 18:00, Sábados das 08:00 às 12:00. Retornaremos em breve!",
                requer_transbordo=True
            ))
        
        return excecoes
    
    def validar_dados(self, dados: dict) -> List[ExcecaoDetectada]:
        """Valida dados fornecidos pelo usuário"""
        excecoes = []
        
        # Validar CPF
        if "cpf" in dados and dados["cpf"]:
            if not self._validar_cpf(dados["cpf"]):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.DADOS_INVALIDOS,
                    confianca=1.0,
                    descricao="CPF inválido",
                    prioridade=1,
                    sugestao_resposta="O CPF informado parece estar incorreto. Poderia verificar e informar novamente?",
                    requer_transbordo=False
                ))
        
        # Validar telefone
        if "telefone" in dados and dados["telefone"]:
            if not self._validar_telefone(dados["telefone"]):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.DADOS_INVALIDOS,
                    confianca=0.8,
                    descricao="Telefone inválido",
                    prioridade=1,
                    sugestao_resposta="O telefone informado parece estar incompleto. Poderia informar com DDD?",
                    requer_transbordo=False
                ))
        
        # Validar email
        if "email" in dados and dados["email"]:
            if not self._validar_email(dados["email"]):
                excecoes.append(ExcecaoDetectada(
                    tipo=TipoExcecao.DADOS_INVALIDOS,
                    confianca=0.9,
                    descricao="Email inválido",
                    prioridade=1,
                    sugestao_resposta="O email informado parece estar incorreto. Poderia verificar?",
                    requer_transbordo=False
                ))
        
        return excecoes
    
    def _validar_cpf(self, cpf: str) -> bool:
        """Valida formato básico do CPF"""
        cpf_numeros = re.sub(r'[^0-9]', '', cpf)
        return len(cpf_numeros) == 11 and not cpf_numeros == cpf_numeros[0] * 11
    
    def _validar_telefone(self, telefone: str) -> bool:
        """Valida formato básico do telefone"""
        telefone_numeros = re.sub(r'[^0-9]', '', telefone)
        return len(telefone_numeros) >= 10
    
    def _validar_email(self, email: str) -> bool:
        """Valida formato básico do email"""
        padrao_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(padrao_email, email) is not None
