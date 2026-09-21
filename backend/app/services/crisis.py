from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import CrewMember, CrisisState, HealthStatus
from app.services import autonomy, journal, triage


def get_or_create_crisis(db: Session) -> CrisisState:
    row = db.query(CrisisState).filter(CrisisState.id == 1).first()
    if not row:
        row = CrisisState(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def trigger_crisis(db: Session, sick_ratio: float | None = None) -> dict:
    ratio = sick_ratio if sick_ratio is not None else settings.crisis_sick_ratio
    crisis = get_or_create_crisis(db)
    before = autonomy.compare_policies(db)

    crew = db.query(CrewMember).order_by(CrewMember.id).all()
    target = max(1, int(len(crew) * ratio))

    for i, member in enumerate(crew):
        if i < target:
            member.health_status = HealthStatus.sick
            member.severity_score = 40 + (i % 5) * 10
        else:
            if member.health_status != HealthStatus.quarantine:
                member.health_status = HealthStatus.healthy
                member.severity_score = 0

    crisis.active = True
    crisis.sick_ratio = ratio
    crisis.autonomy_snapshot_before = before
    db.commit()

    triage.update_triage_scores(db)
    sick_count = sum(1 for c in crew if c.health_status == HealthStatus.sick)

    journal.log_decision(
        db,
        action="crisis_trigger",
        summary=f"Crise epidemique: {sick_count} malades ({ratio:.0%})",
        payload={"sick_ratio": ratio, "sick_count": sick_count},
    )

    return {
        "sick_count": sick_count,
        "sick_ratio": ratio,
        "autonomy_before": before,
    }


def activate_rationing(db: Session) -> dict:
    crisis = get_or_create_crisis(db)
    crisis.rationing_active = True
    db.commit()

    members = db.query(CrewMember).filter(CrewMember.health_status == HealthStatus.sick).all()
    for m in members[: max(1, len(members) // 2)]:
        m.health_status = HealthStatus.quarantine

    db.commit()
    triage.update_triage_scores(db)

    result = autonomy.compare_policies(db)
    journal.log_decision(
        db,
        action="rationing",
        summary="Rationnement et quarantaine actives",
        payload=result,
    )
    return result


def reset_crew_health(db: Session) -> None:
    for m in db.query(CrewMember).all():
        m.health_status = HealthStatus.healthy
        m.severity_score = 0
        m.triage_priority = 99
    crisis = get_or_create_crisis(db)
    crisis.active = False
    crisis.rationing_active = False
    crisis.sick_ratio = 0.0
    crisis.autonomy_snapshot_before = None
    db.commit()
