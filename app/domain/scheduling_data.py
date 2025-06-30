from pydantic import BaseModel
from typing import Optional


class SchedulingData(BaseModel):
    """
    Representa os dados de agendamento.
    """

    user_name: Optional[str] = None
