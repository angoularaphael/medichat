# Cahier des charges — EIR

**Workshop national EPSI B3 — Horizon 2080**  
**Pilier : HumanTech et HealthTech spatiales**  
**Vaisseau : patch Yggdrasil (couplage avec MIMIR, pilier DeepTech)**  
**Version : prototype V0.5 — mise à jour du 23 septembre 2026**

---

## 1. Identité du projet

| Élément | Contenu |
|--------|---------|
| Nom | **EIR** (déesse nordique de la guérison) |
| Slogan pitch | Pharmacie de bord qui soigne en sécurité et fait durer les médicaments sur toute la mission |
| Problème ESA 2080 | Aucun réapprovisionnement terrestre ; stock fini ; pas d’assistance médicale immédiate ; risque d’épidémie en milieu confiné |
| Crise officielle du sujet | **15 % de l’équipage contaminé** — triage, quarantaine, rationnement |
| Positionnement | Système d’**aide à la décision** (prototype de démonstration, **pas** un dispositif médical certifié) |

---

## 2. Idée

EIR est la **pharmacie intelligente embarquée** du vaisseau interstellaire. Elle centralise les dossiers de l’équipage, le stock de médicaments (quantités réelles, non réapprovisionnables), et guide le personnel via une interface conversationnelle **100 % hors ligne**.

Le cœur n’est pas « une IA qui prescrit », mais un **moteur de règles médicales déterministe** (allergies, interactions, doses, urgence) que l’interface (LLM local) explique en langage clair. En crise, EIR **trie** les patients, **propose** quarantaine et rationnement, et **quantifie** combien de jours d’autonomie médicale restent selon la politique choisie.

---

## 3. Solution fonctionnelle

### 3.1 Modules

1. **Dossiers équipage** — Identité, âge, allergies, antécédents, traitements en cours (PostgreSQL).
2. **Pharmacie embarquée** — Catalogue médicaments (substance, classe thérapeutique, stock, unité, dose max), mouvements de stock (sortie, perte, rationnement).
3. **Moteur de règles** — Évalue une demande de soin : contre-indications, interactions, stock disponible, niveau d’urgence ; sortie structurée (options écartées + raison, recommandation, escalade humaine si grave).
4. **Graphe de substitution** — Si médicament A indisponible ou contre-indiqué, recherche d’alternatives dans la même indication (autre classe si besoin), avec traçabilité.
5. **Compréhension conversationnelle** — segmentation des clauses, négations,
   détection de l'équipier concerné et extraction multi-symptômes par règles
   locales ; Ollama peut compléter l'extraction dans un catalogue fermé.
6. **Réponse structurée par symptôme** — chaque problème détecté est évalué
   séparément contre la base ; le LLM reformule uniquement le résultat.
7. **Identification et continuité** — authentification JWT, rôles,
   reconnaissance faciale locale optionnelle et conversations persistantes.
8. **Simulateur d’épidémie** — scénario 15 % sur équipage simulé et triage.
9. **Indicateur d’autonomie** — jours d’autonomie par médicament et comparaison
   « à la demande » / « rationnement + quarantaine ».
10. **Pharmacie vivante** — plantes et cultures biologiques proposées seulement
    lorsque les médicaments utiles sont réellement épuisés. EIR explique
    l'origine botanique ou microbienne du médicament essentiel et le relais de
    confort. Il ne décrit pas une fabrication (fermentation, extraction,
    purification). Détail : `docs/pharmacie-vivante.md`.
11. **Journal des décisions** — historique horodaté pour audit.

### 3.2 Flux principal (nominal)

1. L’astronaute s’identifie (ou sélection de profil en démo).
2. Il décrit ses symptômes via le chat.
3. Le système détecte le sujet, les clauses, négations et problèmes distincts.
4. Ollama local peut enrichir l'extraction sans pouvoir ajouter librement une
   prescription.
5. Chaque problème interroge le moteur de règles avec le profil, les traitements,
   les interactions, les stocks et cultures de la base.
6. Le système affiche ce qu'il a compris, les options écartées et un plan par
   symptôme.
