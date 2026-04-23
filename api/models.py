from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    exchange = Column(String(20), nullable=False)
    tax_year = Column(Integer, nullable=False)
    account_holder = Column(String(255), nullable=False, comment="Email in Hanko")
    uid = Column(String(128), nullable=False, comment="User Id in Hanko")
    status = Column(String(20), nullable=False)
    request_payload_json = Column(JSON, nullable=False)
    result_payload_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")

class JobEvent(Base):
    __tablename__ = "job_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    message = Column(String(255), nullable=True)
    event_payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="events")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(50), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    job = relationship("Job", back_populates="documents")
