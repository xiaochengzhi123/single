from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from signaltutor.db.base import Base


def new_id() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    messages: Mapped[list[Message]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ProblemAsset(Base):
    __tablename__ = "problem_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str | None] = mapped_column(String(36), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("problem_assets.id"))
    status: Mapped[str] = mapped_column(String(40), default="parsed")
    question_text: Mapped[str] = mapped_column(Text)
    chapter: Mapped[str | None] = mapped_column(String(80), index=True)
    topics_json: Mapped[list] = mapped_column(JSON, default=list)
    parse_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProblemAttempt(Base):
    __tablename__ = "problem_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id"), index=True)
    student_id: Mapped[str | None] = mapped_column(String(36), index=True)
    mode: Mapped[str] = mapped_column(String(40))
    correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    solution_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KnowledgeCardModel(Base):
    __tablename__ = "knowledge_cards"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject: Mapped[str] = mapped_column(String(80), default="signals_and_systems")
    chapter: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(240))
    content_json: Mapped[dict] = mapped_column(JSON)
    search_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))


class SolutionPatternModel(Base):
    __tablename__ = "solution_patterns"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    chapter: Mapped[str] = mapped_column(String(80), index=True)
    topics_json: Mapped[list] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String(240))
    content_json: Mapped[dict] = mapped_column(JSON)


class ErrorPatternModel(Base):
    __tablename__ = "error_patterns"
    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    chapter: Mapped[str] = mapped_column(String(80), index=True)
    topics_json: Mapped[list] = mapped_column(JSON)
    content_json: Mapped[dict] = mapped_column(JSON)


class ProblemExampleModel(Base):
    __tablename__ = "problem_examples"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    chapter: Mapped[str] = mapped_column(String(80), index=True)
    topics_json: Mapped[list] = mapped_column(JSON)
    difficulty: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[dict] = mapped_column(JSON)


class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    topic: Mapped[str] = mapped_column(String(160), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.5)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (Index("ux_student_topic", "student_id", "topic", unique=True),)


class StudentError(Base):
    __tablename__ = "student_errors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    problem_id: Mapped[str | None] = mapped_column(String(36), index=True)
    topic: Mapped[str] = mapped_column(String(160), index=True)
    error_code: Mapped[str] = mapped_column(String(100), index=True)
    error_step: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    problem_id: Mapped[str] = mapped_column(String(36), index=True)
    workflow: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_usage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_confidence: Mapped[float | None] = mapped_column(Float)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_version: Mapped[str] = mapped_column(String(40))
    convention_version: Mapped[str] = mapped_column(String(40))
    taxonomy_version: Mapped[str] = mapped_column(String(40))


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    duration_ms: Mapped[int] = mapped_column(Integer)
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    problem_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str | None] = mapped_column(String(36), index=True)
    rating: Mapped[str] = mapped_column(String(40))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
