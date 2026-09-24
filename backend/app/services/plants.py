from sqlalchemy.orm import Session

from app.models.entities import PlantCulture
from app.services import journal

READY_THRESHOLD = 50.0

# Catalogue de serre. Les textes nomment l'origine connue d'un medicament
# essentiel et le relais de confort. Ils ne decrivent pas une extraction,
# une decoction dosee, ni une purification.
DEFAULT_PLANTS = [
    {
        "code": "thymus",
        "name": "Thym de la serre",
        "species": "Thymus vulgaris",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 82.0,
        "growth_rate": 5.2,
        "status": "ready",
        "notes": "Quand les antibiotiques sont vides, une tisane legere de thym adoucit la gorge. Ca ne remplace pas le flacon.",
        "description": "Le thym calme une gorge irritee. Ce n'est pas un antibiotique.",
    },
    {
        "code": "allium",
        "name": "Ail de la serre",
        "species": "Allium sativum",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 71.0,
        "growth_rate": 4.4,
        "status": "ready",
        "notes": "Une gousse d'ail avec le repas, quand les antibiotiques sont vides. Ca aide un peu. Ce n'est pas un medicament.",
        "description": "L'ail se mange. Il ne remplace pas l'amoxicilline.",
    },
    {
        "code": "artemisia",
        "name": "Armoise",
        "species": "Artemisia annua",
        "indication": "reference",
        "replaces_drug_class": "antimalarial",
        "biomass_percent": 54.0,
        "growth_rate": 3.6,
        "status": "growing",
        "notes": "C'est la plante d'ou viennent certains medicaments contre le paludisme. On la garde en reference. On ne la prepare pas a bord.",
        "description": "L'armoise rappelle l'origine d'un medicament. Elle ne se boit pas comme un traitement.",
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
        "notes": "Une infusion tiede de menthe, quand les comprimes contre les nausees sont vides. Bois lentement.",
        "description": "La menthe calme l'estomac. Ce n'est pas le comprime de l'armoire.",
    },
    {
        "code": "salix",
        "name": "Saule blanc",
        "species": "Salix alba",
        "indication": "pain_mild",
        "replaces_drug_class": "analgesic",
        "biomass_percent": 78.0,
        "growth_rate": 4.8,
        "status": "ready",
        "notes": "C'est la plante d'ou vient l'aspirine. Une tisane legere quand les comprimes sont vides. Si tu prends un medicament qui fluidifie le sang, n'en prends pas.",
        "description": "Le saule calme un peu la douleur ou la fievre. Ce n'est pas un comprime. Avec un anticoagulant, on n'y touche pas.",
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
        "notes": "Un aliment de la serre pour reprendre des forces. Ca ne soigne pas la maladie.",
        "description": "La spiruline se mange. Elle ne remplace ni un antidouleur ni un antibiotique.",
    },
    {
        "code": "oryza",
        "name": "Riz de la serre",
        "species": "Oryza sativa",
        "indication": "diarrhea",
        "replaces_drug_class": "adsorbent",
        "biomass_percent": 88.0,
        "growth_rate": 5.5,
        "status": "ready",
        "notes": "Riz nature et eau de cuisson, par petites gorgees, quand les sachets contre la diarrhee sont vides.",
        "description": "Le riz aide a tenir. Le vrai traitement, ce sont les sels de l'armoire quand il en reste.",
    },
    {
        "code": "zingiber",
        "name": "Gingembre de cabine",
        "species": "Zingiber officinale",
        "indication": "nausea",
        "replaces_drug_class": "antiemetic",
        "biomass_percent": 74.0,
        "growth_rate": 4.2,
        "status": "ready",
        "notes": "Une lamelle ou une infusion tiede, quand les comprimes contre les nausees sont vides. Bois lentement.",
        "description": "Le gingembre calme le mal de transport. Ce n'est pas le comprime de l'armoire.",
    },
    {
        "code": "aloe",
        "name": "Aloes de serre",
        "species": "Aloe vera",
        "indication": "brulure",
        "replaces_drug_class": "topical",
        "biomass_percent": 76.0,
        "growth_rate": 3.2,
        "status": "ready",
        "notes": "Apres de l'eau tiede, le gel clair de la feuille sur une petite brulure, seulement si la peau n'est pas ouverte.",
        "description": "L'aloes soulage une petite brulure. Si elle est grande ou profonde, dis-le tout de suite.",
    },
    {
        "code": "calendula",
        "name": "Souci de cabine",
        "species": "Calendula officinalis",
        "indication": "skin",
        "replaces_drug_class": "topical",
        "biomass_percent": 68.0,
        "growth_rate": 4.5,
        "status": "ready",
        "notes": "Une compresse tiede sur une peau qui gratte, si elle n'est pas ouverte.",
        "description": "Le souci calme une peau qui gratte. Pas sur une plaie profonde.",
    },
    {
        "code": "plantago",
        "name": "Plantain de coursive",
        "species": "Plantago major",
        "indication": "skin",
        "replaces_drug_class": "topical",
        "biomass_percent": 62.0,
        "growth_rate": 4.0,
        "status": "ready",
        "notes": "Apres un lavage a l'eau, une feuille rincee sur une petite coupure.",
        "description": "Le plantain couvre une petite ecorchure. Si ca rougit ou si tu as de la fievre, redis-le.",
    },
    {
        "code": "matricaria",
        "name": "Camomille de cabine",
        "species": "Matricaria chamomilla",
        "indication": "sleep",
        "replaces_drug_class": "comfort",
        "biomass_percent": 70.0,
        "growth_rate": 5.0,
        "status": "ready",
        "notes": "Une infusion legere le soir pour t'aider a te poser. Ce n'est pas un comprime pour dormir.",
        "description": "La camomille accompagne le sommeil ou le stress. Lumiere basse, pas d'ecran.",
    },
    {
        "code": "cinchona",
        "name": "Quinquina",
        "species": "Cinchona officinalis",
        "indication": "reference",
        "replaces_drug_class": "antimalarial",
        "biomass_percent": 28.0,
        "growth_rate": 1.2,
        "status": "growing",
        "notes": "C'est la plante d'ou vient la quinine, un medicament contre le paludisme. On ne prepare pas l'ecorce a bord: elle peut rendre malade.",
        "description": "Le quinquina est une reference. On attend le flacon. On ne dose pas l'ecorce.",
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
    allowed = {item["code"] for item in DEFAULT_PLANTS}
    for stale in db.query(PlantCulture).filter(PlantCulture.code.notin_(allowed)).all():
        db.delete(stale)
    existing = {row.code: row for row in db.query(PlantCulture).all()}
    for item in DEFAULT_PLANTS:
        row = existing.get(item["code"])
        if row:
            row.name = item["name"]
            row.species = item["species"]
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
        "ready": plant.biomass_percent >= READY_THRESHOLD and plant.indication != "reference",
    }


def find_ready_plant(db: Session, indication: str) -> PlantCulture | None:
    indications = [indication]
    if indication == "fever":
        indications.append("pain_mild")
    if indication == "pain_renal":
        indications.append("pain_mild")
    if indication in {"nausea", "motion"}:
        indications.extend(["nausea", "motion"])
    if indication == "diarrhea":
        indications.append("diarrhea")
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
    if plant.indication == "reference":
        return plant, "Culture de reference. EIR ne la transforme pas en medicament."
    if plant.biomass_percent < READY_THRESHOLD:
        return plant, "Biomasse insuffisante. Irriguez ou boostez la lumiere avant recolte."
    plant.biomass_percent = max(12.0, plant.biomass_percent - 28.0)
    _refresh_status(plant)
    db.commit()
    journal.log_decision(
        db,
        action="plant_harvest",
        summary=f"Recolte {plant.name} pour relais de confort",
        payload={"plant_code": plant.code, "biomass_percent": plant.biomass_percent},
    )
    return plant, None
