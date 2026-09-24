# Rapport d'ingénierie technique — source à exporter en PDF

Nom réglementaire à l'export : `Workshop2026-B3-G<n>-Dossier.pdf`

Informations que l'équipe doit compléter avant export :

- Numéro du groupe.
- Noms des membres et rôle réel de chacun.
- Capture du Kanban J1 à J5.
- Sources médicales validées.
- Captures finales de l'interface.

## 1. Résumé exécutif

EIR est une pharmacie médicale intelligente conçue pour un vaisseau
interstellaire privé de ravitaillement et d'assistance terrestre immédiate. Le
système comprend les messages de l'équipage, consulte les profils médicaux et
les ressources embarquées, puis produit une aide à la décision traçable.

La particularité d'EIR est de séparer strictement :

1. la compréhension du langage, assurée par des règles locales et éventuellement
   par un petit modèle Ollama ;
2. la décision, assurée par un moteur déterministe qui consulte la base locale ;
3. l'explication, produite à partir de la décision structurée ;
4. la validation humaine avant consommation du stock.

## 2. Problème traité

Une mission de plusieurs décennies ne peut pas dépendre d'une chaîne
d'approvisionnement terrestre. Trois risques sont combinés :

- perte de contact ou latence extrême avec la Terre ;
- stocks médicaux finis et profils individuels différents ;
- crise sanitaire touchant simultanément plusieurs membres.

Une simple interface de chat serait insuffisante : elle pourrait halluciner une
prescription, ignorer une allergie ou consommer une ressource critique. EIR
ajoute donc une couche de règles explicables et un suivi d'autonomie.

## 3. Fonctionnement du prototype

### 3.1 Compréhension du message

Le message est découpé en clauses. EIR détecte :

- l'équipier concerné, même s'il n'est pas le profil actif ;
- chaque symptôme distinct ;
- certaines négations ;
- les motifs critiques nécessitant un isolement immédiat ;
- le contexte d'une conversation persistante.

Ollama peut compléter l'extraction dans un catalogue fermé. En cas
d'indisponibilité, l'extraction déterministe reste opérationnelle.

### 3.2 Décision médicale démonstrative

Pour chaque symptôme, le moteur consulte PostgreSQL :

- allergies et classes contre-indiquées ;
- traitements en cours et interactions ;
- doses maximales du catalogue ;
- stock disponible ;
- substitutions autorisées ;
- plantes et cultures biologiques prêtes.

Le relais biologique n'est proposé qu'après épuisement de toutes les options
médicamenteuses utiles. Les urgences critiques interrompent le flux normal et
activent le protocole cabine médicale.

### 3.3 Crise et autonomie

Le scénario « 15 % contaminés » remplit un triage et recalcule l'autonomie des
ressources. Le dashboard compare la politique à la demande avec le rationnement
et la quarantaine. Les événements importants sont journalisés.

### 3.4 Interconnexion

EIR publie les crises et stocks faibles sur MQTT et reçoit les alertes de
sécurité de MIMIR. Cette intégration montre que le prototype peut devenir une
brique du système global du vaisseau.

## 4. Architecture

```text
Navigateur React
  |
  | HTTPS/REST dans une V1, HTTP local dans le prototype
  v
API FastAPI
  |-- Compréhension du message
  |-- Moteur de règles
  |-- Triage et autonomie
  |-- Authentification et journal
  |
  |-- PostgreSQL : profils, stocks, conversations, cultures, décisions
  |-- Ollama local : extraction complémentaire et reformulation
  `-- Mosquitto MQTT : bus Yggdrasil / MIMIR
```

Le déploiement de démonstration utilise Docker Compose. Tous les composants
essentiels fonctionnent sur le réseau local.

## 5. Sécurité et résilience

- Authentification JWT et mots de passe Argon2.
- Rôles administrateur et équipage.
- Restriction d'accès au profil individuel.
- Confirmation humaine avant décrément du stock.
- Journal horodaté des décisions et consommations.
- Mode dégradé sans Ollama.
- Base et broker locaux persistants.
- 71 tests backend collectés au 24 septembre 2026 (veille, pharmacie vivante,
  règles et crise).

Limites : les secrets de démonstration doivent être remplacés, les échanges
doivent être chiffrés avant mise en production et les règles cliniques doivent
être validées par une autorité médicale.

## 6. Technologies

- React, TypeScript, Vite, React Query.
- Python, FastAPI, Pydantic, SQLAlchemy.
- PostgreSQL.
- Ollama `llama3.2:3b` sur l'hôte : extraction dans un catalogue fermé, puis reformulation du JSON déjà décidé. Hors ligne, un texte modèle prend le relais.
- Simulateur de veille Python (pas de sonde). Voix : synthèse du navigateur, pas Ollama.
- Mosquitto MQTT.
- Docker Compose.
- Pytest.

## 7. Preuve par la démonstration

Scénario principal :

1. Raphael signale qu'Elisa vomit, tousse et a de la fièvre.
2. EIR détecte Elisa et les trois problèmes.
3. Le rapport affiche une décision séparée par symptôme et les exclusions
   provenant de la base.
4. Une rupture totale des médicaments force le relais local.
5. Une crise 15 % déclenche triage et calcul d'autonomie.
6. Page Veille : 40 fiches, scénario contamination, zones et courbe sans lien
   avec le chat.

Scénario de sécurité :

1. L'utilisateur signale une douleur thoracique avec difficulté respiratoire.
2. EIR ne propose aucun médicament.
3. Le protocole critique et l'isolement cabine sont déclenchés.

## 8. Organisation du sprint

### 8.1 Répartition des responsabilités (à compléter par l'équipe)

Remplir avant export PDF : numéro de groupe, noms, rôle réel (backend, front,
règles, démo, doc, MQTT/MIMIR). L'historique Git sur
`https://github.com/angoularaphael/medichat` permet de corroborer qui a touché
quels modules.

