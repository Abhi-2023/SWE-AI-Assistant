import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, func
from datetime import datetime
from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.repository import Repository
    from app.db.models.message import Message


class Conversation(Base):
    __tablename__ = "conversation"

    id:                 Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:            Mapped[str]           = mapped_column(String(36), ForeignKey("user.id",       ondelete="CASCADE"))
    repo_id:            Mapped[str]           = mapped_column(String(36), ForeignKey("repository.id", ondelete="CASCADE"))
    ticket_id:          Mapped[Optional[str]] = mapped_column(String(100),  nullable=True)
    ticket_type:        Mapped[Optional[str]] = mapped_column(String(50),   nullable=True)
    ticket_description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status:             Mapped[str]           = mapped_column(String(50), default="pending")
    created_at:         Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    user:       Mapped["User"]         = relationship("User",       back_populates="conversations")
    repository: Mapped["Repository"]   = relationship("Repository", back_populates="conversations")
    messages:   Mapped[List["Message"]] = relationship("Message",   back_populates="conversation", cascade="all, delete-orphan")