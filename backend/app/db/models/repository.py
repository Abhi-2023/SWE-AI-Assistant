import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, func
from datetime import datetime
from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.conversation import Conversation


class Repository(Base):
    __tablename__ = "repository"

    id:               Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:          Mapped[str]              = mapped_column(String(36), ForeignKey("user.id", ondelete="CASCADE"))
    github_url:       Mapped[str]              = mapped_column(String(255))
    vector_namespace: Mapped[str]              = mapped_column(String(255))
    last_synced_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())

    user:          Mapped["User"]               = relationship("User",         back_populates="repositories")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="repository", cascade="all, delete-orphan")