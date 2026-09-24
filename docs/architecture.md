# Architecture EIR Medichat

## Vue d ensemble

- **Frontend** React (Vite) : authentification, identification faciale locale,
  conversations, rapport clinique, cultures, stocks, autonomie et triage.
- **API** FastAPI : comprehension du message, moteur de regles, crise, journal,
  pont Ollama, authentification JWT et client MQTT.
- **PostgreSQL** : utilisateurs, equipage, visages, conversations, medicaments,
  substitutions, interactions, cultures et journal.
- **Mosquitto** : bus Yggdrasil (publish EIR, subscribe alertes MIMIR).
- **Ollama** (optionnel) : extraction JSON controlee et reformulation de la
  decision structuree. Il ne choisit ni molecule ni dose.

## Flux nominal soin

1. UI `POST /api/chat/message` avec conversation, profil actif et texte libre.
2. `message_understanding` segmente les clauses, traite les negations, detecte
   l equipier concerne et extrait chaque symptome.
3. Ollama peut completer cette extraction avec un JSON limite a un catalogue de
   labels ; les regles locales restent le mode de secours.
4. `rules_engine.evaluate_from_understanding` evalue chaque probleme distinct
   en lisant allergies, traitements, interactions, stock et cultures.
5. En cas de motif critique, le moteur interrompt le flux normal et active le
   protocole d urgence/isolement.
6. `ollama_client.reformulate_with_ollama` explique uniquement le JSON du moteur
   ou utilise un template hors ligne.
7. La confirmation humaine decremente le stock et ajoute une entree au journal.

## Schema de donnees

Tables principales : `users`, `crew_members`, `reconnaissance_faciale`,
`conversations`, `chat_messages`, `drugs`, `drug_substitutions`,
`drug_interactions`, `stock_movements`, `plant_cultures`,
`stock_cultures_biologiques`, `decision_log`, `crisis_state` et
`security_alerts`.

Initialisation : `Base.metadata.create_all` au demarrage API + `seed/demo_data.py`.

## MQTT

Voir [mqtt-yggdrasil.md](./mqtt-yggdrasil.md). MIMIR est le depot
[space-net](https://github.com/angoularaphael/space-net). EIR publie crise et
stock bas, et ecoute `yggdrasil/mimir/security/infirmary`.

## Pharmacie vivante

Voir [pharmacie-vivante.md](./pharmacie-vivante.md). Le relais serre/cuves ne
decrit pas de fabrication de medicament.

## Veille

Les constantes sont simulees. Voir [capteurs-et-ollama.md](./capteurs-et-ollama.md).
`services/surveillance.py` score temperature, SpO2, pouls et respiration sans
lire le chat ni Ollama. Quatre zones de deux places, registre de co-presence,
et historique des dix dernieres minutes.

## Ollama

Deux appels HTTP vers le modele local `llama3.2:3b` : extraire des symptomes
dans un catalogue ferme, puis reformuler le JSON du moteur de regles. Detail
dans [capteurs-et-ollama.md](./capteurs-et-ollama.md).

## Securite du prototype

- Authentification JWT, mots de passe haches Argon2 et separation
  administrateur/equipage.
- Un equipier ne peut consulter et modifier que son propre profil.
- Le poste medical administrateur peut prendre en charge un autre equipier
  explicitement nomme dans le message.
- Secrets de demonstration a remplacer avant tout deploiement hors laboratoire.
- Le prototype n est pas expose a Internet et n est pas un dispositif medical.

## Resilience et limites

- PostgreSQL et Mosquitto disposent de volumes/services locaux.
- Ollama est optionnel ; templates et extraction deterministe assurent le mode
  degrade.
- Les decisions sont testees et tracees, mais les regles cliniques restent un
  catalogue de demonstration non valide par une autorite medicale.
- Ameliorations V1 : migrations Alembic versionnees, metriques de sante,
  sauvegarde automatisee, sonde reelle a la place du simulateur, validation clinique.
