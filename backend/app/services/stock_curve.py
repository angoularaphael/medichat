from sqlalchemy.orm import Session

from app.models.entities import Drug, StockMovement


def build_stock_curve(db: Session) -> dict:
    drugs = db.query(Drug).all()
    movements = (
        db.query(StockMovement)
        .order_by(StockMovement.created_at.asc(), StockMovement.id.asc())
        .all()
    )
    names = {drug.id: drug.name for drug in drugs}
    total_now = sum(drug.stock_units for drug in drugs)
    start = total_now - sum(row.delta for row in movements)
    points = [{"label": "Depart", "units": start, "reason": "stock initial"}]
    running = start
    for row in movements:
        running += row.delta
        label = row.created_at.strftime("%H:%M") if row.created_at else row.reason
        points.append(
            {
                "label": label,
                "units": running,
                "reason": names.get(row.drug_id, row.reason),
            }
        )
    if len(points) == 1:
        points.append({"label": "Maintenant", "units": total_now, "reason": "aucun mouvement"})
    return {"points": points, "now": total_now}
