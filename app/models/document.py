from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, BigInteger
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    original_filename = Column(String(512), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    file_size = Column(BigInteger, default=0)
    mime_type = Column(String(128), nullable=True)
    is_directory = Column(Boolean, nullable=False, default=False)
    is_renamed = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Document(id={self.id}, name={self.original_filename})>"
