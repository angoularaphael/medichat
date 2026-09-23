# Cas de test EIR

État vérifié le 23 septembre 2026 : **59 tests backend réussis**.

Suites : authentification et rôles, moteur clinique, chat et conversations,
plantes/cultures, catalogue de symptômes, compréhension multi-symptômes et
urgences.

| ID | Entree | Attendu |
|----|--------|---------|
| T01 | Elisa + mal de tete | AINS ecartes ; paracetamol si stock |
| T02 | Elisa + demande ibuprofene | Refus / pas ibuprofene recommande |
| T03 | Raphael (warfarine) + ibuprofene | Alerte interaction |
| T04 | Stock paracetamol 0 | Substitution ou protocole alternatif |
| T05 | Douleur thoracique | Protocole urgence embarque |
| T06 | Patient inconnu | Refus / regle patient_unknown |
| T07 | Dose > dose max | Refus dose |
| T08 | Crise 15 % | Triage non vide |
| T09 | Rationnement | Autonomie rationnement >= demande (post-crise) |
| T10 | Crise + triage | Priorites ordonnees |
| T11 | Elsa + mal de tete | Paracetamol OK sans exclusion allergie |
| T12 | Confirm sans stock | HTTP 400 stock insuffisant |
| T13 | Reset demo | Stocks et sante equipage reinitialises |
| T14 | Journal apres confirm | Entree care_confirm presente |
| T15 | MQTT crise | Message sur yggdrasil/eir/alert/crisis (mosquitto_sub) |
| T16 | MQTT stock low | Message sur yggdrasil/eir/stock/low |
| T17 | Simulateur MIMIR | GET /api/security/alerts non vide |
| T18 | Chat mode template | llm_mode=template si Ollama off |
| T19 | Amoxicilline stock 0 + infection | Substitution azithromycine (si scenario ajoute) |
| T20 | Deux malades triage | Priorite 1 avant priorite 2 |
| T21 | « mal au cran » | Reconnu comme mal de tête |
| T22 | « je dors pas » | Protocole sommeil, aucun paracétamol automatique |
| T23 | Fatigue après mal de dos | Ne réutilise pas abusivement le symptôme précédent |
| T24 | Perte d'appétit | Protocole dédié non médicamenteux |
| T25 | Elisa vomit + tousse + fièvre | Sujet Elisa et plan séparé pour chaque problème |
| T26 | Convulsion | Isolement cabine et urgence critique |
| T27 | Hémorragie sévère | Isolement cabine et urgence critique |
| T28 | Allergie paracétamol seule | Ibuprofène si profil et stock compatibles |
| T29 | Paracétamol + warfarine | AINS écartés avec raison explicite |
| T30 | Stock complet de l'indication à zéro | Relais plante/culture seulement après épuisement |

## Commandes

```powershell
cd backend
pytest -q
curl -X POST http://localhost:8000/api/care/evaluate -H "Content-Type: application/json" -d "{\"crew_member_code\":\"elisa\",\"symptoms\":[\"mal de tete\"]}"
```

## Limites de validation

Ces tests valident la cohérence logicielle du prototype, pas l'efficacité
clinique. Une V1 exige une validation des règles, doses, contre-indications et
protocoles biologiques par un professionnel de santé.
