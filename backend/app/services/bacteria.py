from sqlalchemy.orm import Session

from app.models.entities import BiologicalCulture
from app.services import journal

# Temperatures affichees = conservation du stock de demonstration.
# Aucune consigne de fermentation, de milieu ou de purification.
DEFAULT_CULTURES = [
    {
        "code": "penicillium_chrysogenum",
        "nom_souche": "Moisissure a penicilline",
        "categorie": "Antibiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 12,
        "statut_viabilite": "Actif",
        "indication": "infection",
        "treatable": True,
        "notes": "En usine, cette moisissure sert a fabriquer la penicilline. A bord, on ne l'ouvre pas et on ne la boit pas. Elle explique d'ou vient l'antibiotique quand les flacons sont vides.",
        "description": "Quand il n'y a plus d'antibiotique et plus de plante, EIR montre cette cuve. On ne la prepare pas ici.",
    },
    {
        "code": "streptomyces_griseus",
        "nom_souche": "Bacterie de la streptomycine",
        "categorie": "Reference",
        "temperature_celsius": 4.0,
        "quantite_boites": 8,
        "statut_viabilite": "Actif",
        "indication": "reference",
        "treatable": False,
        "notes": "En usine, cette bacterie sert a fabriquer la streptomycine. A bord, c'est seulement une reference. On ne la donne a personne.",
        "description": "On garde le nom pour expliquer l'origine du medicament. On ne l'utilise pas comme traitement.",
    },
    {
        "code": "saccharopolyspora_erythraea",
        "nom_souche": "Bacterie de l'erythromycine",
        "categorie": "Reference",
        "temperature_celsius": 4.0,
        "quantite_boites": 4,
        "statut_viabilite": "Actif",
        "indication": "reference",
        "treatable": False,
        "notes": "En usine, cette bacterie sert a fabriquer l'erythromycine, de la meme famille que l'azithromycine de l'armoire. A bord, on ne l'ouvre pas.",
        "description": "L'azithromycine du stock vient de cette famille. On attend le flacon.",
    },
    {
        "code": "ecoli_k12",
        "nom_souche": "Bacterie de l'insuline",
        "categorie": "Synthese",
        "temperature_celsius": 4.0,
        "quantite_boites": 20,
        "statut_viabilite": "Actif",
        "indication": "protein",
        "treatable": False,
        "notes": "En usine, une bacterie de laboratoire sert a fabriquer l'insuline. A bord, on ne la donne a personne.",
        "description": "C'est une reserve de reference. Ce n'est pas un traitement a prendre.",
    },
    {
        "code": "lactobacillus_acidophilus",
        "nom_souche": "Ferment pour le ventre",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 18,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Un ferment alimentaire pour la flore, apres une diarrhee ou un antibiotique. Ce n'est pas un medicament.",
        "description": "Ca aide le ventre a se refaire. Bois souvent a cote.",
    },
    {
        "code": "bacillus_subtilis",
        "nom_souche": "Second ferment",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 10,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Un autre ferment alimentaire, si le premier vient a manquer. Ce n'est pas un antibiotique.",
        "description": "Reserve pour la flore du ventre. On ne l'utilise pas comme un medicament.",
    },
    {
        "code": "bifidobacterium_longum",
        "nom_souche": "Troisieme ferment",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 8,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Encore un ferment alimentaire pour le ventre. Ce n'est pas un medicament.",
        "description": "Meme role que les autres ferments: aider apres une diarrhee.",
    },
    {
        "code": "saccharomyces_cerevisiae",
        "nom_souche": "Levure de bord",
        "categorie": "Levure",
        "temperature_celsius": 20.0,
        "quantite_boites": 16,
        "statut_viabilite": "Actif",
        "indication": "support",
        "treatable": False,
        "notes": "Une levure alimentaire. En usine, certaines levures servent a fabriquer des molecules. A bord, on ne la prepare pas.",
        "description": "On la garde comme reserve. Ce n'est pas un traitement a prendre.",
    },
    {
        "code": "staphylococcus_aureus",
        "nom_souche": "Bacterie de test",
        "categorie": "Test",
        "temperature_celsius": 4.0,
        "quantite_boites": 6,
        "statut_viabilite": "Actif",
        "indication": "assay",
        "treatable": False,
        "notes": "Boite de test, au froid. On ne l'ouvre pas. Ce n'est pas un medicament.",
        "description": "Cette bacterie ne soigne personne. On la laisse fermee.",
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
    if row.code == "staphylococcus_aureus" or row.statut_viabilite == "Contamine":
        return row
    if row.categorie == "Reference":
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
    if row.code == "staphylococcus_aureus":
        return row, "Souche de test, pas un traitement. Incubation et prelevement interdits."
    if not row.treatable:
        return row, "Cette souche n'est pas un traitement. Reserve de reference uniquement."
    if row.statut_viabilite != "Actif" or row.quantite_boites < 1:
        return row, "Souche non viable ou stock de boites insuffisant."
    row.quantite_boites = max(0, row.quantite_boites - 3)
    if row.quantite_boites == 0:
        row.statut_viabilite = "En sommeil"
    db.commit()
    journal.log_decision(
        db,
        action="bacteria_harvest",
        summary=f"Prelevement {row.nom_souche} pour relais de bord",
        payload={"culture_code": row.code, "quantite_boites": row.quantite_boites},
    )
    return row, None
