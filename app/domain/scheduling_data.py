from pydantic import BaseModel
from typing import Optional


class SchedulingData(BaseModel):
    """
    Representa os dados de agendamento.
    """

    user_name: Optional[str] = None
    professional_name: Optional[str] = None
    specialty: Optional[str] = None
    date_scheduled: Optional[str] = None
    turn_scheduled: Optional[str] = None
    specific_time: Optional[str] = None
