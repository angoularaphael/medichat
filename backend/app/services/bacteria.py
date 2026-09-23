from sqlalchemy.orm import Session

from app.models.entities import BiologicalCulture
from app.services import journal

DEFAULT_CULTURES = [
    {
        "code": "penicillium_chrysogenum",
        "nom_souche": "Penicillium chrysogenum",
        "categorie": "Antibiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 12,
        "statut_viabilite": "Actif",
        "indication": "infection",
        "treatable": True,
        "notes": "Synthese de penicilline a bord. Relais lent si amoxicilline et azithromycine sont vides.",
        "description": "Moississure de reference pour produire de la penicilline. Cuve fermee, 4 C. Utile contre une infection courante quand les flacons synthetiques et les plantes antiseptiques sont epuises. Delai de synthese long: ce n'est pas une prise immediate.",
    },
    {
        "code": "streptomyces_griseus",
        "nom_souche": "Streptomyces griseus",
        "categorie": "Antibiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 8,
        "statut_viabilite": "Actif",
        "indication": "infection",
        "treatable": True,
        "notes": "Streptomycine de secours si resistance a la penicilline.",
        "description": "Actinobacterie productrice de streptomycine. Reserve si Penicillium ne suffit plus ou si une souche testee a bord resiste a la penicilline. Meme protocole: confinement, 4 C, synthese puis controle sur souche test.",
    },
    {
        "code": "ecoli_k12",
        "nom_souche": "Escherichia coli K-12",
        "categorie": "Synthese",
        "temperature_celsius": 4.0,
        "quantite_boites": 20,
        "statut_viabilite": "Actif",
        "indication": "protein",
        "treatable": False,
        "notes": "Outil de labo. Synthese de proteines (insuline). Pas un traitement d'infection.",
        "description": "Souche K-12 desarmee, standard de genie genetique. Permet au labo embarque de produire des proteines d'urgence (insuline). Elle n'est jamais administree comme antibiotique ni comme probiotique.",
    },
    {
        "code": "lactobacillus_acidophilus",
        "nom_souche": "Lactobacillus acidophilus",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 18,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Cuve probiotique. Refait la flore apres antibiotiques ou diarrhee.",
        "description": "Cuve Lactobacillus acidophilus, souche alimentaire. C'est la pharmacie vivante digestive: regenerer la flore apres amoxicilline, azithromycine, diarrhee ou stress spatial. Usage oral du ferment. Jamais une souche pathogene.",
    },
    {
        "code": "saccharomyces_cerevisiae",
        "nom_souche": "Saccharomyces cerevisiae",
        "categorie": "Levure",
        "temperature_celsius": 20.0,
        "quantite_boites": 16,
        "statut_viabilite": "Actif",
        "indication": "support",
        "treatable": False,
        "notes": "Levure de labo: tests de toxicite, bio-ingenierie, complement de survie.",
        "description": "Levure de boulanger / labo. Sert aux tests de toxicite, a la bio-ingenierie, et comme apport calorique de survie. Ce n'est pas un antibiotique.",
    },
    {
        "code": "staphylococcus_aureus",
        "nom_souche": "Staphylococcus aureus",
        "categorie": "Test",
        "temperature_celsius": 4.0,
        "quantite_boites": 6,
        "statut_viabilite": "Actif",
        "indication": "assay",
        "treatable": False,
        "notes": "Cobaye de labo. Sert a tester les antibiotiques produits a bord. Jamais un traitement.",
        "description": "Souche conservee uniquement pour eprouver l'activite des antibiotiques synthetises (penicilline, streptomycine) avant toute administration a l'equipage. Confinement strict. Interdit: inoculer, soigner, ou ouvrir hors protocole BSL de bord.",
    },
]


