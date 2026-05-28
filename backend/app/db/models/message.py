import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from datetime import datetime
from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class Message(Base):
    __tablename__ = "message"

    id:              Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str]           = mapped_column(String(36), ForeignKey("conversation.id", ondelete="CASCADE"))
    role:            Mapped[str]           = mapped_column(String(20))
    content:         Mapped[str]           = mapped_column(Text)
    pr_url:          Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    agent_steps:     Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    files_changed:   Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")