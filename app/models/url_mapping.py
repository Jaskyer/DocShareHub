from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class UrlMapping(Base):
    __tablename__ = "url_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True)
    url_name = Column(String(256), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("project_id", "url_name", name="uq_project_url_name"),
    )

    def __repr__(self):
        return f"<UrlMapping(id={self.id}, url_name={self.url_name})>"
