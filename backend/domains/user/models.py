from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.domains.shared.db_base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # API Configuration for LLM providers
    api_provider = Column(String, nullable=True)  # "gemini", "vertex", "openrouter"
    api_key_encrypted = Column(Text, nullable=True)  # Encrypted API key for gemini/openrouter
    provider_config_encrypted = Column(Text, nullable=True)  # Encrypted Vertex JSON config
    gemini_model = Column(String, nullable=True)
    vertex_model = Column(String, nullable=True)
    openrouter_model = Column(String, nullable=True)

    jobs = relationship("TranslationJob", back_populates="owner")