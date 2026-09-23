# Plan d'amélioration technique orienté notation

Objectif : gagner des points visibles au jury, pas ajouter des fonctionnalités
qui ne pourront pas être démontrées proprement.

## Priorité 1 — sécuriser la démonstration

Gain estimé : fort sur qualité du prototype et pitch.

- Ajouter un script `demo-check` qui vérifie API, PostgreSQL, MQTT, stock,
  Ollama et scénario principal avant le passage.
- Préparer un jeu de données immuable et une seule commande de reset.
- Mesurer le temps de réponse du chat avec et sans Ollama.
- Enregistrer une vidéo de secours locale de 45 à 60 secondes.
- Tester la démonstration complète trois fois après un redémarrage Docker.

Critère de réussite : aucune action de la démonstration ne dépend d'Internet et
le scénario principal tient en moins de 75 secondes.

## Priorité 2 — dialogue clinique de clarification

Gain estimé : fort sur innovation et crédibilité.

Avant toute proposition ambiguë, EIR doit demander :

- localisation exacte ;
- intensité sur 10 ;
- durée ;
- symptômes associés ;
- signes vitaux si disponibles.

Le moteur doit retourner un état `needs_clarification` avec les champs manquants
au lieu de choisir un traitement par défaut.

Critère de réussite : « je me sens mal » ne produit jamais directement une
molécule ; « mal de tête 3/10 depuis ce matin, sans vomissement » peut être
évalué.

## Priorité 3 — preuve matérielle minimale

Gain estimé : fort sur innovation/différenciation.

Option réaliste :

- ESP32 ou capteur simulé envoyant température et fréquence cardiaque sur MQTT ;
- EIR affiche la dernière mesure avec horodatage et état « mesure simulée » ou
  « capteur réel » ;
- une température élevée devient un élément de contexte, pas une prescription
  automatique.

Un seul capteur bien intégré vaut mieux que plusieurs capteurs factices.

## Priorité 4 — règles médicales versionnées et sourcées

Gain estimé : fort sur maintenabilité et Q&A.

- Sortir indications, doses, contre-indications et protocoles du code Python vers
  un catalogue YAML/JSON versionné.
- Ajouter pour chaque règle : source, version, date, niveau de confiance.
- Séparer clairement démonstration pédagogique et recommandation validée.
- Retirer ou marquer « expérimental » tout relais botanique non sourcé.

Critère de réussite : le jury peut ouvrir une règle et voir pourquoi elle existe
sans lire le moteur Python.

## Priorité 5 — résilience démontrable

Gain estimé : moyen à fort sur résilience.

- Ajouter des healthchecks API, PostgreSQL, MQTT et Ollama dans le dashboard.
- Tester explicitement : Ollama coupé, MQTT coupé, redémarrage API, base
  temporairement indisponible.
- Ajouter sauvegarde et restauration PostgreSQL automatisées.
- Remplacer `create_all` seul par des migrations Alembic versionnées.
- Exposer quelques métriques : latence, erreurs, décisions template/Ollama,
  autonomie, alertes.

## Priorité 6 — sécurité du prototype

Gain estimé : moyen sur qualité et Q&A.

- Générer un secret JWT hors dépôt au premier démarrage.
- Changer les mots de passe de démonstration avant une présentation publique.
- Ajouter expiration de session visible et journal des accès administrateur.
- Limiter la taille et le type des images/descripteurs faciaux.
- Ajouter un reverse proxy HTTPS uniquement si cela reste stable.

## Priorité 7 — qualité frontend

Gain estimé : moyen sur prototype et pitch.

- Afficher clairement le membre réellement pris en charge quand il diffère du
  profil actif.
- Permettre de confirmer chaque traitement d'un plan multi-symptômes, pas
  uniquement la première recommandation.
- Ajouter un état de chargement et un délai maximal visible pour Ollama.
- Afficher « règle locale », « enrichi par Ollama » ou « mode dégradé » avec une
  explication accessible.
- Vérifier 375 px et 900 px sans débordement.

## Ce qu'il ne faut pas ajouter avant la soutenance

- Un nouveau modèle 3D complexe.
- Un diagnostic libre généré par le LLM.
- Une dizaine de capteurs non fiables.
- Grafana uniquement pour faire joli.
- Une nouvelle base ou un nouveau framework.
- Des fonctionnalités médicales non testées.

## Ordre conseillé si le temps est très court

1. PDF et PowerPoint finalisés.
2. Script de prévol et vidéo de secours.
3. Questions de clarification.
4. Une intégration ESP32/MQTT.
5. Sources des règles et plantes.
6. Healthchecks et sauvegarde.
