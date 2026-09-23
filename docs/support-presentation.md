# Support de présentation — contenu à intégrer dans le PPTX

Nom réglementaire à l'export : `Workshop2026-B3-G<n>-Pres.pptx`

Règle visuelle : une idée principale par diapositive, très peu de texte, grandes
captures lisibles et aucun écran de code pendant les cinq minutes.

## Diapositive 1 — Accroche et équipe (0:00 à 0:40)

Titre : **EIR — quand la Terre ne peut plus livrer ni répondre**

Phrase :

> In deep space, a wrong medical decision is dangerous. Running out of medicine
> is inevitable. EIR helps the crew manage both.

Ajouter les membres avec une phrase anglaise courte et leur rôle réel.

Visuel : logo EIR et une vue du vaisseau ou du dashboard.

## Diapositive 2 — Problème ESA 2080 (0:40 à 1:20)

Trois éléments seulement :

- assistance terrestre non immédiate ;
- médicaments non renouvelables ;
- crise sanitaire en milieu confiné.

Phrase orale :

> Notre problème n'est pas seulement de diagnostiquer. Il faut soigner sans
> halluciner et préserver les ressources pendant plusieurs décennies.

## Diapositive 3 — Solution différenciante (1:20 à 2:00)

Schéma à quatre blocs :

```text
Message équipage
   -> compréhension locale
   -> règles + base du vaisseau
   -> décision expliquée et tracée
```

À dire :

- Ollama comprend et reformule.
- Le moteur déterministe décide.
- La base fournit profil, interactions, stock et cultures.
- L'humain confirme.

## Diapositive 4 — Démonstration (2:00 à 3:05)

Ne pas surcharger la diapositive : afficher uniquement trois captures ou
effectuer la démonstration live.

1. Elisa : vomissements, toux et fièvre.
2. Rupture totale : relais biologique/protocole.
3. Crise 15 % : triage et autonomie rationnée.

Phrase de transition :

> Une phrase, trois problèmes, trois réponses vérifiables dans la base locale.

## Diapositive 5 — Architecture et preuves (3:05 à 4:00)

Architecture simplifiée :

```text
React -> FastAPI -> PostgreSQL
             |-> Ollama local
             `-> MQTT Yggdrasil
```

Preuves à afficher :

- fonctionnement hors ligne ;
- 59 tests backend ;
- authentification et rôles ;
- journal d'audit ;
- fallback sans Ollama ;
- intégration MIMIR.

## Diapositive 6 — Impact et limites (4:00 à 4:35)

Impact :

- évite une contre-indication ;
- fait durer les stocks ;
- priorise l'équipage en crise ;
- conserve une capacité locale quand la Terre est absente.

Limites assumées :

- prototype non médicalement certifié ;
- catalogue réduit ;
- validation clinique et capteurs à ajouter.

Dire les limites augmente la crédibilité : ne jamais présenter le projet comme
un médecin autonome.

## Diapositive 7 — Pitch final (4:35 à 5:00)

Texte suggéré :

> Si l'ESA ne devait embarquer qu'une seule solution, elle devrait choisir EIR
> parce que chaque autre système dépend d'un équipage vivant et soigné. EIR
> fonctionne localement, explique ses choix et transforme un stock médical fini
> en autonomie mesurable.

Finir sur l'écran d'autonomie ou le rapport clinique, pas sur une diapositive
« merci » vide.

## Questions/réponses à préparer

### « Votre IA peut-elle halluciner ? »

Elle peut mal reformuler ou manquer un symptôme, mais elle ne peut pas inventer
une molécule dans la décision. Le moteur n'accepte que son catalogue local et
contrôle profil, interactions et stock.

### « Est-ce un dispositif médical ? »

Non. C'est une preuve de concept d'aide à la décision. Une V1 nécessite
validation clinique, certification et essais.

### « Pourquoi des plantes ? »

Elles illustrent une ressource renouvelable du vaisseau. Elles ne sont utilisées
qu'après épuisement du stock utile et doivent être validées cliniquement.

### « Que se passe-t-il si Ollama tombe ? »

Le catalogue local, les règles, la base et les templates continuent de
fonctionner. La démonstration peut être faite sans modèle.

### « Où est l'innovation ? »

Dans la combinaison compréhension multi-problèmes, décision explicable,
autonomie de stock, pharmacie vivante et coordination MQTT avec le vaisseau.
