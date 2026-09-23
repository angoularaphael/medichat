from sqlalchemy.orm import Session

from app.models.entities import PlantCulture
from app.services import journal

READY_THRESHOLD = 50.0

DEFAULT_PLANTS = [
    {
        "code": "thymus",
        "name": "Thymus hydroponique",
        "species": "Thymus vulgaris",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 82.0,
        "growth_rate": 5.2,
        "status": "ready",
        "notes": "Huile antiseptique. Relais si les antibiotiques sont epuises.",
        "description": "Thym cultive en nappe hydroponique. Ses huiles (thymol) servent d'antiseptique de bord quand amoxicilline et azithromycine sont a zero. Recolte des sommites fleuries, infusion concentree, usage externe ou oral leger selon protocole EIR.",
    },
    {
        "code": "allium",
        "name": "Allium orbital",
        "species": "Allium sativum",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 71.0,
        "growth_rate": 4.4,
        "status": "ready",
        "notes": "Extrait antimicrobien. Deuxieme relais botanique.",
        "description": "Ail orbital a bulbe compact. L'allicine prend le relais antimicrobien si le thymus est trop faible. Conservation des caieux au sec, broyage juste avant usage pour garder l'activite.",
    },
    {
        "code": "artemisia",
        "name": "Artemisia luna",
        "species": "Artemisia annua",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 54.0,
        "growth_rate": 3.6,
        "status": "growing",
        "notes": "Culture antibacterienne lente, en reserve.",
        "description": "Armoise annuelle sous LED lune. Croissance lente, reserve strategique. Utile si thymus et allium sont deja recoltes. Feuilles sechees, decoction courte, surveillance des constantes apres prise.",
    },
    {
        "code": "mentha",
        "name": "Menthe de cabine",
        "species": "Mentha spicata",
        "indication": "nausea",
        "replaces_drug_class": "antiemetic",
        "biomass_percent": 66.0,
        "growth_rate": 6.1,
        "status": "ready",
        "notes": "Relais si l'ondansetron n'est plus en stock.",
        "description": "Menthe verte de cabine, pousse rapide. Feuilles pour nausees de microgravite quand l'ondansetron est epuise. Infusion tiede, petites prises rapprochées, eviter si reflux severe.",
    },
    {
        "code": "salix",
        "name": "Salix orbital",
        "species": "Salix alba",
        "indication": "pain_mild",
        "replaces_drug_class": "analgesic",
        "biomass_percent": 78.0,
        "growth_rate": 4.8,
        "status": "ready",
        "notes": "Ecorce analgesique. Relais du paracetamol et des AINS.",
        "description": "Saule blanc orbital. L'ecorce contient des salicines, relais naturel si paracetamol, ibuprofene et aspirine sont interdits (allergie) ou epuises. Decoction d'ecorce, ne pas associer a la warfarine.",
    },
    {
        "code": "spirulina",
        "name": "Spiruline Yggdrasil",
        "species": "Arthrospira platensis",
        "indication": "recovery",
        "replaces_drug_class": "support",
        "biomass_percent": 90.0,
        "growth_rate": 8.0,
        "status": "ready",
        "notes": "Soutien nutritionnel. Ne remplace pas un antalgique ni un antibiotique.",
        "description": "Cyanobacterie en photobioreacteur. Proteines, fer, soutien apres effort ou infection. Ce n'est pas un medicament de crise: on l'utilise en recuperation, jamais a la place d'un relais therapeutique.",
    },
]

def _refresh_status(plant: PlantCulture) -> None:
    if plant.biomass_percent < 20:
        plant.status = "depleted"
    elif plant.biomass_percent < READY_THRESHOLD:
        plant.status = "growing"
    else:
        plant.status = "ready"


def seed_plants(db: Session) -> None:
    existing = {row.code: row for row in db.query(PlantCulture).all()}
    for item in DEFAULT_PLANTS:
        row = existing.get(item["code"])
        if row:
            row.notes = item["notes"]
            row.description = item["description"]
            row.indication = item["indication"]
            row.replaces_drug_class = item["replaces_drug_class"]
        else:
            db.add(PlantCulture(**item))


def reset_plants(db: Session) -> None:
    by_code = {item["code"]: item for item in DEFAULT_PLANTS}
    for plant in db.query(PlantCulture).all():
        source = by_code.get(plant.code)
        if not source:
            continue
        plant.biomass_percent = source["biomass_percent"]
        plant.growth_rate = source["growth_rate"]
        plant.status = source["status"]
        plant.notes = source["notes"]
        plant.description = source["description"]
    seed_plants(db)


def list_plants(db: Session) -> list[PlantCulture]:
    return db.query(PlantCulture).order_by(PlantCulture.name).all()


def serialize(plant: PlantCulture) -> dict:
    return {
        "code": plant.code,
        "name": plant.name,
        "species": plant.species,
        "indication": plant.indication,
        "replaces_drug_class": plant.replaces_drug_class,
        "biomass_percent": round(plant.biomass_percent, 1),
        "growth_rate": plant.growth_rate,
        "status": plant.status,
        "notes": plant.notes,
        "description": plant.description,
        "ready": plant.biomass_percent >= READY_THRESHOLD,
    }


def find_ready_plant(db: Session, indication: str) -> PlantCulture | None:
    indications = [indication]
    if indication == "fever":
        indications.append("pain_mild")
    rows = (
        db.query(PlantCulture)
        .filter(PlantCulture.indication.in_(indications))
        .filter(PlantCulture.biomass_percent >= READY_THRESHOLD)
        .order_by(PlantCulture.biomass_percent.desc())
        .all()
    )
    preferred = [row for row in rows if row.indication == indication]
    return (preferred or rows)[0] if rows else None


def irrigate(db: Session, code: str) -> PlantCulture | None:
    plant = db.query(PlantCulture).filter(PlantCulture.code == code).first()
    if not plant:
        return None
    plant.biomass_percent = min(100.0, plant.biomass_percent + plant.growth_rate * 2)
    _refresh_status(plant)
    db.commit()
    journal.log_decision(
        db,
        action="plant_irrigate",
        summary=f"Irrigation {plant.name} ({plant.biomass_percent:.0f} %)",
        payload={"plant_code": plant.code, "biomass_percent": plant.biomass_percent},
    )
    return plant


def boost_light(db: Session, code: str) -> PlantCulture | None:
    plant = db.query(PlantCulture).filter(PlantCulture.code == code).first()
    if not plant:
        return None
    plant.biomass_percent = min(100.0, plant.biomass_percent + plant.growth_rate * 3)
    _refresh_status(plant)
    db.commit()
    journal.log_decision(
        db,
        action="plant_boost",
        summary=f"Boost lumiere {plant.name} ({plant.biomass_percent:.0f} %)",
        payload={"plant_code": plant.code, "biomass_percent": plant.biomass_percent},
    )
    return plant


def harvest(db: Session, code: str) -> tuple[PlantCulture | None, str | None]:
    plant = db.query(PlantCulture).filter(PlantCulture.code == code).first()
    if not plant:
        return None, "Culture inconnue"
    if plant.biomass_percent < READY_THRESHOLD:
        return plant, "Biomasse insuffisante. Irriguez ou boostez la lumiere avant recolte."
    plant.biomass_percent = max(12.0, plant.biomass_percent - 28.0)
    _refresh_status(plant)
    db.commit()
    journal.log_decision(
        db,
        action="plant_harvest",
        summary=f"Recolte {plant.name} pour protocole de bord",
        payload={"plant_code": plant.code, "biomass_percent": plant.biomass_percent},
    )
    return plant, None
