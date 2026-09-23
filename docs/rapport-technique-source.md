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
- 59 tests backend réussis au 23 septembre 2026.

Limites : les secrets de démonstration doivent être remplacés, les échanges
doivent être chiffrés avant mise en production et les règles cliniques doivent
être validées par une autorité médicale.

## 6. Technologies

- React, TypeScript, Vite, React Query.
- Python, FastAPI, Pydantic, SQLAlchemy.
- PostgreSQL.
- Ollama avec modèle léger local.
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

Scénario de sécurité :

1. L'utilisateur signale une douleur thoracique avec difficulté respiratoire.
2. EIR ne propose aucun médicament.
3. Le protocole critique et l'isolement cabine sont déclenchés.

## 8. Organisation du sprint

Ajouter ici les éléments réels, sans inventer :

- répartition nominative des responsabilités ;
- captures ou export du Kanban ;
- décisions prises à chaque revue ;
- difficultés rencontrées et correctifs ;
- contribution individuelle vérifiable dans Git.

## 9. Limites assumées

- Prototype pédagogique, non certifié comme dispositif médical.
- Compréhension du langage non garantie pour toute formulation.
- Catalogue thérapeutique réduit.
- Pas encore de mesures physiques SpO2, température ou fréquence cardiaque.
- Sources cliniques et protocoles botaniques à consolider.
- Migrations et observabilité encore limitées pour une V1 industrielle.

## 10. Passage vers une V1

Priorités :

1. intégrer un capteur réel ou simulateur ESP32 signé ;
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
