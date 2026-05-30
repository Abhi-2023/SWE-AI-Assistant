import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, func
from datetime import datetime
from app.db.database import Base

if TYPE_CHECKING:
    from app.db.models.repository import Repository
    from app.db.models.conversation import Conversation


class User(Base):
    __tablename__ = "user"

    id:              Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email:           Mapped[str]           = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str]           = mapped_column(String(255))
    github_token:    Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    repositories:  Mapped[List["Repository"]]  = relationship("Repository",  back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")