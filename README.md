# EIR Medichat

Pharmacie embarquee **EIR** (Workshop EPSI Horizon 2080, pilier HealthTech). Depot code : [github.com/angoularaphael/medichat](https://github.com/angoularaphael/medichat).

EIR est le **pilier 1 HumanTech / HealthTech** du vaisseau Yggdrasil. MIMIR, le
projet DeepTech, reste le systeme nerveux numerique : EIR lui envoie les crises
et les stocks critiques, et recoit ses alertes de securite infirmerie par MQTT.
Les deux projets fonctionnent ensemble, mais EIR continue seul si MIMIR ou la
Terre sont coupes.

Prototype d **aide a la decision** — pas un dispositif medical certifie. Le
moteur de regles deterministe decide a partir du profil, des interactions et de
la base locale. Ollama peut enrichir l extraction des symptomes et reformuler la
decision, mais il ne prescrit jamais seul.

## Fonctionnalites actuelles

- Chat clinique multi-symptomes : segmentation du message, negations, sujet
  concerne et extraction locale completee par Ollama si disponible.
- Lecture a voix haute des reponses, et message de bienvenue parle au debut
  de chaque nouvelle discussion. Le bouton Voix coupe ou relance la lecture.
- Reponse distincte pour chaque symptome, avec options ecartees et raisons.
- Profils equipage, allergies, traitements, authentification JWT et roles.
- Identification faciale locale optionnelle et conversations persistantes.
- Stocks, confirmations de prise, interactions, substitutions et journal audit.
- Relais par plantes ou cultures biologiques quand tous les flacons utiles sont
  epuises. EIR nomme l'origine du medicament essentiel et le confort possible.
  Il ne decrit pas de fabrication. Voir `docs/pharmacie-vivante.md`.
- Urgences critiques et guide explicite des cas d isolement cabine medicale.
- Crise 15 %, triage, rationnement et comparaison d autonomie medicale.
- MQTT vers le bus Yggdrasil et reception des alertes securite MIMIR.

## Prerequis

- Docker Desktop (Windows)
- Optionnel : Ollama sur l hote (`llama3.2:3b` ou modele leger)

Pour activer la reformulation IA locale :

```powershell
ollama pull llama3.2:3b
ollama serve
```

## Demarrage

```powershell
cd EIR
copy .env.example .env
docker compose up --build
```

- UI : http://localhost:5173
- API : http://localhost:8000/docs
- MQTT : localhost:1883

Sans Ollama, le chat utilise automatiquement une reponse securisee hors ligne.
L extraction deterministe reste disponible, y compris en cas de panne du modele.

## Connexion

Comptes de demonstration : `raphael`, `elisa`, `elsa`, `jovani`, `carine`.

Mot de passe commun : `qwerty123`.

`raphael` dispose des commandes de crise et de reinitialisation. Les autres comptes
sont limites a leur propre profil medical.

Apres une ancienne version du projet, recreer une fois la base de demonstration :

```powershell
docker compose down -v
docker compose up --build
```

## Demo soutenance (60 a 90 s)

1. Connecte comme **Raphael** (poste medical), message : « Elisa vomit, tousse
   beaucoup et a de la fievre ».
2. Montrer le patient detecte, les trois symptomes et le plan separe issu de la
   base locale.
3. **Rupture totale des stocks** -> nouveau message -> relais serre/cuves ou
   protocole de bord.
4. **Crise 15 %** puis **rationnement** -> triage et autonomie compares.
5. Facultatif si le temps le permet : urgence « douleur poitrine et difficulte
   a respirer » -> isolement cabine medicale.

Voir [docs/demo-soutenance.md](docs/demo-soutenance.md), le
[rapport technique source](docs/rapport-technique-source.md) et le
[support de presentation source](docs/support-presentation.md).

Priorites pour gagner des points :
[docs/plan-amelioration-technique.md](docs/plan-amelioration-technique.md).

## Tests

```powershell
cd backend
pip install -r requirements.txt
pytest
```

Etat verifie le 23 septembre 2026 : **59 tests backend reussis**.

## Reset demo

```powershell
./scripts/reset-demo.ps1
```

## Sauvegarde PostgreSQL (ASRBD)

```powershell
docker compose exec db pg_dump -U eir eir > backup-eir.sql
```

## MQTT MIMIR (test)

```powershell
python tools/mqtt-simulate-mimir.py localhost
```

Contrat topics : [docs/mqtt-yggdrasil.md](docs/mqtt-yggdrasil.md).

## Configuration Cursor (local)

Le dossier `.cursor/` (rules IDE) est **ignore par git** et ne doit **pas** etre pousse sur GitHub. Chaque poste garde ses propres rules en local.
