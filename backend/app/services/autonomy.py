from sqlalchemy.orm import Session

from app.models.entities import CrewMember, CrisisState, Drug, HealthStatus
from app.config import settings


def _effective_burn(drug: Drug, sick_count: int, crew_size: int, rationing: bool) -> float:
    base = drug.daily_burn_rate
    if crew_size <= 0:
        return base
    load = 1.0 + (sick_count / crew_size) * 2.0
    if rationing:
        load *= 0.55
    return base * load


def compute_autonomy(
    db: Session,
    *,
    policy: str = "on_demand",
) -> dict:
    crisis = db.query(CrisisState).filter(CrisisState.id == 1).first()
    rationing = crisis.rationing_active if crisis else False
    if policy == "rationing_quarantine":
        rationing = True

    crew = db.query(CrewMember).all()
    crew_size = len(crew) or settings.crew_size
    sick_count = sum(1 for c in crew if c.health_status in (HealthStatus.sick, HealthStatus.quarantine))

    drugs = db.query(Drug).filter(Drug.is_critical == True).all()  # noqa: E712
    if not drugs:
        drugs = db.query(Drug).all()

    rows = []
    min_days = 9999.0
    for drug in drugs:
        burn = _effective_burn(drug, sick_count, crew_size, rationing)
        if burn <= 0:
            days = float(drug.stock_units) * 365
        else:
            days = drug.stock_units / burn
        rows.append(
            {
                "drug_code": drug.code,
                "drug_name": drug.name,
                "stock_units": drug.stock_units,
                "days_remaining": round(days, 1),
            }
        )
        min_days = min(min_days, days)

    if min_days == 9999.0:
        min_days = 0.0

    return {
        "policy": policy,
        "global_days": round(min_days, 1),
        "drugs": rows,
        "sick_count": sick_count,
        "crew_size": crew_size,
    }


def compare_policies(db: Session) -> dict:
    crisis = db.query(CrisisState).filter(CrisisState.id == 1).first()
    return {
        "on_demand": compute_autonomy(db, policy="on_demand"),
        "rationing_quarantine": compute_autonomy(db, policy="rationing_quarantine"),
        "crisis_active": bool(crisis and crisis.active),
        "rationing_active": bool(crisis and crisis.rationing_active),
    }
