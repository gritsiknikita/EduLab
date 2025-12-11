from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="teacher")  # admin/teacher

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Workstation(Base):
    __tablename__ = "workstations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pc_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # ID агента
    name: Mapped[str] = mapped_column(String(128))
    room: Mapped[str] = mapped_column(String(128), default="")

    online: Mapped[bool] = mapped_column(Boolean, default=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    last_seen: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workstation_id: Mapped[int] = mapped_column(ForeignKey("workstations.id"))
    type: Mapped[str] = mapped_column(String(50))  # LOCK / UNLOCK / OPEN_URL
    payload: Mapped[dict] = mapped_column(JSON, default={})

    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued/sent/done/error
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workstation = relationship("Workstation")