def seed_cultures(db: Session) -> None:
    allowed = {item["code"] for item in DEFAULT_CULTURES}
    for stale in db.query(BiologicalCulture).filter(BiologicalCulture.code.notin_(allowed)).all():
        db.delete(stale)
    existing = {row.code: row for row in db.query(BiologicalCulture).all()}
    for item in DEFAULT_CULTURES:
        row = existing.get(item["code"])
        if row:
            row.nom_souche = item["nom_souche"]
            row.categorie = item["categorie"]
            row.temperature_celsius = item["temperature_celsius"]
            row.notes = item["notes"]
            row.description = item["description"]
            row.indication = item["indication"]
            row.treatable = item["treatable"]
        else:
            db.add(BiologicalCulture(**item))


def reset_cultures(db: Session) -> None:
    by_code = {item["code"]: item for item in DEFAULT_CULTURES}
    for row in db.query(BiologicalCulture).all():
        source = by_code.get(row.code)
        if not source:
            continue
        row.quantite_boites = source["quantite_boites"]
        row.statut_viabilite = source["statut_viabilite"]
        row.notes = source["notes"]
        row.description = source["description"]
    seed_cultures(db)


def list_cultures(db: Session) -> list[BiologicalCulture]:
    return db.query(BiologicalCulture).order_by(BiologicalCulture.categorie, BiologicalCulture.nom_souche).all()


def serialize(row: BiologicalCulture) -> dict:
    return {
        "id_culture": row.id_culture,
        "code": row.code,
        "nom_souche": row.nom_souche,
        "categorie": row.categorie,
        "temperature_celsius": row.temperature_celsius,
        "quantite_boites": row.quantite_boites,
        "statut_viabilite": row.statut_viabilite,
        "indication": row.indication,
        "treatable": row.treatable,
        "notes": row.notes,
        "description": row.description,
        "ready": row.statut_viabilite == "Actif" and row.quantite_boites > 0 and row.treatable,
    }


def find_ready(db: Session, indication: str) -> BiologicalCulture | None:
    wanted = [indication]
    if indication == "diarrhea":
        wanted.append("flora")
    if indication == "infection":
        wanted.append("infection")
    rows = (
        db.query(BiologicalCulture)
        .filter(BiologicalCulture.indication.in_(wanted))
        .filter(BiologicalCulture.treatable.is_(True))
        .filter(BiologicalCulture.statut_viabilite == "Actif")
        .filter(BiologicalCulture.quantite_boites > 0)
        .order_by(BiologicalCulture.quantite_boites.desc())
        .all()
    )
    preferred = [row for row in rows if row.indication == indication]
    if indication == "diarrhea":
        preferred = [row for row in rows if row.indication == "flora"]
    return (preferred or rows)[0] if rows else None


def incubate(db: Session, code: str) -> BiologicalCulture | None:
    row = db.query(BiologicalCulture).filter(BiologicalCulture.code == code).first()
    if not row:
        return None
    if row.statut_viabilite == "Contamine":
        return row
    row.quantite_boites = min(40, row.quantite_boites + 3)
    row.statut_viabilite = "Actif"
    db.commit()
    journal.log_decision(
        db,
        action="bacteria_incubate",
        summary=f"Incubation {row.nom_souche} ({row.quantite_boites} boites)",
        payload={"culture_code": row.code, "quantite_boites": row.quantite_boites},
    )
    return row


def harvest(db: Session, code: str) -> tuple[BiologicalCulture | None, str | None]:
    row = db.query(BiologicalCulture).filter(BiologicalCulture.code == code).first()
    if not row:
        return None, "Culture inconnue"
    if not row.treatable:
        return row, "Cette souche n'est pas un traitement. Reserve de labo uniquement."
    if row.statut_viabilite != "Actif" or row.quantite_boites < 1:
        return row, "Souche non viable ou stock de boites insuffisant."
    row.quantite_boites = max(0, row.quantite_boites - 3)
    if row.quantite_boites == 0:
        row.statut_viabilite = "En sommeil"
    db.commit()
    journal.log_decision(
        db,
        action="bacteria_harvest",
        summary=f"Prelevement {row.nom_souche} pour protocole de bord",
        payload={"culture_code": row.code, "quantite_boites": row.quantite_boites},
    )
    return row, None
