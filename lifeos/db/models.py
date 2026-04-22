from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    tasks_json: Mapped[list] = mapped_column(JSON, nullable=False)
    events_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    total_reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    productivity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    wellbeing_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    timestep: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[float] = mapped_column(Float, nullable=False)
    stress: Mapped[float] = mapped_column(Float, nullable=False)
    money: Mapped[float] = mapped_column(Float, nullable=False)
    relationship_score: Mapped[float] = mapped_column(Float, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    tasks_json: Mapped[list] = mapped_column(JSON, nullable=False)
    pending_events_json: Mapped[list] = mapped_column(JSON, nullable=False)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    reward: Mapped[float] = mapped_column(Float, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    timestep: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_random: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    num_episodes: Mapped[int] = mapped_column(Integer, nullable=False)
    rewards_json: Mapped[list] = mapped_column(JSON, nullable=False)
    model_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