7. Validation humaine simulée (« confirmer » ou protocole d'urgence).

### 3.3 Flux crise (15 %)

1. Déclenchement épidémie : X % de l’équipage passe en état « malade » (données simulées ou profils marqués).
2. **Triage** : gravité, besoins en ressources, ordre de prise en charge.
3. Stock et autonomie **chutent** ; affichage avant/après chiffré.
4. Activation **plan de rationnement et quarantaine** : recalcul autonomie, file d’attente, cabines isolées (statut logique).
5. Si stock à zéro : substitution via graphe ou protocole non médicamenteux documenté.

### 3.4 Mode hors ligne

- Aucune dépendance à Internet ou à une API pharmacie terrestre.
- FastAPI, React, PostgreSQL, Mosquitto et Ollama sur le réseau local du
  vaisseau avec Docker Compose.
- Données médicales stockées et sauvegardées localement (ASRBD : sauvegarde, accès restreint).
- Si Ollama ne répond plus, extraction déterministe et réponses template.

### 3.5 Interconnexion vaisseau (Axe 3 jury)

Contrat minimal **MQTT** (à aligner avec MIMIR et les autres équipes) :

| Topic (proposition) | Direction | Contenu |
|---------------------|-----------|---------|
| `yggdrasil/eir/alert/crisis` | EIR publie | `{ "level": "epidemic", "sick_ratio": 0.15, "autonomy_days": 9 }` |
| `yggdrasil/eir/stock/low` | EIR publie | `{ "drug_id": "...", "remaining_units": 0 }` |
| `yggdrasil/mimir/security/infirmary` | MIMIR publie | alertes réseau infirmerie (optionnel démo croisée) |

EIR peut **écouter** une alerte MIMIR (données de stock falsifiées) pour montrer la cohérence du vaisseau.

---

## 4. Technologies envisagées

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Base de données | **PostgreSQL** | Patients, médicaments, stocks, journal, règles métier |
| API / logique | **Node.js** ou **Python (FastAPI)** | Moteur de règles, simulateur SIR, API REST |
| Interface | **React** (ou Vue) | Dashboard stock, triage, chat, crise |
| IA interface | **Ollama** + modèle léger | Dialogue ; pas de décision médicale seule |
| Moteur de règles | Code applicatif (JSON/YAML règles + tests) | Décisions explicables |
| Bus vaisseau | **MQTT** (ex. Mosquitto) | Échange avec MIMIR / autres piliers |
| Conteneurisation | **Docker Compose** | Reproductibilité labo, démo vendredi |
| Monitoring (option) | Grafana + métriques custom | Stocks, autonomie, patients en attente |
| Sécurité | Rôles DB, HTTPS local si reverse proxy | Données santé ; travail ASRBD |

**À éviter pour le sprint :** ERP lourd (Dolibarr, etc.), dépendance à un matériel non validé par le coach.

**Référence données :** liste inspirée OMS médicaments essentiels (version réduite pour la démo) ; hypothèses de contagion et consommation documentées dans le dossier PDF final.

---

## 5. Objectifs et critères de succès

### 5.1 Alignement grille locale (extraits)

- **Pertinence** : stock fini, crise 15 %, impact vie humaine à bord.
- **Prototype** : chat + règles + crise jouable en direct en moins d’une minute.
- **Innovation** : graphe de substitution + simulateur d’autonomie (pas un MedBox générique).
- **Résilience** : offline, journal, escalade humaine, gestion stock à zéro.
- **Doc et Q&A** : règles et cas de test reproductibles.

### 5.2 Démo soutenance (minutes 2-3, environ 60 s)

1. Raphael signale : « Elisa vomit, tousse et a de la fièvre » : patient et
   trois symptômes identifiés, plan séparé issu de la base.
2. **Rupture totale des médicaments** : relais biologique ou protocole de bord.
3. **Crise 15 %** : triage et baisse d'autonomie visibles.
4. **Rationnement / quarantaine** : comparaison chiffrée des deux politiques.

### 5.3 Périmètre par priorité

**Indispensable (mercredi soir / jeudi)**

- Schéma PostgreSQL + jeu de données démo (equipage, 10-20 médicaments).
- Moteur de règles avec au moins : allergie, stock insuffisant, urgence simple.
- Interface chat branchée sur Ollama + API règles.
- Scénario crise 15 % + triage basique.
- Journal des décisions.

**Important**

- Graphe de substitution (2-3 chaînes démo).
- Simulateur SIR + comparaison deux politiques (courbes ou chiffres).
- Publication MQTT crise / stock bas.

**Bonus**

- Reformulation LLM des raisons métier.
- Lien démo avec MIMIR (alerte sécurité infirmerie).
- Grafana ou tableau de bord unifié Yggdrasil.

---

## 6. Cas de test médicaux (minimum 20, à étendre)

Numéro | Entrée | Attendu
------|--------|--------
T01 |Allergie ibuprofène + mal de tête | AINS écartés ; paracétamol si stock
T02 |Allergie + demande ibuprofène | Refus explicite
T03 |Interaction connue (à définir dans le catalogue) | Alerte interaction
T04 |Stock paracétamol = 0 | Substitution ou protocole alternatif
T05 |Symptômes graves (douleur thoracique simulée) | Escalade médecin, pas auto-traitement
T06 |Patient inconnu | Refus ou profil générique limité
T07 |Dose demandée au-dessus du max | Refus dose
T08 |Crise 15 % déclenchée | Triage non vide, stock diminue
T09 |Rationnement activé | Autonomie globale augmente vs sans plan
T10 |Deux patients même médicament stock faible | Priorisation triage

*(Compléter T11-T20 dans `docs/cas-de-test.md` avant jeudi.)*

---

## 7. Organisation des tâches (équipe type 4 ASRBD + 1 Dev)

| Rôle | Responsabilités EIR |
|------|---------------------|
| ASRBD 1 | PostgreSQL : schéma, données démo, sauvegardes, droits |
| ASRBD 2 | Docker Compose, MQTT, réseau offline, déploiement Ollama |
| ASRBD 3 | Sécurité accès données santé, reverse proxy si besoin |
| ASRBD 4 | Monitoring / logs, documentation infra, tests déploiement |
| Dev | API moteur de règles, simulateur, frontend chat + dashboard crise |

**Kanban** : colonnes A faire / En cours / Revue / Terminé ; mise à jour quotidienne (suivi individuel 20 pts).

**Livrables workshop (jeudi)** — à intégrer dans le dossier groupe :

- `Workshop2026-B3-G<n>-Dossier.pdf` (ce document enrichi + architecture + organisation).
- `Workshop2026-B3-G<n>-Pres.pptx`.
- `Workshop2026-B3-G<n>-Code.zip` ou dépôt GitHub.

---

## 8. Architecture logique (schéma)

```
[Astronaute] -> [UI React : Chat + Dashboard]
                      |
                      v
              [API EIR : règles + SIR + triage]
                 /    |     \
                v     v      v
         [PostgreSQL] [Ollama] [MQTT client]
                              |
                              v
                    [Bus Yggdrasil / MIMIR]
```

---

## 9. Risques et parades

| Risque | Parade |
|--------|--------|
| LLM invente un traitement | Le LLM ne lit que la sortie du moteur de règles ; pas de prescription libre |
| Démo Ollama lente | Réponses courtes ; cache ; scénarios scriptés en secours |
| Scope trop large avec MIMIR | Gel des bonus EIR si retard ; prioriser indispensable |
| Jury médical sceptique | Vocabulaire « aide à la décision », cas de test, règles affichables |

---

## 10. Évolutions V1 (après workshop)

- Intégration capteurs réels (SpO2, température) type MedBox.
- Modèle SIR calibré sur données ESA / littérature.
- Synchronisation OfflineSpace (file d’attente sync Terre).
- Multi-langue équipage.

---

## 11. Validation mardi — checklist coach

- [x] Pilier HealthTech et positionnement aide à la décision.
- [x] Docker, PostgreSQL, Mosquitto et fallback sans Ollama.
- [x] Moteur de règles, profils, conversations, stocks, crise et cultures.
- [x] Contrat MQTT MIMIR implémenté côté EIR.
- [x] Tests automatisés backend (59 réussis au 23 septembre 2026).
- [ ] Rapport final exporté en PDF au nom réglementaire.
- [ ] Support final exporté en PPTX au nom réglementaire.
- [ ] Kanban et répartition réelle des contributions ajoutés au dossier.
- [ ] Sources médicales des règles et plantes ajoutées au dossier.

---

*Document de travail — à faire évoluer après retour coach lundi/mardi.*
