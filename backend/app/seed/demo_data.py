from sqlalchemy.orm import Session

from app.models.entities import CrewMember, CrisisState, Drug, DrugInteraction, DrugSubstitution, StockMovement
from app.services import crisis


def run_seed(db: Session) -> None:
    if db.query(CrewMember).count() > 0:
        return

    crew = []
    names = [
        ("elisa", "Elisa Martin", 34),
        ("marc", "Marc Dupont", 41),
        ("sofia", "Sofia Nguyen", 29),
        ("jonas", "Jonas Keller", 38),
        ("amira", "Amira Benali", 32),
    ]
    for i in range(20):
        if i < len(names):
            code, name, age = names[i]
            allergies = ["ibuprofen", "AINS"] if code == "elisa" else []
            treatments = [{"drug_code": "warfarin", "dose_mg": 5}] if code == "marc" else []
        else:
            code = f"crew{i+1:02d}"
            name = f"Astronaute {i+1}"
            age = 28 + (i % 12)
            allergies = []
            treatments = []
        crew.append(
            CrewMember(
                code=code,
                full_name=name,
                age=age,
                allergies=allergies,
                conditions=[],
                current_treatments=treatments,
            )
        )
    db.add_all(crew)

    drugs_data = [
        ("paracetamol", "Paracetamol", "paracetamol", "analgesic", "pain_mild", 1000, 600, 1.2, True),
        ("ibuprofen", "Ibuprofene", "ibuprofen", "AINS", "pain_mild", 400, 200, 0.4, True),
        ("aspirin", "Aspirine", "aspirin", "AINS", "pain_mild", 500, 150, 0.3, False),
        ("amoxicillin", "Amoxicilline", "amoxicillin", "antibiotic", "infection", 1500, 80, 0.6, True),
        ("azithromycin", "Azithromycine", "azithromycin", "antibiotic", "infection", 500, 60, 0.5, True),
        ("warfarin", "Warfarine", "warfarin", "anticoagulant", "anticoagulation", 10, 90, 0.2, True),
        ("ondansetron", "Ondansetron", "ondansetron", "antiemetic", "nausea", 8, 40, 0.15, False),
        ("salbutamol", "Salbutamol", "salbutamol", "bronchodilator", "asthma", 800, 30, 0.1, False),
    ]
    drugs: dict[str, Drug] = {}
    for code, name, substance, tclass, indication, dose_max, stock, burn, critical in drugs_data:
        d = Drug(
            code=code,
            name=name,
            substance=substance,
            therapeutic_class=tclass,
            indication=indication,
            dose_max_mg=dose_max,
            stock_units=stock,
            daily_burn_rate=burn,
            is_critical=critical,
        )
        db.add(d)
        drugs[code] = d
    db.flush()

    subs = [
        ("ibuprofen", "paracetamol", "pain_mild", 1),
        ("aspirin", "paracetamol", "pain_mild", 1),
        ("amoxicillin", "azithromycin", "infection", 1),
    ]
    for fr, to, ind, pri in subs:
        db.add(
            DrugSubstitution(
                from_drug_id=drugs[fr].id,
                to_drug_id=drugs[to].id,
                indication=ind,
                priority=pri,
            )
        )

    db.add(
        DrugInteraction(
            drug_a_id=drugs["ibuprofen"].id,
            drug_b_id=drugs["warfarin"].id,
            severity="major",
            description="Interaction majeure ibuprofene / warfarine (risque hemorragique).",
        )
    )
    db.add(
        DrugInteraction(
            drug_a_id=drugs["aspirin"].id,
            drug_b_id=drugs["warfarin"].id,
            severity="major",
            description="Interaction majeure aspirine / warfarine.",
        )
    )

    crisis.get_or_create_crisis(db)
    db.commit()


def reset_demo(db: Session) -> None:
    crisis.reset_crew_health(db)
    defaults = {
        "paracetamol": 600,
        "ibuprofen": 200,
        "aspirin": 150,
        "amoxicillin": 80,
        "azithromycin": 60,
        "warfarin": 90,
        "ondansetron": 40,
        "salbutamol": 30,
    }
    for code, stock in defaults.items():
        drug = db.query(Drug).filter(Drug.code == code).first()
        if drug:
            drug.stock_units = stock
    db.query(StockMovement).delete()
    db.commit()
