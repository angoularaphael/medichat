import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

FlexibleJSON = JSON().with_variant(PG_JSONB, "postgresql")


class HealthStatus(str, enum.Enum):
    healthy = "healthy"
    sick = "sick"
    quarantine = "quarantine"


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    age: Mapped[int] = mapped_column(Integer)
    allergies: Mapped[list] = mapped_column(FlexibleJSON, default=list)
    conditions: Mapped[list] = mapped_column(FlexibleJSON, default=list)
    current_treatments: Mapped[list] = mapped_column(FlexibleJSON, default=list)
    health_status: Mapped[HealthStatus] = mapped_column(
        Enum(HealthStatus, native_enum=False), default=HealthStatus.healthy
    )
    severity_score: Mapped[int] = mapped_column(Integer, default=0)
    triage_priority: Mapped[int] = mapped_column(Integer, default=99)
    avatar_data: Mapped[str | None] = mapped_column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default="crew")
    crew_member_code: Mapped[str] = mapped_column(String(32), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    substance: Mapped[str] = mapped_column(String(128))
    therapeutic_class: Mapped[str] = mapped_column(String(64))
    indication: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(32), default="dose")
    dose_max_mg: Mapped[float] = mapped_column(Float, default=1000)
    stock_units: Mapped[int] = mapped_column(Integer, default=0)
    daily_burn_rate: Mapped[float] = mapped_column(Float, default=0.5)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)


class DrugSubstitution(Base):
    __tablename__ = "drug_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    to_drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    indication: Mapped[str] = mapped_column(String(128))
    priority: Mapped[int] = mapped_column(Integer, default=1)


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_a_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    drug_b_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    severity: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    crew_member_id: Mapped[int | None] = mapped_column(ForeignKey("crew_members.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CareRequest(Base):
    __tablename__ = "care_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_member_id: Mapped[int] = mapped_column(ForeignKey("crew_members.id"))
    symptoms: Mapped[list] = mapped_column(FlexibleJSON, default=list)
    requested_drug_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_dose_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(String(32), default="routine")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DecisionLog(Base):
    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_member_id: Mapped[int | None] = mapped_column(ForeignKey("crew_members.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(FlexibleJSON, default=dict)
    stock_snapshot: Mapped[dict | None] = mapped_column(FlexibleJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrisisState(Base):
    __tablename__ = "crisis_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    sick_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    rationing_active: Mapped[bool] = mapped_column(Boolean, default=False)
    autonomy_snapshot_before: Mapped[dict | None] = mapped_column(FlexibleJSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(FlexibleJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(FlexibleJSON, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlantCulture(Base):
    __tablename__ = "plant_cultures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    species: Mapped[str] = mapped_column(String(128))
    indication: Mapped[str] = mapped_column(String(128))
    replaces_drug_class: Mapped[str] = mapped_column(String(64))
    biomass_percent: Mapped[float] = mapped_column(Float, default=50.0)
    growth_rate: Mapped[float] = mapped_column(Float, default=4.0)
    status: Mapped[str] = mapped_column(String(32), default="growing")
    notes: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")


class BiologicalCulture(Base):
    __tablename__ = "stock_cultures_biologiques"

    id_culture: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nom_souche: Mapped[str] = mapped_column(String(128))
    categorie: Mapped[str] = mapped_column(String(64))
    temperature_celsius: Mapped[float] = mapped_column(Float)
    quantite_boites: Mapped[int] = mapped_column(Integer, default=0)
    statut_viabilite: Mapped[str] = mapped_column(String(32), default="Actif")
    indication: Mapped[str] = mapped_column(String(64), default="")
    treatable: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
