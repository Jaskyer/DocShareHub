from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(16), nullable=False, default="pending")  # pending | approved | rejected
    feishu_message_id = Column(String(128), nullable=True)
    processor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AccessRequest(id={self.id}, status={self.status})>"
