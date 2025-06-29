from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import JSON, TIMESTAMP, String, UUID, ForeignKey, Integer, TEXT, BOOLEAN
# from sqlalchemy.dialects.postgresql import VECTOR  # Comentado temporariamente
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.database_session import Base

class User(Base):
    __tablename__ = 'users'
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.now, onupdate=datetime.now)

    episodes: Mapped[list["EpisodicMemory"]] = relationship("EpisodicMemory", back_populates="user")

class EpisodicMemory(Base):
    __tablename__ = 'episodic_memory'
    
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(TEXT)
    outcome: Mapped[Optional[str]] = mapped_column(String(50))
    key_entities: Mapped[Optional[dict]] = mapped_column(JSON)
    conversation_turns: Mapped[Optional[int]] = mapped_column(Integer)
    # embedding: Mapped[Optional[list]] = mapped_column(VECTOR(1536))  # Comentado temporariamente
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.now)

    user: Mapped["User"] = relationship("User", back_populates="episodes")

class AgentHeuristic(Base):
    __tablename__ = 'agent_heuristics'
    
    heuristic_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_description: Mapped[str] = mapped_column(TEXT, nullable=False)
    rule_type: Mapped[Optional[str]] = mapped_column(String(50))
    actionable_knowledge: Mapped[Optional[dict]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, default=True)
    origin_analysis_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.now)