from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import (
    CrewMember,
    CrisisState,
    Drug,
    DrugInteraction,
    DrugSubstitution,
    StockMovement,
    User,
)
from app.services import auth, crisis, plants, bacteria


DEMO_USERS = [
    ("elisa", "Elisa", "crew"),
    ("raphael", "Raphael", "admin"),
    ("elsa", "Elsa", "crew"),
    ("jovani", "Jovani", "crew"),
    ("carine", "Carine", "crew"),
]


def _seed_users(db: Session) -> None:
    existing = {user.username for user in db.query(User).all()}
    password_hash = auth.hash_password(settings.demo_user_password)
    for username, full_name, role in DEMO_USERS:
        if username not in existing:
            db.add(
                User(
                    username=username,
                    full_name=full_name,
                    role=role,
                    crew_member_code=username,
                    password_hash=password_hash,
                )
            )


def _sync_demo_invariants(db: Session) -> None:
    raphael = db.query(CrewMember).filter(CrewMember.code == "raphael").first()
    if raphael:
        raphael.age = 19
    _seed_users(db)
    seed_formulary(db)
    plants.seed_plants(db)
    bacteria.seed_cultures(db)


FORMULARY = [
    ("paracetamol", "Paracetamol", "paracetamol", "analgesic", "pain_mild", 1000, 600, 1.2, True),
    ("ibuprofen", "Ibuprofene", "ibuprofen", "AINS", "pain_mild", 400, 200, 0.4, True),
    ("aspirin", "Aspirine", "aspirin", "AINS", "pain_mild", 500, 150, 0.3, False),
    ("amoxicillin", "Amoxicilline", "amoxicillin", "antibiotic", "infection", 1500, 80, 0.6, True),
    ("azithromycin", "Azithromycine", "azithromycin", "antibiotic", "infection", 500, 60, 0.5, True),
    ("warfarin", "Warfarine", "warfarin", "anticoagulant", "anticoagulation", 10, 90, 0.2, True),
    ("ondansetron", "Ondansetron", "ondansetron", "antiemetic", "nausea", 8, 40, 0.15, True),
    ("meclizine", "Meclizine", "meclizine", "antihistamine", "nausea", 50, 40, 0.2, True),
    ("smecta", "Smecta", "diosmectite", "adsorbent", "diarrhea", 3000, 48, 0.3, True),
    ("loperamide", "Loperamide", "loperamide", "antidiarrheal", "diarrhea", 16, 36, 0.2, True),
    ("ors", "Sels de rehydration", "ors", "rehydration", "diarrhea", 1, 90, 0.5, True),
    ("macrogol", "Macrogol", "macrogol", "laxative", "constipation", 10000, 40, 0.25, True),
    ("omeprazole", "Omeprazole", "omeprazole", "ppi", "reflux", 40, 50, 0.2, False),
    ("salbutamol", "Salbutamol", "salbutamol", "bronchodilator", "asthma", 800, 30, 0.1, False),
]

SUBSTITUTIONS = [
    ("ibuprofen", "paracetamol", "pain_mild", 1),
    ("aspirin", "paracetamol", "pain_mild", 1),
    ("amoxicillin", "azithromycin", "infection", 1),
    ("ondansetron", "meclizine", "nausea", 1),
    ("meclizine", "ondansetron", "nausea", 1),
    ("smecta", "ors", "diarrhea", 1),
    ("smecta", "loperamide", "diarrhea", 2),
    ("loperamide", "smecta", "diarrhea", 1),
    ("ors", "smecta", "diarrhea", 1),
]


def seed_formulary(db: Session) -> dict[str, Drug]:
    drugs = {row.code: row for row in db.query(Drug).all()}
    for code, name, substance, tclass, indication, dose_max, stock, burn, critical in FORMULARY:
        if code in drugs:
            continue
        item = Drug(
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
        db.add(item)
        drugs[code] = item
    db.flush()
    for fr, to, ind, pri in SUBSTITUTIONS:
        if fr not in drugs or to not in drugs:
            continue
        exists = (
            db.query(DrugSubstitution)
            .filter(
                DrugSubstitution.from_drug_id == drugs[fr].id,
                DrugSubstitution.to_drug_id == drugs[to].id,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            DrugSubstitution(
                from_drug_id=drugs[fr].id,
                to_drug_id=drugs[to].id,
                indication=ind,
                priority=pri,
            )
        )
    if "ibuprofen" in drugs and "warfarin" in drugs:
        exists = (
            db.query(DrugInteraction)
            .filter(
                DrugInteraction.drug_a_id == drugs["ibuprofen"].id,
                DrugInteraction.drug_b_id == drugs["warfarin"].id,
            )
            .first()
        )
        if not exists:
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
    return drugs


def run_seed(db: Session) -> None:
    if db.query(CrewMember).count() > 0:
        _sync_demo_invariants(db)
        db.commit()
        return

    crew = []
    names = [
        ("elisa", "Elisa", 34),
        ("raphael", "Raphael", 19),
        ("elsa", "Elsa", 29),
        ("jovani", "Jovani", 38),
        ("carine", "Carine", 32),
    ]
    for code, name, age in names:
        allergies = ["ibuprofen", "AINS"] if code == "elisa" else []
        treatments = [{"drug_code": "warfarin", "dose_mg": 5}] if code == "raphael" else []
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
    seed_formulary(db)
    crisis.get_or_create_crisis(db)
    _seed_users(db)
    plants.seed_plants(db)
    bacteria.seed_cultures(db)
    db.commit()


DEFAULT_STOCKS = {row[0]: row[6] for row in FORMULARY}


def restock_drugs(db: Session) -> None:
    for code, stock in DEFAULT_STOCKS.items():
        drug = db.query(Drug).filter(Drug.code == code).first()
        if drug:
            drug.stock_units = stock
    db.query(StockMovement).delete()
    db.commit()


def reset_demo(db: Session) -> None:
    crisis.reset_crew_health(db)
    restock_drugs(db)
    plants.reset_plants(db)
    bacteria.reset_cultures(db)
    db.commit()
