"""Motifs cliniques embarques et declencheurs d'isolement cabine medicale."""

import re
from typing import Iterable

# Isolement immediat: escalate_to_physician + protocole ONBOARD_EMERGENCY
ISOLATION_SYMPTOM_LABELS = frozenset(
    {
        "douleur thoracique",
        "difficulte respiratoire",
        "perte de connaissance",
        "convulsion",
        "hemorragie severe",
        "choc anaphylactique",
        "accident vasculaire",
        "contamination toxique",
    }
)

ISOLATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"douleur thoracique|mal (?:a|à) la poitrine|poitrine.*(serre|oppresse)|"
            r"oppression.*poitrine|chest pain",
            re.I,
        ),
        "douleur thoracique",
    ),
    (
        re.compile(
            r"essouffl|difficult[ée].*respir|mal [àa] respirer|dyspn[ée]e|"
            r"ne respire plus|n['']?arrive plus.*respir|etouff|detresse respiratoire",
            re.I,
        ),
        "difficulte respiratoire",
    ),
    (re.compile(r"convulsion|crise.*[ée]pile|épilep|secousse.*incontrol", re.I), "convulsion"),
    (
        re.compile(
            r"perte de connaissance|évanoui|evanoui|s['']est evanoui|syncope|inconscient|"
            r"ne reprend pas connaissance|réveille pas",
            re.I,
        ),
        "perte de connaissance",
    ),
    (
        re.compile(
            r"paralysie.*visage|visage.*paralys|visage.*(tombe|affais)|trouble.*parole|"
            r"avc|accident vasculaire|demi.*corps.*(paralys|faible)",
            re.I,
        ),
        "accident vasculaire",
    ),
    (
        re.compile(
            r"saigne.*beaucoup|hemorragie|hémorragie|sang.*abondant|"
            r"vomis|vomir.*sang|sang.*vomir|toux.*sang|crache.*sang|selles.*noires",
            re.I,
        ),
        "hemorragie severe",
    ),
    (
        re.compile(
            r"choc anaphylact|anaphylax|gorge qui se serre|gorge.*(serre|gonfle)|"
            r"langue.*gonfle|urticaire.*(respir|etouff)",
            re.I,
        ),
        "choc anaphylactique",
    ),
    (
        re.compile(
            r"fum[ée]e toxique|fuite.*(produit|gaz)|exposition.*chimique|"
            r"contamination.*(majeure|cabine)|odeur.*brul",
            re.I,
        ),
        "contamination toxique",
    ),
]

ROUTINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"mal de t[êe]te|cephalee|headache", re.I), "mal de tete"),
    (
        re.compile(
            r"mal au cr[âa]ne|mal au cran\b|mal a la tete|mal à la tête|mal dans la tete",
            re.I,
        ),
        "mal de tete",
    ),
    (
        re.compile(
            r"insomnie|dors pas|ne dors|pas dormir|mal [àa] dormir|du mal [àa] dormir|"
            r"peine [àa] dormir|n[' ]?arrive pas [àa] dormir|arrive pas [àa] dormir|"
            r"nuit blanche|mal dormir",
            re.I,
        ),
        "insomnie",
    ),
    (
        re.compile(
            r"\bfatigu|épuis[ée]|epuise[ée]?|sans energie|manque d[' ]energie|crev[ée]",
            re.I,
        ),
        "fatigue",
    ),
    (
        re.compile(
            r"pas d[' ]appetit|manque d[' ]appetit|sans appetit|perte d[' ]appetit|"
            r"ne mange plus|anorexie",
            re.I,
        ),
        "perte appetit",
    ),
    (re.compile(r"mal au rein|reins?|colique n[eé]phr|flanc", re.I), "mal au rein"),
    (re.compile(r"fi[eè]vre|fever|temperature.*(haute|elevee)", re.I), "fievre"),
    (re.compile(r"naus[ée]e?|envie de vomir|vomissement", re.I), "nausee"),
    (re.compile(r"diarrh[ée]e|selles liquides|gastro", re.I), "diarrhee"),
    (re.compile(r"constip|pas de selle|ventre bloqu", re.I), "constipation"),
    (re.compile(r"reflux|br[uû]lure d[' ]estomac|aigreur", re.I), "reflux"),
    (re.compile(r"mal de dos|lombalgie|dorsalgie|courbature", re.I), "mal de dos"),
    (re.compile(r"mal de l[' ]espace|cin[eé]tose|mal des transports", re.I), "mal de l'espace"),
    (re.compile(r"congestion|nez bouch|sinus|rhume|ecoulement nasal", re.I), "congestion"),
    (re.compile(r"toux(?!.*sang)|cough", re.I), "toux"),
    (re.compile(r"mal au ventre|douleur abdominale|abdominal|colique", re.I), "mal de ventre"),
    (re.compile(r"vertige|[ée]tourdissement|dizzy", re.I), "vertige"),
    (re.compile(r"mal de gorge|gorge.*mal|sore throat|angine", re.I), "mal de gorge"),
    (re.compile(r"infection|infecte|plaie|antibiot", re.I), "infection"),
    (
        re.compile(
            r"deshydrat|soif intense|ne urine plus|pas uriner depuis|peu uriner",
            re.I,
        ),
        "deshydratation",
    ),
    (re.compile(r"demange|urticaire|prurit|bouton.*qui grat", re.I), "prurit"),
    (re.compile(r"brulure(?!.*chimique)|coup de soleil", re.I), "brulure"),
    (re.compile(r"stress|anxieux|angoiss|panique(?!.*poitrine)", re.I), "anxiete"),
    (re.compile(r"mal (?:a|à) l[' ]oreille|otite|oreille.*(mal|douleur)", re.I), "mal oreille"),
    (re.compile(r"j[' ]ai mal|mal (au|a la|à la|de)|douleur", re.I), "douleur"),
]

ALL_SYMPTOM_PATTERNS: list[tuple[re.Pattern[str], str]] = ISOLATION_PATTERNS + ROUTINE_PATTERNS


def labels_from_text(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in ALL_SYMPTOM_PATTERNS:
        if pattern.search(text) and label not in found:
            found.append(label)
    return found


def isolation_labels_from_text(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in ISOLATION_PATTERNS:
        if pattern.search(text) and label not in found:
            found.append(label)
    return found


def check_isolation(symptoms: Iterable[str]) -> tuple[bool, str | None]:
    for raw in symptoms:
        label = raw.lower().strip()
        if label in ISOLATION_SYMPTOM_LABELS:
            slug = label.replace(" ", "_")
            return True, f"isolation_{slug}"
    return False, None


# Reference pour l'equipage (utilise aussi en tests)
ISOLATION_CASES_FR: list[tuple[str, list[str]]] = [
    ("Douleur thoracique ou oppression poitrine", ["j'ai mal a la poitrine"]),
    ("Detresse respiratoire", ["je n'arrive plus a respirer"]),
    ("Convulsions", ["il fait une convulsion"]),
    ("Perte de connaissance / syncope", ["je me suis evanoui"]),
    ("Signes neurologiques brutaux (AVC)", ["visage paralyse et trouble de parole brutal"]),
    ("Hemorragie severe", ["je vomis du sang"]),
    ("Choc anaphylactique", ["gorge qui se serre et urticaire"]),
    ("Contamination toxique majeure", ["fuite de produit chimique dans la cabine"]),
]

NON_ISOLATION_EXAMPLES_FR: list[tuple[str, list[str]]] = [
    ("Fatigue, sommeil, perte d'appetit", ["je suis fatigue"]),
    ("Fievre, douleur legere, rhume", ["j'ai de la fievre"]),
    ("Nausee, diarrhee, constipation", ["j'ai la diarrhee"]),
    ("Plus d'option medicament mais signes stables", ["(protocole surveillance)"]),
]
