from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from database import Base


class ClaimRecord(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)

    claim_text = Column(String, unique=True)

    verification_status = Column(String)

    confidence_score = Column(Integer)

    verification_reason = Column(String)

    sources = Column(String)


class ReviewQueueRecord(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, index=True)

    claim_text = Column(String, unique=True)

    decision = Column(String)

    message = Column(String)

    verification_status = Column(String)

    confidence_score = Column(Integer)

    verification_reason = Column(String)

    sources = Column(String)

    status = Column(String, default="PENDING")

    created_at = Column(DateTime, default=datetime.utcnow)