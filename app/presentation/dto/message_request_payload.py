from typing import Optional

from pydantic import BaseModel, Field


class TextMessage(BaseModel):
    """Representa o objeto de texto aninhado na mensagem."""

    message: str = Field(..., description="O conteúdo da mensagem de texto.")


class WebhookPayload(BaseModel):
    """
    Representa o payload completo recebido do webhook.
    Funciona como um 'contrato' de dados entre o serviço externo e nossa API.
    """

    # --- Campos Essenciais ---
    message_id: str = Field(
        alias="messageId",
        description="ID exclusivo da mensagem.",
    )
    phone_number: str = Field(
        alias="phone",
        description="Número de telefone do remetente.",
    )
    text: TextMessage = Field(description="O objeto de texto contendo a mensagem.")

    # --- Campos Opcionais Úteis ---
    chat_name: Optional[str] = Field(
        default=None,
        alias="chatName",
        description="Nome do chat (pode ser o nome do contato).",
    )
    sender_name: Optional[str] = Field(
        default=None,
        alias="senderName",
        description="Nome do remetente.",
    )
    instance_id: Optional[str] = Field(
        default=None,
        alias="instanceId",
        description="ID da instância que recebeu a mensagem.",
    )
    from_me: bool = Field(
        default=False,
        alias="fromMe",
        description="Indica se a mensagem foi enviada por nós.",
    )
    is_group: bool = Field(
        default=False,
        alias="isGroup",
        description="Indica se a mensagem é de um grupo.",
    )

    @property
    def message(self) -> str:
        """Propriedade de atalho para acessar a mensagem de texto diretamente."""
        return self.text.message

    class Config:
        """
        Configurações do modelo Pydantic.
        'allow_population_by_field_name = True' permite que o modelo seja
        preenchido usando tanto o nome do campo em Python (ex: message_id)
        quanto seu alias (ex: messageId).
        """

        allow_population_by_field_name = True
        anystr_strip_whitespace = True
