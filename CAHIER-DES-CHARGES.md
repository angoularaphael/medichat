# Cahier des charges — EIR

**Workshop national EPSI B3 — Horizon 2080**  
**Pilier : HumanTech et HealthTech spatiales**  
**Vaisseau : patch Yggdrasil (couplage avec MIMIR, pilier DeepTech)**  
**Version : validation mardi (Sprint 2) — évolutive jusqu’à jeudi**

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
5. **Interface conversationnelle** — Ollama (modèle léger) : collecte symptômes en texte libre, appelle le moteur de règles, **reformule** uniquement la décision (ne décide pas seul).
6. **Simulateur d’épidémie** — Modèle simple (type SIR) sur équipage simulé ; déclenchement manuel « crise 15 % » pour la démo.
7. **Indicateur d’autonomie** — Pour chaque médicament critique et globalement : **jours d’autonomie restants** ; comparaison politique « à la demande » vs « rationnement + quarantaine ».
8. **Journal des décisions** — Historique horodaté pour audit et soutenance (qui, quoi, pourquoi, stock avant/après).

### 3.2 Flux principal (nominal)

1. L’astronaute s’identifie (ou sélection de profil en démo).
2. Il décrit ses symptômes via le chat.
3. Le LLM structure la demande (symptômes, durée) et interroge le moteur de règles avec le profil + stock.
4. Le système affiche les options écartées (ex. AINS si allergie ibuprofène) et une **proposition** (ex. paracétamol si stock OK).
5. Validation humaine simulée (« confirmer » / « escalade médecin de bord »).

### 3.3 Flux crise (15 %)

1. Déclenchement épidémie : X % de l’équipage passe en état « malade » (données simulées ou profils marqués).
2. **Triage** : gravité, besoins en ressources, ordre de prise en charge.
3. Stock et autonomie **chutent** ; affichage avant/après chiffré.
4. Activation **plan de rationnement et quarantaine** : recalcul autonomie, file d’attente, cabines isolées (statut logique).
5. Si stock à zéro : substitution via graphe ou protocole non médicamenteux documenté.

### 3.4 Mode hors ligne

- Aucune dépendance à Internet ou à une API pharmacie terrestre.
- Ollama et PostgreSQL sur le réseau local du vaisseau (Docker Compose ou services locaux).
- Données médicales stockées et sauvegardées localement (ASRBD : sauvegarde, accès restreint).

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

1. Profil **Elisa**, allergique ibuprofène : mal de tête -> options écartées + paracétamol proposé.
2. Bouton **Crise 15 %** : triage visible, autonomie passe (ex. 30 j -> 9 j).
3. Activation **rationnement / quarantaine** : autonomie remonte (chiffres mesurés en amont).
4. **Stock paracétamol à zéro** : alternative ou protocole non médicamenteux + journal.

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

- [ ] Pilier HealthTech validé, pas de doublon MedBox identique dans la classe.
- [ ] Matériel : Docker OK sur les postes, Ollama installé, MQTT broker.
- [ ] Périmètre indispensable validé pour 48 h de prototype.
- [ ] Format d’interconnexion avec MIMIR (topics MQTT) acté.

---

*Document de travail — à faire évoluer après retour coach lundi/mardi.*
