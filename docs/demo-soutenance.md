# Demo soutenance (75 s)

Contexte : minute 2-3 du passage vendredi (prototype live).

## Preparation

- `docker compose up --build`
- Reset mission puis connexion **Raphael** (`qwerty123`).
- Ollama est facultatif : la demonstration doit rester identique en mode
  template hors ligne.
- Ouvrir un nouveau chat avant de lancer le chronometre.

## Script

| Temps | Action | Attendu visible |
|-------|--------|-----------------|
| 0-20 s | Chat : « Elisa vomit, tousse beaucoup et a de la fievre » | Elisa identifiee comme patiente ; trois problemes lus ; plan distinct par symptome |
| 20-30 s | Montrer le rapport clinique | Origine du texte, mode extraction, options ecartees et decision issue de la base |
| 30-45 s | Dashboard : **Rupture de stock** | Tous les stocks medicaments passent a zero |
| 45-58 s | Nouveau chat : « j ai mal au crane » | Relais serre/culture si disponible, sinon protocole de surveillance |
| 58-75 s | **Crise 15 %**, puis **Rationnement** | Triage rempli et autonomie rationnee comparee a la demande |

## Phrase jury

« EIR lit chaque probleme, identifie le bon membre d equipage, puis interroge
les allergies, traitements, stocks et cultures de la base locale. Le modele
local aide a comprendre et expliquer ; seul le moteur trace choisit la
decision. »

## Secours

Si Ollama est indisponible : le mode `template` ou `rules` confirme le mode
secours prevu au cahier des charges.

Si la demonstration multi-symptomes prend trop de temps :

1. « Elisa a de la fievre et elle vomit ».
2. Montrer les deux lignes du plan.
3. Passer directement a la rupture totale puis au scenario crise.

## Questions probables du jury

- **Pourquoi ne pas laisser le LLM prescrire ?** Une sortie generative n est
  ni stable ni auditable. EIR limite le modele a la comprehension et a
  l explication.
- **Que se passe-t-il hors ligne ?** L API, la base, MQTT et l extraction par
  regles sont locaux ; Ollama est lui aussi local et reste optionnel.
- **Comment eviter une erreur medicale ?** Allergies, interactions, dose,
  stock et urgences sont controles avant affichage. Le prototype demande une
  confirmation humaine.
- **Limite principale ?** Les regles et plantes doivent etre validees par des
  professionnels avant une V1 medicale.
