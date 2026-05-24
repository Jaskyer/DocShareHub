from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feishu_open_id = Column(String(128), unique=True, nullable=False, index=True)
    feishu_user_id = Column(String(128), nullable=True)
    feishu_name = Column(String(128), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User(id={self.id}, name={self.feishu_name})>"
