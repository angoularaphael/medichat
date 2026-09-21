# Cas de test EIR (T01-T20)

Automatises T01-T10 : `backend/tests/test_rules.py` (`pytest`).

| ID | Entree | Attendu |
|----|--------|---------|
| T01 | Elisa + mal de tete | AINS ecartes ; paracetamol si stock |
| T02 | Elisa + demande ibuprofene | Refus / pas ibuprofene recommande |
| T03 | Marc (warfarine) + ibuprofene | Alerte interaction |
| T04 | Stock paracetamol 0 | Substitution ou protocole alternatif |
| T05 | Douleur thoracique | Escalade medecin |
| T06 | Patient inconnu | Refus / regle patient_unknown |
| T07 | Dose > dose max | Refus dose |
| T08 | Crise 15 % | Triage non vide |
| T09 | Rationnement | Autonomie rationnement >= demande (post-crise) |
| T10 | Crise + triage | Priorites ordonnees |
| T11 | Sofia + mal de tete | Paracetamol OK sans exclusion allergie |
| T12 | Confirm sans stock | HTTP 400 stock insuffisant |
| T13 | Reset demo | Stocks et sante equipage reinitialises |
| T14 | Journal apres confirm | Entree care_confirm presente |
| T15 | MQTT crise | Message sur yggdrasil/eir/alert/crisis (mosquitto_sub) |
| T16 | MQTT stock low | Message sur yggdrasil/eir/stock/low |
| T17 | Simulateur MIMIR | GET /api/security/alerts non vide |
| T18 | Chat mode template | llm_mode=template si Ollama off |
| T19 | Amoxicilline stock 0 + infection | Substitution azithromycine (si scenario ajoute) |
| T20 | Deux malades triage | Priorite 1 avant priorite 2 |

## Commandes

```powershell
cd backend
pytest tests/test_rules.py -v
curl -X POST http://localhost:8000/api/care/evaluate -H "Content-Type: application/json" -d "{\"crew_member_code\":\"elisa\",\"symptoms\":[\"mal de tete\"]}"
```
