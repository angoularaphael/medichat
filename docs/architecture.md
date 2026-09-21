# Architecture EIR Medichat

## Vue d ensemble

- **Frontend** React (Vite) : chat, dashboard stocks/autonomie/triage, actions demo crise.
- **API** FastAPI : moteur de regles, crise, journal, pont Ollama, client MQTT.
- **PostgreSQL** : equipage, medicaments, graphe substitution, interactions, journal.
- **Mosquitto** : bus Yggdrasil (publish EIR, subscribe alertes MIMIR).
- **Ollama** (optionnel) : reformulation uniquement.

## Flux nominal soin

1. UI `POST /api/chat/message` avec profil + texte libre.
2. Extraction symptomes (regex + heuristiques).
3. `rules_engine.evaluate_care` lit allergies, interactions, stock, doses.
4. `ollama_client.reformulate_with_ollama` ou template secours.
5. Confirmation humaine `POST /api/care/confirm` decremente stock + journal.

## Schema de donnees

Tables principales : `crew_members`, `drugs`, `drug_substitutions`, `drug_interactions`, `stock_movements`, `decision_log`, `crisis_state`, `chat_messages`, `security_alerts`.

Initialisation : `Base.metadata.create_all` au demarrage API + `seed/demo_data.py`.

## MQTT

Voir [mqtt-yggdrasil.md](./mqtt-yggdrasil.md).

## Securite demo

Pas d auth sur le prototype labo. Ne pas exposer sur Internet sans reverse proxy et authentification (travail ASRBD).
