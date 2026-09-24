# Capteurs et Ollama

Les constantes de la page Veille et le modele Ollama sont deux chemins distincts.
Ollama ne lit pas les capteurs. Les capteurs ne decident pas d'un medicament.

## Comment les capteurs sont faits

Il n'y a pas de branchement materiel. Pas d'ESP32, pas de sonde SpO2, pas de
thermometre. Le coach n'a pas fourni de capteur, donc la veille est un
simulateur logiciel dans `backend/app/services/surveillance.py`.

1. Au demarrage, EIR cree 40 fiches dans `watch_subjects` : les 5 membres
   nommes (Raphael, Elisa, Elsa, Jovani, Carine) et les cabines 06 a 40.
2. Un scenario ecrit des mesures synthetiques : temperature, SpO2, pouls,
   respiration. Elles sont horodatees dans `vital_samples`.
3. Un score deterministe additionne des points par constante. Le total donne
   une priorite : routine, bas, moyen, haut. Ce n'est pas un NEWS2 valide.
4. L'isolement n'est pas declenche par la fievre seule. Il faut une fievre
   associee a une desaturation, une respiration haute, ou une priorite moyenne
   ou haute.
5. Quatre zones Q1 a Q4, deux places chacune. Si une zone se remplit, elle est
   marquee fermee. Le manque de place reste visible. Les paires qui partagent
   une zone sont enregistrees dans `zone_contacts`.
6. La sortie de zone exige au moins 120 secondes et deux observations stables,
   espacees d'au moins deux secondes. Une rechute remet le compteur a zero.
   Cette duree est une convention de demonstration.
7. La page Veille trace les echantillons des dix dernieres minutes. Un trait
   jaune marque le dernier changement de niveau.

Scenarios, reserves a un compte administrateur :

| Scenario | Effet |
|---|---|
| `nominal` | Constantes stables, aucune zone occupee |
| `false-alarm` | Raphael a de la fievre, SpO2 et respiration normales : pas d'isolement |
| `contamination` | 6 personnes sur 40 se degradent et entrent en zone |
| `slow-burn` | Elisa se degrade sur dix minutes, la courbe montre le changement de niveau |

Declencher la crise 15 % depuis le tableau de bord lance aussi le scenario
`contamination`. Le chat Medichat ne modifie aucune de ces mesures.

La voix du chat n'est pas un capteur. C'est la synthese vocale du navigateur
(`speechSynthesis`, voix francaise si elle est installee). Elle lit le message
de bienvenue et les reponses. Elle n'envoie rien a Ollama.

Le branchement d'une vraie sonde (ESP32, MQTT) reste une evolution. Le
simulateur montre deja le contrat : mesure, horodatage, score, zone.

## A quoi sert Ollama

Ollama tourne sur la machine hote, pas dans le conteneur API. Le modele de
demonstration est `llama3.2:3b`. L'API l'appelle en HTTP local.

| Variable | Valeur de demonstration |
|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | `llama3.2:3b` |
| `OLLAMA_EXTRACT_SYMPTOMS` | `true` |

Deux appels, et seulement deux :

1. **Extraction** (`message_understanding.refine_with_ollama`). Le modele recoit
   le message et doit repondre en JSON, avec des libelles copies dans un
   catalogue ferme. Un libelle hors catalogue est ignore. Si Ollama ne repond
   pas, l'extraction par regles locales reste seule.
2. **Reformulation** (`ollama_client.reformulate_with_ollama`). Le modele recoit
   le JSON deja decide par le moteur de regles. Il le dit en francais simple.
   Il ne choisit ni molecule, ni dose, ni culture. S'il tombe, un texte
   modele hors ligne est affiche. L'interface marque alors « Reponse securisee
   hors ligne ».

Le tableau de bord interroge `GET /api/tags` sur Ollama. S'il repond, le mode
affiche est `rules+ollama`. Sinon : `rules-offline`.

Ollama ne fait pas :

- prescrire un medicament absent du JSON ;
- calculer le score des constantes ;
- decider une quarantaine ;
- decrire une fermentation, une extraction ou une purification.

Installation locale :

```powershell
ollama pull llama3.2:3b
ollama serve
```

Sans cette etape, EIR reste utilisable. Les regles, les stocks, la veille et
la voix du navigateur ne dependent pas du modele.