### 8.2 Kanban et revues (à compléter)

- Insérer une capture du Kanban J1 à J5.
- Noter les décisions de revue : gel du périmètre bonus si retard ; priorité
  chat + règles + crise avant polish ; ajout veille et voix après analyse du
  dossier MedBox concurrent.

### 8.3 Difficultés rencontrées et correctifs

| Difficulté | Impact | Correctif retenu |
|------------|--------|------------------|
| Périmètre double (EIR + cahier MIMIR sur `space-net` vide) | Retard documentation réseau | Cahier dev MIMIR et contrat MQTT écrits ; EIR publie crise/stock bas, file `offline_outbox.jsonl` si broker absent |
| Pharmacie vivante vs risque de « recette » de médicament | Crédibilité jury et sécurité | Origine botanique/microbienne + relais de confort uniquement ; souches « référence » non incubables ; prompts Ollama et tests qui refusent fermentation/extraction |
| Pas de capteurs matériels fournis | Impossible de démo hardware type MedBox | Simulateur `surveillance.py` : 40 sujets, score déterministe, zones Q1–Q4, scénarios nominal / fausse alerte / contamination / dégradation lente ; chat et Ollama exclus du score |
| Séparation chat / constantes (exigence MedBox) | Risque de mélanger LLM et priorité vitale | API veille dédiée ; tests qui prouvent que `evaluate` chat ne modifie pas les sujets |
| MQTT refusé si Mosquitto arrêté (Windows) | Logs d'erreur au démarrage API | Docker Compose avec broker ; messages mis en file et rejoués à la reconnexion |
| Ollama lent ou absent | Démo instable | Timeouts courts ; mode `rules-offline` et texte modèle ; dashboard affiche l'état ; démo soutenance prévue sans dépendre d'Ollama |
| Voix navigateur (autoplay, Chrome) | Bienvenue silencieuse au chargement | `primeSpeech` au clic ; bouton Écouter ; délai après `cancel` ; voix fr-FR si installée |
| Dates SQLite naïves vs fuseau sur courbe veille | Erreur ou courbe vide | Filtrage des 10 dernières minutes corrigé côté Python |
| Documentation décalée du code (stack « envisagée ») | Jury mal informé | Cahier V0.6, `docs/capteurs-et-ollama.md`, rapport et README alignés sur FastAPI/React/PostgreSQL |
| Environnement Windows (ports Vite, pytest long) | Friction dev | Un seul `docker compose up` pour la démo ; tests regroupés en CI locale avant push |

Ce que le projet **n'a pas** fait : entraîner un réseau de neurones. Le modèle
`llama3.2:3b` est pré-entraîné ; l'équipe a construit le moteur de règles, les
garde-fous et l'orchestration (catalogue fermé, JSON décisionnel, repli hors
ligne).

### 8.4 Contributions individuelles (à compléter)

Pour chaque membre : modules principaux, commits ou PR, partie de la démo
soutenance. Ne pas attribuer du travail non vérifiable dans Git.

## 9. Limites assumées

- Prototype pédagogique, non certifié comme dispositif médical.
- Compréhension du langage non garantie pour toute formulation.
- Catalogue thérapeutique réduit.
- Constantes de veille simulées (température, SpO2, pouls, respiration). Aucune sonde physique n'est branchée.
- Sources cliniques et protocoles botaniques à consolider.
- Migrations et observabilité encore limitées pour une V1 industrielle.

## 10. Passage vers une V1

Priorités :

1. brancher une sonde réelle sur le simulateur de veille déjà en place ;
2. ajouter un dialogue de clarification avant toute recommandation ambiguë ;
3. versionner la base avec Alembic et automatiser les sauvegardes ;
4. produire des métriques de santé et un test de coupure d'Ollama/PostgreSQL ;
5. externaliser les règles dans un catalogue versionné et sourcé ;
6. faire valider les protocoles par un professionnel de santé.

## 11. Conclusion

EIR ne cherche pas à remplacer un médecin. Il fournit au vaisseau une capacité
locale, explicable et résiliente pour comprendre une situation, protéger les
stocks et guider l'équipage lorsque la Terre n'est plus immédiatement
joignable.
