from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    visible_path = Column(String(256), unique=True, nullable=False, index=True)
    security_level = Column(Integer, nullable=False, default=1)  # 1=L1, 2=L2, 3=L3, 4=L4
    password_hash = Column(String(128), nullable=True)
    allow_listing = Column(Boolean, nullable=False, default=False)  # 是否允许目录列表
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, path={self.visible_path})>"
