"""Libelles francais pour les motifs cliniques (chat + comprehension)."""

TOPIC_FR: dict[str, str] = {
    "mal de tete": "le mal de tete",
    "mal de dos": "le mal de dos",
    "mal au rein": "le mal au rein",
    "douleur": "la douleur",
    "fievre": "la fievre",
    "nausee": "les nausees / vomissements",
    "diarrhee": "la diarrhee",
    "constipation": "la constipation",
    "infection": "l'infection",
    "insomnie": "le sommeil",
    "fatigue": "la fatigue",
    "perte appetit": "la perte d'appetit",
    "congestion": "la congestion",
    "toux": "la toux",
    "mal de ventre": "le mal de ventre",
    "vertige": "les vertiges",
    "deshydratation": "la deshydratation",
    "prurit": "les demangeaisons",
    "brulure": "la brulure",
    "anxiete": "le stress",
    "mal oreille": "l'oreille",
    "mal de gorge": "le mal de gorge",
    "mal de l'espace": "le mal de l'espace",
    "reflux": "le reflux",
    "douleur thoracique": "la douleur thoracique",
    "difficulte respiratoire": "la detresse respiratoire",
}


def topic_for_label(label: str) -> str:
    return TOPIC_FR.get(label.lower().strip(), label)
