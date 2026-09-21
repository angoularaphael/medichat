# Demo soutenance (60 s)

Contexte : minute 2-3 du passage vendredi (prototype live).

## Preparation

- `docker compose up --build`
- Reset : `./scripts/reset-demo.ps1`
- Profil **Elisa** selectionne

## Script

| Temps | Action | Attendu visible |
|-------|--------|-----------------|
| 0-15 s | Chat : « mal de tete » | Ibuprofene ecarte (allergie), paracetamol propose ; badge template ou ollama |
| 15-25 s | Confirmer proposition | Stock paracetamol -1, ligne journal |
| 25-35 s | Bouton **Crise 15 %** | Triage rempli, autonomie globale baisse (ex. ~30 j vers ~9 j selon seed) |
| 35-45 s | **Rationnement / quarantaine** | Autonomie rationnement > autonomie a la demande |
| 45-60 s | **Stock paracetamol a 0** puis nouveau message mal de tete | Protocole non medicamenteux ou substitution ; journal |

## Phrase jury

« EIR est une aide a la decision : les regles medicamenteuses sont deterministes et tracees ; l IA reformule sans prescrire seule. »

## Secours

Si Ollama indisponible : le badge `template` confirme le mode secours prevu au cahier des charges.
