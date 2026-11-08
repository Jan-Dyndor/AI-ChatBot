from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.db import Base


class StatusMessage(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileStatus(StrEnum):
    PROCESSING = "PROCESSING"
    READY = "READY"
    DELETING = "DELETING"


class IndexingStatus(StrEnum):
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"


class Conversations(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    user: Mapped[Users] = relationship(back_populates="conversations")

    messages: Mapped[list[Messages]] = relationship(
        back_populates="conversation", order_by="Messages.created_at.asc()"
    )
    summary: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Messages(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False
    )
    conversation: Mapped[Conversations] = relationship(back_populates="messages")
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(tz=UTC)
    )
    status: Mapped[StatusMessage] = mapped_column(
        default=StatusMessage.PENDING, nullable=False
    )


class Users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    conversations: Mapped[list[Conversations]] = relationship(back_populates="user")
    files: Mapped[list[Files]] = relationship(back_populates="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(tz=UTC)
    )


class Files(Base):
    __tablename__ = "files"

    __table_args__ = (
        Index(
            "uq_user_file_sha",
            "user_id",
            "file_sha",
            unique=True,
            postgresql_where=text("file_sha != 'NOT COMPUTED'"),
        ),
    )

    __table_args__ = (
        Index(
            "uq_user_file_sha",
            "user_id",
            "file_sha",
            unique=True,
            postgresql_where=text("file_sha != 'NOT COMPUTED'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped[Users] = relationship(back_populates="files")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(tz=UTC)
    )
    index_status: Mapped[IndexingStatus] = mapped_column(
        String,
        nullable=False,
        default=IndexingStatus.PENDING,
        server_default=IndexingStatus.PENDING,
    )
    task_id: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
    )
    file_sha: Mapped[str] = mapped_column(String, nullable=False, unique=False)
    file_status: Mapped[FileStatus] = mapped_column(
        String,
        nullable=False,
        server_default=FileStatus.PROCESSING,
        default=FileStatus.PROCESSING,
    )
