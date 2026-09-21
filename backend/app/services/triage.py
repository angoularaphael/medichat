from sqlalchemy.orm import Session

from app.models.entities import CrewMember, HealthStatus


def update_triage_scores(db: Session) -> list[CrewMember]:
    members = (
        db.query(CrewMember)
        .filter(CrewMember.health_status != HealthStatus.healthy)
        .order_by(CrewMember.severity_score.desc(), CrewMember.triage_priority.asc())
        .all()
    )
    priority = 1
    for m in members:
        m.triage_priority = priority
        priority += 1
    db.commit()
    return members


def list_triage(db: Session) -> list[dict]:
    members = (
        db.query(CrewMember)
        .filter(CrewMember.health_status != HealthStatus.healthy)
        .order_by(CrewMember.triage_priority.asc(), CrewMember.severity_score.desc())
        .all()
    )
    return [
        {
            "crew_member_code": m.code,
            "full_name": m.full_name,
            "health_status": m.health_status.value,
            "severity_score": m.severity_score,
            "triage_priority": m.triage_priority,
        }
        for m in members
    ]
