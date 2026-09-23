# MIMIR — cahier des charges developpeur

Projet : securisation et autonomie du reseau de capsule, vaisseau Yggdrasil.  
Pilier : DeepTech, cas CyberSpace et OfflineSpace.  
Lien EIR : bus MQTT local. EIR reste la pharmacie ; MIMIR reste le reseau.

## Note honnete de l'etat actuel

Le document et les deux schemas existent. Le laboratoire pfSense, Suricata et la messagerie locale ne sont pas encore un prototype demontrable dans le depot.

| Axe local | Note actuelle | Potentiel si le lab tourne |
|---|---:|---:|
| Pertinence et impact | 4,2 / 5 | 4,7 / 5 |
| Faisabilite et prototype | 1,5 / 5 | 4,2 / 5 |
| Innovation et complexite | 2,2 / 4 | 3,4 / 4 |
| Perennite et resilience | 1,8 / 4 | 3,5 / 4 |
| Documentation et Q&A | 1,0 / 2 | 1,7 / 2 |
| Total | 10,7 / 20 | 17,5 / 20 |

Aujourd'hui, MIMIR est un bon sujet mais un prototype incomplet. Le jury notera la demonstration, pas le schema. Le couplage avec EIR est le principal levier de differenciation : une alerte Suricata doit apparaitre dans le journal medical.

## Ce qui est volontairement hors perimetre

Aucun script de cle USB, de scraping de donnees reelles ou d'exfiltration n'est a developper. Pour la demonstration, `tools/lab-traffic-marker.py` envoie seulement le texte fictif `LAB_DUMMY_NOT_REAL_DATA` avec l'en-tete `X-Yggdrasil-Lab: exfil-demo`. Les regles `infra/suricata/yggdrasil-lab.rules` detectent ce marqueur.

## Reseau de laboratoire

| Hote | IP | Role |
|---|---|---|
| pfSense | passerelle LAN | DHCP, DNS local, filtrage, miroir de port |
| Windows 10 | 192.168.10.20 | Poste operateur et interface EIR |
| Kali | 192.168.10.100 | Mosquitto, recepteur du marqueur, Suricata ou console |
| Objets IoT | 192.168.10.x | Capteurs publies uniquement en local |

LAN : `192.168.10.0/24`. Aucune dependance Internet pour les echanges internes.

## Cas 1 — detection

1. Le poste Windows envoie le marqueur vers Kali.
2. pfSense copie le flux vers Suricata.
3. Suricata leve l'alerte `sid:2080001` ou `sid:2080002`.
4. pfSense bloque ensuite ce flux de demonstration.
5. Kali publie sur `yggdrasil/mimir/security/infirmary`.
6. EIR enregistre l'alerte et l'affiche dans le journal administrateur.

Critere de reussite : une capture Suricata, une regle pfSense et la meme alerte visible dans EIR.

## Cas 2 — coupure du lien Terre

1. Desactiver la passerelle WAN de pfSense.
2. Verifier que DHCP et DNS internes repondent encore.
3. Windows, Kali et EIR continuent de publier sur Mosquitto local.
4. Si le broker est coupe, EIR ecrit les messages dans `backend/data/offline_outbox.jsonl`.
5. Au retour du broker, rejouer cette file. Le lien Terre n'est pas necessaire.

Critere de reussite : le chat EIR et un message MQTT restent possibles pendant que le WAN est coupe.

## Configuration pfSense a livrer

- Interface LAN `192.168.10.1/24`.
- DHCP : plage `192.168.10.50` a `192.168.10.150`, reservation `.20` et `.100`.
- DNS Resolver actif, domaines locaux uniquement.
- Regle LAN : autoriser MQTT `1883` vers Kali.
- Regle de demonstration : bloquer le flux marque `exfil-demo` apres capture.
- Port miroir vers l'interface d'ecoute Suricata.
- Scenario 2 : desactiver WAN sans toucher LAN.

Exporter la configuration XML et la deposer dans le livrable, sans mot de passe reel.

## Ordre de realisation

1. Faire communiquer Windows et Kali en ping et MQTT sans Internet.
2. Lancer le marqueur et obtenir l'alerte Suricata.
3. Bloquer ce flux dans pfSense.
4. Publier l'alerte vers EIR et la montrer au journal.
5. Couper le WAN et refaire un echange local.
6. Montrer la file d'attente EIR si MQTT tombe.
7. Preparer trois captures et un scenario oral de 60 secondes.

## Phrase de soutenance

MIMIR empeche une fuite de donnees de capsule et maintient le dialogue interne quand la Terre disparait. EIR recoit l'alerte et continue de soigner avec les ressources locales.
