# EIR Medichat

Pharmacie embarquee **EIR** (Workshop EPSI Horizon 2080, pilier HealthTech). Depot code : [github.com/angoularaphael/medichat](https://github.com/angoularaphael/medichat).

Prototype d **aide a la decision** — pas un dispositif medical certifie. Le moteur de regles deterministe decide ; Ollama reformule uniquement.

## Prerequis

- Docker Desktop (Windows)
- Optionnel : Ollama sur l hote (`llama3.2:3b` ou modele leger)

## Demarrage

```powershell
cd EIR
copy .env.example .env
docker compose up --build
```

- UI : http://localhost:5173
- API : http://localhost:8000/docs
- MQTT : localhost:1883

Sans Ollama, le chat utilise le **mode template** (badge `template`).

## Demo soutenance (60 s)

1. Profil **Elisa**, message « mal de tete » -> ibuprofene ecarte, paracetamol propose.
2. **Crise 15 %** -> triage + baisse autonomie.
3. **Rationnement / quarantaine** -> autonomie remonte.
4. **Stock paracetamol a 0** -> protocole alternatif / journal.

Voir [docs/demo-soutenance.md](docs/demo-soutenance.md).

## Tests

```powershell
cd backend
pip install -r requirements.txt
pytest
```

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
