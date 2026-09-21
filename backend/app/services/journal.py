from sqlalchemy.orm import Session

from app.models.entities import CrewMember, DecisionLog


def log_decision(
    db: Session,
    *,
    action: str,
    summary: str,
    payload: dict | None = None,
    crew_member_id: int | None = None,
    stock_snapshot: dict | None = None,
) -> DecisionLog:
    entry = DecisionLog(
        action=action,
        summary=summary,
        payload=payload or {},
        crew_member_id=crew_member_id,
        stock_snapshot=stock_snapshot,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_recent(db: Session, limit: int = 50) -> list[DecisionLog]:
    return (
        db.query(DecisionLog)
        .order_by(DecisionLog.created_at.desc())
        .limit(limit)
        .all()
    )
