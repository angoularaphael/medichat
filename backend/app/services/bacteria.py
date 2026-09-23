from sqlalchemy.orm import Session

from app.models.entities import BiologicalCulture
from app.services import journal

# Temperatures affichees = conservation du stock de demonstration.
# Aucune consigne de fermentation, de milieu ou de purification.
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
        "notes": "Source industrielle de la penicilline, famille de l'amoxicilline. On nomme la souche quand les flacons et la serre sont vides. Pas de fermentation a bord.",
        "description": "Penicillium chrysogenum est la moisissure dont les usines tirent la penicilline. Elles cultivent le champignon en cuve fermee puis purifient la molecule. EIR indique cette origine au poste medical. Il ne donne ni milieu, ni precurseur, ni extraction. Le prelevement de demonstration decremente seulement les boites.",
    },
    {
        "code": "streptomyces_griseus",
        "nom_souche": "Streptomyces griseus",
        "categorie": "Reference",
        "temperature_celsius": 4.0,
        "quantite_boites": 8,
        "statut_viabilite": "Actif",
        "indication": "reference",
        "treatable": False,
        "notes": "Source industrielle de la streptomycine. Reference nommee, pas un traitement a prelever.",
        "description": "Streptomyces griseus produit la streptomycine en industrie. Cette molecule n'est pas un antibiotique de premier recours (toxicite auditive et renale). EIR conserve le nom pour expliquer l'origine. Aucun protocole de culture.",
    },
    {
        "code": "saccharopolyspora_erythraea",
        "nom_souche": "Saccharopolyspora erythraea",
        "categorie": "Reference",
        "temperature_celsius": 4.0,
        "quantite_boites": 4,
        "statut_viabilite": "Actif",
        "indication": "reference",
        "treatable": False,
        "notes": "Source industrielle de l'erythromycine, famille de l'azithromycine du stock.",
        "description": "Saccharopolyspora erythraea est l'organisme dont l'industrie obtient l'erythromycine. L'azithromycine d'EIR est un macrolide de la meme famille, livre en flacon. EIR ne decrit pas la fermentation ni l'extraction.",
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
        "notes": "Hote historique de l'insuline industrielle. Souche de labo, jamais un traitement.",
        "description": "Escherichia coli K-12 est une souche de laboratoire desarmee. L'industrie l'a utilisee comme hote pour produire l'insuline. EIR ne fournit ni construction genetique, ni expression, ni purification. La souche n'est pas administree.",
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
        "notes": "Souche alimentaire. Ferment oral pour la flore apres antibiotique ou diarrhee. Pas un antibiotique.",
        "description": "Lactobacillus acidophilus, cuve alimentaire. Elle aide a refaire la flore apres amoxicilline, azithromycine ou diarrhee. Ce n'est pas une souche pathogene et EIR ne donne pas de milieu de culture.",
    },
    {
        "code": "bacillus_subtilis",
        "nom_souche": "Bacillus subtilis",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 10,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Souche alimentaire de secours pour la flore. Ne fabrique pas d'antibiotique a bord.",
        "description": "Bacillus subtilis est utilisee dans l'alimentation et, en usine, comme hote d'enzymes. A bord, c'est un ferment oral de reserve si Lactobacillus vient a manquer. Pas de recette de cuve.",
    },
    {
        "code": "bifidobacterium_longum",
        "nom_souche": "Bifidobacterium longum",
        "categorie": "Probiotique",
        "temperature_celsius": 4.0,
        "quantite_boites": 8,
        "statut_viabilite": "Actif",
        "indication": "flora",
        "treatable": True,
        "notes": "Second ferment alimentaire. Flore digestive, pas un medicament essentiel.",
        "description": "Bifidobacterium longum, souche alimentaire. Meme role que Lactobacillus: confort digestif apres diarrhee ou antibiotique. EIR ne decrit pas sa culture.",
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
        "notes": "Levure alimentaire et de labo. Hote industriel possible, sans mode d'emploi a bord.",
        "description": "Saccharomyces cerevisiae. En usine, des souches modifiees servent parfois a produire des molecules. A bord, c'est une levure de test et un appoint alimentaire. EIR ne decrit aucune modification.",
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
        "notes": "Souche de test conservee au froid. Interdit: incuber, ouvrir, administrer.",
        "description": "Staphylococcus aureus n'est pas un medicament et n'est pas une usine a traitement. Stock de test seulement. EIR refuse l'incubation et le prelevement, et ne donne aucune condition de culture. La temperature affichee est une conservation, pas une consigne.",
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
