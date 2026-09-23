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
        "name": "Thymus hydroponique",
        "species": "Thymus vulgaris",
        "indication": "infection",
        "replaces_drug_class": "antibiotic",
        "biomass_percent": 82.0,
        "growth_rate": 5.2,
        "status": "ready",
        "notes": "Amoxicilline et azithromycine vides. Le thym ne les fabrique pas: infusion legere des sommites pour une gorge irritee, puis poste medical. La penicilline industrielle vient de Penicillium.",
        "description": "Thymus vulgaris, confort de gorge quand les antibiotiques essentiels sont a zero. Le thymol est un constituant de la plante, pas un medicament du catalogue. EIR ne decrit pas d'extraction d'huile essentielle.",
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
        "notes": "Ail alimentaire. Ecraser une gousse fraiche libere l'allicine, utile en cuisine et en confort si les antibiotiques sont vides. Ce n'est pas de l'amoxicilline.",
        "description": "Allium sativum. Relais de confort seulement. L'industrie ne tire pas l'amoxicilline ni l'azithromycine de l'ail. Pas de preparation concentree.",
    },
    {
        "code": "artemisia",
        "name": "Artemisia luna",
        "species": "Artemisia annua",
        "indication": "reference",
        "replaces_drug_class": "antimalarial",
        "biomass_percent": 54.0,
        "growth_rate": 3.6,
        "status": "growing",
        "notes": "Source historique de l'artemisinine (artesunate, artemether). Reference de serre, pas une tisane antipaludique.",
        "description": "Artemisia annua est la plante d'ou vient l'artemisinine, base des antipaludiques essentiels. L'usine extrait et purifie la molecule. Une tisane maison n'est pas ce medicament. EIR ne donne aucun mode d'extraction. La culture reste une reference, pas une ordonnance.",
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
        "notes": "Feuilles de menthe en infusion tiede si l'ondansetron est vide. Confort des nausees, pas une copie du medicament.",
        "description": "Mentha spicata. Relais de confort quand les antiemetiques essentiels manquent. Eviter si le reflux est severe. Pas de dose en milligrammes.",
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
        "notes": "Saule blanc, source historique des salicines, famille de l'aspirine. Si paracetamol, ibuprofene et aspirine sont vides ou interdits: signaler le saule, ne pas doser une decoction. Interaction possible avec la warfarine. Poste medical.",
        "description": "Salix alba. L'aspirine du stock est une molecule fabriquee en usine, pas une ecorce. EIR nomme le lien historique et refuse une preparation dosee, a cause de l'irritation et des anticoagulants.",
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
        "notes": "Cyanobacterie alimentaire: proteines et fer en recuperation. Ne remplace ni un antalgique ni un antibiotique.",
        "description": "Arthrospira platensis en photobioreacteur. Soutien nutritionnel apres l'episode, jamais a la place d'un medicament essentiel.",
    },
    {
        "code": "oryza",
        "name": "Riz orbital",
        "species": "Oryza sativa",
        "indication": "diarrhea",
        "replaces_drug_class": "adsorbent",
        "biomass_percent": 88.0,
        "growth_rate": 5.5,
        "status": "ready",
        "notes": "Riz nature et eau de cuisson si Smecta, sels et loperamide sont vides. Ca aide a lier et a manger. Ce n'est pas un antidiarrheique fabrique.",
        "description": "Oryza sativa. Relais alimentaire de la diarrhee, avec boisson par petites gorgees. Le vrai medicament de rehydration reste les sels oraux du stock.",
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
        "notes": "Lamelle de gingembre ou infusion tiede contre les nausees si ondansetron et meclizine sont vides. Eviter en reflux severe.",
        "description": "Zingiber officinale, etudie pour le mal de mouvement. Confort de bord, pas une synthese d'ondansetron.",
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
        "notes": "Apres eau tiede, gel clair de la feuille sur une petite brulure a peau non ouverte. Pas sur brulure grave, chimique ou infectee.",
        "description": "Aloe vera. Geste de premiers secours deja connu, pas une pommade pharmaceutique. Grande surface: alerte medicale, pas la serre.",
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
        "notes": "Fleurs en compresse tiede sur peau intacte qui gratte, s'il n'y a pas de creme. Pas sur plaie profonde ni infection.",
        "description": "Calendula officinalis. Confort cutane. Ce n'est pas un antiseptique essentiel et EIR ne decrit pas d'extrait alcoolique.",
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
        "notes": "Apres lavage, une feuille rincee peut couvrir une petite ecorchure. Ce n'est pas de l'amoxicilline. Fievre ou rougeur qui s'etend: poste medical.",
        "description": "Plantago major. Couverture de petite plaie propre. Les antibiotiques essentiels restent les flacons, puis la source nommee Penicillium, sans fermentation a bord.",
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
        "notes": "Infusion legere le soir pour accompagner le sommeil ou le stress. Pas un somnifere, pas une dose en milligrammes.",
        "description": "Matricaria chamomilla. Rituel de confort. Aucun hypnotique essentiel n'est fabrique a partir de cette fleur dans EIR.",
    },
    {
        "code": "cinchona",
        "name": "Quinquina de reference",
        "species": "Cinchona officinalis",
        "indication": "reference",
        "replaces_drug_class": "antimalarial",
        "biomass_percent": 28.0,
        "growth_rate": 1.2,
        "status": "growing",
        "notes": "Source historique de la quinine. Ecorce non utilisable en preparation maison: risque de toxicite.",
        "description": "Cinchona officinalis est la source historique de la quinine, antipaludique essentiel fabrique et dose en pharmacie. L'ecorce brute peut intoxiquer (cinchonisme). EIR ne donne ni dose d'ecorce ni extraction. On attend le flacon ou le poste medical.",
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
