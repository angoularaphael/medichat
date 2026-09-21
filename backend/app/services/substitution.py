from sqlalchemy.orm import Session

from app.models.entities import Drug, DrugSubstitution


def find_substitutes(
    db: Session,
    excluded_drug_id: int,
    indication: str,
) -> list[Drug]:
    rows = (
        db.query(DrugSubstitution, Drug)
        .join(Drug, DrugSubstitution.to_drug_id == Drug.id)
        .filter(DrugSubstitution.from_drug_id == excluded_drug_id)
        .filter(DrugSubstitution.indication == indication)
        .order_by(DrugSubstitution.priority.asc())
        .all()
    )
    return [drug for _, drug in rows if drug.stock_units > 0]


def find_substitutes_by_code(
    db: Session,
    from_code: str,
    indication: str,
) -> list[Drug]:
    source = db.query(Drug).filter(Drug.code == from_code).first()
    if not source:
        return []
    return find_substitutes(db, source.id, indication)
